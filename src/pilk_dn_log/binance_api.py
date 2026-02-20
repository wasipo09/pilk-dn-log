"""Binance Options API integration via ccxt."""

import ccxt
from typing import Optional
import asyncio


class BinanceOptions:
    """Fetch option data from Binance via ccxt."""
    
    def __init__(self, api_key: str = None, secret: str = None):
        # Binance options requires separate exchange instance
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'option',  # Use options market
            }
        })
    
    async def get_option_delta(self, symbol: str) -> Optional[float]:
        """
        Fetch current delta for an option symbol.
        Symbol format: BTC-240227-70000-C
        """
        try:
            # Fetch option ticker
            ticker = await self.exchange.fetch_ticker(symbol)
            
            # Binance options ticker should include greeks
            # Check for delta in info field
            info = ticker.get('info', {})
            delta = info.get('delta')
            
            if delta is not None:
                return float(delta)
            
            # Fallback: try to get from greeks field
            greeks = info.get('greeks', {})
            if 'delta' in greeks:
                return float(greeks['delta'])
            
            return None
            
        except Exception as e:
            print(f"Error fetching delta for {symbol}: {e}")
            return None
    
    async def get_options_chain(self, base: str = 'BTC') -> dict:
        """Fetch full options chain for a base asset."""
        try:
            markets = await self.exchange.load_markets()
            options = {}
            
            for symbol, market in markets.items():
                if market.get('type') == 'option' and market.get('base') == base:
                    options[symbol] = market
            
            return options
            
        except Exception as e:
            print(f"Error fetching options chain: {e}")
            return {}
    
    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()


class MockBinanceOptions:
    """Mock API for testing without credentials."""
    
    async def get_option_delta(self, symbol: str) -> Optional[float]:
        """Return mock delta for testing."""
        # Parse symbol to estimate delta
        # BTC-240227-70000-C -> strike 70000, call
        import re
        match = re.search(r'(\d+)-(C|P)$', symbol)
        if match:
            strike = int(match.group(1))
            opt_type = match.group(2)
            
            # Mock: assume BTC at 67000, estimate delta
            btc_price = 67000
            moneyness = btc_price / strike
            
            # Simple delta estimation
            if opt_type == 'C':
                if moneyness > 1.05:
                    return 0.70 + (moneyness - 1.05) * 0.5  # ITM call
                elif moneyness > 0.95:
                    return 0.50 + (moneyness - 1.0) * 2  # ATM call
                else:
                    return 0.30 + (moneyness - 0.9) * 2  # OTM call
            else:
                if moneyness < 0.95:
                    return 0.70 + (1 - moneyness) * 0.5  # ITM put
                elif moneyness > 1.05:
                    return 0.30 - (moneyness - 1) * 0.5  # OTM put
                else:
                    return 0.50 - (moneyness - 1) * 2  # ATM put
        
        return 0.50  # Default
    
    async def close(self):
        pass


def get_binance_api(api_key: str = None, secret: str = None, mock: bool = False):
    """Get Binance API instance."""
    if mock or not api_key:
        return MockBinanceOptions()
    return BinanceOptions(api_key, secret)
