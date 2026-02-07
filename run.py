import json
import os
import sys
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "sniper_trade.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def clear_data():
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    print("\n🗑️  Trade data cleared. Ready for a new mission.")

def get_float(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("❌ Invalid number. Try again.")

def new_trade():
    print("\n" + "="*40)
    print("🆕  INITIALIZE NEW SNIPER TRADE")
    print("="*40)
    
    # 1. THE INPUTS YOU REQUESTED
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

    # 2. LOGIC: CALCULATE STARTING HEDGE
    # Call (+Delta) -> Needs Short Hedge (-Delta) to be 0
    # Put  (-Delta) -> Needs Long Hedge (+Delta) to be 0
    
    raw_delta_exposure = size * entry_delta
    
    if option_type == 'call':
        required_hedge = -raw_delta_exposure # Short
        hedge_desc = "SHORT"
    else:
        required_hedge = raw_delta_exposure  # Long
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
    data = {
        "start_time": str(datetime.now()),
        "name": contract_name,
        "type": option_type,
        "strike": strike,
        "size": size,
        "band": band,
        "current_hedge_pos": required_hedge, # Negative = Short, Positive = Long
        "trades_count": 0,
        "last_delta": entry_delta  # Initialize with entry delta
    }
    save_data(data)
    print("💾 Data Saved. You can close the terminal now.")
    return data

def archive_trade(data):
    history_file = "trade_history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except:
            history = []
            
    data['end_time'] = str(datetime.now())
    history.append(data)
    
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=4)
        
    print(f"📚 Trade archived to {history_file}")

def check_status(data):
    print("\n" + "="*40)
    print(f"🔎 CHECK STATUS: {data['name']}")
    print(f"   Size: {data['size']} | Band: {data['band']} | Type: {data['type'].upper()}")
    print("="*40)
    
    # 1. GET LIVE DATA
    current_delta = get_float("\nInput Current Option Delta (0.0 - 1.0): ")
    
    # 2. CALCULATE MATH
    # What represents "Neutral" right now?
    # If Call: Delta is positive. Neutral Hedge is Negative (Short).
    # If Put: Delta is negative (usually shown as -0.5). Neutral Hedge is Positive (Long).
    
    # Normalize Delta Sign based on type
    if data['type'] == 'call':
        # If user types 0.50, it is +0.50
        contract_delta_val = abs(current_delta)
        target_hedge = -(data['size'] * contract_delta_val) # We want to be Short
    else:
        # If user types 0.40 (for put), it implies -0.40 exposure.
        # We need +0.40 Hedge to fix it.
        contract_delta_val = abs(current_delta) 
        target_hedge = (data['size'] * contract_delta_val) # We want to be Long

    current_hedge = data['current_hedge_pos']
    
    # DIFF = Where we are vs Where we should be
    # Example: Target -0.60 (Short more), Current -0.50. Diff = -0.10.
    diff = target_hedge - current_hedge
    
    print("\n-----------------------------------")
    print(f"🎯 Target Hedge Needed: {target_hedge:.5f} BTC")
    print(f"💼 Current Hedge Held:  {current_hedge:.5f} BTC")
    print(f"📉 Deviation (Diff):    {diff:.5f} BTC")
    print("-----------------------------------")

    # 3. DECISION LOGIC
    abs_diff = abs(diff)
    
    if abs_diff > data['band']:
        print(f"\n🚨 ALERT: DIFF {abs_diff:.5f} > BAND {data['band']}")
        
        if diff > 0:
            # Diff is Positive. We need to ADD to our position number.
            # If Short (-0.5) needs to go to (-0.4), Diff is +0.1.
            # Adding +0.1 to a Short means BUYING back.
            action = "BUY / LONG"
            reason = "Covering Short or Adding Long"
        else:
            # Diff is Negative. We need to SUBTRACT.
            # If Short (-0.5) needs to go to (-0.6), Diff is -0.1.
            # Subtracting means SELLING more.
            action = "SELL / SHORT"
            reason = "Increasing Short or Selling Long"

        print(f"\n👉 EXECUTE: ** {action} **")
        print(f"   AMOUNT:  {abs_diff:.4f} BTC")
        print(f"   REASON:  {reason}")
        
        confirm = input("\nDid you do it? (y/n): ")
        if confirm.lower() == 'y':
            data['current_hedge_pos'] += diff
            data['trades_count'] += 1
            data['last_delta'] = current_delta # Update last delta
            save_data(data)
            print("✅ Database Updated. Back to Neutral.")
            
    else:
        print("\n✅ STATUS: SAFE")
        print("   (Inside the Band. Do nothing.)")
        # Update last delta anyway for display purposes if verified
        data['last_delta'] = current_delta
        save_data(data)

def main():
    while True:
        data = load_data()
        
        if not data:
            print("\n" + "."*30)
            print("🚫 NO ACTIVE TRADE")
            print("1. New Trade")
            print("2. Exit App")
            
            choice = input("Select: ")
            
            if choice == '1':
                new_trade()
            elif choice == '2':
                sys.exit()
            else:
                print("Invalid selection.")
        else:
            print("\n" + "."*30)
            print(f"ACTIVE: {data['name']} ({data['type'].upper()})")
            # Handle legacy data that might not have last_delta
            last_delta = data.get('last_delta', 'N/A')
            print(f"Current Delta: {last_delta}")
            
            print("1. Update / Check Delta")
            print("2. Close/Delete Trade")
            print("3. Exit App")
            
            choice = input("Select: ")
            
            if choice == '1':
                check_status(data)
            elif choice == '2':
                archive_trade(data)
                clear_data()
                sys.exit() # Exit after closing
            elif choice == '3':
                sys.exit()

if __name__ == "__main__":
    main()