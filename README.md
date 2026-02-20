# Pilk DN Log

Delta-Neutral Trade Logger with TUI and Binance integration.

## Features

- **TUI Dashboard**: Beautiful terminal interface with Textual
- **Multi-position support**: Track multiple delta-neutral positions simultaneously
- **Live delta fetching**: Auto-fetch delta from Binance via ccxt
- **Band trading**: Only suggest rehedges when delta deviation exceeds threshold
- **Position history**: Archive closed trades for review

## Installation

```bash
cd ~/Projects/pilk-dn-log
pip install -e .
```

Or with pipx for isolated install:

```bash
pipx install .
```

## Usage

```bash
dn-log
```

### Keyboard Shortcuts

- `n` - New position
- `r` - Refresh
- `q` - Quit
- `Enter` - Select/view position details

### Adding a Position

1. Press `n` or click "➕ New Position"
2. Enter:
   - **Expiry**: e.g., `27FEB`
   - **Type**: CALL or PUT
   - **Strike**: e.g., `70000`
   - **Size**: Position size in BTC
   - **Entry Delta**: Delta at entry (0.0-1.0)
   - **Band**: Rehedge threshold (e.g., 0.0038)

### Monitoring

- Dashboard shows all positions with current status
- Click a row to see details and fetch live delta
- Status indicators:
  - ✅ OK - Within band
  - ⚠️ REHEDGE - Needs adjustment

## Data Storage

- Positions: `~/.pilk/dn_positions.json`
- History: `~/.pilk/dn_history.json`

## Configuration

For live Binance delta fetching, set environment variables:

```bash
export BINANCE_API_KEY="your_key"
export BINANCE_SECRET="your_secret"
```

Without credentials, the app uses a mock delta estimator.

## Legacy CLI (`run.py`)

Updated multi-position CLI with delta updating:

```bash
python run.py
```

### Commands

- **List Positions** — View all active trades with delta and hedge status
- **New Position** — Add a new delta-neutral trade position
- **Update Delta** — Enter current delta for a position, auto-calculate rehedge
- **Close Position** — Archive a trade to history
- **Trade History** — View all closed trades

### Data Storage

- Active positions: `sniper_trade.json`
- Trade history: `trade_history.json`

## Requirements

- Python 3.10+
- textual >= 0.47.0 (for TUI)
- ccxt >= 4.0.0 (for Binance integration)
- rich >= 13.0.0
