"""Processes trade data from websockets and routes to StockHandler instances"""
from typing import Dict, Optional, Callable
import logging
import asyncio

from app.stocks.stockHandler import StockHandler
from models.websocket_models import TradeData

logger = logging.getLogger(__name__)


class TradeDataAggregator:
    """Buffers websocket trade data and routes to synchronous StockHandler instances"""

    def __init__(self, callback: Optional[Callable] = None, input_queue = asyncio.Queue(500)):
        self.queue = input_queue  # Buffer for 50 stocks
        self.callback = callback
        self.stock_handlers: Dict[str, StockHandler] = {}
        self.SHUTDOWN_SENTINAL = object()

    @staticmethod
    def create_trade_data(websocket_data) -> TradeData:
        """Factory method to create TradeData instances from websocket data"""
        if isinstance(websocket_data, dict):
            return TradeData.dict_to_data(websocket_data)
        if isinstance(websocket_data, TradeData):
            return websocket_data
        # Handle raw websocket data structure
        return TradeData(
            s=getattr(websocket_data, 's', websocket_data.get('s', None)),
            p=getattr(websocket_data, 'p', websocket_data.get('p', None)),
            t=getattr(websocket_data, 't', websocket_data.get('t', None)),
            v=getattr(websocket_data, 'v', websocket_data.get('v', None)),
            c=getattr(websocket_data, 'c', websocket_data.get('c', []))
        )

    async def process_tick_queue(self):
        """Process queued trades - async for I/O, calls sync StockHandlers"""
        while True:
            input_data = await self.queue.get() #this releases control
            if input_data == self.SHUTDOWN_SENTINAL:
                break
            #convert data
            trade_data = self.create_trade_data(input_data)
            symbol = trade_data.s


            # Create StockHandler if needed (sync operation)
            self.stock_handlers.setdefault(symbol, StockHandler(symbol))

            # Process trade (sync OHLCV computation)
            self.stock_handlers[symbol].process_trade(trade_data)

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
    
    async def shutdown(self):
        """Shutdown gracefully"""
        await self.queue.put(self.SHUTDOWN_SENTINAL)

