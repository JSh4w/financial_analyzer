import { useEffect, useState } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'
import { getAuthToken } from '../lib/auth'
import { colors, borderRadius, typography } from '../theme'

interface Balance {
  balanceAmount: {
    amount: string
    currency: string
  }
  balanceType: string
  referenceDate?: string
}

interface PendingRequisition {
  requisition_id: string
  institution_id: string
  institution_name: string
  status: string
  link?: string
  message: string
}

interface BalancesData {
  balances: {
    [institutionName: string]: Balance[]
  }
  pending_requisitions: PendingRequisition[]
}

export default function AccountBalances() {
  const [balancesData, setBalancesData] = useState<BalancesData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadBalances = async () => {
      setLoading(true)
      setError(null)
      try {
        const token = await getAuthToken()
        if (!token) {
          throw new Error('Please sign in to view your balances')
        }

        const df = new BankClientDatafeed()
        const data = await df.getAllBalances(token)
        setBalancesData(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    }
    loadBalances()
  }, [])

  const formatCurrency = (amount: string, currency: string) => {
    const num = parseFloat(amount)
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(num)
  }

  return (
    <div>
      <h3 style={{ margin: '0 0 8px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>Account Balances</h3>
      <p style={{ margin: '0 0 24px 0', color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>
        View all your connected bank account balances
      </p>

      {loading && <div style={{ color: colors.text.tertiary }}>Loading balances...</div>}
      {error && <div style={{ color: colors.status.error, padding: '16px', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: borderRadius.lg, border: `1px solid ${colors.status.error}` }}>Error: {error}</div>}

      {!loading && !error && balancesData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Pending Requisitions Section */}
          {balancesData.pending_requisitions && balancesData.pending_requisitions.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: colors.status.warning, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>
                Pending Bank Connections ({balancesData.pending_requisitions.length})
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {balancesData.pending_requisitions.map((pending) => (
                  <div
                    key={pending.requisition_id}
                    style={{
                      padding: 20,
                      borderRadius: borderRadius.lg,
                      border: `1px solid ${colors.status.warning}`,
                      backgroundColor: colors.bg.tertiary,
                    }}
                  >
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                        {pending.institution_name}
                      </div>
                      <div style={{ fontSize: typography.fontSize.sm, color: colors.status.warning, marginTop: 4 }}>
                        Status: {pending.status}
                      </div>
                    </div>
                    <div style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: 16 }}>
                      {pending.message}
                    </div>
                    {pending.link && (
                      <a
                        href={pending.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          display: 'inline-block',
                          padding: '10px 20px',
                          background: colors.accent.primary,
                          color: 'white',
                          textDecoration: 'none',
                          borderRadius: borderRadius.md,
                          fontSize: typography.fontSize.sm,
                          fontWeight: typography.fontWeight.semibold,
                        }}
                      >
                        Complete Authentication →
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Active Balances Section */}
          {Object.keys(balancesData.balances).length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>Connected Banks</h4>
              {Object.entries(balancesData.balances).map(([institutionName, balances]) => (
                <div
                  key={institutionName}
                  style={{
                    padding: 20,
                    borderRadius: borderRadius.lg,
                    border: `1px solid ${colors.border.default}`,
                    backgroundColor: colors.bg.secondary,
                    marginBottom: 16,
                  }}
                >
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                      {institutionName}
                    </div>
                  </div>

                  {Array.isArray(balances) && balances.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {balances.map((balance, idx) => (
                        <div
                          key={idx}
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
                              {balance.balanceType}
                            </div>
                            {balance.referenceDate && (
                              <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: 4 }}>
                                As of {new Date(balance.referenceDate).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                          <div style={{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.status.success }}>
                            {formatCurrency(
                              balance.balanceAmount.amount,
                              balance.balanceAmount.currency
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>No balances available</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {Object.keys(balancesData.balances).length === 0 &&
           (!balancesData.pending_requisitions || balancesData.pending_requisitions.length === 0) && (
            <div style={{ color: colors.text.secondary, textAlign: 'center', padding: 24 }}>
              No connected bank accounts found. Connect a bank to view your balances.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
