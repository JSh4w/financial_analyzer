import { useEffect, useMemo, useState, CSSProperties } from 'react'
import { SnapTradeReact } from 'snaptrade-react'
import { SnapTradeService, Brokerage } from '../services/snaptrade-service'
import { getAuthToken } from '../lib/auth'
import { colors, borderRadius } from '../theme'

interface SelectBrokerageProps {
  onSuccess?: () => void
}

export default function SelectBrokerage({ onSuccess }: SelectBrokerageProps) {
  const [brokerages, setBrokerages] = useState<Brokerage[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [loginLink, setLoginLink] = useState<string>('')
  const [portalOpen, setPortalOpen] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const service = new SnapTradeService()
        const list = await service.listBrokerages()
        setBrokerages(list)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const brokeragesSorted = useMemo(() => {
    return brokerages
      .slice()
      .sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }))
  }, [brokerages])

  const handleBrokerageClick = async (brokerage: Brokerage) => {
    setConnecting(true)
    setError(null)
    setSuccessMessage(null)
    try {
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Please sign in to connect your brokerage')
      }

      const service = new SnapTradeService()
      const result = await service.getLoginUrl(token, brokerage.slug, true)

      // Extract the URL string from the response
      const url = typeof result.redirect_url === 'string'
        ? result.redirect_url
        : (result.redirect_url as Record<string, string>)?.redirectURI || ''

      setLoginLink(url)
      setPortalOpen(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setConnecting(false)
    }
  }

  const handlePortalSuccess = (authorizationId: string) => {
    setPortalOpen(false)
    setLoginLink('')
    setSuccessMessage(`Brokerage connected successfully! (ID: ${authorizationId})`)
    onSuccess?.()
  }

  const handlePortalError = (data: { statusCode: string; detail: string }) => {
    setPortalOpen(false)
    setLoginLink('')
    setError(`Connection failed: ${data.detail}`)
  }

  const handlePortalClose = () => {
    setPortalOpen(false)
    setLoginLink('')
  }

  const getCardStyle = (isHovered: boolean): CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '16px',
    textAlign: 'left',
    borderRadius: borderRadius.lg,
    border: `1px solid ${isHovered ? colors.accent.primary : colors.border.default}`,
    backgroundColor: isHovered ? colors.bg.hover : colors.bg.tertiary,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
  })

  return (
    <div>
      <h3 style={{ margin: '0 0 8px 0', color: colors.text.primary, fontSize: '18px', fontWeight: 600 }}>
        Connect a brokerage
      </h3>
      <p style={{ margin: '0 0 16px 0', color: colors.text.secondary, fontSize: '14px', lineHeight: 1.5 }}>
        Choose a brokerage to connect your investment account and view your holdings.
      </p>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '13px', color: colors.text.tertiary }}>
          {brokerages.length} brokerages available
        </div>
      </div>

      {loading && (
        <div style={{ color: colors.text.secondary, padding: '20px 0' }}>
          Loading brokerages...
        </div>
      )}
      {connecting && (
        <div style={{
          color: colors.accent.primary,
          padding: '16px',
          backgroundColor: colors.accent.muted,
          borderRadius: borderRadius.lg,
          marginBottom: '16px'
        }}>
          Preparing connection portal...
        </div>
      )}
      {successMessage && (
        <div style={{
          color: 'white',
          padding: '16px',
          backgroundColor: colors.status.success,
          borderRadius: borderRadius.lg,
          marginBottom: '16px'
        }}>
          {successMessage}
        </div>
      )}
      {error && (
        <div style={{
          color: colors.status.error,
          padding: '16px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderRadius: borderRadius.lg,
          marginBottom: '16px',
          border: `1px solid ${colors.status.error}`
        }}>
          Error: {error}
        </div>
      )}

      {!loading && !error && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
          gap: '12px'
        }}>
          {brokeragesSorted.map((brokerage) => (
            <button
              key={brokerage.id}
              onClick={() => handleBrokerageClick(brokerage)}
              onMouseEnter={() => setHoveredId(brokerage.id)}
              onMouseLeave={() => setHoveredId(null)}
              disabled={connecting}
              style={getCardStyle(hoveredId === brokerage.id)}
            >
              <div style={{
                width: '48px',
                height: '48px',
                flex: '0 0 48px',
                backgroundColor: '#ffffff',
                borderRadius: borderRadius.md,
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {brokerage.square_logo_url || brokerage.logo_url ? (
                  <img
                    src={brokerage.square_logo_url || brokerage.logo_url}
                    alt={brokerage.name}
                    style={{
                      width: '40px',
                      height: '40px',
                      objectFit: 'contain'
                    }}
                  />
                ) : (
                  <div style={{
                    width: '40px',
                    height: '40px',
                    backgroundColor: colors.bg.hover,
                    borderRadius: borderRadius.sm,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '16px',
                    fontWeight: 700,
                    color: colors.text.tertiary,
                  }}>
                    {brokerage.name.charAt(0)}
                  </div>
                )}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '14px',
                  fontWeight: 600,
                  color: colors.text.primary,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {brokerage.display_name || brokerage.name}
                </div>
                {brokerage.allows_trading && (
                  <div style={{
                    fontSize: '11px',
                    color: colors.status.success,
                    marginTop: '2px',
                  }}>
                    Trading enabled
                  </div>
                )}
              </div>
            </button>
          ))}

          {brokeragesSorted.length === 0 && (
            <div style={{
              gridColumn: '1 / -1',
              color: colors.text.tertiary,
              padding: '40px 20px',
              textAlign: 'center'
            }}>
              No brokerages found.
            </div>
          )}
        </div>
      )}

      {portalOpen && loginLink && (
        <SnapTradeReact
          loginLink={loginLink}
          isOpen={portalOpen}
          close={handlePortalClose}
          onSuccess={handlePortalSuccess}
          onError={handlePortalError}
          onExit={handlePortalClose}
        />
      )}
    </div>
  )
}
