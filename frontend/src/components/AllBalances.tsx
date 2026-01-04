import { useEffect, useState } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'
import { T212Service, T212Summary, T212Error } from '../services/t212-service'
import { getAuthToken } from '../lib/auth'

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
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#1a1a1a',
          borderRadius: 12,
          padding: 32,
          maxWidth: 500,
          width: '90%',
          border: '1px solid #2a2a2a',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 8px 0', color: '#e0e0e0', fontSize: 20 }}>
          Add Trading212 API Keys
        </h3>
        <p style={{ margin: '0 0 24px 0', color: '#666', fontSize: 14 }}>
          Enter your Trading212 API credentials to connect your account
        </p>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label
              htmlFor="keyId"
              style={{ display: 'block', marginBottom: 8, color: '#a0a0a0', fontSize: 14 }}
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
                fontSize: 14,
                backgroundColor: '#0f0f0f',
                color: '#e0e0e0',
                border: '1px solid #333',
                borderRadius: 8,
                outline: 'none',
              }}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label
              htmlFor="keySecret"
              style={{ display: 'block', marginBottom: 8, color: '#a0a0a0', fontSize: 14 }}
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
                fontSize: 14,
                backgroundColor: '#0f0f0f',
                color: '#e0e0e0',
                border: '1px solid #333',
                borderRadius: 8,
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
                color: '#a0a0a0',
                border: '1px solid #333',
                borderRadius: 6,
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !keyId.trim() || !keySecret.trim()}
              style={{
                padding: '10px 20px',
                backgroundColor: loading || !keyId.trim() || !keySecret.trim() ? '#333' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: loading || !keyId.trim() || !keySecret.trim() ? 'not-allowed' : 'pointer',
                fontSize: 14,
                fontWeight: 600,
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
          <h3 style={{ margin: '0 0 8px 0', color: '#e0e0e0' }}>All Balances</h3>
          <p style={{ margin: 0, color: '#666' }}>
            View all your connected accounts and investments
          </p>
        </div>
        <button
          onClick={() => setShowValues(!showValues)}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2a2a2a',
            color: '#e0e0e0',
            border: '1px solid #333',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          {showValues ? '👁 Hide Values' : '👁‍🗨 Show Values'}
        </button>
      </div>

      {loading && <div style={{ color: '#666' }}>Loading balances...</div>}
      {error && (
        <div
          style={{
            color: '#ef4444',
            padding: '16px',
            backgroundColor: '#7f1d1d',
            borderRadius: '8px',
            marginBottom: 16,
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
              borderRadius: 12,
              border: '2px solid #3b82f6',
              backgroundColor: '#1a1a1a',
            }}
          >
            <div style={{ fontSize: 14, color: '#a0a0a0', marginBottom: 8 }}>Total Net Worth</div>
            <div style={{ fontSize: 36, fontWeight: 700, color: '#10b981' }}>
              {showValues ? formatCurrency(grandTotal, 'GBP') : obfuscateValue()}
            </div>
            <div style={{ fontSize: 13, color: '#666', marginTop: 12 }}>
              Bank: {showValues ? formatCurrency(totalBankBalance, 'GBP') : obfuscateValue()} |
              Trading212: {showValues ? formatCurrency(totalT212Balance, 'GBP') : obfuscateValue()}
            </div>
          </div>

          {/* Bank Balances Section */}
          {balancesData && Object.keys(balancesData.balances).length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: '#e0e0e0', fontSize: 18 }}>
                Bank Accounts
              </h4>
              {Object.entries(balancesData.balances).map(([institutionName, balances]) => (
                <div
                  key={institutionName}
                  style={{
                    padding: 20,
                    borderRadius: 8,
                    border: '1px solid #2a2a2a',
                    backgroundColor: '#1a1a1a',
                    marginBottom: 16,
                  }}
                >
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 20, fontWeight: '600', color: '#e0e0e0' }}>
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
                            borderRadius: 6,
                            backgroundColor: '#2a2a2a',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div>
                            <div style={{ fontSize: 14, fontWeight: 500, color: '#a0a0a0' }}>
                              {balance.balanceType}
                            </div>
                            {balance.referenceDate && (
                              <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                                As of {new Date(balance.referenceDate).toLocaleDateString()}
                              </div>
                            )}
                          </div>
                          <div style={{ fontSize: 24, fontWeight: 700, color: '#10b981' }}>
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
                    <div style={{ color: '#666', fontSize: 13 }}>No balances available</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Trading212 Section */}
          <div>
            <h4 style={{ margin: '0 0 16px 0', color: '#e0e0e0', fontSize: 18 }}>
              Trading212 Investment Account
            </h4>
            {t212Summary ? (
              <div
                style={{
                  padding: 20,
                  borderRadius: 8,
                  border: '1px solid #2a2a2a',
                  backgroundColor: '#1a1a1a',
                }}
              >
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 20, fontWeight: '600', color: '#e0e0e0' }}>
                    Trading212
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 6,
                      backgroundColor: '#2a2a2a',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: '#a0a0a0' }}>
                        Total Worth
                      </div>
                    </div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: '#10b981' }}>
                      {showValues
                        ? formatCurrency(t212Summary.totalWorth, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>

                  <div
                    style={{
                      padding: 16,
                      borderRadius: 6,
                      backgroundColor: '#2a2a2a',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: '#a0a0a0' }}>
                        Cash Available
                      </div>
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: '#e0e0e0' }}>
                      {showValues
                        ? formatCurrency(t212Summary.free, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>

                  <div
                    style={{
                      padding: 16,
                      borderRadius: 6,
                      backgroundColor: '#2a2a2a',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: '#a0a0a0' }}>
                        Invested Value
                      </div>
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 600, color: '#e0e0e0' }}>
                      {showValues
                        ? formatCurrency(t212Summary.investedValue, 'GBP')
                        : obfuscateValue()}
                    </div>
                  </div>

                  <div
                    style={{
                      padding: 16,
                      borderRadius: 6,
                      backgroundColor: '#2a2a2a',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: '#a0a0a0' }}>
                        Profit/Loss
                      </div>
                    </div>
                    <div
                      style={{
                        fontSize: 20,
                        fontWeight: 600,
                        color: t212Summary.totalPpl >= 0 ? '#10b981' : '#ef4444',
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
                  borderRadius: 8,
                  border: '1px solid #f59e0b',
                  backgroundColor: '#2a2a2a',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 16, color: '#e0e0e0', marginBottom: 12 }}>
                  Trading212 Not Connected
                </div>
                <div style={{ fontSize: 14, color: '#a0a0a0', marginBottom: 20 }}>
                  Add your Trading212 API keys to view your investment account
                </div>
                <button
                  onClick={() => setShowT212Modal(true)}
                  style={{
                    padding: '12px 24px',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: 'pointer',
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  Add Trading212 Keys
                </button>
              </div>
            ) : (
              <div style={{ color: '#666', fontSize: 13 }}>Loading Trading212 data...</div>
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
