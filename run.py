import json
import os
import sys
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "sniper_trade.json"
HISTORY_FILE = "trade_history.json"

def load_positions():
    """Load all positions from data file."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_positions(positions):
    """Save all positions to data file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(positions, f, indent=4)

def get_position_by_id(pos_id):
    """Find a position by its ID."""
    positions = load_positions()
    for pos in positions:
        if pos['id'] == pos_id:
            return pos
    return None

def remove_position(pos_id):
    """Remove a position by ID."""
    positions = load_positions()
    positions = [p for p in positions if p['id'] != pos_id]
    save_positions(positions)

def generate_id():
    """Generate a unique ID for a new position."""
    positions = load_positions()
    if not positions:
        return 1
    return max(p['id'] for p in positions) + 1

def get_float(prompt):
    """Get a float input from user with validation."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("❌ Invalid number. Try again.")

def list_positions():
    """List all active positions."""
    positions = load_positions()
    
    if not positions:
        print("\n🚫 NO ACTIVE POSITIONS")
        return None
    
    print("\n" + "="*50)
    print("📋 ACTIVE POSITIONS")
    print("="*50)
    
    for pos in positions:
        last_delta = pos.get('last_delta', 'N/A')
        print(f"  [{pos['id']}] {pos['name']}")
        print(f"      Type: {pos['type'].upper()} | Size: {pos['size']} | Band: {pos['band']}")
        print(f"      Last Delta: {last_delta} | Hedges: {pos['trades_count']}")
        print(f"      Hedge Position: {pos['current_hedge_pos']:.5f} BTC")
        print("-" * 50)
    
    return positions

def new_trade():
    """Create a new trade position."""
    print("\n" + "="*40)
    print("🆕  INITIALIZE NEW TRADE")
    print("="*40)
    
    # 1. INPUTS
    expiry = input("📅 Expiry (e.g. 29MAR): ").strip().upper()
    
    while True:
        option_type = input("📈 Type (call/put): ").lower().strip()
        if option_type in ['call', 'put', 'c', 'p']:
            option_type = 'call' if 'c' in option_type else 'put'
            break
            
    strike = get_float("🎯 Strike Price ($): ")
    band = get_float("🌊 Band (Trigger limit, e.g. 0.0038): ")
    entry_delta = get_float("Δ  Entry Delta (0.0 to 1.0): ")
    size = get_float("📦 Size (Contracts, e.g. 0.1): ")

    # Auto-generate name
    contract_name = f"BTC-{expiry}-{int(strike)}"
    if option_type == 'call':
        contract_name += "-C"
    else:
        contract_name += "-P"

    # 2. CALCULATE STARTING HEDGE
    raw_delta_exposure = size * entry_delta
    
    if option_type == 'call':
        required_hedge = -raw_delta_exposure
        hedge_desc = "SHORT"
    else:
        required_hedge = raw_delta_exposure
        hedge_desc = "LONG"

    print("\n" + "-"*40)
    print(f"✅ CALCULATED STARTING HEDGE:")
    print(f"   You are Long {option_type.upper()}. Exposure: {raw_delta_exposure:.4f} BTC")
    print(f"   👉 ACTION: Open {hedge_desc} Perp Position: {abs(required_hedge):.4f} BTC")
    print("-" * 40)
    
    confirm = input("Did you execute this hedge? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Setup cancelled.")
        return None

    # 3. SAVE TO FILE
    pos_id = generate_id()
    position = {
        "id": pos_id,
        "start_time": str(datetime.now()),
        "name": contract_name,
        "type": option_type,
        "strike": strike,
        "size": size,
        "band": band,
        "current_hedge_pos": required_hedge,
        "trades_count": 0,
        "last_delta": entry_delta
    }
    
    positions = load_positions()
    positions.append(position)
    save_positions(positions)
    
    print(f"\n💾 Position saved with ID: {pos_id}")
    return position

def update_delta(pos_id):
    """Update delta for a specific position."""
    position = get_position_by_id(pos_id)
    if not position:
        print("❌ Position not found.")
        return
    
    print("\n" + "="*40)
    print(f"🔎 UPDATE DELTA: {position['name']} [ID: {pos_id}]")
    print(f"   Size: {position['size']} | Band: {position['band']} | Type: {position['type'].upper()}")
    print("="*40)
    
    current_delta = get_float("\nInput Current Option Delta (0.0 - 1.0): ")
    
    # CALCULATE MATH
    if position['type'] == 'call':
        contract_delta_val = abs(current_delta)
        target_hedge = -(position['size'] * contract_delta_val)
    else:
        contract_delta_val = abs(current_delta)
        target_hedge = (position['size'] * contract_delta_val)

    current_hedge = position['current_hedge_pos']
    diff = target_hedge - current_hedge
    
    print("\n-----------------------------------")
    print(f"🎯 Target Hedge Needed: {target_hedge:.5f} BTC")
    print(f"💼 Current Hedge Held:  {current_hedge:.5f} BTC")
    print(f"📉 Deviation (Diff):    {diff:.5f} BTC")
    print("-----------------------------------")

    # DECISION LOGIC
    abs_diff = abs(diff)
    
    if abs_diff > position['band']:
        print(f"\n🚨 ALERT: DIFF {abs_diff:.5f} > BAND {position['band']}")
        
        if diff > 0:
            action = "BUY / LONG"
            reason = "Covering Short or Adding Long"
        else:
            action = "SELL / SHORT"
            reason = "Increasing Short or Selling Long"

        print(f"\n👉 EXECUTE: ** {action} **")
        print(f"   AMOUNT:  {abs_diff:.4f} BTC")
        print(f"   REASON:  {reason}")
        
        confirm = input("\nDid you do it? (y/n): ")
        if confirm.lower() == 'y':
            # Update position
            position['current_hedge_pos'] += diff
            position['trades_count'] += 1
            position['last_delta'] = current_delta
            
            # Update in positions list
            positions = load_positions()
            for i, pos in enumerate(positions):
                if pos['id'] == pos_id:
                    positions[i] = position
                    break
            save_positions(positions)
            
            print("✅ Position updated. Back to Neutral.")
    else:
        print("\n✅ STATUS: SAFE")
        print("   (Inside the Band. Do nothing.)")
        # Still update last_delta even if no rehedge
        position['last_delta'] = current_delta
        positions = load_positions()
        for i, pos in enumerate(positions):
            if pos['id'] == pos_id:
                positions[i] = position
                break
        save_positions(positions)

def close_position(pos_id):
    """Close and archive a position."""
    position = get_position_by_id(pos_id)
    if not position:
        print("❌ Position not found.")
        return
    
    print(f"\n📦 Closing position: {position['name']}")
    confirm = input("Are you sure? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Cancelled.")
        return
    
    # Archive to history
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except:
            history = []
    
    position['end_time'] = str(datetime.now())
    history.append(position)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)
    
    # Remove from active positions
    remove_position(pos_id)
    
    print(f"✅ Position archived to {HISTORY_FILE}")

def show_history():
    """Show trade history."""
    if not os.path.exists(HISTORY_FILE):
        print("\n🚫 No trade history found.")
        return
    
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)
    
    if not history:
        print("\n🚫 Trade history is empty.")
        return
    
    print("\n" + "="*50)
    print("📚 TRADE HISTORY")
    print("="*50)
    
    for trade in history:
        print(f"\n  [{trade['id']}] {trade['name']}")
        print(f"      Start: {trade['start_time']}")
        print(f"      End: {trade.get('end_time', 'N/A')}")
        print(f"      Type: {trade['type'].upper()} | Size: {trade['size']}")
        print(f"      Final Hedge: {trade['current_hedge_pos']:.5f} BTC")
        print(f"      Total Hedges: {trade['trades_count']}")
        print("-" * 50)

def main_menu():
    """Display main menu options."""
    print("\n" + "="*30)
    print("🎯 DN-LOG CLI")
    print("="*30)
    print("1. List Positions")
    print("2. New Position")
    print("3. Update Delta")
    print("4. Close Position")
    print("5. Trade History")
    print("6. Exit")
    print("-"*30)

def main():
    while True:
        main_menu()
        choice = input("Select: ").strip()
        
        if choice == '1':
            list_positions()
        
        elif choice == '2':
            new_trade()
        
        elif choice == '3':
            positions = list_positions()
            if positions:
                try:
                    pos_id = int(input("\nEnter position ID to update: "))
                    update_delta(pos_id)
                except ValueError:
                    print("❌ Invalid ID.")
        
        elif choice == '4':
            positions = list_positions()
            if positions:
                try:
                    pos_id = int(input("\nEnter position ID to close: "))
                    close_position(pos_id)
                except ValueError:
                    print("❌ Invalid ID.")
        
        elif choice == '5':
            show_history()
        
        elif choice == '6':
            print("\n👋 Goodbye!")
            sys.exit()
        
        else:
            print("❌ Invalid selection.")

if __name__ == "__main__":
    main()
