"""
Binance Futures API client with rate limiting and error handling.
"""

import time
import hashlib
import hmac
import requests
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from collections import deque
from datetime import datetime


class BinanceRateLimiter:
    """
    Rate limiter for Binance API.
    Binance limits: 2400 requests per minute, 1200 per minute per IP weight.
    """

    def __init__(self, max_requests_per_minute: int = 1200):
        self.max_requests = max_requests_per_minute
        self.requests = deque()
        self.window_sec = 60

    def wait_if_needed(self, weight: int = 1) -> None:
        """Wait if rate limit would be exceeded."""
        now = time.time()

        # Remove requests outside the window
        while self.requests and self.requests[0] < now - self.window_sec:
            self.requests.popleft()

        # Check if we would exceed the limit
        if len(self.requests) + weight > self.max_requests:
            sleep_time = self.window_sec - (now - self.requests[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                # Clear old requests after sleeping
                self.requests.clear()

        # Add current request(s)
        for _ in range(weight):
            self.requests.append(now)


class BinanceFuturesClient:
    """Binance USDT-M Futures API client."""

    BASE_URL = "https://fapi.binance.com"
    TESTNET_URL = "https://testnet.binancefuture.com"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        max_retries: int = 3,
        timeout: int = 10
    ):
        """
        Initialize Binance Futures client.

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet if True
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.max_retries = max_retries
        self.timeout = timeout
        self.rate_limiter = BinanceRateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': api_key,
            'Content-Type': 'application/json',
        })

    def _sign(self, params: Dict[str, Any]) -> str:
        """Generate signature for signed endpoints."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        endpoint: str,
        signed: bool = False,
        params: Optional[Dict[str, Any]] = None,
        weight: int = 1
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Binance API with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            signed: Whether to sign the request
            params: Request parameters
            weight: API weight for rate limiting

        Returns:
            JSON response

        Raises:
            requests.exceptions.RequestException: On API error
        """
        if params is None:
            params = {}

        # Add timestamp and signature for signed endpoints
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign(params)

        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self.rate_limiter.wait_if_needed(weight)

                # Make request
                if method == 'GET':
                    response = self.session.get(url, params=params, timeout=self.timeout)
                elif method == 'POST':
                    response = self.session.post(url, params=params, timeout=self.timeout)
                elif method == 'DELETE':
                    response = self.session.delete(url, params=params, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                # Handle response
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                # Check for specific Binance errors
                if response.status_code == 429:
                    # Rate limit exceeded, wait and retry
                    time.sleep(60)
                elif response.status_code >= 500:
                    # Server error, retry
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                raise e

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise

            except requests.exceptions.ConnectionError:
                if attempt < self.max_retries - 1:
                    time.sleep(2)
                    continue
                raise

        raise Exception(f"Failed after {self.max_retries} retries")

    # ===== Market Data Endpoints =====

    def get_server_time(self) -> int:
        """Get Binance server time in milliseconds."""
        response = self._request('GET', '/fapi/v1/time', weight=1)
        return response['serverTime']

    def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information (symbols, limits, etc.)."""
        return self._request('GET', '/fapi/v1/exchangeInfo', weight=1)

    def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for a symbol."""
        params = {'symbol': symbol}
        return self._request('GET', '/fapi/v1/ticker/price', params=params, weight=1)

    def get_ticker_24h(self, symbol: str) -> Dict[str, Any]:
        """Get 24-hour ticker statistics."""
        params = {'symbol': symbol}
        return self._request('GET', '/fapi/v1/ticker/24hr', params=params, weight=1)

    def get_orderbook(self, symbol: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get orderbook depth.

        Args:
            symbol: Trading symbol
            limit: Number of levels (5, 10, 20, 50, 100, 500, 1000)

        Returns:
            Orderbook with bids and asks
        """
        params = {'symbol': symbol, 'limit': limit}
        weight = 2 if limit <= 50 else (5 if limit <= 100 else (10 if limit <= 500 else 20))
        return self._request('GET', '/fapi/v1/depth', params=params, weight=weight)

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500
    ) -> List[List]:
        """
        Get candlestick (kline) data.

        Args:
            symbol: Trading symbol
            interval: Timeframe (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, etc.)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Number of candles (max 1500)

        Returns:
            List of klines: [timestamp, open, high, low, close, volume, ...]
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1500)
        }
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time

        return self._request('GET', '/fapi/v1/klines', params=params, weight=1)

    def get_funding_rate(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get funding rate history."""
        params = {'symbol': symbol, 'limit': limit}
        return self._request('GET', '/fapi/v1/fundingRate', params=params, weight=1)

    def get_mark_price(self, symbol: str) -> Dict[str, Any]:
        """Get mark price and funding rate."""
        params = {'symbol': symbol}
        return self._request('GET', '/fapi/v1/premiumIndex', params=params, weight=1)

    # ===== Account Endpoints (Signed) =====

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information (balances, positions)."""
        return self._request('GET', '/fapi/v2/account', signed=True, weight=5)

    def get_balance(self) -> List[Dict[str, Any]]:
        """Get account balance."""
        return self._request('GET', '/fapi/v2/balance', signed=True, weight=5)

    def get_position_info(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get position information."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v2/positionRisk', signed=True, params=params, weight=5)

    # ===== Trading Endpoints (Signed) =====

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = 'GTC',
        reduce_only: bool = False,
        post_only: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new order.

        Args:
            symbol: Trading symbol
            side: BUY or SELL
            order_type: LIMIT or MARKET
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            time_in_force: GTC, IOC, FOK
            reduce_only: Reduce-only order
            post_only: Post-only (maker-only)
            **kwargs: Additional parameters

        Returns:
            Order response
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'timeInForce': time_in_force if order_type == 'LIMIT' else None,
            'reduceOnly': 'true' if reduce_only else 'false',
        }

        if price is not None and order_type == 'LIMIT':
            params['price'] = price

        if post_only:
            params['timeInForce'] = 'GTX'  # Post-only

        # Add any additional params
        params.update(kwargs)

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        return self._request('POST', '/fapi/v1/order', signed=True, params=params, weight=1)

    def cancel_order(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an order."""
        params = {'symbol': symbol}
        if order_id:
            params['orderId'] = order_id
        if client_order_id:
            params['origClientOrderId'] = client_order_id

        return self._request('DELETE', '/fapi/v1/order', signed=True, params=params, weight=1)

    def cancel_all_orders(self, symbol: str) -> Dict[str, Any]:
        """Cancel all open orders for a symbol."""
        params = {'symbol': symbol}
        return self._request('DELETE', '/fapi/v1/allOpenOrders', signed=True, params=params, weight=1)

    def get_order(self, symbol: str, order_id: Optional[int] = None, client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Get order status."""
        params = {'symbol': symbol}
        if order_id:
            params['orderId'] = order_id
        if client_order_id:
            params['origClientOrderId'] = client_order_id

        return self._request('GET', '/fapi/v1/order', signed=True, params=params, weight=1)

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders."""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/openOrders', signed=True, params=params, weight=1)

    # ===== Margin and Leverage =====

    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for a symbol."""
        params = {'symbol': symbol, 'leverage': leverage}
        return self._request('POST', '/fapi/v1/leverage', signed=True, params=params, weight=1)

    def set_margin_type(self, symbol: str, margin_type: str) -> Dict[str, Any]:
        """
        Set margin type (ISOLATED or CROSSED).

        Args:
            symbol: Trading symbol
            margin_type: ISOLATED or CROSSED
        """
        params = {'symbol': symbol, 'marginType': margin_type}
        return self._request('POST', '/fapi/v1/marginType', signed=True, params=params, weight=1)

    # ===== Helper Methods =====

    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol (convenience method)."""
        ticker = self.get_ticker_price(symbol)
        return float(ticker['price'])

    def get_minimum_order_size(self, symbol: str) -> float:
        """Get minimum order size for a symbol."""
        info = self.get_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        return float(f['minQty'])
        raise ValueError(f"Symbol {symbol} not found")

    def round_quantity(self, symbol: str, quantity: float) -> float:
        """Round quantity to valid step size."""
        info = self.get_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        precision = len(str(step_size).split('.')[-1].rstrip('0'))
                        return round(quantity - (quantity % step_size), precision)
        return quantity

    def round_price(self, symbol: str, price: float) -> float:
        """Round price to valid tick size."""
        info = self.get_exchange_info()
        for s in info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        tick_size = float(f['tickSize'])
                        precision = len(str(tick_size).split('.')[-1].rstrip('0'))
                        return round(price - (price % tick_size), precision)
        return price


if __name__ == "__main__":
    # Test client (requires API keys in environment)
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')

    if not api_key or not api_secret:
        print("Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file")
        exit(1)

    client = BinanceFuturesClient(api_key, api_secret, testnet=False)

    # Test public endpoints
    print("Testing Binance Futures API client...")

    server_time = client.get_server_time()
    print(f"✓ Server time: {datetime.fromtimestamp(server_time/1000)}")

    price = client.get_current_price('BTCUSDT')
    print(f"✓ BTC/USDT price: ${price:,.2f}")

    ticker = client.get_ticker_24h('BTCUSDT')
    print(f"✓ 24h volume: ${float(ticker['quoteVolume']):,.0f}")

    # Test klines
    klines = client.get_klines('BTCUSDT', '15m', limit=10)
    print(f"✓ Retrieved {len(klines)} 15m candles")

    # Test orderbook
    orderbook = client.get_orderbook('BTCUSDT', limit=5)
    print(f"✓ Orderbook: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")

    print("\n✅ All tests passed!")
