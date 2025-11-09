import { useState, useEffect, useRef } from 'react'

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
    // Connect to news stream
    const eventSource = new EventSource(`${backendUrl}/news/stream`)
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
      setStatus('error')
    }

    // Cleanup on unmount
    return () => {
      eventSource.close()
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
      backgroundColor: '#1a1a1a',
      borderRadius: '8px',
      padding: '20px',
      marginTop: '20px'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '15px'
      }}>
        <h2 style={{ margin: 0 }}>Market News</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {status === 'connected' && (
            <>
              <span style={{
                width: '8px',
                height: '8px',
                backgroundColor: '#4CAF50',
                borderRadius: '50%',
                display: 'inline-block'
              }} />
              <span style={{ fontSize: '14px', color: '#4CAF50' }}>Live</span>
            </>
          )}
          {status === 'connecting' && (
            <span style={{ fontSize: '14px', color: '#ff9800' }}>Connecting...</span>
          )}
          {status === 'error' && (
            <span style={{ fontSize: '14px', color: '#f44336' }}>Connection Error</span>
          )}
        </div>
      </div>

      <div style={{
        maxHeight: '400px',
        overflowY: 'auto',
        border: '1px solid #333',
        borderRadius: '4px',
        padding: '10px'
      }}>
        {newsItems.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '20px',
            color: '#888'
          }}>
            Waiting for news...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {newsItems.map((item, index) => (
              <div
                key={index}
                style={{
                  backgroundColor: '#242424',
                  borderRadius: '4px',
                  padding: '12px',
                  cursor: 'pointer',
                  transition: 'background-color 0.2s',
                  border: expandedIndex === index ? '1px solid #008CBA' : '1px solid transparent'
                }}
                onClick={() => toggleExpand(index)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontWeight: 'bold',
                      marginBottom: '6px',
                      fontSize: '14px'
                    }}>
                      {item.headline}
                    </div>
                    {item.tickers && item.tickers.length > 0 && (
                      <div style={{
                        display: 'flex',
                        gap: '6px',
                        marginBottom: '6px',
                        flexWrap: 'wrap'
                      }}>
                        {item.tickers.slice(0, 5).map((ticker, i) => (
                          <span
                            key={i}
                            style={{
                              backgroundColor: '#333',
                              padding: '2px 8px',
                              borderRadius: '3px',
                              fontSize: '11px',
                              color: '#4CAF50'
                            }}
                          >
                            {ticker}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div style={{
                    fontSize: '12px',
                    color: '#888',
                    marginLeft: '12px',
                    whiteSpace: 'nowrap'
                  }}>
                    {formatTime(item.time)}
                  </div>
                </div>

                {expandedIndex === index && item.summary && (
                  <div style={{
                    marginTop: '12px',
                    paddingTop: '12px',
                    borderTop: '1px solid #333',
                    fontSize: '13px',
                    lineHeight: '1.5',
                    color: '#ccc'
                  }}>
                    {item.summary}
                    {item.url && (
                      <div style={{ marginTop: '8px' }}>
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            color: '#008CBA',
                            fontSize: '12px',
                            textDecoration: 'none'
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
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default NewsFeed
