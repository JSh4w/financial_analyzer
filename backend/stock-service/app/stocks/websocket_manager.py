# backend/python-service/app/main_test.py
from typing import Optional, Any, Set, Dict, List
from dataclasses import dataclass, field
from collections import defaultdict
import json
import asyncio
import logging
import copy
import time 
from enum import Enum

import websockets

from app.stocks.errors import ConnectionFailedError
from app.config import Settings

settings = Settings()
logger = logging.getLogger(__name__)


@dataclass
class SubscriptionConfig:
    """Configuration for different subscription types"""

    subscription_type: str  # 'trades', 'quotes', 'bars'
    max_symbols: Optional[int] = None  # None means unlimited
    message_type_identifier: str = None  # 't' for trades, 'q' for quotes, 'b' for bars

    def __post_init__(self):
        if self.message_type_identifier is None:
            type_map = {"trades": "t", "quotes": "q", "bars": "b"}
            self.message_type_identifier = type_map.get(self.subscription_type, "t")

    def create_subscribe_message(self, symbols: List[str]) -> str:
        """Create subscription message for Alpaca API"""
        return json.dumps({"action": "subscribe", self.subscription_type: symbols})

    def create_unsubscribe_message(self, symbols: List[str]) -> str:
        """Create unsubscription message for Alpaca API"""
        return json.dumps({"action": "unsubscribe", self.subscription_type: symbols})


@dataclass
class AlpacaSubscriptionSettings:
    """Alpaca API subscription settings and limits"""

    trades: SubscriptionConfig = field(
        default_factory=lambda: SubscriptionConfig("trades", 30, "t")
    )
    quotes: SubscriptionConfig = field(
        default_factory=lambda: SubscriptionConfig("quotes", 30, "q")
    )
    bars: SubscriptionConfig = field(
        default_factory=lambda: SubscriptionConfig("bars", None, "b")
    )

    def get_config(self, subscription_type: str) -> SubscriptionConfig:
        return getattr(self, subscription_type, self.trades)

    def get_all_configs(self) -> Dict[str, SubscriptionConfig]:
        return {"trades": self.trades, "quotes": self.quotes, "bars": self.bars}


@dataclass
class SubscriptionRequest:
    """Message for subscription management"""

    action: str  # 'subscribe' or 'unsubscribe'
    symbol: str
    subscription_type: str = "trades"  # Default to trades for backward compatibility
    user_id: Optional[int] = None  # For tracking/logging


