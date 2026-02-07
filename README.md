# Sniper Trade Logger

A Python-based CLI tool for tracking and managing delta-neutral option strategies (Gamma Rent / Scalping).

## Features

- **Trade Initialization**: Easily set up new option trades with contract details, strike price, size, and entry delta.
- **Delta Management**: specialized logic for calculating initial hedge requirements for both Calls and Puts.
- **Dynamic Monitoring**: Compare your current hedge position against the target hedge based on live delta inputs.
- **Band Trading**: "Trigger limits" (Bands) prevent over-trading by only suggesting adjustments when the delta deviation exceeds a specified threshold.
- **Persistence**: automatically saves active trade data to `sniper_trade.json` so you can resume sessions later.

## Usage

Run the script using Python:

```bash
python run.py
```

### 1. Initialize New Trade
If no active trade is found, the tool will guide you through the setup:
- **Expiry**: e.g., `29MAR`
- **Type**: `Call` or `Put`
- **Strike Price**: The option's strike price
- **Band**: The logic buffer; adjustments are only suggested if deviation > band
- **Entry Delta**: The delta at the time of entry (0.0 to 1.0)
- **Size**: Position size in contracts

The tool will automatically generate a contract name (e.g., `BTC-29MAR-72000-C`) and calculate your **Starting Hedge**.

### 2. Main Menu
Once initialized, you have three options:

1.  **Update / Check Delta**:
    - Input the *current* option delta.
    - The tool calculates the **Target Hedge** vs. **Current Hedge**.
    - If the difference exceeds your **Band**, it recommends a `BUY` or `SELL` action to re-hedge.
2.  **Close/Delete Trade**: Clears the saved data to start fresh.
3.  **Exit App**: Closes the tool (data remains saved).

## Configuration

- **Data File**: `sniper_trade.json` (created in the same directory)
