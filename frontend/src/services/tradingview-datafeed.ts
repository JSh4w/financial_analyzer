/**
 * TradingView Datafeed API implementation
 * Connects TradingView charts to our Alpaca backend data
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

interface Bar {
  time: number; // Unix timestamp in milliseconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface SubscriberUID {
  id: string;
}

interface DatafeedConfiguration {
  supported_resolutions: string[];
  supports_marks: boolean;
  supports_timescale_marks: boolean;
  supports_time: boolean;
}

interface LibrarySymbolInfo {
  name: string;
  ticker: string;
  description: string;
  type: string;
  session: string;
  exchange: string;
  listed_exchange: string;
  timezone: string;
  minmov: number;
  pricescale: number;
  has_intraday: boolean;
  supported_resolutions: string[];
  volume_precision: number;
  data_status: string;
}

export class AlpacaDatafeed {
  private subscriptions: Map<string, EventSource> = new Map();

  /**
   * Called when TradingView initializes
   */
  onReady(callback: (config: DatafeedConfiguration) => void) {
    console.log('[Datafeed] onReady called');

    fetch(`${BACKEND_URL}/api/tradingview/config`)
      .then(res => res.json())
      .then(config => {
        console.log('[Datafeed] Configuration:', config);
        setTimeout(() => callback(config), 0);
      })
      .catch(err => {
        console.error('[Datafeed] onReady error:', err);
        // Provide default config if fetch fails
        setTimeout(() => callback({
          supported_resolutions: ['1'],
          supports_marks: false,
          supports_timescale_marks: false,
          supports_time: true,
        }), 0);
      });
  }

  /**
   * Resolve symbol information
   */
  resolveSymbol(
    symbolName: string,
    onResolve: (symbolInfo: LibrarySymbolInfo) => void,
    onError: (reason: string) => void
  ) {
    console.log('[Datafeed] resolveSymbol:', symbolName);

    fetch(`${BACKEND_URL}/api/tradingview/symbol_info?symbol=${symbolName}`)
      .then(res => res.json())
      .then(symbolInfo => {
        console.log('[Datafeed] Symbol info:', symbolInfo);
        setTimeout(() => onResolve(symbolInfo), 0);
      })
      .catch(err => {
        console.error('[Datafeed] resolveSymbol error:', err);
        setTimeout(() => onError(`Symbol resolution failed: ${err.message}`), 0);
      });
  }

  /**
   * Fetch historical bars
   */
  getBars(
    symbolInfo: LibrarySymbolInfo,
    resolution: string,
    periodParams: {
      from: number; // Unix timestamp in seconds
      to: number;   // Unix timestamp in seconds
      firstDataRequest: boolean;
    },
    onResult: (bars: Bar[], meta: { noData: boolean }) => void,
    onError: (reason: string) => void
  ) {
    const { from, to, firstDataRequest } = periodParams;
    console.log('[Datafeed] getBars called:', {
      symbol: symbolInfo.ticker,
      resolution,
      from: new Date(from * 1000).toISOString(),
      to: new Date(to * 1000).toISOString(),
      firstDataRequest
    });

    fetch(
      `${BACKEND_URL}/api/tradingview/history?symbol=${symbolInfo.ticker}&from_ts=${from}&to_ts=${to}&resolution=${resolution}`
    )
      .then(res => res.json())
      .then(data => {
        console.log('[Datafeed] History response:', data);

        if (data.s === 'no_data') {
          console.log('[Datafeed] No data available');
          setTimeout(() => onResult([], { noData: true }), 0);
          return;
        }

        if (data.s !== 'ok') {
          console.error('[Datafeed] Invalid response status:', data.s);
          setTimeout(() => onResult([], { noData: true }), 0);
          return;
        }

        // Transform to TradingView Bar format
        const bars: Bar[] = data.t.map((_: any, index: number) => ({
          time: data.t[index] * 1000, // Convert to milliseconds
          open: data.o[index],
          high: data.h[index],
          low: data.l[index],
          close: data.c[index],
          volume: data.v[index],
        }));

        console.log(`[Datafeed] Returning ${bars.length} bars`);
        setTimeout(() => onResult(bars, { noData: bars.length === 0 }), 0);
      })
      .catch(err => {
        console.error('[Datafeed] getBars error:', err);
        setTimeout(() => onError(`Failed to fetch bars: ${err.message}`), 0);
      });
  }

  /**
   * Subscribe to real-time updates using existing SSE stream
   */
  subscribeBars(
    symbolInfo: LibrarySymbolInfo,
    resolution: string,
    onTick: (bar: Bar) => void,
    listenerGuid: string,
    onResetCacheNeededCallback: () => void
  ) {
    console.log('[Datafeed] subscribeBars:', symbolInfo.ticker, listenerGuid);

    // Use your existing SSE endpoint
    const eventSource = new EventSource(`${BACKEND_URL}/stream/${symbolInfo.ticker}`);

    eventSource.onopen = () => {
      console.log('[Datafeed] SSE connection opened for', symbolInfo.ticker);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle initial snapshot (don't send to chart)
        if (data.is_initial) {
          console.log('[Datafeed] Received initial snapshot, ignoring for chart');
          return;
        }

        // Get the latest candle from delta update
        if (data.candles && Object.keys(data.candles).length > 0) {
          const timestamps = Object.keys(data.candles).sort();
          const latestTimestamp = timestamps[timestamps.length - 1];
          const candle = data.candles[latestTimestamp];

          const bar: Bar = {
            time: new Date(latestTimestamp).getTime(),
            open: candle.open,
            high: candle.high,
            low: candle.low,
            close: candle.close,
            volume: candle.volume,
          };

          console.log('[Datafeed] Sending tick update:', bar);
          onTick(bar);
        }
      } catch (err) {
        console.error('[Datafeed] Error parsing SSE message:', err);
      }
    };

    eventSource.onerror = (error) => {
      console.error('[Datafeed] SSE error:', error);
      eventSource.close();
      this.subscriptions.delete(listenerGuid);
    };

    // Store for cleanup
    this.subscriptions.set(listenerGuid, eventSource);
  }

  /**
   * Unsubscribe from real-time updates
   */
  unsubscribeBars(listenerGuid: string) {
    console.log('[Datafeed] unsubscribeBars:', listenerGuid);

    const eventSource = this.subscriptions.get(listenerGuid);
    if (eventSource) {
      eventSource.close();
      this.subscriptions.delete(listenerGuid);
      console.log('[Datafeed] Closed SSE connection for', listenerGuid);
    }
  }
}
