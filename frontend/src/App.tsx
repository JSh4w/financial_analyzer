import { useState, useEffect, useRef } from 'react'
import './App.css'

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
  update_timestamp?: number
}

function App() {
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [stockData, setStockData] = useState<StockData[]>([])
  const [status, setStatus] = useState('')
  const eventSourceRef = useRef<EventSource | null>(null)

  const BACKEND_URL = 'http://localhost:8001'

  const subscribeToApple = async () => {
    try {
      setStatus('Subscribing to AAPL...')
      const response = await fetch(`${BACKEND_URL}/ws_manager/AAPL`)
      const result = await response.json()
      
      if (result.status === 'subscribed') {
        setIsSubscribed(true)
        setStatus(`✅ ${result.message}`)
      } else {
        setStatus(`❌ ${result.message}`)
      }
    } catch (error) {
      setStatus(`❌ Error: ${error}`)
    }
  }

  const startStreaming = () => {
    if (!isSubscribed) {
      setStatus('❌ Please subscribe to AAPL first')
      return
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    setStatus('Starting SSE connection...')
    const eventSource = new EventSource(`${BACKEND_URL}/stream/AAPL`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setIsStreaming(true)
      setStatus('🔴 Live streaming AAPL data')
    }

    eventSource.onmessage = (event) => {
      try {
        const data: StockData = JSON.parse(event.data)
        setStockData(prev => [data, ...prev.slice(0, 9)]) // Keep last 10 updates
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error)
      setStatus('❌ SSE connection error')
      setIsStreaming(false)
    }
  }

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsStreaming(false)
    setStatus('Stopped streaming')
  }

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  return (
    <>
      <div>
        <h1>Stock Market SSE Test</h1>
        
        <div className="card" style={{ textAlign: 'left' }}>
          <h2>Controls</h2>
          <div style={{ marginBottom: '20px' }}>
            <button 
              onClick={subscribeToApple}
              disabled={isSubscribed}
              style={{ 
                marginRight: '10px',
                backgroundColor: isSubscribed ? '#4CAF50' : '#008CBA',
                opacity: isSubscribed ? 0.6 : 1
              }}
            >
              {isSubscribed ? '✅ Subscribed to AAPL' : 'Subscribe to AAPL'}
            </button>
            
            {!isStreaming ? (
              <button onClick={startStreaming}>
                🔴 Start Streaming
              </button>
            ) : (
              <button onClick={stopStreaming} style={{ backgroundColor: '#f44336' }}>
                ⏹️ Stop Streaming
              </button>
            )}
          </div>
          
          <div style={{ marginBottom: '20px' }}>
            <strong>Status:</strong> <span>{status}</span>
          </div>
        </div>

        <div className="card" style={{ textAlign: 'left' }}>
          <h2>Live Data Stream</h2>
          {stockData.length === 0 ? (
            <p>No data received yet...</p>
          ) : (
            <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {stockData.map((data, index) => (
                <div key={index} style={{ 
                  border: '1px solid #ddd', 
                  padding: '10px', 
                  marginBottom: '10px',
                  backgroundColor: index === 0 ? '#2a2a2a' : '#1a1a1a',
                  color: '#ffffff',
                  borderRadius: '8px'
                }}>
                  <div style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#61dafb' }}>Symbol:</strong> {data.symbol}
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#61dafb' }}>Timestamp:</strong> {data.update_timestamp ? new Date(data.update_timestamp * 1000).toLocaleTimeString() : new Date().toLocaleTimeString()}
                  </div>
                  {data.candles && Object.keys(data.candles).length > 0 && (
                    <div>
                      <strong style={{ color: '#61dafb' }}>OHLCV Data ({Object.keys(data.candles).length} candles):</strong>
                      <div style={{ marginLeft: '20px', marginTop: '5px', maxHeight: '200px', overflowY: 'auto' }}>
                        {Object.entries(data.candles)
                          .sort(([a], [b]) => parseInt(b) - parseInt(a)) // Sort by timestamp descending (latest first)
                          .map(([timestamp, candle]) => (
                            <div key={timestamp} style={{ 
                              marginBottom: '10px', 
                              padding: '8px', 
                              border: '1px solid #444', 
                              borderRadius: '4px',
                              backgroundColor: '#333'
                            }}>
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.9em' }}>
                                <div><strong>Open:</strong> <span style={{ color: '#4CAF50' }}>${candle.open?.toFixed(2)}</span></div>
                                <div><strong>High:</strong> <span style={{ color: '#4CAF50' }}>${candle.high?.toFixed(2)}</span></div>
                                <div><strong>Low:</strong> <span style={{ color: '#f44336' }}>${candle.low?.toFixed(2)}</span></div>
                                <div><strong>Close:</strong> <span style={{ color: candle.close > candle.open ? '#4CAF50' : '#f44336' }}>${candle.close?.toFixed(2)}</span></div>
                                <div style={{ gridColumn: 'span 2' }}><strong>Volume:</strong> <span style={{ color: '#ff9800' }}>{candle.volume?.toLocaleString()}</span></div>
                                <div style={{ gridColumn: 'span 2', fontSize: '0.8em', color: '#888' }}>
                                  Time: {new Date(parseInt(timestamp)).toLocaleString()}
                                </div>
                              </div>
                            </div>
                          ))
                        }
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default App
