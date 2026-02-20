"""Position management for delta-neutral trades."""

import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional
from pathlib import Path

DATA_DIR = Path.home() / ".pilk"
POSITIONS_FILE = DATA_DIR / "dn_positions.json"
HISTORY_FILE = DATA_DIR / "dn_history.json"


@dataclass
class Position:
    """A delta-neutral option position."""
    id: str
    name: str
    option_type: str  # 'call' or 'put'
    strike: float
    expiry: str
    size: float
    entry_delta: float
    band: float
    current_hedge: float
    created_at: str
    updated_at: str
    rehedge_count: int = 0
    is_active: bool = True
    binance_symbol: Optional[str] = None  # e.g., "BTC-240227-70000-C"
    
    @property
    def target_hedge(self) -> float:
        """Calculate current target hedge based on entry delta."""
        delta_exposure = self.size * self.entry_delta
        if self.option_type == 'call':
            return -delta_exposure  # Short for calls
        else:
            return delta_exposure  # Long for puts
    
    def calculate_target_hedge(self, current_delta: float) -> float:
        """Calculate target hedge for given delta."""
        delta_exposure = self.size * current_delta
        if self.option_type == 'call':
            return -delta_exposure
        else:
            return delta_exposure
    
    def check_rehedge(self, current_delta: float) -> tuple[bool, float, str]:
        """
        Check if rehedge needed.
        Returns: (needs_rehedge, amount, action)
        """
        target = self.calculate_target_hedge(current_delta)
        diff = target - self.current_hedge
        abs_diff = abs(diff)
        
        if abs_diff > self.band:
            if diff > 0:
                action = "BUY"
            else:
                action = "SELL"
            return True, abs_diff, action
        return False, 0.0, ""


class PositionManager:
    """Manages multiple delta-neutral positions."""
    
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def load_positions(self) -> list[Position]:
        """Load all active positions."""
        if not POSITIONS_FILE.exists():
            return []
        try:
            with open(POSITIONS_FILE, 'r') as f:
                data = json.load(f)
            return [Position(**p) for p in data if p.get('is_active', True)]
        except:
            return []
    
    def save_positions(self, positions: list[Position]):
        """Save positions to file."""
        # Load existing to preserve inactive ones
        all_positions = []
        if POSITIONS_FILE.exists():
            try:
                with open(POSITIONS_FILE, 'r') as f:
                    all_positions = json.load(f)
            except:
                pass
        
        # Update active ones
        active_ids = {p.id for p in positions}
        for p in all_positions:
            if p['id'] not in active_ids:
                positions.append(Position(**p))
        
        with open(POSITIONS_FILE, 'w') as f:
            json.dump([asdict(p) for p in positions], f, indent=2)
    
    def add_position(self, pos: Position):
        """Add a new position."""
        positions = self.load_positions()
        positions.append(pos)
        self.save_positions(positions)
    
    def update_position(self, pos: Position):
        """Update an existing position."""
        positions = self.load_positions()
        for i, p in enumerate(positions):
            if p.id == pos.id:
                positions[i] = pos
                break
        self.save_positions(positions)
    
    def close_position(self, pos_id: str):
        """Archive a position."""
        positions = self.load_positions()
        for p in positions:
            if p.id == pos_id:
                p.is_active = False
                p.updated_at = datetime.now().isoformat()
                self._archive_position(p)
                break
        self.save_positions([p for p in positions if p.id != pos_id])
    
    def _archive_position(self, pos: Position):
        """Archive closed position to history."""
        history = []
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            except:
                pass
        history.append(asdict(pos))
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    
    @staticmethod
    def generate_id() -> str:
        """Generate unique position ID."""
        return datetime.now().strftime("%Y%m%d-%H%M%S")
    
    @staticmethod
    def make_contract_name(expiry: str, strike: float, option_type: str) -> str:
        """Generate contract name like BTC-27FEB-70000-C."""
        return f"BTC-{expiry.upper()}-{int(strike)}-{option_type[0].upper()}"
    
    @staticmethod
    def make_binance_symbol(expiry: str, strike: float, option_type: str) -> str:
        """Generate Binance symbol like BTC-240227-70000-C."""
        # Convert 27FEB to 240227 format
        import re
        match = re.match(r'(\d{1,2})(\w{3})', expiry.upper())
        if match:
            day, month = match.groups()
            months = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                      'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                      'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}
            month_num = months.get(month, '01')
            year = '26'  # Assume 2026 for now
            date_str = f"{year}{month_num}{int(day):02d}"
            return f"BTC-{date_str}-{int(strike)}-{option_type[0].upper()}"
        return None
