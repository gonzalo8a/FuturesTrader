#!/usr/bin/env python3
"""
Quick script to check BTC/USDT Futures price.
Usage: python check_price.py
"""

import os
from dotenv import load_dotenv
from src.data.binance_client import BinanceFuturesClient

# Load environment variables
load_dotenv()

# Initialize client
client = BinanceFuturesClient(
    os.getenv('BINANCE_API_KEY'),
    os.getenv('BINANCE_API_SECRET')
)

# Get current price
price = client.get_current_price('BTCUSDT')
ticker = client.get_ticker_24h('BTCUSDT')

print(f"\n{'='*50}")
print(f"BTC/USDT PERPETUAL FUTURES")
print(f"{'='*50}")
print(f"Current Price:  ${price:,.2f}")
print(f"24h Change:     {float(ticker['priceChangePercent']):+.2f}%")
print(f"24h High:       ${float(ticker['highPrice']):,.2f}")
print(f"24h Low:        ${float(ticker['lowPrice']):,.2f}")
print(f"24h Volume:     ${float(ticker['quoteVolume']):,.0f}")
print(f"{'='*50}\n")
