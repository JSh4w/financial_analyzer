"""News based websocket manager"""
import asyncio
import json
from app.config import Settings
from logging import getLogger 

import websockets


settings = Settings()
logger = getLogger(__name__)

class NewsWebsocket:
    """Basic websocket setup - for single news source"""
    def __init__(self, uri = None, headers = None, output_queue = None):
        self._uri = uri or  "wss://stream.data.alpaca.markets/v1beta1/news"
        self._websocket = None
        self._headers = headers or {
              "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
              "APCA-API-SECRET-KEY": settings.ALPACA_API_SECRET
          }
        self._output_queue = output_queue
        self.connection_task = None
        self.queueing_task = None
        

    async def connect(self):
        """Connect to websocket"""
        try:
            self._websocket = await websockets.connect(self._uri, additional_headers=self._headers)
            connect_response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
            logger.info("Connect response: %s",json.loads(connect_response))
            auth_response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
            auth_data = json.loads(auth_response)
            logger.info("Auth response: %s", auth_data)

            # Check for connection limit error
            if isinstance(auth_data, list):
                for msg in auth_data:
                    if msg.get('T') == 'error' and msg.get('code') == 406:
                        logger.error("Connection limit exceeded: %s. Please close other connections.", msg.get('msg'))
                        if self._websocket:
                            await self._websocket.close()
                        self._websocket = None
                        return False

            # Subscribe to all news after successful authentication
            subscribe_msg = json.dumps({"action": "subscribe", "news": ["*"]})
            await self._websocket.send(subscribe_msg)
            logger.info("Subscribed to all news feeds")

            # Wait for subscription confirmation
            sub_response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
            logger.info("Subscription response %s",json.loads(sub_response))

            return True
        except websockets.exceptions.InvalidStatus as e:
            logger.error("Connection failed, possible due to an invalid key: %s",e)
            self._websocket = None
            return False
        except Exception as e:
            logger.error("Connection failed %s",e)
            self._websocket = None
            return False


    async def listen(self):
        while True:
            try:
                await self.connect()
                message_count = 0 
                async for message in self._websocket:
                    message_count +=1
                    if message == 1:
                        logger.debug("Recieved ping")
                        continue
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    await self.process(message)
            except(websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidURI,
                    websockets.exceptions.WebSocketException,
                    asyncio.TimeoutError) as e:
                logger.warning("Connection issue (%s), attempting reconnect...", type(e).__name__)
                if not await self.connect():
                    logger.error("Reconnection failed, stopping listener")
                    break
            except Exception as e:
                logger.error("Unexpected error (%s: %s), attempting reconnect...", type(e).__name__, e)
                if not await self.connect():
                    logger.error("Reconnection failed, stopping listener")
                    break

    async def process(self,message):
        try:
            data = json.loads(message)
            if isinstance(data,list):
                message_count = 0
                for msg in data:
                    logger.info("NEWS ITEM: %s",msg)
                    if self._output_queue:
                        await self._output_queue.put(msg)
                        message_count += 1
                if message_count > 0:
                    logger.debug(f"Queued {message_count} news messages")
            else:
                # Single message
                if self._output_queue:
                    await self._output_queue.put(data)
                else:
                    logger.info("Control/unknown message: %s", data)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse message: %s", e)
        except Exception as e:
            logger.error("Error processing message: %s", e)
    
    async def start(self):
        """Start the WebSocket manager"""
        if self.connection_task and not self.connection_task.done():
            return

        self.connection_task = asyncio.create_task(self.listen())
        logger.info("WebSocket manager started")

    async def stop(self):
        """Stop the WebSocket manager"""
        if self.connection_task:
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass
        await self.disconnect()
        logger.info("WebSocket manager stopped")

    async def disconnect(self):
        """Close WebSocket connection and clear attributes"""
        if self._websocket:
            try:
                await self._websocket.close()
                self._websocket = None
            except Exception as e:
                logger.warning("Issue when disconnecting WebSocket: %s",e)
        else:
            logger.info("Not connected")
        logger.info("Disconnected from WebSocket")

    @staticmethod
    def process_news_data(data):
        """Process news data from Alpaca API"""
        if not data.get('created_at') or not data.get('headline'):
            raise ValueError("Missing required news fields")
        
        return {
            'time': data['created_at'],
            'headline': data['headline'],
            'summary': data.get('summary', ''),
            'tickers': data.get('symbols', []),
            'source': data.get('source', 'Alpaca'),
            'url': data.get('url', '')
        }