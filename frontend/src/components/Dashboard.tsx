import { useState, useEffect, useRef } from 'react'
import './Dashboard.css'
import LightweightStockChart from './LightweightStockChart'
import NewsFeed from './NewsFeed'
import { supabase } from '../lib/supabase'
import { apiClient } from '../lib/api-client'
import { getAuthToken } from '../lib/auth'
import SelectBank from './SelectBank'

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
  status: 'loading' | 'streaming' | 'paused' | 'error'
  errorMessage?: string
  isSubscribed: boolean
}

type View = 'stocks' | 'portfolio'

export default function Dashboard() {
  const [searchSymbol, setSearchSymbol] = useState('')
  const [activeStocks, setActiveStocks] = useState<Map<string, StockSubscription>>(new Map())
  const [selectedStock, setSelectedStock] = useState<string | null>(null)
  const [currentView, setCurrentView] = useState<View>('stocks')
  const [globalStatus, setGlobalStatus] = useState('')
  const [bankConnectionStatus, setBankConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [bankConnectionMessage, setBankConnectionMessage] = useState('')
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map())

  const BACKEND_URL = 'http://localhost:8001'

  // Handle GoCardless callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const ref = params.get('ref')
    const error = params.get('error')

    if (error) {
      setBankConnectionStatus('error')
      setBankConnectionMessage(`Bank connection failed: ${error}`)
      setCurrentView('portfolio')
      // Clean up URL
      window.history.replaceState({}, '', '/portfolio')
    } else if (ref) {
      setBankConnectionStatus('success')
      setBankConnectionMessage('Bank connected successfully! You can now access your account data.')
      setCurrentView('portfolio')
      // Clean up URL
      window.history.replaceState({}, '', '/portfolio')
      // Auto-dismiss after 10 seconds
      setTimeout(() => {
        setBankConnectionStatus('idle')
      }, 10000)
    }
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
  }

  const pauseStream = (symbol: string) => {
    const eventSource = eventSourcesRef.current.get(symbol)
    if (eventSource) {
      eventSource.close()
      eventSourcesRef.current.delete(symbol)

      setActiveStocks(prev => {
        const updated = new Map(prev)
        const stock = updated.get(symbol)
        if (stock) {
          stock.status = 'paused'
          stock.eventSource = null
        }
        return updated
      })
    }
  }

  const resumeStream = async (symbol: string) => {
    const subscription = activeStocks.get(symbol)
    if (!subscription || !subscription.isSubscribed) return

    setActiveStocks(prev => {
      const updated = new Map(prev)
      const stock = updated.get(symbol)
      if (stock) {
        stock.status = 'loading'
      }
      return updated
    })

    try {
      const token = await getAuthToken()
      if (!token) throw new Error('Not authenticated')
      const eventSource = new EventSource(`${BACKEND_URL}/stream/${symbol}?token=${token}`)
      eventSourcesRef.current.set(symbol, eventSource)

      eventSource.onopen = () => {
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(symbol)
          if (stock) {
            stock.status = 'streaming'
            stock.eventSource = eventSource
          }
          return updated
        })
      }

      eventSource.onmessage = (event) => {
        try {
          const data: StockData = JSON.parse(event.data)

          setActiveStocks(prev => {
            const updated = new Map(prev)
            const stock = updated.get(symbol)
            if (!stock) return prev

            if ((data as any).is_initial) {
              stock.stockData = data
            } else {
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
          console.error(`Error parsing SSE data for ${symbol}:`, error)
        }
      }

      eventSource.onerror = (error) => {
        console.error(`SSE Error for ${symbol}:`, error)
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(symbol)
          if (stock) {
            stock.status = 'error'
            stock.errorMessage = 'Stream connection error'
          }
          return updated
        })
      }
    } catch (error) {
      console.error(`Error resuming stream for ${symbol}:`, error)
    }
  }

  const addStock = async (symbol: string) => {
    const upperSymbol = symbol.toUpperCase().trim()

    if (!upperSymbol) {
      setGlobalStatus('Please enter a stock symbol')
      return
    }

    // If stock already exists, pause current and switch to it
    if (activeStocks.has(upperSymbol)) {
      if (selectedStock && selectedStock !== upperSymbol) {
        pauseStream(selectedStock)
      }
      setSelectedStock(upperSymbol)
      const stock = activeStocks.get(upperSymbol)
      if (stock && stock.status === 'paused') {
        await resumeStream(upperSymbol)
      }
      return
    }

    // Pause current stock stream if any
    if (selectedStock) {
      pauseStream(selectedStock)
    }

    // Initialize stock subscription
    setActiveStocks(prev => new Map(prev).set(upperSymbol, {
      symbol: upperSymbol,
      eventSource: null,
      stockData: null,
      status: 'loading',
      isSubscribed: false
    }))

    setGlobalStatus(`Subscribing to ${upperSymbol}...`)

    try {
      // Step 1: Subscribe via WebSocket manager
      const result = await apiClient.get<{status: string
        message?: string 
        symbol?: string
      }>(`/ws_manager/${upperSymbol}`)

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
        setGlobalStatus(`Failed to subscribe to ${upperSymbol}`)
        return
      }

      // Mark as subscribed
      setActiveStocks(prev => {
        const updated = new Map(prev)
        const stock = updated.get(upperSymbol)
        if (stock) {
          stock.isSubscribed = true
        }
        return updated
      })

      // Step 2: Start SSE streaming
      const token = await getAuthToken()
      if (!token) throw new Error('Not authenticated')
      const eventSource = new EventSource(`${BACKEND_URL}/stream/${upperSymbol}?token=${token}`)
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
        setSelectedStock(upperSymbol)
        setGlobalStatus(`Now streaming ${upperSymbol}`)
      }

      eventSource.onmessage = (event) => {
        try {
          const data: StockData = JSON.parse(event.data)

          setActiveStocks(prev => {
            const updated = new Map(prev)
            const stock = updated.get(upperSymbol)
            if (!stock) return prev

            if ((data as any).is_initial) {
              stock.stockData = data
            } else {
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
      setGlobalStatus(`Error: ${error}`)
    }
  }

  const switchToStock = async (symbol: string) => {
    if (selectedStock === symbol) return

    // Pause current stock stream
    if (selectedStock) {
      pauseStream(selectedStock)
    }

    setSelectedStock(symbol)

    // Resume stream for the selected stock
    const stock = activeStocks.get(symbol)
    if (stock && stock.status === 'paused') {
      await resumeStream(symbol)
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
      await apiClient.get(`/ws_manager/close/${upperSymbol}`)
    } catch (error) {
      console.error(`Error unsubscribing from ${upperSymbol}:`, error)
    }

    // Remove from active stocks
    setActiveStocks(prev => {
      const updated = new Map(prev)
      updated.delete(upperSymbol)

      // If the removed stock was selected, select a new one
      if (selectedStock === upperSymbol) {
        const firstStockKey = updated.keys().next().value
        setSelectedStock(firstStockKey || null)

        // Resume stream for the new selection
        if (firstStockKey) {
          const newStock = updated.get(firstStockKey)
          if (newStock && newStock.status === 'paused') {
            resumeStream(firstStockKey)
          }
        }
      }

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

  useEffect(() => {
    // Cleanup: close all EventSource connections on unmount
    return () => {
      eventSourcesRef.current.forEach(eventSource => eventSource.close())
      eventSourcesRef.current.clear()
    }
  }, [])

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      backgroundColor: '#0f0f0f',
      color: '#e0e0e0',
      overflow: 'hidden',
      margin: 0,
      padding: 0
    }}>
      {/* Left Sidebar - Navigation */}
      <div style={{
        width: '200px',
        backgroundColor: '#1a1a1a',
        borderRight: '1px solid #2a2a2a',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0
      }}>
        {/* Logo/Header */}
        <div style={{
          padding: '20px',
          borderBottom: '1px solid #2a2a2a',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            backgroundColor: '#3b82f6',
            borderRadius: '6px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
            fontWeight: 'bold'
          }}>
            F
          </div>
          <span style={{ fontSize: '16px', fontWeight: '600' }}>Finance</span>
        </div>

        {/* Navigation Menu */}
        <div style={{ padding: '5px 0' }}>
          <button
            onClick={() => setCurrentView('stocks')}
            style={{
              width: '100%',
              padding: '12px 20px',
              border: 'none',
              backgroundColor: currentView === 'stocks' ? '#2a2a2a' : 'transparent',
              color: currentView === 'stocks' ? '#3b82f6' : '#a0a0a0',
              cursor: 'pointer',
              textAlign: 'left',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'all 0.2s',
              borderLeft: currentView === 'stocks' ? '3px solid #3b82f6' : '3px solid transparent'
            }}
          >
            Stocks
          </button>
          <button
            onClick={() => setCurrentView('portfolio')}
            style={{
              width: '100%',
              padding: '12px 20px',
              border: 'none',
              backgroundColor: currentView === 'portfolio' ? '#2a2a2a' : 'transparent',
              color: currentView === 'portfolio' ? '#3b82f6' : '#a0a0a0',
              cursor: 'pointer',
              textAlign: 'left',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'all 0.2s',
              borderLeft: currentView === 'portfolio' ? '3px solid #3b82f6' : '3px solid transparent'
            }}
          >
            Portfolio
          </button>
        </div>

        {/* Stock List */}
        {currentView === 'stocks' && activeStocks.size > 0 && (
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '5px 0',
            borderTop: '1px solid #2a2a2a'
          }}>
            <div style={{
              padding: '5px 10px',
              fontSize: '12px',
              color: '#666',
              fontWeight: '600',
              textTransform: 'uppercase'
            }}>
              Watching
            </div>
            {Array.from(activeStocks.entries()).map(([symbol, stock]) => (
              <div
                key={symbol}
                onClick={() => switchToStock(symbol)}
                style={{
                  padding: '5px 10px',
                  cursor: 'pointer',
                  backgroundColor: selectedStock === symbol ? '#2a2a2a' : 'transparent',
                  borderLeft: selectedStock === symbol ? '3px solid #3b82f6' : '3px solid transparent',
                  transition: 'all 0.2s',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '300', color: '#e0e0e0' }}>
                    {symbol}
                  </div>
                  <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                    {stock.status === 'streaming' && '🔴 Live'}
                    {stock.status === 'paused' && '⏸ Paused'}
                    {stock.status === 'loading' && '⏳ Loading'}
                    {stock.status === 'error' && '⚠ Error'}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    removeStock(symbol)
                  }}
                  style={{
                    padding: '4px 8px',
                    fontSize: '11px',
                    backgroundColor: 'transparent',
                    color: '#666',
                    border: '1px solid #333',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Bottom - Sign Out */}
        <div style={{
          marginTop: 'auto',
          padding: '20px',
          borderTop: '1px solid #2a2a2a'
        }}>
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: 'transparent',
              color: '#a0a0a0',
              border: '1px solid #333',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Top Search Bar */}
        <div style={{
          padding: '16px 24px',
          backgroundColor: '#1a1a1a',
          borderBottom: '1px solid #2a2a2a',
          display: 'flex',
          alignItems: 'center',
          gap: '16px'
        }}>
          <input
            type="text"
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleViewStock()
              }
            }}
            placeholder="Search for stocks..."
            style={{
              flex: 1,
              maxWidth: '600px',
              padding: '12px 16px',
              fontSize: '14px',
              backgroundColor: '#0f0f0f',
              color: '#e0e0e0',
              border: '1px solid #333',
              borderRadius: '8px',
              outline: 'none'
            }}
          />
          {globalStatus && (
            <span style={{ fontSize: '13px', color: '#666' }}>{globalStatus}</span>
          )}
        </div>

        {/* Content - Two Column Layout (Chart + News) */}
        <div style={{
          flex: 1,
          display: 'flex',
          overflow: 'hidden'
        }}>
          {/* Center - Stock Chart */}
          <div style={{
            flex: '1 1 55%',
            overflowY: 'auto',
            padding: '12px'
          }}>
            {currentView === 'portfolio' ? (
              <div style={{
                backgroundColor: '#1a1a1a',
                borderRadius: '12px',
                padding: '60px',
                textAlign: 'center',
                border: '1px solid #2a2a2a'
              }}>
                <h2 style={{ fontSize: '24px', marginBottom: '12px', color: '#e0e0e0' }}>Portfolio</h2>
                <p style={{ fontSize: '16px', color: '#666' }}>
                  Your portfolio view is coming soon. Track your investments, performance, and more.
                </p>

                {bankConnectionStatus === 'success' && (
                  <div style={{
                    backgroundColor: '#10b981',
                    color: 'white',
                    padding: '16px',
                    borderRadius: '8px',
                    marginBottom: '24px',
                    fontSize: '14px'
                  }}>
                    ✓ {bankConnectionMessage}
                  </div>
                )}

                {bankConnectionStatus === 'error' && (
                  <div style={{
                    backgroundColor: '#ef4444',
                    color: 'white',
                    padding: '16px',
                    borderRadius: '8px',
                    marginBottom: '24px',
                    fontSize: '14px'
                  }}>
                    ✗ {bankConnectionMessage}
                  </div>
                )}

                <SelectBank onSelect={(inst) => console.log('Selected bank:', inst)} />
              </div>
            ) : activeStocks.size === 0 ? (
              <div style={{
                backgroundColor: '#1a1a1a',
                borderRadius: '12px',
                padding: '60px',
                textAlign: 'center',
                border: '1px solid #2a2a2a'
              }}>
                <h2 style={{ fontSize: '24px', marginBottom: '12px', color: '#e0e0e0' }}>No stocks yet</h2>
                <p style={{ fontSize: '16px', color: '#666' }}>
                  Search for a stock symbol above to start tracking.
                </p>
              </div>
            ) : selectedStock ? (() => {
              const subscription = activeStocks.get(selectedStock)
              if (!subscription) return null

              return (
                <div>
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '20px'
                  }}>
                    <div>
                      <h1 style={{ fontSize: '32px', margin: 0, color: '#e0e0e0' }}>
                        {subscription.symbol}
                      </h1>
                      <div style={{ fontSize: '13px', color: '#666', marginTop: '4px' }}>
                        {subscription.status === 'streaming' && (
                          <span style={{ color: '#10b981' }}>● Live stream</span>
                        )}
                        {subscription.status === 'paused' && (
                          <span style={{ color: '#f59e0b' }}>⏸ Stream paused</span>
                        )}
                        {subscription.status === 'loading' && (
                          <span style={{ color: '#f59e0b' }}>⏳ Loading...</span>
                        )}
                        {subscription.status === 'error' && (
                          <span style={{ color: '#ef4444' }}>⚠ Error</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {subscription.status === 'error' && (
                    <div style={{
                      padding: '16px',
                      backgroundColor: '#7f1d1d',
                      color: '#fecaca',
                      borderRadius: '8px',
                      marginBottom: '20px',
                      border: '1px solid #991b1b'
                    }}>
                      Error: {subscription.errorMessage || 'Unknown error'}
                    </div>
                  )}

                  {subscription.status === 'loading' && (
                    <div style={{
                      backgroundColor: '#1a1a1a',
                      borderRadius: '12px',
                      padding: '60px',
                      textAlign: 'center',
                      border: '1px solid #2a2a2a'
                    }}>
                      <div style={{ fontSize: '16px', color: '#666' }}>
                        Connecting to {subscription.symbol}...
                      </div>
                    </div>
                  )}

                  {(subscription.status === 'streaming' || subscription.status === 'paused') &&
                   subscription.stockData?.candles &&
                   Object.keys(subscription.stockData.candles).length > 0 && (
                    <div style={{
                      backgroundColor: '#1a1a1a',
                      borderRadius: '12px',
                      padding: '20px',
                      border: '1px solid #2a2a2a'
                    }}>
                      <LightweightStockChart
                        symbol={subscription.stockData.symbol}
                        candles={subscription.stockData.candles}
                      />
                    </div>
                  )}

                  {(subscription.status === 'streaming' || subscription.status === 'paused') &&
                   (!subscription.stockData?.candles || Object.keys(subscription.stockData.candles).length === 0) && (
                    <div style={{
                      backgroundColor: '#1a1a1a',
                      borderRadius: '12px',
                      padding: '60px',
                      textAlign: 'center',
                      border: '1px solid #2a2a2a'
                    }}>
                      <div style={{ fontSize: '16px', color: '#666' }}>
                        Waiting for data from {subscription.symbol}...
                      </div>
                    </div>
                  )}
                </div>
              )
            })() : null}
          </div>

          {/* Right Sidebar - News Feed */}
          {currentView === 'stocks' && (
            <div style={{
              width: '380px',
              flexShrink: 0,
              backgroundColor: '#1a1a1a',
              borderLeft: '1px solid #2a2a2a',
              overflowY: 'auto'
            }}>
              <NewsFeed backendUrl={BACKEND_URL} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

