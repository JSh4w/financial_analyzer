import { useState, useEffect, useRef } from 'react'
import { getAuthToken } from '../lib/auth'
import { colors, borderRadius, typography } from '../theme'

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
      padding: '20px'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '16px'
      }}>
        <h2 style={{ margin: 0, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>Market News</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {status === 'connected' && (
            <>
              <span style={{
                width: '6px',
                height: '6px',
                backgroundColor: colors.status.success,
                borderRadius: '50%',
                display: 'inline-block'
              }} />
              <span style={{ fontSize: typography.fontSize.xs, color: colors.status.success }}>Live</span>
            </>
          )}
          {status === 'connecting' && (
            <span style={{ fontSize: typography.fontSize.xs, color: colors.status.warning }}>Connecting...</span>
          )}
          {status === 'error' && (
            <span style={{ fontSize: typography.fontSize.xs, color: colors.status.error }}>Error</span>
          )}
        </div>
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}>
        {newsItems.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: colors.text.tertiary,
            fontSize: typography.fontSize.sm
          }}>
            Waiting for news...
          </div>
        ) : (
          newsItems.map((item, index) => (
            <div
              key={index}
              style={{
                backgroundColor: colors.bg.primary,
                borderRadius: borderRadius.lg,
                padding: '14px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                border: expandedIndex === index ? `1px solid ${colors.accent.primary}` : `1px solid ${colors.border.default}`
              }}
              onClick={() => toggleExpand(index)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontWeight: typography.fontWeight.medium,
                    marginBottom: '8px',
                    fontSize: typography.fontSize.sm,
                    lineHeight: '1.4',
                    color: colors.text.primary
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
                            backgroundColor: colors.accent.muted,
                            padding: '2px 8px',
                            borderRadius: borderRadius.sm,
                            fontSize: typography.fontSize.xs,
                            color: colors.accent.primary,
                            fontWeight: typography.fontWeight.medium,
                            fontFamily: typography.fontFamily.mono
                          }}
                        >
                          {ticker}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{
                  fontSize: typography.fontSize.xs,
                  color: colors.text.tertiary,
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
                  borderTop: `1px solid ${colors.border.default}`,
                  fontSize: typography.fontSize.xs,
                  lineHeight: '1.6',
                  color: colors.text.secondary
                }}>
                  {item.summary}
                  {item.url && (
                    <div style={{ marginTop: '10px' }}>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: colors.accent.primary,
                          fontSize: typography.fontSize.xs,
                          textDecoration: 'none',
                          fontWeight: typography.fontWeight.medium
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
