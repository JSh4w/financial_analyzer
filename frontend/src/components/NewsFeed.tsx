import { useState, useEffect, useRef } from 'react'
import { getAuthToken } from '../lib/auth'

interface NewsItem {
  time: string
  headline: string
  summary: string
  tickers: string[]
  source: string
  url: string
}

interface NewsFeedProps {
  backendUrl: string
}

function NewsFeed({ backendUrl }: NewsFeedProps) {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)
  const [status, setStatus] = useState<'connecting' | 'connected' | 'error'>('connecting')
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    let reconnectAttempts = 0
    const maxReconnectAttempts = 3
    let reconnectTimeout: NodeJS.Timeout

    // Connect to news stream with authentication
    const connectNewsStream = async () => {
      try {
        const token = await getAuthToken()
        if (!token) {
          console.error('Not authenticated for news stream')
          setStatus('error')
          return
        }

        // Close existing connection before creating new one
        if (eventSourceRef.current) {
          eventSourceRef.current.close()
        }

        const eventSource = new EventSource(`${backendUrl}/news/stream?token=${token}`)
        eventSourceRef.current = eventSource

        eventSource.onopen = () => {
          setStatus('connected')
          console.log('News stream connected')
        }

        eventSource.onmessage = (event) => {
          try {
            const newsItem: NewsItem = JSON.parse(event.data)
            setNewsItems((prev) => [newsItem, ...prev].slice(0, 50)) // Keep last 50 items
          } catch (error) {
            console.error('Error parsing news data:', error)
          }
        }

        eventSource.onerror = (error) => {
          console.error('News stream error:', error)
          eventSource.close()
          setStatus('error')

          // Attempt to reconnect
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++
            console.log(`News stream connection unsuccessful, attempt ${reconnectAttempts}...`)
            setStatus('connecting')
            reconnectTimeout = setTimeout(() => {
              connectNewsStream()
            }, 2000 * reconnectAttempts) // Exponential backoff
          }
        }
      } catch (error) {
        console.error('Failed to connect news stream:', error)
        setStatus('error')
      }
    }

    connectNewsStream()

    // Cleanup on unmount
    return () => {
      clearTimeout(reconnectTimeout)
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
    }
  }, [backendUrl])

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    })
  }

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '600', color: '#e0e0e0' }}>Market News</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {status === 'connected' && (
            <>
              <span style={{
                width: '6px',
                height: '6px',
                backgroundColor: '#10b981',
                borderRadius: '50%',
                display: 'inline-block'
              }} />
              <span style={{ fontSize: '12px', color: '#10b981' }}>Live</span>
            </>
          )}
          {status === 'connecting' && (
            <span style={{ fontSize: '12px', color: '#f59e0b' }}>Connecting...</span>
          )}
          {status === 'error' && (
            <span style={{ fontSize: '12px', color: '#ef4444' }}>Error</span>
          )}
        </div>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {newsItems.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: '#666',
            fontSize: '14px'
          }}>
            Waiting for news...
          </div>
        ) : (
          newsItems.map((item, index) => (
            <div
              key={index}
              style={{
                backgroundColor: '#0f0f0f',
                borderRadius: '8px',
                padding: '14px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                border: expandedIndex === index ? '1px solid #3b82f6' : '1px solid #2a2a2a'
              }}
              onClick={() => toggleExpand(index)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontWeight: '500',
                    marginBottom: '8px',
                    fontSize: '13px',
                    lineHeight: '1.4',
                    color: '#e0e0e0'
                  }}>
                    {item.headline}
                  </div>
                  {item.tickers && item.tickers.length > 0 && (
                    <div style={{
                      display: 'flex',
                      gap: '4px',
                      marginBottom: '4px',
                      flexWrap: 'wrap'
                    }}>
                      {item.tickers.slice(0, 5).map((ticker, i) => (
                        <span
                          key={i}
                          style={{
                            backgroundColor: '#1e3a4f',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            color: '#60a5fa',
                            fontWeight: '500'
                          }}
                        >
                          {ticker}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{
                  fontSize: '11px',
                  color: '#666',
                  whiteSpace: 'nowrap',
                  flexShrink: 0
                }}>
                  {formatTime(item.time)}
                </div>
              </div>

              {expandedIndex === index && item.summary && (
                <div style={{
                  marginTop: '12px',
                  paddingTop: '12px',
                  borderTop: '1px solid #2a2a2a',
                  fontSize: '12px',
                  lineHeight: '1.6',
                  color: '#a0a0a0'
                }}>
                  {item.summary}
                  {item.url && (
                    <div style={{ marginTop: '10px' }}>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: '#3b82f6',
                          fontSize: '12px',
                          textDecoration: 'none',
                          fontWeight: '500'
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        Read more →
                      </a>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default NewsFeed
