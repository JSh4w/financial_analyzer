import { useEffect, useMemo, useState, CSSProperties } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'
import { getAuthToken } from '../lib/auth'
import { colors, borderRadius } from '../theme'

interface Institution {
  id: string
  name: string
  bic?: string
  transaction_total_days?: string
  countries?: string[]
  logo?: string
  max_access_valid_for_days?: string
  max_access_valid_for_days_reconfirmation?: string
}

export default function SelectBank() {
  const [institutions, setInstitutions] = useState<Institution[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const df = new BankClientDatafeed()
        const list = await df.getInstitutions()
        setInstitutions(list || [])
      } catch (err: any) {
        setError(String(err))
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const institutionsSorted = useMemo(() => {
    return institutions
      .slice()
      .sort((a, b) => (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }))
  }, [institutions])

  const handleBankClick = async (inst: Institution) => {
    setConnecting(true)
    setError(null)
    try {
      // Get auth token
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Please sign in to connect your bank')
      }

      // Create requisition
      const df = new BankClientDatafeed()
      const redirectUri = `${window.location.origin}/portfolio`
      const result = await df.createRequisition(inst.id, redirectUri, token)

      // Redirect to GoCardless auth page
      window.location.href = result.link
    } catch (err: any) {
      setError(String(err.message || err))
      setConnecting(false)
    }
  }

  const getBankCardStyle = (isHovered: boolean): CSSProperties => ({
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
        Select your bank
      </h3>
      <p style={{ margin: '0 0 16px 0', color: colors.text.secondary, fontSize: '14px', lineHeight: 1.5 }}>
        Choose the bank you want to connect. This makes the Open Banking flow quicker and
        more reliable.
      </p>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '13px', color: colors.text.tertiary }}>
          {institutions.length} banks available
        </div>
      </div>

      {loading && (
        <div style={{ color: colors.text.secondary, padding: '20px 0' }}>
          Loading banks...
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
          Connecting to bank...
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
          {institutionsSorted.map((inst) => (
            <button
              key={inst.id}
              onClick={() => handleBankClick(inst)}
              onMouseEnter={() => setHoveredId(inst.id)}
              onMouseLeave={() => setHoveredId(null)}
              disabled={connecting}
              style={getBankCardStyle(hoveredId === inst.id)}
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
                {inst.logo ? (
                  <img
                    src={inst.logo}
                    alt={inst.name}
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
                    borderRadius: borderRadius.sm
                  }} />
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
                  {inst.name}
                </div>
              </div>
            </button>
          ))}

          {institutionsSorted.length === 0 && (
            <div style={{
              gridColumn: '1 / -1',
              color: colors.text.tertiary,
              padding: '40px 20px',
              textAlign: 'center'
            }}>
              No banks found.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
