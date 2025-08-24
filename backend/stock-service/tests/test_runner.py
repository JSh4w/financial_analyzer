"""Test runner script for manual testing and demos"""
import asyncio
import json
from pathlib import Path

from tests.synthetic_data_generator import SyntheticDataGenerator, generate_demo_data, generate_test_data
from models.websocket_models import TradeData
from app.stocks.data_aggregator import TradeDataAggregator
from app.stocks.stockHandler import StockHandler


async def demo_realtime_processing():
    """Demo of real-time trade processing"""
    print("=== Real-time Processing Demo ===")
    
    # Create aggregator with callback to track processed trades
    processed_count = 0
    def track_trades(trade_data):
        nonlocal processed_count
        processed_count += 1
        if processed_count % 100 == 0:
            print(f"Processed {processed_count} trades...")
    
    aggregator = TradeDataAggregator(callback=track_trades)
    
    # Generate synthetic data
    generator = SyntheticDataGenerator(['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'])
    trades = generator.generate_realtime_stream(duration_seconds=60, trades_per_second=10)
    
    print(f"Generated {len(trades)} trades for 5 symbols over 60 seconds")
    
    # Start processing task
    async def process_trades():
        max_iterations = 10000  # Safety limit
        iteration = 0
        while iteration < max_iterations:
            if aggregator.queue.qsize() > 0:
                trade_data = await aggregator.queue.get()
                symbol = trade_data.s
                
                if symbol not in aggregator.stock_handlers:
                    aggregator.stock_handlers[symbol] = StockHandler(symbol)
                
                aggregator.stock_handlers[symbol].process_trade(trade_data)
                
                if aggregator.callback:
                    aggregator.callback(trade_data)
            else:
                await asyncio.sleep(0.001)  # Small delay when queue is empty
            iteration += 1
        
        print(f"Process trades loop completed after {iteration} iterations")
    
    # Start processor
    processor_task = asyncio.create_task(process_trades())
    
    # Queue trades with realistic timing
    for i, trade in enumerate(trades):
        await aggregator.add_tick(trade.data_to_dict())
        
        # Add small delay to simulate real-time
        if i % 50 == 0:
            await asyncio.sleep(0.1)
    
    # Let processing finish
    await asyncio.sleep(1)
    processor_task.cancel()
    
    # Show results
    print(f"\nProcessed {processed_count} trades")
    print(f"Created handlers for {len(aggregator.stock_handlers)} symbols")
    
    for symbol, handler in aggregator.stock_handlers.items():
        candle = handler._current_candle
        if candle:
            print(f"{symbol}: O:{candle['open']:.2f} H:{candle['high']:.2f} "
                  f"L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")


def demo_unit_testing():
    """Demo of unit testing capabilities"""
    print("\n=== Unit Testing Demo ===")
    
    # Test StockHandler directly
    handler = StockHandler("DEMO")
    
    # Create sample trades
    test_trades = generate_test_data("DEMO", count=10)
    
    print(f"Processing {len(test_trades)} trades for DEMO symbol")
    
    for trade in test_trades:
        handler.process_trade(trade)
    
    candle = handler._current_candle
    print(f"Final OHLCV: O:{candle['open']:.2f} H:{candle['high']:.2f} "
          f"L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}")


def demo_synthetic_data():
    """Demo of synthetic data generation"""
    print("\n=== Synthetic Data Demo ===")
    
    generator = SyntheticDataGenerator()
    
    # Generate different types of data
    single_trade = generator.generate_single_trade("AAPL")
    print(f"Single trade: {single_trade.s} @ ${single_trade.p} vol:{single_trade.v}")
    
    burst_trades = generator.generate_burst_scenario("TSLA", 5)
    print(f"Generated {len(burst_trades)} burst trades for TSLA")
    
    # Save demo data
    demo_trades = generate_demo_data(symbols_count=3, days=1)
    generator.save_to_file(demo_trades, "demo_output.json")
    print(f"Saved {len(demo_trades)} demo trades to demo_output.json")


async def stress_test():
    """Stress test with high volume"""
    print("\n=== Stress Test ===")
    
    aggregator = TradeDataAggregator()
    
    # Generate high volume data
    generator = SyntheticDataGenerator()
    trades = generator.generate_realtime_stream(duration_seconds=10, trades_per_second=100)
    
    print(f"Stress testing with {len(trades)} trades")
    
    # Queue all trades rapidly
    start_time = asyncio.get_event_loop().time()
    
    for trade in trades:
        await aggregator.add_tick(trade.data_to_dict())
    
    queue_time = asyncio.get_event_loop().time() - start_time
    print(f"Queued {len(trades)} trades in {queue_time:.3f} seconds")
    
    # Process rapidly
    process_start = asyncio.get_event_loop().time()
    processed = 0
    
    while aggregator.queue.qsize() > 0:
        trade_data = await aggregator.queue.get()
        symbol = trade_data.s
        
        if symbol not in aggregator.stock_handlers:
            aggregator.stock_handlers[symbol] = StockHandler(symbol)
        
        aggregator.stock_handlers[symbol].process_trade(trade_data)
        processed += 1
    
    process_time = asyncio.get_event_loop().time() - process_start
    print(f"Processed {processed} trades in {process_time:.3f} seconds")
    print(f"Rate: {processed/process_time:.0f} trades/second")


async def main():
    """Run all demos"""
    print("Financial Analyzer - Testing & Demo Suite")
    print("=========================================")
    
    # Run demos
    demo_synthetic_data()
    demo_unit_testing()
    await demo_realtime_processing()
    await stress_test()
    
    print("\n=== All demos completed ===")


if __name__ == "__main__":
    asyncio.run(main())