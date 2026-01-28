import { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, HistogramSeries, type IChartApi, type CandlestickData, type Time } from 'lightweight-charts';
import { colors, borderRadius, typography } from '../theme';

interface CandleData {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface LightweightStockChartProps {
  symbol: string;
  candles: { [timestamp: string]: CandleData };
}

/**
 * TradingView Lightweight Charts component
 * Uses your existing SSE data stream for real-time updates
 */
const LightweightStockChart: React.FC<LightweightStockChartProps> = ({ symbol, candles }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) {
      console.log('[LightweightChart] No container ref');
      return;
    }

    console.log('[LightweightChart] Initializing chart...');

    try {
      // Create chart
      const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 600,
      layout: {
        background: { color: colors.bg.secondary },
        textColor: colors.text.secondary,
      },
      grid: {
        vertLines: { color: colors.border.subtle },
        horzLines: { color: colors.border.subtle },
      },
      crosshair: {
        mode: 1, // Normal crosshair
      },
      rightPriceScale: {
        borderColor: colors.border.default,
      },
      timeScale: {
        borderColor: colors.border.default,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series (Lightweight Charts v5 - use imported series class)
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: colors.chart.up,
      downColor: colors.chart.down,
      borderUpColor: colors.chart.up,
      borderDownColor: colors.chart.down,
      wickUpColor: colors.chart.up,
      wickDownColor: colors.chart.down,
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Add volume series (Lightweight Charts v5 - use imported series class)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: colors.chart.volume,
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // empty string for right scale
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8, // highest point of the series will be 80% away from the top
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;

    console.log('[LightweightChart] Chart initialized successfully');

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartRef.current) {
          chartRef.current.remove();
          chartRef.current = null;
        }
      };
    } catch (error) {
      console.error('Error initializing Lightweight Charts:', error);
      // Chart creation failed, but don't crash the app
      return () => {};
    }
  }, []);

  // Update chart data when candles change
  useEffect(() => {
    if (!candlestickSeriesRef.current || !volumeSeriesRef.current || !candles) {
      console.log('[LightweightChart] Missing dependencies:', {
        hasCandlestickSeries: !!candlestickSeriesRef.current,
        hasVolumeSeries: !!volumeSeriesRef.current,
        hasCandles: !!candles,
        candleCount: candles ? Object.keys(candles).length : 0
      });
      return;
    }

    console.log('[LightweightChart] Updating chart data...', Object.keys(candles).length, 'candles');

    try {
      // Convert your candle data to Lightweight Charts format
      const sortedEntries = Object.entries(candles).sort(([a], [b]) => a.localeCompare(b));

    const candlestickData: CandlestickData[] = sortedEntries.map(([timestamp, candle]) => {
      const date = new Date(timestamp);
      // Convert to Unix timestamp in seconds
      const time = Math.floor(date.getTime() / 1000) as Time;

      return {
        time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      };
    });

    const volumeData = sortedEntries.map(([timestamp, candle]) => {
      const date = new Date(timestamp);
      const time = Math.floor(date.getTime() / 1000) as Time;

      // Color volume bars based on price movement
      const isGreen = candle.close >= candle.open;
      const color = isGreen ? 'rgba(34, 197, 94, 0.4)' : 'rgba(239, 68, 68, 0.4)';

      return {
        time,
        value: candle.volume,
        color,
      };
    });

    // Update series data - setData preserves the zoom/pan state
    candlestickSeriesRef.current.setData(candlestickData);
    volumeSeriesRef.current.setData(volumeData);

      console.log('[LightweightChart] Data updated successfully. First bar:', candlestickData[0]);

      // Only fit content on initial load (when series has no data)
      // Don't call fitContent() on updates to preserve user's zoom/pan
    } catch (error) {
      console.error('[LightweightChart] Error updating chart data:', error);
      // Don't crash the app if chart update fails
    }
  }, [candles]);

  return (
    <div>
      <div
        style={{
          marginBottom: 0,
          padding: '12px 16px',
          backgroundColor: colors.bg.secondary,
          borderRadius: `${borderRadius.lg} ${borderRadius.lg} 0 0`,
          borderBottom: `1px solid ${colors.border.default}`,
        }}
      >
        <h3 style={{ margin: 0, color: colors.accent.primary, fontSize: typography.fontSize.md, fontWeight: typography.fontWeight.semibold }}>
          {symbol}
        </h3>
        <p style={{ margin: '4px 0 0 0', fontSize: typography.fontSize.xs, color: colors.text.tertiary }}>
          Live data from Alpaca • {candles ? Object.keys(candles).length : 0} candles
        </p>
      </div>
      <div
        ref={chartContainerRef}
        style={{
          width: '100%',
          height: '600px',
          borderRadius: `0 0 ${borderRadius.lg} ${borderRadius.lg}`,
          backgroundColor: colors.bg.secondary,
        }}
      />
    </div>
  );
};

export default LightweightStockChart;
