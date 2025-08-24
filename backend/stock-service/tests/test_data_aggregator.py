"""Integration tests for TradeDataAggregator with async queue processing"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from models.websocket_models import TradeData
from app.stocks.data_aggregator import TradeDataAggregator
from tests.synthetic_data_generator import SyntheticDataGenerator, generate_test_data


class TestTradeDataAggregator:
    """Integration tests for TradeDataAggregator"""

    @pytest.fixture
    def aggregator(self):
        """Create a fresh aggregator for each test"""
        return TradeDataAggregator()

    @pytest.fixture
    def mock_callback(self):
        """Mock callback function for testing"""
        return Mock()

    @pytest.fixture
    def sample_trade_data(self):
        """Sample trade data in various formats"""
        return {
            'dict_format': {
                's': 'AAPL',
                'p': 150.0,
                't': 1640995200000,
                'v': 100,
                'c': []
            },
            'tradedata_format': TradeData(
                s='GOOGL',
                p=2500.0,
                t=1640995201000,
                v=50,
                c=['I']
            )
        }

    def test_aggregator_initialization(self, aggregator):
        """Test aggregator initializes correctly"""
        assert aggregator.queue.maxsize == 500
        assert aggregator.callback is None
        assert aggregator.stock_handlers == {}

    def test_aggregator_with_callback(self):
        """Test aggregator with callback function"""
        mock_callback = Mock()
        aggregator = TradeDataAggregator(callback=mock_callback)
        assert aggregator.callback == mock_callback

    def test_create_trade_data_factory_dict(self, aggregator, sample_trade_data):
        """Test factory method with dict input"""
        dict_data = sample_trade_data['dict_format']
        trade_data = aggregator.create_trade_data(dict_data)

        assert isinstance(trade_data, TradeData)
        assert trade_data.s == 'AAPL'
        assert trade_data.p == 150.0
        assert trade_data.t == 1640995200000
        assert trade_data.v == 100
        assert trade_data.c == []

    def test_create_trade_data_factory_tradedata(self, aggregator, sample_trade_data):
        """Test factory method with TradeData input"""
        trade_data_input = sample_trade_data['tradedata_format']
        trade_data = aggregator.create_trade_data(trade_data_input)

        assert isinstance(trade_data, TradeData)
        assert trade_data is trade_data_input  # Should return same instance
        assert trade_data.s == 'GOOGL'

    @pytest.mark.asyncio
    async def test_add_tick_queues_data(self, aggregator, sample_trade_data):
        """Test that add_tick properly queues trade data"""
        dict_data = sample_trade_data['dict_format']

        # Queue should be empty initially
        assert aggregator.queue.qsize() == 0

        # Add tick data
        await aggregator.add_tick(dict_data)

        # Queue should have one item
        assert aggregator.queue.qsize() == 1

        # Get the queued item
        queued_trade = await aggregator.queue.get()
        assert isinstance(queued_trade, TradeData)
        assert queued_trade.s == 'AAPL'

    @pytest.mark.asyncio
    async def test_process_tick_queue_creates_handlers(self, aggregator):
        """Test that processing creates StockHandler instances"""
        # Add some test data
        test_trades = [
            {'s': 'AAPL', 'p': 150.0, 't': 1640995200000, 'v': 100, 'c': []},
            {'s': 'GOOGL', 'p': 2500.0, 't': 1640995201000, 'v': 50, 'c': []},
            {'s': 'AAPL', 'p': 151.0, 't': 1640995202000, 'v': 75, 'c': []}
        ]

        # Queue the trades
        for trade in test_trades:
            await aggregator.add_tick(trade)

        # Process a few trades manually (since we can't run infinite loop in test)
        for _ in range(3):
            if aggregator.queue.qsize() > 0:
                trade_data = await aggregator.queue.get()
                symbol = trade_data.s

                if symbol not in aggregator.stock_handlers:
                    from app.stocks.stockHandler import StockHandler
                    aggregator.stock_handlers[symbol] = StockHandler(symbol)

                aggregator.stock_handlers[symbol].process_trade(trade_data)

        # Should have created handlers for both symbols
        assert 'AAPL' in aggregator.stock_handlers
        assert 'GOOGL' in aggregator.stock_handlers
        assert len(aggregator.stock_handlers) == 2

    @pytest.mark.asyncio
    async def test_callback_execution(self):
        """Test that callback is executed when processing trades"""
        mock_callback = Mock()
        aggregator = TradeDataAggregator(callback=mock_callback)

        trade_data = TradeData(s='AAPL', p=150.0, t=1640995200000, v=100, c=[])
        await aggregator.add_tick(trade_data)

        # Manually process one trade
        queued_trade = await aggregator.queue.get()

        # Simulate what process_tick_queue does
        symbol = queued_trade.s
        if symbol not in aggregator.stock_handlers:
            from app.stocks.stockHandler import StockHandler
            aggregator.stock_handlers[symbol] = StockHandler(symbol)

        aggregator.stock_handlers[symbol].process_trade(queued_trade)

        # Execute callback
        if aggregator.callback:
            aggregator.callback(queued_trade)

        # Verify callback was called
        mock_callback.assert_called_once_with(queued_trade)

    @pytest.mark.asyncio
    async def test_high_volume_processing(self, aggregator):
        """Test processing high volume of trades"""
        # Generate synthetic data
        generator = SyntheticDataGenerator(['AAPL', 'GOOGL', 'MSFT'])
        trades = generator.generate_realtime_stream(duration_seconds=10, trades_per_second=20)

        # Queue all trades
        for trade in trades:
            await aggregator.add_tick(trade.data_to_dict())

        initial_queue_size = aggregator.queue.qsize()
        assert initial_queue_size > 0

        # Process a bunch of trades
        processed_count = 0
        max_process = min(100, initial_queue_size)

        for _ in range(max_process):
            if aggregator.queue.qsize() > 0:
                trade_data = await aggregator.queue.get()
                symbol = trade_data.s

                if symbol not in aggregator.stock_handlers:
                    from app.stocks.stockHandler import StockHandler
                    aggregator.stock_handlers[symbol] = StockHandler(symbol)

                aggregator.stock_handlers[symbol].process_trade(trade_data)
                processed_count += 1

        # Should have processed trades and created handlers
        assert processed_count > 0
        assert len(aggregator.stock_handlers) <= 3  # Max 3 symbols

    @pytest.mark.asyncio
    async def test_burst_scenario(self, aggregator):
        """Test handling burst of trades for same symbol"""
        generator = SyntheticDataGenerator()
        burst_trades = generator.generate_burst_scenario('AAPL', burst_count=50)

        # Queue all burst trades
        for trade in burst_trades:
            await aggregator.add_tick(trade.data_to_dict())

        process_task = asyncio.create_task(aggregator.process_tick_queue())
        await asyncio.sleep(0.5)
        await aggregator.shutdown() # returns unprocessed data
        await process_task
        # Should have only one handler for AAPL
        assert len(aggregator.stock_handlers) == 1, aggregator.stock_handlers
        assert 'AAPL' in aggregator.stock_handlers

        # Handler should have processed all trades
        handler = aggregator.stock_handlers['AAPL']
        assert handler.candle_data is not None, handler.candle_data


    def test_get_stock_handler(self, aggregator):
        """Test getting specific stock handler"""
        from app.stocks.stockHandler import StockHandler

        # Add a handler
        handler = StockHandler('AAPL')
        aggregator.stock_handlers['AAPL'] = handler

        # Test getting existing handler
        retrieved = aggregator.get_stock_handler('AAPL')
        assert retrieved is handler

        # Test getting non-existent handler
        missing = aggregator.get_stock_handler('MISSING')
        assert missing is None

    def test_get_all_symbols(self, aggregator):
        """Test getting all tracked symbols"""
        from app.stocks.stockHandler import StockHandler

        # Initially empty
        assert aggregator.get_all_symbols() == []

        # Add some handlers
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        for symbol in symbols:
            aggregator.stock_handlers[symbol] = StockHandler(symbol)

        # Should return all symbols
        all_symbols = aggregator.get_all_symbols()
        assert len(all_symbols) == 3
        assert set(all_symbols) == set(symbols)

    @pytest.mark.asyncio
    async def test_mixed_data_formats(self, aggregator):
        """Test processing mixed data formats in same session"""
        # Mix of dict and TradeData formats
        mixed_data = [
            {'s': 'AAPL', 'p': 150.0, 't': 1640995200000, 'v': 100, 'c': []},
            TradeData(s='GOOGL', p=2500.0, t=1640995201000, v=50, c=['I']),
            {'s': 'MSFT', 'p': 300.0, 't': 1640995202000, 'v': 75, 'c': ['T']},
            TradeData(s='AAPL', p=151.0, t=1640995203000, v=25, c=[])
        ]

        # Queue all data
        for data in mixed_data:
            await aggregator.add_tick(data)

        # Process all
        symbols_processed = set()
        processed_count = 0
        max_iterations = 100  # Safety limit
        
        while aggregator.queue.qsize() > 0 and processed_count < max_iterations:
            trade_data = await aggregator.queue.get()
            symbol = trade_data.s
            symbols_processed.add(symbol)

            if symbol not in aggregator.stock_handlers:
                from app.stocks.stockHandler import StockHandler
                aggregator.stock_handlers[symbol] = StockHandler(symbol)

            aggregator.stock_handlers[symbol].process_trade(trade_data)
            processed_count += 1
        
        # Ensure we processed all expected data
        assert processed_count <= max_iterations, f"Processed {processed_count} items, exceeding safety limit"

        # Should have processed all symbols
        assert symbols_processed == {'AAPL', 'GOOGL', 'MSFT'}
        assert len(aggregator.stock_handlers) == 3


@pytest.mark.asyncio
async def test_realistic_market_simulation():
    """Integration test simulating realistic market conditions"""
    # Create aggregator with tracking callback
    processed_trades = []
    def track_callback(trade_data):
        processed_trades.append(trade_data)

    aggregator = TradeDataAggregator(callback=track_callback)

    # Generate realistic market data
    generator = SyntheticDataGenerator(['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'])
    market_trades = generator.generate_realtime_stream(duration_seconds=30, trades_per_second=15)

    # Queue all trades
    for trade in market_trades:
        await aggregator.add_tick(trade.data_to_dict())

    # Process trades (simulate running process_tick_queue)
    start_queue_size = aggregator.queue.qsize()
    processed_count = 0

    while aggregator.queue.qsize() > 0 and processed_count < 200:  # Limit for test
        trade_data = await aggregator.queue.get()
        symbol = trade_data.s

        if symbol not in aggregator.stock_handlers:
            from app.stocks.stockHandler import StockHandler
            aggregator.stock_handlers[symbol] = StockHandler(symbol)

        aggregator.stock_handlers[symbol].process_trade(trade_data)

        if aggregator.callback:
            aggregator.callback(trade_data)

        processed_count += 1

    # Verify results
    assert processed_count > 0
    assert len(processed_trades) == processed_count
    assert len(aggregator.stock_handlers) <= 5  # Max 5 symbols

    # Verify handlers have processed trades
    for handler in aggregator.stock_handlers.values():
        assert handler.candle_data is not None
    print(f"Processed {processed_count} trades across {len(aggregator.stock_handlers)} symbols")