import { useEffect, useState } from 'react'
import { SnapTradeService, SnapTradeError } from '../services/snaptrade-service'
import { getAuthToken } from '../lib/auth'
import { colors, borderRadius, typography } from '../theme'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HoldingsResponse = any

export default function BrokerageBalances() {
  const [data, setData] = useState<HoldingsResponse>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showValues, setShowValues] = useState(false)
  const [notConnected, setNotConnected] = useState(false)
  const [expandedAccounts, setExpandedAccounts] = useState<Set<number>>(new Set())

  const toggleAccount = (idx: number) => {
    setExpandedAccounts(prev => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  const loadData = async () => {
    setLoading(true)
    setError(null)
    setNotConnected(false)

    try {
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Please sign in to view your brokerage balances')
      }

      const service = new SnapTradeService()
      const result = await service.getHoldings(token)
      setData(result)
    } catch (err) {
      if (err instanceof SnapTradeError && err.statusCode === 404) {
        setNotConnected(true)
      } else {
        setError(err instanceof Error ? err.message : String(err))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(amount)
  }

  const obfuscate = () => '••••••'

  const holdings = data?.holdings || []

  const totalValue = holdings.reduce((sum: number, h: HoldingsResponse) => {
    return sum + (h.total_value?.value || 0)
  }, 0)

  const totalCurrency = holdings[0]?.total_value?.currency || 'GBP'

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h3 style={{ margin: '0 0 8px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>
            Brokerage Balances
          </h3>
          <p style={{ margin: 0, color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>
            View your connected brokerage accounts and holdings
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={loadData}
            disabled={loading}
            style={{
              padding: '10px 20px',
              backgroundColor: colors.bg.tertiary,
              color: colors.text.primary,
              border: `1px solid ${colors.border.default}`,
              borderRadius: borderRadius.md,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.semibold,
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button
            onClick={() => setShowValues(!showValues)}
            style={{
              padding: '10px 20px',
              backgroundColor: colors.bg.tertiary,
              color: colors.text.primary,
              border: `1px solid ${colors.border.default}`,
              borderRadius: borderRadius.md,
              cursor: 'pointer',
              fontSize: typography.fontSize.sm,
              fontWeight: typography.fontWeight.semibold,
            }}
          >
            {showValues ? 'Hide Values' : 'Show Values'}
          </button>
        </div>
      </div>

      {loading && <div style={{ color: colors.text.tertiary }}>Loading brokerage balances...</div>}
      {error && (
        <div style={{
          color: colors.status.error,
          padding: '16px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderRadius: borderRadius.lg,
          marginBottom: 16,
          border: `1px solid ${colors.status.error}`,
        }}>
          {error}
        </div>
      )}

      {!loading && notConnected && (
        <div style={{
          padding: 24,
          borderRadius: borderRadius.lg,
          border: `1px solid ${colors.status.warning}`,
          backgroundColor: colors.bg.tertiary,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: typography.fontSize.md, color: colors.text.primary, marginBottom: 12 }}>
            No Brokerage Connected
          </div>
          <div style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary }}>
            Connect a brokerage account from the "Connect Brokerage" tab to view your holdings
          </div>
        </div>
      )}

      {!loading && holdings.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Total Value Card */}
          <div style={{
            padding: 24,
            borderRadius: borderRadius.xl,
            border: `1px solid ${colors.accent.primary}`,
            background: `linear-gradient(135deg, ${colors.accent.muted} 0%, ${colors.bg.secondary} 100%)`,
          }}>
            <div style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: 8 }}>Total Brokerage Value</div>
            <div style={{ fontSize: '36px', fontWeight: typography.fontWeight.bold, color: colors.status.success }}>
              {showValues ? formatCurrency(totalValue, totalCurrency) : obfuscate()}
            </div>
            <div style={{ fontSize: typography.fontSize.sm, color: colors.text.tertiary, marginTop: 12 }}>
              {holdings.length} account{holdings.length !== 1 ? 's' : ''} connected
            </div>
          </div>

          {/* Per-Account Cards */}
          {holdings.map((holding: HoldingsResponse, accountIdx: number) => {
            const account = holding.account || {}
            const accountName = String(account.name || account.institution_name || `Account ${accountIdx + 1}`)
            const accountNumber = String(account.number || '')
            const accountType = account.meta?.type ? String(account.meta.type) : null
            const accountCurrency = holding.total_value?.currency || account.meta?.currency || 'GBP'
            const accountTotal = holding.total_value?.value || 0

            return (
              <div
                key={String(account.id || accountIdx)}
                style={{
                  padding: 20,
                  borderRadius: borderRadius.lg,
                  border: `1px solid ${colors.border.default}`,
                  backgroundColor: colors.bg.secondary,
                }}
              >
                {/* Account Header — click to expand/collapse */}
                <div
                  onClick={() => toggleAccount(accountIdx)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    cursor: 'pointer',
                    userSelect: 'none',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontSize: typography.fontSize.sm,
                        color: colors.text.tertiary,
                        transition: 'transform 0.2s',
                        display: 'inline-block',
                        transform: expandedAccounts.has(accountIdx) ? 'rotate(90deg)' : 'rotate(0deg)',
                      }}>
                        &#9654;
                      </span>
                      <span style={{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                        {accountName}
                      </span>
                    </div>
                    {accountNumber && (
                      <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: 4, marginLeft: 22 }}>
                        Account: {accountNumber}
                      </div>
                    )}
                    {accountType && (
                      <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: 2, marginLeft: 22 }}>
                        {accountType}
                      </div>
                    )}
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary }}>Total Value</div>
                    <div style={{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.status.success }}>
                      {showValues ? formatCurrency(accountTotal, accountCurrency) : obfuscate()}
                    </div>
                  </div>
                </div>

                {expandedAccounts.has(accountIdx) && <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
                  {/* Cash Balances */}
                  {(holding.balances || []).map((bal: HoldingsResponse, idx: number) => {
                    const cashAmount = Number(bal.cash) || 0
                    const currCode = String(bal.currency?.code || 'GBP')
                    return (
                      <div
                        key={`cash-${idx}`}
                        style={{
                          padding: 16,
                          borderRadius: borderRadius.md,
                          backgroundColor: colors.bg.tertiary,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <div>
                          <div style={{ fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.medium, color: colors.text.secondary }}>
                            Cash ({currCode})
                          </div>
                        </div>
                        <div style={{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.text.primary }}>
                          {showValues ? formatCurrency(cashAmount, currCode) : obfuscate()}
                        </div>
                      </div>
                    )
                  })}

                  {/* Positions */}
                  {(holding.positions || []).map((pos: HoldingsResponse, idx: number) => {
                    // pos.symbol.symbol is the inner UniversalSymbol object
                    const innerSymbol = pos.symbol?.symbol || {}
                    const ticker = String(innerSymbol.symbol || innerSymbol.raw_symbol || 'Unknown')
                    const description = String(innerSymbol.description || '')
                    const currCode = String(pos.currency?.code || innerSymbol.currency?.code || 'GBP')
                    const units = Number(pos.units) || 0
                    const price = Number(pos.price) || 0
                    const avgPrice = Number(pos.average_purchase_price) || 0
                    const openPnl = Number(pos.open_pnl) || 0
                    const positionValue = units * price

                    return (
                      <div
                        key={`pos-${idx}`}
                        style={{
                          padding: 16,
                          borderRadius: borderRadius.md,
                          backgroundColor: colors.bg.tertiary,
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: typography.fontSize.sm, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                            {ticker}
                          </div>
                          {description && (
                            <div style={{
                              fontSize: typography.fontSize.xs,
                              color: colors.text.tertiary,
                              marginTop: 2,
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                            }}>
                              {description}
                            </div>
                          )}
                          <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: 4 }}>
                            {units} units @ {showValues ? formatCurrency(avgPrice, currCode) : obfuscate()} avg
                          </div>
                          <div style={{
                            fontSize: typography.fontSize.xs,
                            color: openPnl >= 0 ? colors.status.success : colors.status.error,
                            marginTop: 2,
                          }}>
                            P/L: {showValues ? formatCurrency(openPnl, currCode) : obfuscate()}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', marginLeft: 16 }}>
                          <div style={{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                            {showValues ? formatCurrency(positionValue, currCode) : obfuscate()}
                          </div>
                          <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: 2 }}>
                            @ {showValues ? formatCurrency(price, currCode) : obfuscate()}
                          </div>
                        </div>
                      </div>
                    )
                  })}

                  {(!holding.positions || holding.positions.length === 0) && (!holding.balances || holding.balances.length === 0) && (
                    <div style={{ color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>No holdings data available</div>
                  )}
                </div>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
