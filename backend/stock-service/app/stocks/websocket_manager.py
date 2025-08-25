# backend/python-service/app/main_test.py
import os
from typing import Optional, Any, Set, Dict, List, Callable
from dataclasses import dataclass
import json
import asyncio
import logging
from enum import Enum
import websockets

#from app.stocks.market_data_handler import TradeDataHandler
from app.stocks.data_aggregator import TradeDataAggregator
from app.config import Settings

settings = Settings()
logger = logging.getLogger(__name__)

@dataclass
class SubscriptionRequest:
    """Message for subscription management"""
    action: str  # 'subscribe' or 'unsubscribe'
    symbol: str
    user_id: Optional[int] = None  # For tracking/logging

class ConnectionState(Enum):
    """Enum for upstream connection state"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTTING_DOWN  = "shutting_down"

class WebSocketManager:
    """ Manages Websocket connections with dynamic subscriptions
    allowing scope for multiple users"""
    def __init__(self, output_queue = asyncio.Queue(maxsize = 500)):
        self.finnhub_api_key = settings.FINNHUB_API_KEY
        if not self.finnhub_api_key:
            raise ValueError("FINNHUB_API_KEY variable is required")

        self.websocket: Optional[Any] = None
        self.upstream_task: Optional[asyncio.Task] = None
        self.state = ConnectionState.DISCONNECTED
        self._state_lock = asyncio.Lock()
        self._subscription_lock = asyncio.Lock()

        self.subscription_queue = asyncio.Queue(maxsize = 20)
        self.output_queue = output_queue

        self.active_subscriptions :  Dict[str , List[int]] = {}
        self.subscription_task : Optional[asyncio.Task] = None

        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5

        self.connection_task: Optional[asyncio.Task] = None
        self.queueing_task: Optional[asyncio.Task] = None


    async def connect(self):
        """Try connecting to Finnhub, return if connected"""
        async with self._state_lock:
            if self.state == ConnectionState.CONNECTED:
                return True # Exit True no need to change anything
            if self.state == ConnectionState.CONNECTING:
                return False # Already processing, dont update
            if self.state == ConnectionState.SHUTTING_DOWN:
                return False # Dont try and start during shutdown

            # If reconnecting or disconnecting I want to process
            self.state = ConnectionState.CONNECTING

        try:
            uri = f"wss://ws.finnhub.io?token={self.finnhub_api_key}"
            self.websocket = await websockets.connect(uri)
            async with self._state_lock:
                self.state = ConnectionState.CONNECTED
            logger.info("Connected to Finnhub WebSocket")

            # Reconnect all symbols
            async with self._subscription_lock:
                symbols_to_reconnect = list(self.active_subscriptions.keys())
            
            failed_symbols=[]
            for symbol in symbols_to_reconnect:
                success = await self._subscribe_symbol(symbol)
                if not success:
                    failed_symbols.append(symbol)
            if failed_symbols:
                logger.warning("Failed to resubsribe to symbols: %s ", failed_symbols)
            return True

        except Exception as e:
            logger.error("Connection failed %s",e)
            async with self._state_lock:
                self.state = ConnectionState.DISCONNECTED
                self.websocket = None
            return False

    async def disconnect(self):
        """Close WebSocket connection and clear attributed"""
        if self.websocket:
            try:
                await self.websocket.close()
                async with self._state_lock:
                    self.state = ConnectionState.DISCONNECTED
                self.websocket = None
            except Exception as e:
                logger.WARNING("Issue when diconnecting Webscocket %s",e)
        else:
            logger.info("Not connected")
        logger.info("Disconnected from WebSocket")

    async def subscribe(self, symbol: str, user_id : int)-> bool:
        """Subscribe to a symbol and optionally register a data handler
        to update database, notify frontend or process data"""
        symbol = symbol.upper()

        subscribe_symbol = False
        async with self._subscription_lock:
            if symbol in self.active_subscriptions:
                logger.info("Subscriptions to %s already present",symbol)
                if user_id in self.active_subscriptions[symbol]:
                    logger.warning("User already subscribed")
                else:
                    self.active_subscriptions[symbol].append(user_id)  # Add user directly
                return True
            else:
                subscribe_symbol = True

        if subscribe_symbol:
            subscribed = await self._subscribe_symbol(symbol)
            if subscribed:
                async with self._subscription_lock:
                    self.active_subscriptions.setdefault(symbol, []).append(user_id)
            return subscribed

        logger.info("subscription to %s queued - not connected to websocket", symbol)
        ##implement queue logic
        return False

    async def _subscribe_symbol(self, symbol : str):
        """Send subscription message for a symbol"""
        symbol = symbol.upper()
        if self.state != ConnectionState.CONNECTED:
            logger.warning("Can not subscribe to %s stock, no websocket connection", symbol)
            return False

        try:
            message = json.dumps({"type": "subscribe", "symbol":symbol})
            await self.websocket.send(message)
            logger.info("Subscribed to %s",symbol)
            return True
        except Exception as e:
            logger.error("Failed to subscribe to %s, error %s", symbol, e)
            return False

    async def unsubscribe(self, symbol: str, user_id : int)-> bool:
        """Unscribe a symbol from websocket and data handler"""
        symbol = symbol.upper()
        unsubscribed_symbol = False
        async with self._subscription_lock:
            if symbol not in self.active_subscriptions:
                logger.info("Tried to remove user from non-existent symbol: %s", symbol)
                return True 
            elif user_id not in self.active_subscriptions[symbol]:
                logger.info("Tried to remove non-existent user_id: %s from symbol: %s", user_id, symbol)
                return True
            if len(self.active_subscriptions[symbol])==1:
                unsubscribed_symbol = True

        if unsubscribed_symbol:
            unsubscribed = await self._unsubscribe_symbol(symbol)
            if not unsubscribed:
                logger.info("unsubscribe unsuccessful")
                return False

        async with self._subscription_lock:
            try:
                self.active_subscriptions[symbol].remove(user_id)
            except KeyError:
                logger.info("Tried to remove user from non-existent symbol: %s", symbol)
                return True
            except ValueError:
                logger.info("Tried to remove non-existent user_id: %s from symbol: %s", user_id, symbol)
                return True
            if len(self.active_subscriptions[symbol])==0:
                del self.active_subscriptions[symbol]
        return True


    async def _unsubscribe_symbol(self, symbol: str) -> bool:
        """Send unsubscription message for a symbol"""
        if self.state != ConnectionState.CONNECTED:
            logger.warning("Cannot unsubscribe from %s - no Websocket connection", symbol)
            return False
        try:
            message = json.dumps({"type": "unsubscribe", "symbol": symbol})
            await self.websocket.send(message)
            return True
        except Exception as e:
            logger.error("Failed to unsubscribe from %s : %s", symbol, e)
            return False


    async def get_subscriptions(self, user_id : Optional[int]) -> Set[str]:
        """Get the set of current subscriptions"""
        #Not used elsewhere so no locks
        if user_id:
            user_stocks = set()
            #TODO this is computational super inneficient
            for symbol, user_list in self.active_subscriptions.items():
                if user_id in user_list:
                    user_stocks.add(symbol)
            return user_stocks
        else:
            return set(self.active_subscriptions.keys())

    async def log_current_status(self):
        """Log comprehensive status of all subscriptions and connected users"""
        total_symbols = len(self.active_subscriptions)
        total_users = sum(len(users) for users in self.active_subscriptions.values())
        # no locks as only a snapshot of current instance, not to be used in business logic
        logger.info("=== WebSocket Manager Status ===")
        logger.info("Connection State: %s", self.state.value)
        logger.info("Total Symbols: %s", total_symbols)
        logger.info("Total User Subscriptions: %s", total_users)
        logger.info("Queue Size: %s", self.subscription_queue.qsize())

        if self.active_subscriptions:
            logger.info("Active Subscriptions:")
            for symbol, user_list in self.active_subscriptions.items():
                logger.info("  %s: %s users %s", symbol, len(user_list), user_list)
        else:
            logger.info("No active subscriptions")
        logger.info("================================")

    async def _auto_reconnect(self)-> bool:
        """Reconnect if connection is broken"""

        # Handling a reconnect can be done in a couple ways realistically
        # For loop until connect or tap out ?
        for attempt in range(1, self.max_reconnect_attempts+1):
            logger.info("reconnect attempt %s , out of a total %s",attempt, self.max_reconnect_attempts)

            delay = self.reconnect_delay * attempt
            await asyncio.sleep(delay)

            if await self.connect():
                logger.info("Reconnection successful after %s attempts",attempt)
                return True

        logger.error("All reconnection attemps failed")
        return False

    async def _process_message(self, message: str):
        """Process incoming WebSocket messages"""
        try:
            data = json.loads(message)
            # Handle different message types
            if 'data' in data:
                # Trade data
                for trade in data['data']:
                    if self.output_queue:
                        await self.output_queue.put(trade)

            elif 'type' in data:
                # Control messages
                logger.info("Control message: %s",data)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse message: %s",e)
        except Exception as e:
            logger.error("Error processing message: %s", e)

    async def start_listening(self):
        """Start listening for a WebSocket message"""
        while True:
            try:
                await self.connect()

                async for message in self.websocket:
                    if message == 1:
                        logger.debug("Recieved ping")
                        continue
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    #logger.info("Processing messagge %s",message)
                    await self._process_message(message)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection lost, attempting reconnect...")
                if not await self._auto_reconnect():
                    logger.error("Reconnection failed, stopping listener")
                    break
            except Exception as e:
                logger.error("error occured %s",e)
                break#

    async def start(self):
        """Start the WebSocket manager"""
        if self.connection_task and not self.connection_task.done():
            return

        self.connection_task = asyncio.create_task(self.start_listening())
        self.queueing_task = asyncio.create_task(self._process_subscription_queue())
        logger.info("WebSocket manager started")

    async def stop(self):
        """Stop the WebSocket manager"""
        if self.queueing_task:
            self.queueing_task.cancel()
            try:
                await self.queueing_task
            except asyncio.CancelledError:
                pass
        if self.connection_task:
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass
        await self.disconnect()
        logger.info("WebSocket manager stopped")


    # Handling the queueing aspect
    async def enqueue_subscription(self, symbol:str, user_id: int, action:str = "subscribe"):
        """External interface for queueinng subscription requests"""
        request = SubscriptionRequest(action=action, symbol=symbol, user_id= user_id)
        try:
            await self.subscription_queue.put(request)
            logger.info("Queued %s request for %s, user %s", action, symbol, user_id)
        except asyncio.QueueFull:
            logger.error("Subscription queue full, dropping %s request",action)
            return False
        return True

    async def enqueue_unsubscription(self, symbol: str, user_id: int):
        """External interface for queueing unsubscription requests"""
        return await self.enqueue_subscription(symbol, user_id, "unsubscribe")

    async def _process_subscription_queue(self):
        """Continuously process subscription requests - independent of connection state"""
        while True:
            try:
                request = await self.subscription_queue.get()
                await self._handle_queue_request(request)
                self.subscription_queue.task_done()

            except Exception as e:
                logger.error("Error processing subscription queue: %s",e)
                self.subscription_queue.task_done()

    async def _handle_queue_request(self, request: SubscriptionRequest ):
        success = False
        if request.action == "subscribe":
            success = await self.subscribe(request.symbol, request.user_id)
        elif request.action == "unsubscribe":
            success = await self.unsubscribe(request.symbol, request.user_id)
        if not success and self.state != ConnectionState.CONNECTED:
            logger.info("Subscription queued- will process when connected")


