import { useEffect, useState } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'
import { getAuthToken } from '../lib/auth'
import {
  BalancesData,
  accountTitle,
  balanceTypeName,
  getAccounts,
} from '../lib/bankAccounts'
import { colors, borderRadius, typography } from '../theme'

export default function AccountBalances() {
  const [balancesData, setBalancesData] = useState<BalancesData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [removingId, setRemovingId] = useState<string | null>(null)
  const [removeError, setRemoveError] = useState<string | null>(null)

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

  const handleRemovePending = async (requisitionId: string, institutionName: string) => {
    if (!window.confirm(`Remove the pending ${institutionName} connection?`)) return

    setRemovingId(requisitionId)
    setRemoveError(null)
    try {
      const token = await getAuthToken()
      if (!token) throw new Error('Please sign in to remove connections')

      await new BankClientDatafeed().deleteRequisition(requisitionId, token)
      setBalancesData((prev) =>
        prev && {
          ...prev,
          pending_requisitions: prev.pending_requisitions.filter(
            (p) => p.requisition_id !== requisitionId
          ),
        }
      )
    } catch (err) {
      setRemoveError(err instanceof Error ? err.message : String(err))
    } finally {
      setRemovingId(null)
    }
  }

  const formatCurrency = (amount: string, currency: string) => {
    const num = parseFloat(amount)
    return new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: currency,
    }).format(num)
  }

  const accounts = balancesData ? getAccounts(balancesData) : []
  const pending = balancesData?.pending_requisitions ?? []

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
          {/* Pending connections */}
          {pending.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: colors.status.warning, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>
                Pending Bank Connections ({pending.length})
              </h4>
              {removeError && (
                <div style={{ color: colors.status.error, fontSize: typography.fontSize.sm, marginBottom: 12 }}>
                  {removeError}
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {pending.map((p) => {
                  const removing = removingId === p.requisition_id
                  return (
                    <div
                      key={p.requisition_id}
                      style={{
                        padding: 20,
                        borderRadius: borderRadius.lg,
                        border: `1px solid ${colors.status.warning}`,
                        backgroundColor: colors.bg.tertiary,
                      }}
                    >
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                          {p.institution_name}
                        </div>
                        <div style={{ fontSize: typography.fontSize.sm, color: colors.status.warning, marginTop: 4 }}>
                          {p.status_label ?? `Status: ${p.status}`}
                        </div>
                      </div>
                      <div style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: 16 }}>
                        {p.message}
                      </div>
                      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        {p.link && (
                          <a
                            href={p.link}
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
                        <button
                          type="button"
                          onClick={() => handleRemovePending(p.requisition_id, p.institution_name)}
                          disabled={removing}
                          style={{
                            padding: '10px 20px',
                            backgroundColor: 'transparent',
                            color: colors.status.error,
                            border: `1px solid ${colors.status.error}`,
                            borderRadius: borderRadius.md,
                            cursor: removing ? 'default' : 'pointer',
                            fontSize: typography.fontSize.sm,
                            fontWeight: typography.fontWeight.semibold,
                          }}
                        >
                          {removing ? 'Removing...' : 'Remove'}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Connected accounts, one card each */}
          {accounts.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>
                Connected Accounts ({accounts.length})
              </h4>
              {accounts.map((account) => (
                <div
                  key={account.account_id}
                  style={{
                    padding: 20,
                    borderRadius: borderRadius.lg,
                    border: `1px solid ${colors.border.default}`,
                    backgroundColor: colors.bg.secondary,
                    marginBottom: 16,
                  }}
                >
                  <div style={{ marginBottom: 16, fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                    {accountTitle(account, accounts)}
                  </div>

                  {account.balances.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {account.balances.map((balance, idx) => (
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
                              {balanceTypeName(balance.balanceType)}
                            </div>
                            {balance.referenceDate && (
                              <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: 4 }}>
                                As of {new Date(balance.referenceDate).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                          <div style={{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.status.success }}>
                            {formatCurrency(balance.balanceAmount.amount, balance.balanceAmount.currency)}
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

          {accounts.length === 0 && pending.length === 0 && (
            <div style={{ color: colors.text.secondary, textAlign: 'center', padding: 24 }}>
              No connected bank accounts found. Connect a bank to view your balances.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
