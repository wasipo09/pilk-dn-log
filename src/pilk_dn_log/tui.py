"""Textual TUI for Pilk DN Log."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Static, Label, Input, Select,
    DataTable, RichLog
)
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual import on
from rich.text import Text
from rich.style import Style
from datetime import datetime
from typing import Optional
import asyncio

from .positions import Position, PositionManager
from .binance_api import get_binance_api


class NewPositionModal(ModalScreen):
    """Modal for adding a new position."""
    
    CSS = """
    NewPositionModal {
        align: center middle;
    }
    
    NewPositionModal > Container {
        width: 60;
        height: 22;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .row {
        height: 3;
        margin-bottom: 1;
    }
    
    .row Input {
        width: 30;
    }
    
    .row Select {
        width: 20;
    }
    
    .buttons {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    
    Button {
        margin: 0 2;
    }
    
    .error {
        color: $error;
        text-align: center;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("🆕 NEW POSITION", classes="title")
            yield Container(
                Label("Expiry (e.g., 27FEB):"),
                Input(placeholder="27FEB", id="expiry"),
                classes="row"
            )
            yield Container(
                Label("Type:"),
                Select(
                    options=[("CALL", "call"), ("PUT", "put")],
                    id="opt_type",
                    allow_blank=False
                ),
                classes="row"
            )
            yield Container(
                Label("Strike:"),
                Input(placeholder="70000", id="strike"),
                classes="row"
            )
            yield Container(
                Label("Size (BTC):"),
                Input(placeholder="0.1", id="size"),
                classes="row"
            )
            yield Container(
                Label("Entry Delta:"),
                Input(placeholder="0.25", id="entry_delta"),
                classes="row"
            )
            yield Container(
                Label("Band (rehedge threshold):"),
                Input(placeholder="0.0038", id="band"),
                classes="row"
            )
            yield Label("", id="error", classes="error")
            with Horizontal(classes="buttons"):
                yield Button("✓ Add", variant="success", id="add")
                yield Button("✗ Cancel", variant="error", id="cancel")
    
    @on(Button.Pressed, "#add")
    def on_add(self):
        try:
            expiry = self.query_one("#expiry", Input).value.strip().upper()
            opt_type = self.query_one("#opt_type", Select).value
            strike = float(self.query_one("#strike", Input).value)
            size = float(self.query_one("#size", Input).value)
            entry_delta = float(self.query_one("#entry_delta", Input).value)
            band = float(self.query_one("#band", Input).value)
            
            if not expiry or not strike or not size:
                raise ValueError("Missing fields")
            
            # Create position
            manager = PositionManager()
            pos_id = PositionManager.generate_id()
            name = PositionManager.make_contract_name(expiry, strike, opt_type)
            binance_symbol = PositionManager.make_binance_symbol(expiry, strike, opt_type)
            
            # Calculate initial hedge
            delta_exposure = size * entry_delta
            if opt_type == 'call':
                initial_hedge = -delta_exposure
            else:
                initial_hedge = delta_exposure
            
            now = datetime.now().isoformat()
            pos = Position(
                id=pos_id,
                name=name,
                option_type=opt_type,
                strike=strike,
                expiry=expiry,
                size=size,
                entry_delta=entry_delta,
                band=band,
                current_hedge=initial_hedge,
                created_at=now,
                updated_at=now,
                binance_symbol=binance_symbol
            )
            
            manager.add_position(pos)
            self.dismiss(pos)
            
        except ValueError as e:
            self.query_one("#error", Label).update(f"❌ Invalid input: {e}")
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self):
        self.dismiss(None)


class PositionDetailScreen(Screen):
    """Detailed view of a single position."""
    
    CSS = """
    .header {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .stats {
        height: auto;
        margin-bottom: 1;
    }
    
    .stat-row {
        height: 1;
    }
    
    .actions {
        align: center middle;
        height: 3;
    }
    
    Button {
        margin: 0 1;
    }
    
    .alert {
        color: $warning;
        text-align: center;
        margin: 1;
    }
    
    .safe {
        color: $success;
        text-align: center;
        margin: 1;
    }
    """
    
    position: reactive[Optional[Position]] = reactive(None)
    
    def __init__(self, position: Position):
        super().__init__()
        self.position = position
        self.manager = PositionManager()
        self.api = get_binance_api(mock=True)  # Use mock for now
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Label("", id="title", classes="header")
            with Container(classes="stats"):
                yield Label("", id="stats")
            yield Label("", id="status", classes="safe")
            with Horizontal(classes="actions"):
                yield Button("🔄 Refresh Delta", variant="primary", id="refresh")
                yield Button("✏️ Manual Update", variant="warning", id="manual")
                yield Button("✗ Close Position", variant="error", id="close")
                yield Button("← Back", id="back")
        yield Footer()
    
    def on_mount(self):
        self._update_display()
    
    def _update_display(self):
        if not self.position:
            return
        
        pos = self.position
        self.query_one("#title", Label).update(
            f"📊 {pos.name} ({pos.option_type.upper()})"
        )
        
        stats = f"""Strike: ${pos.strike:,} | Size: {pos.size} BTC
Entry Delta: {pos.entry_delta:.4f} | Band: {pos.band:.5f}
Current Hedge: {pos.current_hedge:+.5f} BTC
Rehedges: {pos.rehedge_count}
Binance: {pos.binance_symbol or 'N/A'}"""
        
        self.query_one("#stats", Label).update(stats)
    
    @on(Button.Pressed, "#refresh")
    async def on_refresh(self):
        """Fetch live delta from Binance."""
        if not self.position or not self.position.binance_symbol:
            self.query_one("#status", Label).update("❌ No Binance symbol configured")
            return
        
        self.query_one("#status", Label).update("⏳ Fetching delta...")
        
        try:
            delta = await self.api.get_option_delta(self.position.binance_symbol)
            if delta is not None:
                needs_rehedge, amount, action = self.position.check_rehedge(delta)
                
                if needs_rehedge:
                    self.query_one("#status", Label).update(
                        f"🚨 REHEDGE NEEDED\n"
                        f"Current Δ: {delta:.4f} | {action} {amount:.4f} BTC",
                        classes="alert"
                    )
                else:
                    self.query_one("#status", Label).update(
                        f"✅ SAFE\nCurrent Δ: {delta:.4f}",
                        classes="safe"
                    )
            else:
                self.query_one("#status", Label).update("❌ Could not fetch delta")
        except Exception as e:
            self.query_one("#status", Label).update(f"❌ Error: {e}")
    
    @on(Button.Pressed, "#manual")
    def on_manual(self):
        """Manually input delta and apply rehedge."""
        # For now, use Input modal - could be enhanced
        self.app.push_screen("manual_delta", callback=self._apply_manual_delta)
    
    def _apply_manual_delta(self, delta_str: str):
        try:
            delta = float(delta_str)
            needs_rehedge, amount, action = self.position.check_rehedge(delta)
            
            if needs_rehedge:
                self.query_one("#status", Label).update(
                    f"🚨 REHEDGE: {action} {amount:.4f} BTC",
                    classes="alert"
                )
                # After user confirms they did it:
                # Update hedge position
                target = self.position.calculate_target_hedge(delta)
                diff = target - self.position.current_hedge
                self.position.current_hedge = target
                self.position.rehedge_count += 1
                self.position.updated_at = datetime.now().isoformat()
                self.manager.update_position(self.position)
                self._update_display()
            else:
                self.query_one("#status", Label).update(
                    f"✅ SAFE (Δ={delta:.4f})",
                    classes="safe"
                )
        except ValueError:
            pass
    
    @on(Button.Pressed, "#close")
    def on_close(self):
        """Close and archive this position."""
        self.manager.close_position(self.position.id)
        self.app.pop_screen()
    
    @on(Button.Pressed, "#back")
    def on_back(self):
        self.app.pop_screen()


class ManualDeltaModal(ModalScreen):
    """Modal for manually entering delta."""
    
    def compose(self) -> ComposeResult:
        with Container():
            yield Label("Enter current delta:")
            yield Input(placeholder="0.25", id="delta")
            with Horizontal():
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")
    
    @on(Button.Pressed, "#ok")
    def on_ok(self):
        delta = self.query_one("#delta", Input).value
        self.dismiss(delta)
    
    @on(Button.Pressed, "#cancel")
    def on_cancel(self):
        self.dismiss(None)


class MainScreen(Screen):
    """Main dashboard showing all positions."""
    
    CSS = """
    .title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    
    DataTable {
        height: 1fr;
    }
    
    .actions {
        align: center middle;
        height: 3;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
    }
    
    .empty {
        text-align: center;
        color: $text-muted;
        margin: 2;
    }
    """
    
    positions: reactive[list[Position]] = reactive([])
    
    def __init__(self):
        super().__init__()
        self.manager = PositionManager()
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Label("🌸 PILK DELTA-NEUTRAL LOGGER", classes="title")
            yield DataTable(id="positions_table")
            yield Label("", id="empty", classes="empty")
            with Horizontal(classes="actions"):
                yield Button("➕ New Position", variant="success", id="new")
                yield Button("🔄 Refresh", variant="primary", id="refresh")
        yield Footer()
    
    def on_mount(self):
        self._load_positions()
        table = self.query_one("#positions_table", DataTable)
        table.add_columns("Contract", "Type", "Strike", "Size", "Hedge", "Δ", "Band", "Status")
    
    def _load_positions(self):
        self.positions = self.manager.load_positions()
        self._update_table()
    
    def _update_table(self):
        table = self.query_one("#positions_table", DataTable)
        table.clear()
        
        if not self.positions:
            self.query_one("#empty", Label).update("No active positions. Press '➕ New Position' to add one.")
            return
        
        self.query_one("#empty", Label).update("")
        
        for pos in self.positions:
            # Determine status indicator
            needs_rehedge, _, _ = pos.check_rehedge(pos.entry_delta)
            status = "⚠️ REHEDGE" if needs_rehedge else "✅ OK"
            
            table.add_row(
                pos.name,
                pos.option_type.upper(),
                f"${pos.strike:,}",
                f"{pos.size}",
                f"{pos.current_hedge:+.4f}",
                f"{pos.entry_delta:.3f}",
                f"{pos.band:.4f}",
                status
            )
    
    @on(Button.Pressed, "#new")
    def on_new(self):
        def callback(pos: Optional[Position]):
            if pos:
                self._load_positions()
        self.app.push_screen(NewPositionModal(), callback)
    
    @on(Button.Pressed, "#refresh")
    def on_refresh(self):
        self._load_positions()
    
    @on(DataTable.RowSelected, "#positions_table")
    def on_row_selected(self, event: DataTable.RowSelected):
        if event.row_index < len(self.positions):
            pos = self.positions[event.row_index]
            self.app.push_screen(PositionDetailScreen(pos))


class DnLogApp(App):
    """Main TUI Application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    """
    
    SCREENS = {
        "main": MainScreen,
        "manual_delta": ManualDeltaModal,
    }
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "new_position", "New"),
        ("r", "refresh", "Refresh"),
    ]
    
    def on_mount(self):
        self.push_screen("main")
    
    def action_new_position(self):
        self.query_one(MainScreen).on_new()
    
    def action_refresh(self):
        self.query_one(MainScreen).on_refresh()


def main():
    """Entry point."""
    app = DnLogApp()
    app.run()


if __name__ == "__main__":
    main()
