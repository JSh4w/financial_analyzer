import { useState, useEffect, useRef } from 'react'
import LightweightStockChart from './LightweightStockChart'
import NewsFeed from './NewsFeed'
import { supabase } from '../lib/supabase'
import { apiClient } from '../lib/api-client'
import { getAuthToken } from '../lib/auth'
import SelectBank from './SelectBank'
import AccountBalances from './AccountBalances'
import AllBalances from './AllBalances'
import Sidebar from './Sidebar'
import SearchBar from './SearchBar'
import { colors, borderRadius, typography } from '../theme'

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
  isSubscribed: boolean  // Temporary WebSocket subscription (ws_manager)
  isPermanent: boolean   // Permanent database subscription (persisted)
}

type View = 'stocks' | 'portfolio'
type PortfolioSubView = 'all' | 'connect' | 'balances'

export default function Dashboard() {
  const [searchSymbol, setSearchSymbol] = useState('')
  const [activeStocks, setActiveStocks] = useState<Map<string, StockSubscription>>(new Map())
  const [selectedStock, setSelectedStock] = useState<string | null>(null)
  const [currentView, setCurrentView] = useState<View>('stocks')
  const [portfolioSubView, setPortfolioSubView] = useState<PortfolioSubView>('all')
  const [globalStatus, setGlobalStatus] = useState('')
  const [bankConnectionStatus, setBankConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [bankConnectionMessage, setBankConnectionMessage] = useState('')
  const [subscriptionsLoaded, setSubscriptionsLoaded] = useState(false)
  const eventSourcesRef = useRef<Map<string, EventSource>>(new Map())

  const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

  // Handle GoCardless callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const ref = params.get('ref')
    const error = params.get('error')

    if (error) {
      setBankConnectionStatus('error')
      setBankConnectionMessage(`Bank connection failed: ${error}`)
      setCurrentView('portfolio')
      setPortfolioSubView('connect')
      // Clean up URL
      window.history.replaceState({}, '', '/portfolio')
    } else if (ref) {
      setBankConnectionStatus('success')
      setBankConnectionMessage('Bank connected successfully! You can now access your account data.')
      setCurrentView('portfolio')
      setPortfolioSubView('all')
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
      isSubscribed: false,
      isPermanent: false
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
    const stock = activeStocks.get(upperSymbol)

    // If permanent subscription, remove from database first
    if (stock?.isPermanent) {
      try {
        await apiClient.delete(`/api/subscribe/${upperSymbol}`)
      } catch (error) {
        console.error(`Error removing permanent subscription for ${upperSymbol}:`, error)
      }
    }

    // Close EventSource connection
    // Backend will automatically check if WebSocket should be unsubscribed
    // (based on remaining SSE connections + permanent subscribers)
    const eventSource = eventSourcesRef.current.get(upperSymbol)
    if (eventSource) {
      eventSource.close()
      eventSourcesRef.current.delete(upperSymbol)
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

  // Permanent subscription functions
  const addPermanentSubscription = async (symbol: string) => {
    const upperSymbol = symbol.toUpperCase().trim()

    try {
      const result = await apiClient.post<{
        status: string
        symbol: string
        subscriber_count: number
        message: string
      }>(`/api/subscribe/${upperSymbol}`)

      if (result.status === 'subscribed') {
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(upperSymbol)
          if (stock) {
            stock.isPermanent = true
          }
          return updated
        })
        setGlobalStatus(`${upperSymbol} added to watchlist`)
      }
    } catch (error) {
      console.error(`Error adding permanent subscription for ${upperSymbol}:`, error)
      setGlobalStatus(`Failed to add ${upperSymbol} to watchlist`)
    }
  }

  const removePermanentSubscription = async (symbol: string) => {
    const upperSymbol = symbol.toUpperCase().trim()

    try {
      const result = await apiClient.delete<{
        status: string
        symbol: string
        remaining_subscribers: number
        message: string
      }>(`/api/subscribe/${upperSymbol}`)

      if (result.status === 'unsubscribed') {
        setActiveStocks(prev => {
          const updated = new Map(prev)
          const stock = updated.get(upperSymbol)
          if (stock) {
            stock.isPermanent = false
          }
          return updated
        })
        setGlobalStatus(`${upperSymbol} removed from watchlist`)
      }
    } catch (error) {
      console.error(`Error removing permanent subscription for ${upperSymbol}:`, error)
      setGlobalStatus(`Failed to remove ${upperSymbol} from watchlist`)
    }
  }

  const handleViewStock = () => {
    if (searchSymbol.trim()) {
      addStock(searchSymbol)
      setSearchSymbol('') // Clear search after adding
    }
  }

  // Load permanent subscriptions when stocks view is active
  useEffect(() => {
    // Only load when stocks view is active and not already loaded
    if (currentView !== 'stocks' || subscriptionsLoaded) {
      return
    }

    const loadPermanentSubscriptions = async () => {
      try {
        const result = await apiClient.get<{
          symbols: string[]
          count: number
        }>('/api/subscriptions')

        if (result.symbols && result.symbols.length > 0) {
          setGlobalStatus(`Loading ${result.count} saved stocks...`)

          // Add each saved symbol sequentially
          for (const symbol of result.symbols) {
            // Initialize stock subscription
            setActiveStocks(prev => {
              if (prev.has(symbol)) return prev
              return new Map(prev).set(symbol, {
                symbol,
                eventSource: null,
                stockData: null,
                status: 'loading',
                isSubscribed: false,
                isPermanent: true  // Mark as permanent since it's from the watchlist
              })
            })

            try {
              // Subscribe via WebSocket manager
              const wsResult = await apiClient.get<{
                status: string
                message?: string
                symbol?: string
              }>(`/ws_manager/${symbol}`)

              if (wsResult.status !== 'subscribed') {
                setActiveStocks(prev => {
                  const updated = new Map(prev)
                  const stock = updated.get(symbol)
                  if (stock) {
                    stock.status = 'error'
                    stock.errorMessage = wsResult.message || 'Subscription failed'
                  }
                  return updated
                })
                continue
              }

              // Mark as subscribed
              setActiveStocks(prev => {
                const updated = new Map(prev)
                const stock = updated.get(symbol)
                if (stock) {
                  stock.isSubscribed = true
                }
                return updated
              })

              // Start SSE streaming
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

              // Select the first stock
              setActiveStocks(prev => {
                if (prev.size === 1) {
                  setSelectedStock(symbol)
                }
                return prev
              })

            } catch (error) {
              console.error(`Error subscribing to ${symbol}:`, error)
              setActiveStocks(prev => {
                const updated = new Map(prev)
                const stock = updated.get(symbol)
                if (stock) {
                  stock.status = 'error'
                  stock.errorMessage = String(error)
                }
                return updated
              })
            }
          }

          setGlobalStatus(`Loaded ${result.count} saved stocks`)
        }

        setSubscriptionsLoaded(true)
      } catch (error) {
        console.error('Failed to load permanent subscriptions:', error)
        setSubscriptionsLoaded(true) // Mark as loaded to prevent infinite retries
      }
    }

    loadPermanentSubscriptions()
  }, [currentView, subscriptionsLoaded, BACKEND_URL])

  useEffect(() => {
    // Cleanup: close all EventSource connections on unmount
    return () => {
      eventSourcesRef.current.forEach(eventSource => eventSource.close())
      eventSourcesRef.current.clear()
    }
  }, [])

  // Map activeStocks to the format expected by Sidebar
  const sidebarStocks = new Map(
    Array.from(activeStocks.entries()).map(([symbol, stock]) => [
      symbol,
      {
        symbol: stock.symbol,
        status: stock.status,
        isPermanent: stock.isPermanent,
      },
    ])
  )

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      backgroundColor: colors.bg.primary,
      color: colors.text.primary,
      overflow: 'hidden',
      margin: 0,
      padding: 0
    }}>
      {/* Left Sidebar - Navigation */}
      <Sidebar
        currentView={currentView}
        onViewChange={setCurrentView}
        activeStocks={sidebarStocks}
        selectedStock={selectedStock}
        onStockSelect={switchToStock}
        onStockRemove={removeStock}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Top Search Bar */}
        <SearchBar
          value={searchSymbol}
          onChange={setSearchSymbol}
          onSubmit={handleViewStock}
          status={globalStatus}
        />

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
            padding: '16px'
          }}>
            {currentView === 'portfolio' ? (
              <div style={{
                backgroundColor: colors.bg.secondary,
                borderRadius: borderRadius.xl,
                padding: '24px',
                border: `1px solid ${colors.border.default}`
              }}>
                <h2 style={{ fontSize: typography.fontSize['2xl'], marginBottom: '24px', color: colors.text.primary, fontWeight: typography.fontWeight.semibold }}>Portfolio</h2>

                {/* Tabs for Portfolio Subsections */}
                <div style={{
                  display: 'flex',
                  gap: '8px',
                  marginBottom: '24px',
                  borderBottom: `1px solid ${colors.border.default}`,
                  paddingBottom: '0'
                }}>
                  <button
                    onClick={() => setPortfolioSubView('all')}
                    style={{
                      padding: '12px 20px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: portfolioSubView === 'all' ? colors.accent.primary : colors.text.secondary,
                      cursor: 'pointer',
                      fontSize: typography.fontSize.sm,
                      fontWeight: typography.fontWeight.medium,
                      borderBottom: portfolioSubView === 'all' ? `2px solid ${colors.accent.primary}` : '2px solid transparent',
                      transition: 'all 0.2s'
                    }}
                  >
                    All Balances
                  </button>
                  <button
                    onClick={() => setPortfolioSubView('connect')}
                    style={{
                      padding: '12px 20px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: portfolioSubView === 'connect' ? colors.accent.primary : colors.text.secondary,
                      cursor: 'pointer',
                      fontSize: typography.fontSize.sm,
                      fontWeight: typography.fontWeight.medium,
                      borderBottom: portfolioSubView === 'connect' ? `2px solid ${colors.accent.primary}` : '2px solid transparent',
                      transition: 'all 0.2s'
                    }}
                  >
                    Connect Bank
                  </button>
                  <button
                    onClick={() => setPortfolioSubView('balances')}
                    style={{
                      padding: '12px 20px',
                      backgroundColor: 'transparent',
                      border: 'none',
                      color: portfolioSubView === 'balances' ? colors.accent.primary : colors.text.secondary,
                      cursor: 'pointer',
                      fontSize: typography.fontSize.sm,
                      fontWeight: typography.fontWeight.medium,
                      borderBottom: portfolioSubView === 'balances' ? `2px solid ${colors.accent.primary}` : '2px solid transparent',
                      transition: 'all 0.2s'
                    }}
                  >
                    Bank Balances
                  </button>
                </div>

                {/* Bank Connection Status Messages */}
                {bankConnectionStatus === 'success' && (
                  <div style={{
                    backgroundColor: colors.status.success,
                    color: 'white',
                    padding: '16px',
                    borderRadius: borderRadius.lg,
                    marginBottom: '24px',
                    fontSize: typography.fontSize.sm
                  }}>
                    ✓ {bankConnectionMessage}
                  </div>
                )}

                {bankConnectionStatus === 'error' && (
                  <div style={{
                    backgroundColor: colors.status.error,
                    color: 'white',
                    padding: '16px',
                    borderRadius: borderRadius.lg,
                    marginBottom: '24px',
                    fontSize: typography.fontSize.sm
                  }}>
                    ✗ {bankConnectionMessage}
                  </div>
                )}

                {/* Content based on selected subsection */}
                {portfolioSubView === 'all' && (
                  <AllBalances />
                )}

                {portfolioSubView === 'connect' && (
                  <SelectBank />
                )}

                {portfolioSubView === 'balances' && (
                  <AccountBalances />
                )}
              </div>
            ) : activeStocks.size === 0 ? (
              <div style={{
                backgroundColor: colors.bg.secondary,
                borderRadius: borderRadius.xl,
                padding: '60px',
                textAlign: 'center',
                border: `1px solid ${colors.border.default}`
              }}>
                <h2 style={{ fontSize: typography.fontSize['2xl'], marginBottom: '12px', color: colors.text.primary, fontWeight: typography.fontWeight.semibold }}>No stocks yet</h2>
                <p style={{ fontSize: typography.fontSize.md, color: colors.text.tertiary }}>
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
                      <h1 style={{ fontSize: typography.fontSize['3xl'], margin: 0, color: colors.text.primary, fontWeight: typography.fontWeight.bold }}>
                        {subscription.symbol}
                      </h1>
                      <div style={{ fontSize: typography.fontSize.sm, color: colors.text.tertiary, marginTop: '6px' }}>
                        {subscription.status === 'streaming' && (
                          <span style={{ color: colors.status.success }}>● Live stream</span>
                        )}
                        {subscription.status === 'paused' && (
                          <span style={{ color: colors.status.warning }}>◉ Stream paused</span>
                        )}
                        {subscription.status === 'loading' && (
                          <span style={{ color: colors.status.warning }}>○ Loading...</span>
                        )}
                        {subscription.status === 'error' && (
                          <span style={{ color: colors.status.error }}>● Error</span>
                        )}
                      </div>
                    </div>
                    {/* Subscribe/Unsubscribe button for permanent watchlist */}
                    <button
                      onClick={() => subscription.isPermanent
                        ? removePermanentSubscription(subscription.symbol)
                        : addPermanentSubscription(subscription.symbol)
                      }
                      style={{
                        padding: '10px 20px',
                        fontSize: typography.fontSize.sm,
                        fontWeight: typography.fontWeight.medium,
                        backgroundColor: subscription.isPermanent ? 'transparent' : colors.accent.primary,
                        color: subscription.isPermanent ? colors.status.error : '#ffffff',
                        border: subscription.isPermanent ? `1px solid ${colors.status.error}` : 'none',
                        borderRadius: borderRadius.lg,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {subscription.isPermanent ? 'Remove from Watchlist' : 'Add to Watchlist'}
                    </button>
                  </div>

                  {subscription.status === 'error' && (
                    <div style={{
                      padding: '16px',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      color: '#fecaca',
                      borderRadius: borderRadius.lg,
                      marginBottom: '20px',
                      border: `1px solid ${colors.status.error}`
                    }}>
                      Error: {subscription.errorMessage || 'Unknown error'}
                    </div>
                  )}

                  {subscription.status === 'loading' && (
                    <div style={{
                      backgroundColor: colors.bg.secondary,
                      borderRadius: borderRadius.xl,
                      padding: '60px',
                      textAlign: 'center',
                      border: `1px solid ${colors.border.default}`
                    }}>
                      <div style={{ fontSize: typography.fontSize.md, color: colors.text.tertiary }}>
                        Connecting to {subscription.symbol}...
                      </div>
                    </div>
                  )}

                  {(subscription.status === 'streaming' || subscription.status === 'paused') &&
                   subscription.stockData?.candles &&
                   Object.keys(subscription.stockData.candles).length > 0 && (
                    <div style={{
                      backgroundColor: colors.bg.secondary,
                      borderRadius: borderRadius.xl,
                      padding: '20px',
                      border: `1px solid ${colors.border.default}`
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
                      backgroundColor: colors.bg.secondary,
                      borderRadius: borderRadius.xl,
                      padding: '60px',
                      textAlign: 'center',
                      border: `1px solid ${colors.border.default}`
                    }}>
                      <div style={{ fontSize: typography.fontSize.md, color: colors.text.tertiary }}>
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
              backgroundColor: colors.bg.secondary,
              borderLeft: `1px solid ${colors.border.default}`,
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

