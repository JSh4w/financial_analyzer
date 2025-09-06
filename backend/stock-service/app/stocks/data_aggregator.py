"""Processes trade data from websockets and routes to StockHandler instances"""
from typing import Dict, Optional, Callable
import logging
import asyncio
import time

from app.stocks.stockHandler import StockHandler
from models.websocket_models import TradeData

logger = logging.getLogger(__name__)


class TradeDataAggregator:
    """Buffers websocket trade data and routes to synchronous StockHandler instances"""

    def __init__(self,
        callback: Optional[Callable] = None,
        input_queue = asyncio.Queue(500),
        broadcast_callback: Optional[Callable] = None,
        db_manager = None
    ):
        self.queue = input_queue  # Buffer for 500 stocks
        self.callback = callback
        self.broadcast_callback = broadcast_callback #updating SSE
        self.db_manager = db_manager
        self.stock_handlers: Dict[str, StockHandler] = {}
        self.SHUTDOWN_SENTINAL = object()

    @staticmethod
    def create_trade_data(websocket_data) -> Optional[TradeData]:
        """Factory method to create TradeData instances from Alpaca websocket data"""
        if isinstance(websocket_data, TradeData):
            return websocket_data

        if isinstance(websocket_data, dict):
            # Check for required fields: symbol, price, size, timestamp
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
            else:
                logger.warning("Missing required fields (S,p,s,t) in websocket data")
                return None

        logger.warning("Invalid websocket data format")
        return None

    async def process_tick_queue(self):
        """Process queued trades - async for I/O, calls sync StockHandlers"""
        while True:
            input_data = await self.queue.get() #this releases control
            if input_data == self.SHUTDOWN_SENTINAL:
                break
            #convert data
            trade_data = self.create_trade_data(input_data)
            if trade_data is None:
                continue
            symbol = trade_data.S

            # Create StockHandler if needed (sync operation)
            handler_callback = self._create_update_callback() if self.broadcast_callback else None
            self.stock_handlers.setdefault(symbol, StockHandler(
                symbol,
                db_manager=self.db_manager,
                on_update_callback=handler_callback
            ))

            # Process trade (sync OHLCV computation)
            self.stock_handlers[symbol].process_trade(
                price=trade_data.p,
                volume=trade_data.s,
                timestamp=trade_data.t,
                conditions=trade_data.c
            )

            # Optional callback for processed trades
            if self.callback:
                try:
                    self.callback(trade_data)
                except Exception as e:
                    logger.error("Error in trade callback: %s", e)

    def get_stock_handler(self, symbol: str) -> Optional[StockHandler]:
        """Get StockHandler instance for a symbol"""
        return self.stock_handlers.get(symbol)

    def get_all_symbols(self) -> list[str]:
        """Get list of all symbols being tracked"""
        return list(self.stock_handlers.keys())

    def _create_update_callback(self):
        """Create a callback function for StockHandler updates"""
        def update_callback(symbol: str, candle_data: dict):
            if self.broadcast_callback:
                # Create update data for SSE with complete candle dictionary
                update_data = {
                    "symbol": symbol,
                    "candles": candle_data,
                    "update_timestamp": time.time()
                }
                try:
                    # Call the broadcast callback (this will be async in main.py)
                    self.broadcast_callback(update_data)
                except Exception as e:
                    logger.error("Error in broadcast callback: %s", e)

        return update_callback

    async def shutdown(self):
        """Shutdown gracefully"""
        await self.queue.put(self.SHUTDOWN_SENTINAL)

