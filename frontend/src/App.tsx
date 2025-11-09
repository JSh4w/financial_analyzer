import { useState, useEffect, useRef } from 'react'
import './App.css'
import LightweightStockChart from './components/LightweightStockChart'
import NewsFeed from './components/NewsFeed'

interface StockData {
  symbol: string
  candles?: {
    [timestamp: string]: {
      open: number
      high: number
      low: number
      close: number
      volume: number
    }
  }
  update_timestamp?: string
}

interface StockSubscription {
  symbol: string
  eventSource: EventSource | null
  stockData: StockData | null
  status: 'loading' | 'streaming' | 'error'
  errorMessage?: string
}

function App() {
  const [searchSymbol, setSearchSymbol] = useState('')
  const [activeStocks, setActiveStocks] = useState<Map<string, StockSubscription>>(new Map())
  const [globalStatus, setGlobalStatus] = useState('')
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map())

  const BACKEND_URL = 'http://localhost:8001'

  const addStock = async (symbol: string) => {
    const upperSymbol = symbol.toUpperCase().trim()

    if (!upperSymbol) {
      setGlobalStatus('❌ Please enter a stock symbol')
      return
    }

    if (activeStocks.has(upperSymbol)) {
      setGlobalStatus(`❌ Already viewing ${upperSymbol}`)
      return
    }

    // Initialize stock subscription
    setActiveStocks(prev => new Map(prev).set(upperSymbol, {
      symbol: upperSymbol,
      eventSource: null,
      stockData: null,
      status: 'loading'
    }))

    setGlobalStatus(`Subscribing to ${upperSymbol}...`)

    try {
      // Step 1: Subscribe via WebSocket manager
      const response = await fetch(`${BACKEND_URL}/ws_manager/${upperSymbol}`)
      const result = await response.json()

      if (result.status !== 'subscribed') {
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(upperSymbol)
          if (stock) {
            stock.status = 'error'
            stock.errorMessage = result.message || 'Subscription failed'
          }
          return updated
        })
        setGlobalStatus(`❌ Failed to subscribe to ${upperSymbol}`)
        return
      }

      // Step 2: Start SSE streaming
      const eventSource = new EventSource(`${BACKEND_URL}/stream/${upperSymbol}`)
      eventSourcesRef.current.set(upperSymbol, eventSource)

      eventSource.onopen = () => {
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(upperSymbol)
          if (stock) {
            stock.status = 'streaming'
            stock.eventSource = eventSource
          }
          return updated
        })
        setGlobalStatus(`✅ Now streaming ${upperSymbol}`)
      }

      eventSource.onmessage = (event) => {
        try {
          const data: StockData = JSON.parse(event.data)

          setActiveStocks(prev => {
            const updated = new Map(prev)
            const stock = updated.get(upperSymbol)
            if (!stock) return prev

            // Handle initial snapshot vs delta updates
            if ((data as any).is_initial) {
              stock.stockData = data
            } else {
              // Merge delta updates
              stock.stockData = {
                ...data,
                candles: {
                  ...(stock.stockData?.candles || {}),
                  ...data.candles
                },
                update_timestamp: data.update_timestamp || new Date().toISOString()
              }
            }
            return updated
          })
        } catch (error) {
          console.error(`Error parsing SSE data for ${upperSymbol}:`, error)
        }
      }

      eventSource.onerror = (error) => {
        console.error(`SSE Error for ${upperSymbol}:`, error)
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(upperSymbol)
          if (stock) {
            stock.status = 'error'
            stock.errorMessage = 'Stream connection error'
          }
          return updated
        })
      }

    } catch (error) {
      setActiveStocks(prev => {
        const updated = new Map(prev)
        const stock = updated.get(upperSymbol)
        if (stock) {
          stock.status = 'error'
          stock.errorMessage = String(error)
        }
        return updated
      })
      setGlobalStatus(`❌ Error: ${error}`)
    }
  }

  const removeStock = async (symbol: string) => {
    const upperSymbol = symbol.toUpperCase()

    // Close EventSource connection
    const eventSource = eventSourcesRef.current.get(upperSymbol)
    if (eventSource) {
      eventSource.close()
      eventSourcesRef.current.delete(upperSymbol)
    }

    // Unsubscribe from backend
    try {
      await fetch(`${BACKEND_URL}/ws_manager/close/${upperSymbol}`)
    } catch (error) {
      console.error(`Error unsubscribing from ${upperSymbol}:`, error)
    }

    // Remove from active stocks
    setActiveStocks(prev => {
      const updated = new Map(prev)
      updated.delete(upperSymbol)
      return updated
    })

    setGlobalStatus(`Removed ${upperSymbol}`)
  }

  const handleViewStock = () => {
    if (searchSymbol.trim()) {
      addStock(searchSymbol)
      setSearchSymbol('') // Clear search after adding
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleViewStock()
    }
  }

  useEffect(() => {
    // Cleanup: close all EventSource connections on unmount
    return () => {
      eventSourcesRef.current.forEach(eventSource => eventSource.close())
      eventSourcesRef.current.clear()
    }
  }, [])

  return (
    <>
      <div>
        <h1>Multi-Stock Market Dashboard</h1>

        {/* Search and Add Stock */}
        <div className="card" style={{ textAlign: 'left' }}>
          <h2>Add Stock</h2>
          <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input
              type="text"
              value={searchSymbol}
              onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
              onKeyPress={handleKeyPress}
              placeholder="Enter stock symbol (e.g., AAPL, TSLA, MSFT)"
              style={{
                padding: '12px',
                fontSize: '16px',
                width: '300px',
                borderRadius: '4px',
                border: '1px solid #ccc'
              }}
            />
            <button
              onClick={handleViewStock}
              disabled={!searchSymbol.trim()}
              style={{
                padding: '12px 24px',
                fontSize: '16px',
                backgroundColor: '#008CBA',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: searchSymbol.trim() ? 'pointer' : 'not-allowed',
                opacity: searchSymbol.trim() ? 1 : 0.6
              }}
            >
              View
            </button>
          </div>

          {globalStatus && (
            <div style={{ marginBottom: '20px' }}>
              <strong>Status:</strong> <span>{globalStatus}</span>
            </div>
          )}

          {activeStocks.size > 0 && (
            <div style={{ marginTop: '10px' }}>
              <strong>Active Stocks ({activeStocks.size}):</strong>{' '}
              {Array.from(activeStocks.keys()).join(', ')}
            </div>
          )}
        </div>

        {/* Stock Charts Grid */}
        {activeStocks.size === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
            <p style={{ fontSize: '18px', color: '#888' }}>
              No stocks added yet. Search for a stock symbol above and click "View" to start streaming.
            </p>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(600px, 1fr))',
            gap: '20px',
            marginTop: '20px'
          }}>
            {Array.from(activeStocks.entries()).map(([symbol, subscription]) => (
              <div key={symbol} className="card" style={{ textAlign: 'left', position: 'relative' }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '10px'
                }}>
                  <h2 style={{ margin: 0 }}>
                    {symbol}
                    {subscription.status === 'streaming' && (
                      <span style={{ marginLeft: '10px', fontSize: '14px', color: '#4CAF50' }}>
                        🔴 Live
                      </span>
                    )}
                    {subscription.status === 'loading' && (
                      <span style={{ marginLeft: '10px', fontSize: '14px', color: '#ff9800' }}>
                        Loading...
                      </span>
                    )}
                    {subscription.status === 'error' && (
                      <span style={{ marginLeft: '10px', fontSize: '14px', color: '#f44336' }}>
                        Error
                      </span>
                    )}
                  </h2>
                  <button
                    onClick={() => removeStock(symbol)}
                    style={{
                      padding: '8px 16px',
                      fontSize: '14px',
                      backgroundColor: '#f44336',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    Remove
                  </button>
                </div>

                {subscription.status === 'error' && (
                  <div style={{
                    padding: '10px',
                    backgroundColor: '#ffebee',
                    color: '#c62828',
                    borderRadius: '4px',
                    marginBottom: '10px'
                  }}>
                    Error: {subscription.errorMessage || 'Unknown error'}
                  </div>
                )}

                {subscription.status === 'loading' && (
                  <div style={{
                    padding: '40px',
                    textAlign: 'center',
                    color: '#888'
                  }}>
                    Connecting to {symbol}...
                  </div>
                )}

                {subscription.status === 'streaming' && subscription.stockData?.candles &&
                 Object.keys(subscription.stockData.candles).length > 0 && (
                  <LightweightStockChart
                    symbol={subscription.stockData.symbol}
                    candles={subscription.stockData.candles}
                  />
                )}

                {subscription.status === 'streaming' &&
                 (!subscription.stockData?.candles || Object.keys(subscription.stockData.candles).length === 0) && (
                  <div style={{
                    padding: '40px',
                    textAlign: 'center',
                    color: '#888'
                  }}>
                    Waiting for data from {symbol}...
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* News Feed */}
        <NewsFeed backendUrl={BACKEND_URL} />
      </div>
    </>
  )
}

export default App