class ConnectionState(Enum):
    """Enum for upstream connection state"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTTING_DOWN = "shutting_down"


class WebSocketManager:
    """Manages Websocket connections with dynamic subscriptions
    allowing scope for multiple users"""

    def __init__(
        self,
        output_queue=asyncio.Queue(maxsize=500),
        uri: str = None,
        headers: Dict[str, str] = None,
        subscription_settings: AlpacaSubscriptionSettings = None,
    ):
        # default to test environment
        self._uri = uri or "wss://stream.data.alpaca.markets/v2/test"
        self._headers = headers or {
            "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": settings.ALPACA_API_SECRET,
        }
        self.subscription_settings = (
            subscription_settings or AlpacaSubscriptionSettings()
        )

        self._websocket: Optional[Any] = None
        self.upstream_task: Optional[asyncio.Task] = None
        self.state = ConnectionState.DISCONNECTED
        self._state_lock = asyncio.Lock()
        self._symbol_subscription_locks = defaultdict(asyncio.Lock)

        self.subscription_queue = asyncio.Queue(maxsize=20)
        self.output_queue = output_queue

        # symbol -> subscription_type -> users
        self.active_subscriptions: Dict[str, Dict[str, Set[int]]] = {}
        self._subscription_task: Optional[asyncio.Task] = None

        self._max_reconnect_attempts = 3
        self._reconnect_delay = 2
        self._max_reconnect_delay = 60  # Max 60 seconds between attempts

        self.connection_task: Optional[asyncio.Task] = None
        self.queueing_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Try connecting to Alpaca, return True if connected"""
        logger.info("Attempting to connect to WebSocket: %s",self._uri)
        async with self._state_lock:
            if self.state == ConnectionState.CONNECTED:
                logger.info("Already connected")
                return True  # Exit True no need to change anything
            if self.state == ConnectionState.CONNECTING:
                logger.info("Already connecting")
                return False  # Already processing, dont update
            if self.state == ConnectionState.SHUTTING_DOWN:
                logger.info("Websocket is shutdown")
                return False  # Dont try and start during shutdown
            # If reconnecting or disconnecting I want to proceed
            self.state = ConnectionState.CONNECTING
        try:

            async with self._state_lock:
                # Reconnect all symbols
                self._websocket = await websockets.connect(
                    self._uri, additional_headers=self._headers, ping_interval=None
                )
                # Alpaca sends two messages on connect:
                # 1. Welcome message
                connect_response = await asyncio.wait_for(
                    self._websocket.recv(), timeout=10
                )
                logger.debug("Connect response: %s", json.loads(connect_response))
                # 2. Authentication response
                raw_auth = await asyncio.wait_for(self._websocket.recv(), timeout=10)
                auth_data = json.loads(raw_auth)
                logger.info("Auth response: %s",auth_data)
                if isinstance(auth_data, list) and len(auth_data) >0:
                    first_msg = auth_data[0]
                    if auth_data[0].get('T')=='error':
                        code, msg = first_msg.get('code'), first_msg.get('msg')
                        logger.error("Auth failed %s, %s", code,msg)
                        self.state = ConnectionState.DISCONNECTED
                        raise ConnectionFailedError(msg,code)
                self.state = ConnectionState.CONNECTED
                logger.info("Connected to Alpaca WebSocket")
                # Snapshot of active subscriptions
                symbols_to_reconnect = copy.deepcopy(self.active_subscriptions)

            failed_symbols = []
            for symbol in symbols_to_reconnect.keys():
                async with self._symbol_subscription_locks[symbol]:
                    if symbol not in self.active_subscriptions:
                        continue
                    for _type in list(symbols_to_reconnect[symbol].keys()):
                        if _type not in self.active_subscriptions[symbol]:
                            continue
                        success = await self._subscribe_symbol(symbol, _type)
                        if not success:
                            failed_symbols.append((symbol, type))
            if failed_symbols:
                logger.warning("Failed to resubsribe to symbols: %s ", failed_symbols)
            return True
        except Exception as e:
            logger.info("Disconnected for another reason")
            async with self._state_lock:
                await self._websocket.close()
                self.state = ConnectionState.DISCONNECTED
            raise e



    async def disconnect(self):
        """Close WebSocket connection and clear attributed"""
        if self._websocket:
            try:
                async with self._state_lock:
                    await self._websocket.close()
                    self.state = ConnectionState.DISCONNECTED
                    self._websocket = None
            except Exception as e:
                logger.WARNING("Issue when diconnecting Websocket %s", e)
        else:
            logger.info("Not connected")
        logger.info("Disconnected from WebSocket")

    async def subscribe(
        self, symbol: str, user_id: int, subscription_type: str = "trades"
    ) -> bool:
        """Subscribe to a symbol and optionally register a data handler
        to update database, notify frontend or process data"""
        symbol = symbol.upper()

        # Check subscription limits
        config = self.subscription_settings.get_config(subscription_type)
        if config.max_symbols is not None:
            current_count = len(
                [
                    s for s in self.active_subscriptions
                    if subscription_type in self.active_subscriptions[s]
                ]
            )
            if current_count >= config.max_symbols:
                logger.warning(
                    "Subscription limit reached for %s (max: %d)",
                    subscription_type,
                    config.max_symbols,
                )
                return False

        if (
            symbol in self.active_subscriptions
            and subscription_type in self.active_subscriptions[symbol]
        ):
            # Already subscribed to this symbol+type combo
            if user_id in self.active_subscriptions[symbol][subscription_type]:
                logger.info(
                    "User %d already subscribed to %s %s",
                    user_id,
                    symbol,
                    subscription_type,
                )
                return True
            else:
                self.active_subscriptions[symbol][subscription_type].add(user_id)
                return True

        async with self._symbol_subscription_locks[symbol]:
            # Need to subscribe to this symbol+type combo via API
            subscribed = await self._subscribe_symbol(symbol, subscription_type)
            if subscribed:
                if symbol not in self.active_subscriptions:
                    self.active_subscriptions[symbol] = {}
                if subscription_type not in self.active_subscriptions[symbol]:
                    self.active_subscriptions[symbol][subscription_type] = set()
                self.active_subscriptions[symbol][subscription_type].add(user_id)
                return True

        logger.info(
            "subscription to %s %s dropped - not connected to websocket",
            symbol,
            subscription_type,
        )
        return False

    async def _subscribe_symbol(self, symbol: str, subscription_type: str = "trades"):
        """Send subscription message for a symbol"""
        symbol = symbol.upper()
        if self.state != ConnectionState.CONNECTED:
            logger.warning(
                "Can not subscribe to %s %s, no websocket connection",
                symbol,
                subscription_type,
            )
            return False

        try:
            config = self.subscription_settings.get_config(subscription_type)
            message = config.create_subscribe_message([symbol])
            await self._websocket.send(message)
            logger.info("Subscribed to %s %s", symbol, subscription_type)
            return True
        except Exception as e:
            logger.error(
                "Failed to subscribe to %s %s, error %s", symbol, subscription_type, e
            )
            return False

    async def unsubscribe(
        self, symbol: str, user_id: int, subscription_type: str = "trades"
    ) -> bool:
        """Unsubscribe a symbol from websocket and data handler"""
        symbol = symbol.upper()
        unsubscribe_symbol_type = False

        if (
            symbol not in self.active_subscriptions
            or subscription_type not in self.active_subscriptions[symbol]
        ):
            logger.info(
                "Tried to remove user from non-existent symbol+type: %s %s",
                symbol,
                subscription_type,
            )
            return True

        if user_id not in self.active_subscriptions[symbol][subscription_type]:
            logger.info(
                "Tried to remove non-existent user_id: %s from symbol: %s %s",
                user_id,
                symbol,
                subscription_type,
            )
            return True

        # Check if this is the last user for this symbol+type combo
        if len(self.active_subscriptions[symbol][subscription_type]) == 1:
            unsubscribe_symbol_type = True

        if unsubscribe_symbol_type:
            async with self._symbol_subscription_locks[symbol]:
                unsubscribed = await self._unsubscribe_symbol(symbol, subscription_type)
                if not unsubscribed:
                    logger.info(
                        "unsubscribe unsuccessful for %s %s", symbol, subscription_type
                    )
                    return False
                self.active_subscriptions[symbol][subscription_type].discard(user_id)

                # Clean up empty structures
                if len(self.active_subscriptions[symbol][subscription_type]) == 0:
                    del self.active_subscriptions[symbol][subscription_type]
                    if len(self.active_subscriptions[symbol]) == 0:
                        del self.active_subscriptions[symbol]
        else:
            self.active_subscriptions[symbol][subscription_type].discard(user_id)

        return True

    async def _unsubscribe_symbol(
        self, symbol: str, subscription_type: str = "trades"
    ) -> bool:
        """Send unsubscription message for a symbol"""
        if self.state != ConnectionState.CONNECTED:
            logger.warning(
                "Cannot unsubscribe from %s %s - no Websocket connection",
                symbol,
                subscription_type,
            )
            return False
        try:
            config = self.subscription_settings.get_config(subscription_type)
            message = config.create_unsubscribe_message([symbol])
            await self._websocket.send(message)
            logger.info("Unsubscribed from %s %s", symbol, subscription_type)
            return True
        except Exception as e:
            logger.error(
                "Failed to unsubscribe from %s %s: %s", symbol, subscription_type, e
            )
            return False

    async def get_subscriptions(self, user_id: Optional[int]) -> Set[str]:
        """Get the set of current subscriptions"""
        # Not used elsewhere so no locks
        if user_id:
            user_stocks = set()
            # TODO this is computational super inneficient
            for symbol, trade_list in self.active_subscriptions.items():
                for trade_type in trade_list:
                    if user_id in trade_list[trade_type]:
                        user_stocks.add((symbol,trade_type))

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

    async def _auto_reconnect(self) -> bool:
        """Reconnect if connection is broken with exponential backoff"""

        for attempt in range(0, self._max_reconnect_attempts+1):
            # Exponential backoff: delay grows with consecutive failures
            # 2s, 4s, 8s, 16s, 32s, 60s (max)
            base_delay = self._reconnect_delay * attempt
            delay = min(base_delay, self._max_reconnect_delay)
            logger.info(
                "Attempt %s/%s, waiting %ss",
                attempt,
                self._max_reconnect_attempts,
                delay,
            )
            await asyncio.sleep(delay)
            try:
                if await self.connect():
                    return True
            except ConnectionFailedError as e:
                if int(e.code) in [401, 403, 404]:
                    logger.critical("FATAL ERROR: Server rejected handshake with %s.",e.code)
                    logger.critical("Check your API Key and URL. NOT Retrying.")
                    raise ConnectionFailedError(e.message,e.code) from e 
            except websockets.exceptions.ConnectionClosed as e:
                if e.code in [1008, 1002, 1003]:
                    logger.critical("FATAL: Connection closed by server. Code: %s" , e.code)
                    raise ConnectionFailedError("Connection closed by server",e.code) from e
                if e.code in [1006]:
                    logger.info("Improper handshake closing, try again")
                    continue
            except (OSError, asyncio.TimeoutError) as e:
                logger.error("Network error : %s", e)
                continue
            except Exception as e:
                logger.info("Unknown error: %s,  trying again",e)
                continue
            finally:
                if attempt == self._max_reconnect_attempts:
                    logger.info("Sleeping for 10 minutes ")
                    await asyncio.sleep(600)   


    async def _process_message(self, message: str):
        """Process incoming Alpaca WebSocket messages"""
        # Import here to avoid circular import
        from app.main import time_function

        @time_function("websocket_process_message")
        async def process_message_data():
            data = json.loads(message)

            # Handle array of messages (Alpaca format)
            logger.debug(f"data is {data}")
            if isinstance(data, list):
                message_count = 0
                for msg in data:
                    if self.output_queue:
                        message_count += 1
                        await self.output_queue.put(msg)
                if message_count > 0:
                    logger.debug(f"Queued {message_count} market data messages")
            else:
                # Single message
                if self.output_queue:
                    await self.output_queue.put(data)
                else:
                    logger.info("Control/unknown message: %s", data)

        try:
            await process_message_data()
        except json.JSONDecodeError as e:
            logger.error("Failed to parse message: %s", e)
        except Exception as e:
            logger.error("Error processing message: %s", e)

    async def start_listening(self):
        """Start listening for a WebSocket message"""
        while True:
            try:
                if not self._websocket:
                    await self._auto_reconnect()

                if self._websocket:
                    async for message in self._websocket:
                        if message == 1:
                            logger.debug("Recieved ping")
                            continue
                        if isinstance(message, bytes):
                            message = message.decode("utf-8")
                        logger.info("Processing message %s", message)
                        await self._process_message(message)
            #Error code during connection
            except ConnectionFailedError as e:
                logger.warning("FAIL: %s",e)
                return 
            # # Closed from the server side
            except websockets.exceptions.ConnectionClosed as e:
                if e.code in [1008, 1002, 1003]:
                    logger.critical("FATAL: Connection closed by server. Code: %s" , e.code)
                    return
                logger.warning("Connection lost. Code: %s", e.code)
                await self._auto_reconnect()
            # DNS / Wifi / Timeout failures
            except (OSError, asyncio.TimeoutError) as e:
                logger.error("Network error: %s", e)
                self._websocket = None
                await self._auto_reconnect()
            # Shutdown from command line
            except asyncio.CancelledError:
                if self._websocket:
                    await self._websocket.close()
                break
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
    async def enqueue_subscription(
        self, symbol: str, user_id: int, action: str = "subscribe"
    ):
        """External interface for queueinng subscription requests"""
        request = SubscriptionRequest(action=action, symbol=symbol, user_id=user_id)
        try:
            await self.subscription_queue.put(request)
            logger.info("Queued %s request for %s, user %s", action, symbol, user_id)
        except asyncio.QueueFull:
            logger.error("Subscription queue full, dropping %s request", action)
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
            except asyncio.CancelledError:
                logger.info("Subscription processing task cancelled.")
                break
            except Exception as e:
                logger.error("Error processing subscription queue: %s", e)
                self.subscription_queue.task_done()

    async def _handle_queue_request(self, request: SubscriptionRequest):
        """Handles a single request"""
        success = False
        if request.action == "subscribe":
            success = await self.subscribe(request.symbol, request.user_id)
        elif request.action == "unsubscribe":
            success = await self.unsubscribe(request.symbol, request.user_id)
        else:
            logger.error("Request %s, is not legal", request)
        if not success and self.state != ConnectionState.CONNECTED:
            logger.info("Subscription queued- will process when connected")
