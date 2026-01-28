import { useEffect, useState } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'
import { T212Service, T212Summary, T212Error } from '../services/t212-service'
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

interface T212KeysModalProps {
  onClose: () => void
  onSubmit: (keyId: string, keySecret: string) => void
  loading: boolean
}

function T212KeysModal({ onClose, onSubmit, loading }: T212KeysModalProps) {
  const [keyId, setKeyId] = useState('')
  const [keySecret, setKeySecret] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (keyId.trim() && keySecret.trim()) {
      onSubmit(keyId.trim(), keySecret.trim())
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: colors.bg.secondary,
          borderRadius: borderRadius.xl,
          padding: 32,
          maxWidth: 500,
          width: '90%',
          border: `1px solid ${colors.border.default}`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 8px 0', color: colors.text.primary, fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold }}>
          Add Trading212 API Keys
        </h3>
        <p style={{ margin: '0 0 24px 0', color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>
          Enter your Trading212 API credentials to connect your account
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label
              htmlFor="keyId"
              style={{ display: 'block', marginBottom: 8, color: colors.text.secondary, fontSize: typography.fontSize.sm }}
            >
              API Key ID
            </label>
            <input
              id="keyId"
              type="text"
              value={keyId}
              onChange={(e) => setKeyId(e.target.value)}
              placeholder="Enter your API Key ID"
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px 16px',
                fontSize: typography.fontSize.sm,
                backgroundColor: colors.bg.primary,
                color: colors.text.primary,
                border: `1px solid ${colors.border.default}`,
                borderRadius: borderRadius.lg,
                outline: 'none',
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label
              htmlFor="keySecret"
              style={{ display: 'block', marginBottom: 8, color: colors.text.secondary, fontSize: typography.fontSize.sm }}
            >
              API Secret Key
            </label>
            <input
              id="keySecret"
              type="password"
              value={keySecret}
              onChange={(e) => setKeySecret(e.target.value)}
              placeholder="Enter your API Secret Key"
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px 16px',
                fontSize: typography.fontSize.sm,
                backgroundColor: colors.bg.primary,
                color: colors.text.primary,
                border: `1px solid ${colors.border.default}`,
                borderRadius: borderRadius.lg,
                outline: 'none',
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                padding: '10px 20px',
                backgroundColor: 'transparent',
                color: colors.text.secondary,
                border: `1px solid ${colors.border.default}`,
                borderRadius: borderRadius.md,
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: typography.fontSize.sm,
                fontWeight: typography.fontWeight.semibold,
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !keyId.trim() || !keySecret.trim()}
              style={{
                padding: '10px 20px',
                backgroundColor: loading || !keyId.trim() || !keySecret.trim() ? colors.bg.tertiary : colors.accent.primary,
                color: 'white',
                border: 'none',
                borderRadius: borderRadius.md,
                cursor: loading || !keyId.trim() || !keySecret.trim() ? 'not-allowed' : 'pointer',
                fontSize: typography.fontSize.sm,
                fontWeight: typography.fontWeight.semibold,
              }}
            >
              {loading ? 'Adding...' : 'Add Keys'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function AllBalances() {
  const [balancesData, setBalancesData] = useState<BalancesData | null>(null)
  const [t212Summary, setT212Summary] = useState<T212Summary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showValues, setShowValues] = useState(false)
  const [t212NotFound, setT212NotFound] = useState(false)
  const [showT212Modal, setShowT212Modal] = useState(false)
  const [addingKeys, setAddingKeys] = useState(false)

  const loadData = async () => {
    setLoading(true)
    setError(null)
    setT212NotFound(false)

    try {
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Please sign in to view your balances')
      }

      // Load bank balances
      const bankDatafeed = new BankClientDatafeed()
      const bankData = await bankDatafeed.getAllBalances(token)
      setBalancesData(bankData)

      // Try to load T212 summary
      const t212Service = new T212Service()
      try {
        const t212Data = await t212Service.getSummary(token)
        setT212Summary(t212Data)
      } catch (err) {
        if (err instanceof T212Error && err.statusCode === 404) {
          setT212NotFound(true)
        } else {
          console.error('Error loading T212 data:', err)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleAddT212Keys = async (keyId: string, keySecret: string) => {
    setAddingKeys(true)
    try {
      const token = await getAuthToken()
      if (!token) {
        throw new Error('Please sign in')
      }

      const t212Service = new T212Service()
      await t212Service.addUserKeys(keyId, keySecret, token)

      setShowT212Modal(false)
      // Reload data to fetch T212 summary
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setAddingKeys(false)
    }
  }

  const formatCurrency = (amount: string | number, currency: string) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(num)
  }

  const obfuscateValue = () => {
    return '••••••'
  }

  const calculateTotalBankBalance = () => {
    if (!balancesData || !balancesData.balances) return 0

    let total = 0
    Object.values(balancesData.balances).forEach((balances) => {
      if (Array.isArray(balances)) {
        balances.forEach((balance) => {
          const amount = parseFloat(balance.balanceAmount.amount)
          if (!isNaN(amount)) {
            total += amount
          }
        })
      }
    })
    return total
  }

  const totalBankBalance = calculateTotalBankBalance()
  const totalT212Balance = t212Summary?.totalWorth || 0
  const grandTotal = totalBankBalance + totalT212Balance

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h3 style={{ margin: '0 0 8px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>All Balances</h3>
          <p style={{ margin: 0, color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>
            View all your connected accounts and investments
          </p>
        </div>
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

      {loading && <div style={{ color: colors.text.tertiary }}>Loading balances...</div>}
      {error && (
        <div
          style={{
            color: colors.status.error,
            padding: '16px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderRadius: borderRadius.lg,
            marginBottom: 16,
            border: `1px solid ${colors.status.error}`,
          }}
        >
          Error: {error}
        </div>
      )}

      {!loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Grand Total Card */}
          <div
            style={{
              padding: 24,
              borderRadius: borderRadius.xl,
              border: `1px solid ${colors.accent.primary}`,
              backgroundColor: colors.bg.secondary,
              background: `linear-gradient(135deg, ${colors.accent.muted} 0%, ${colors.bg.secondary} 100%)`,
            }}
          >
            <div style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: 8 }}>Total Net Worth</div>
            <div style={{ fontSize: '36px', fontWeight: typography.fontWeight.bold, color: colors.status.success }}>
              {showValues ? formatCurrency(grandTotal, 'GBP') : obfuscateValue()}
            </div>
            <div style={{ fontSize: typography.fontSize.sm, color: colors.text.tertiary, marginTop: 12 }}>
              Bank: {showValues ? formatCurrency(totalBankBalance, 'GBP') : obfuscateValue()} |
              Trading212: {showValues ? formatCurrency(totalT212Balance, 'GBP') : obfuscateValue()}
            </div>
          </div>

          {/* Bank Balances Section */}
          {balancesData && Object.keys(balancesData.balances).length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>
                Bank Accounts
              </h4>
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
                            {showValues
                              ? formatCurrency(
                                  balance.balanceAmount.amount,
                                  balance.balanceAmount.currency
                                )
                              : obfuscateValue()}
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

          {/* Trading212 Section */}
          <div>
            <h4 style={{ margin: '0 0 16px 0', color: colors.text.primary, fontSize: typography.fontSize.lg, fontWeight: typography.fontWeight.semibold }}>
              Trading212 Investment Account
            </h4>
            {t212Summary ? (
              <div
                style={{
                  padding: 20,
                  borderRadius: borderRadius.lg,
                  border: `1px solid ${colors.border.default}`,
                  backgroundColor: colors.bg.secondary,
                }}
              >
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                    Trading212
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div
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
                        Total Worth
                      </div>
                    </div>
                    <div style={{ fontSize: typography.fontSize['2xl'], fontWeight: typography.fontWeight.bold, color: colors.status.success }}>
                      {showValues
                        ? formatCurrency(t212Summary.totalWorth, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>

                  <div
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
                        Cash Available
                      </div>
                    </div>
                    <div style={{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                      {showValues
                        ? formatCurrency(t212Summary.free, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>

                  <div
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
                        Invested Value
                      </div>
                    </div>
                    <div style={{ fontSize: typography.fontSize.xl, fontWeight: typography.fontWeight.semibold, color: colors.text.primary }}>
                      {showValues
                        ? formatCurrency(t212Summary.investedValue, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>

                  <div
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
                        Profit/Loss
                      </div>
                    </div>
                    <div
                      style={{
                        fontSize: typography.fontSize.xl,
                        fontWeight: typography.fontWeight.semibold,
                        color: t212Summary.totalPpl >= 0 ? colors.status.success : colors.status.error,
                      }}
                    >
                      {showValues
                        ? formatCurrency(t212Summary.totalPpl, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>
                </div>
              </div>
            ) : t212NotFound ? (
              <div
                style={{
                  padding: 24,
                  borderRadius: borderRadius.lg,
                  border: `1px solid ${colors.status.warning}`,
                  backgroundColor: colors.bg.tertiary,
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: typography.fontSize.md, color: colors.text.primary, marginBottom: 12 }}>
                  Trading212 Not Connected
                </div>
                <div style={{ fontSize: typography.fontSize.sm, color: colors.text.secondary, marginBottom: 20 }}>
                  Add your Trading212 API keys to view your investment account
                </div>
                <button
                  onClick={() => setShowT212Modal(true)}
                  style={{
                    padding: '12px 24px',
                    backgroundColor: colors.accent.primary,
                    color: 'white',
                    border: 'none',
                    borderRadius: borderRadius.md,
                    cursor: 'pointer',
                    fontSize: typography.fontSize.sm,
                    fontWeight: typography.fontWeight.semibold,
                  }}
                >
                  Add Trading212 Keys
                </button>
              </div>
            ) : (
              <div style={{ color: colors.text.tertiary, fontSize: typography.fontSize.sm }}>Loading Trading212 data...</div>
            )}
          </div>
        </div>
      )}

      {showT212Modal && (
        <T212KeysModal
          onClose={() => setShowT212Modal(false)}
          onSubmit={handleAddT212Keys}
          loading={addingKeys}
        />
      )}
    </div>
  )
}
