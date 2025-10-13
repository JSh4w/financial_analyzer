"""Processes trade data from websockets and routes to StockHandler instances"""
from typing import Dict, Optional, Callable
from collections import defaultdict
import logging
import asyncio
from datetime import datetime, timezone, timedelta

from app.utils import time_function
from app.stocks.stockHandler import StockHandler
from app.stocks.historical_data import AlpacaHistoricalData
from models.websocket_models import TradeData, QuoteData, BarData

logger = logging.getLogger(__name__)


class TradeDataAggregator:
    """Buffers websocket trade data and routes to synchronous StockHandler instances"""

    def __init__(self,
        callback: Optional[Callable] = None,
        input_queue = asyncio.Queue(500),
        broadcast_callback: Optional[Callable] = None,
        db_manager = None,
        historical_fetcher: Optional[AlpacaHistoricalData] = None
    ):
        self.queue = input_queue  # Buffer for 500 stocks
        self.callback = callback
        self.broadcast_callback = broadcast_callback #updating SSE
        self.db_manager = db_manager
        self.historical_fetcher = historical_fetcher
        self.stock_handlers: Dict[str, StockHandler] = {}
        self.SHUTDOWN_SENTINAL = object()
        self._handler_locks = defaultdict(asyncio.Lock)

    @staticmethod
    def create_market_data(websocket_data):
        """Factory method to create market data instances from Alpaca websocket data"""
        if isinstance(websocket_data, (TradeData, QuoteData, BarData)):
            return websocket_data

        if isinstance(websocket_data, dict):
            message_type = websocket_data.get('T', '')
            if message_type == "success":
                logger.info("Success message received, no action")
                return None 

            if message_type == 't':
                # Trade data
                required_fields = ['S', 'p', 's', 't']
                if all(field in websocket_data for field in required_fields):
                    try:
                        return TradeData(
                            T=websocket_data.get('T', 't'),
                            S=websocket_data['S'],
                            i=websocket_data.get('i', 0),
                            x=websocket_data.get('x', ''),
                            p=websocket_data['p'],
                            s=websocket_data['s'],
                            c=websocket_data.get('c', []),
                            t=websocket_data['t'],
                            z=websocket_data.get('z', '')
                        )
                    except Exception as e:
                        logger.error("Failed to create TradeData: %s", e)
                        return None

            elif message_type == 'q':
                # Quote data
                required_fields = ['S', 'bp', 'ap', 't']
                if all(field in websocket_data for field in required_fields):
                    try:
                        return QuoteData(
                            T=websocket_data.get('T', 'q'),
                            S=websocket_data['S'],
                            bx=websocket_data.get('bx', ''),
                            bp=websocket_data['bp'],
                            bs=websocket_data.get('bs', 0),
                            ax=websocket_data.get('ax', ''),
                            ap=websocket_data['ap'],
                            as_=websocket_data.get('as', 0),
                            c=websocket_data.get('c', []),
                            t=websocket_data['t'],
                            z=websocket_data.get('z', '')
                        )
                    except Exception as e:
                        logger.error("Failed to create QuoteData: %s", e)
                        return None

            elif message_type == 'b':
                # Bar/candle data
                required_fields = ['S', 'o', 'h', 'l', 'c', 'v', 't']
                if all(field in websocket_data for field in required_fields):
                    try:
                        return BarData(
                            T=websocket_data.get('T', 'b'),
                            S=websocket_data['S'],
                            o=websocket_data['o'],
                            h=websocket_data['h'],
                            l=websocket_data['l'],
                            c=websocket_data['c'],
                            v=websocket_data['v'],
                            t=websocket_data['t'],
                            n=websocket_data.get('n', 0),
                            vw=websocket_data.get('vw', 0.0)
                        )
                    except Exception as e:
                        logger.error("Failed to create BarData: %s", e)
                        return None
            else:
                logger.warning("Unknown message type: %s", message_type)
                return None

        logger.warning("Invalid websocket data format")
        return None

    async def process_tick_queue(self):
        """Process queued market data - async for I/O, calls sync StockHandlers"""
        while True:
            input_data = await self.queue.get() #this releases control

            if input_data == self.SHUTDOWN_SENTINAL:
                break

            await self._process_market_data(input_data)

    @time_function(f"_process_market_data")
    async def _process_market_data(self, input_data):
        """Process market data with timing"""

        #convert data
        market_data = self.create_market_data(input_data)
        if market_data is None:
            return
        symbol = market_data.S

        # Create StockHandler if needed (sync operation)
        async with self._handler_locks[symbol]:
            if symbol not in self.stock_handlers:
                handler_callback = self._create_update_callback() if self.broadcast_callback else None
                self.stock_handlers[symbol] = StockHandler(
                    symbol,
                    db_manager=self.db_manager,
                    on_update_callback=handler_callback
                )

                # Fetch historical data in background when new handler is created
                if self.historical_fetcher:
                    asyncio.create_task(self._load_historical_data(symbol))

        # Process data based on type
        if isinstance(market_data, TradeData):
            # Process individual trades for OHLCV computation
            self.stock_handlers[symbol].process_trade(
                price=market_data.p,
                volume=market_data.s,
                timestamp=market_data.t,
                conditions=market_data.c
            )
        elif isinstance(market_data, BarData):
            # Process complete candle data directly
            candle_data = market_data.to_candle_dict()
            self.stock_handlers[symbol].process_candle(candle_data)
        elif isinstance(market_data, QuoteData):
            # Process quote data (if your StockHandler supports it)
            # For now, we'll skip quote processing
            logger.debug("Quote data received for %s but not processed", symbol)

        # Optional callback for processed data
        if self.callback:
            try:
                self.callback(market_data)
            except Exception as e:
                logger.error("Error in data callback: %s", e)


    def get_stock_handler(self, symbol: str) -> Optional[StockHandler]:
        """Get StockHandler instance for a symbol"""
        return self.stock_handlers.get(symbol)

    def get_all_symbols(self) -> list[str]:
        """Get list of all symbols being tracked"""
        return list(self.stock_handlers.keys())

    async def ensure_handler_exists(self, symbol: str):
        """
        Ensure StockHandler exists for symbol, create if needed.
        Called by SubscriptionManager on new subscriptions.
        Idempotent - safe to call multiple times.

        Args:
            symbol: Stock symbol to ensure handler exists for
        """
        symbol = symbol.upper()

        async with self._handler_locks[symbol]:
            if symbol not in self.stock_handlers:
                handler_callback = self._create_update_callback() if self.broadcast_callback else None
                self.stock_handlers[symbol] = StockHandler(
                    symbol,
                    db_manager=self.db_manager,
                    on_update_callback=handler_callback
                )
                logger.info(f"Created StockHandler for {symbol} on subscription")

                # Fetch historical data in background
                if self.historical_fetcher:
                    asyncio.create_task(self._load_historical_data(symbol))
            else:
                logger.debug(f"StockHandler already exists for {symbol}")

    def _create_update_callback(self):
        """Create a callback function for StockHandler updates"""
        def update_callback(symbol: str, candle_data: dict, is_initial: bool = False):
            if self.broadcast_callback:
                # Create update data for SSE
                # If is_initial is True, send all candles. Otherwise, send only recent ones
                update_data = {
                    "symbol": symbol,
                    "candles": candle_data,
                    "update_timestamp": datetime.now(timezone.utc).isoformat(),
                    "is_initial": is_initial
                }
                try:
                    # Call the broadcast callback (this will be async in main.py)
                    self.broadcast_callback(update_data)
                except Exception as e:
                    logger.error("Error in broadcast callback: %s", e)

        return update_callback

    async def _load_historical_data(self, symbol: str):
        """
        Load historical data for a symbol in the background

        Args:
            symbol: Stock symbol to fetch historical data for
        """
        try:
            logger.info(f"Fetching historical data for {symbol}")

            # Fetch last 7 days of minute bars to ensure we get trading days
            # Markets are closed weekends/holidays, so we need a wider window
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=7)

            historical_bars_list = await self.historical_fetcher.fetch_historical_bars(
                symbol=symbol,
                timeframe="1Min",
                start=start_time,
                end=end_time,
                limit=10000  # Max limit - API will return available data
            )

            if historical_bars_list:
                # Convert List[BarData] to Dict[str, Dict] format for StockHandler
                historical_bars_dict = {}
                for bar_data in historical_bars_list:
                    candle_dict = bar_data.to_candle_dict()
                    # Extract and format timestamp (minute-aligned)
                    dt = datetime.fromisoformat(candle_dict['timestamp'].replace('Z', '+00:00'))
                    minute_aligned = dt.replace(second=0, microsecond=0)
                    timestamp_key = minute_aligned.isoformat().replace('+00:00', 'Z')

                    historical_bars_dict[timestamp_key] = {
                        'open': candle_dict['open'],
                        'high': candle_dict['high'],
                        'low': candle_dict['low'],
                        'close': candle_dict['close'],
                        'volume': candle_dict['volume']
                    }

                # Load into stock handler with proper locking
                handler = self.stock_handlers.get(symbol)
                if handler:
                    await handler.load_historical_data(historical_bars_dict)
                    logger.info(f"Successfully loaded {len(historical_bars_dict)} historical bars for {symbol}")
            else:
                logger.warning(f"No historical data returned for {symbol}")

        except Exception as e:
            logger.error(f"Failed to load historical data for {symbol}: {e}")

    async def shutdown(self):
        """Shutdown gracefully"""
        await self.queue.put(self.SHUTDOWN_SENTINAL)

