import { useEffect, useState } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'
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
      <h3 style={{ margin: '0 0 8px 0', color: '#e0e0e0' }}>Account Balances</h3>
      <p style={{ margin: '0 0 24px 0', color: '#666' }}>
        View all your connected bank account balances
      </p>

      {loading && <div style={{ color: '#666' }}>Loading balances...</div>}
      {error && <div style={{ color: '#ef4444', padding: '16px', backgroundColor: '#7f1d1d', borderRadius: '8px' }}>Error: {error}</div>}

      {!loading && !error && balancesData && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Pending Requisitions Section */}
          {balancesData.pending_requisitions && balancesData.pending_requisitions.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 16px 0', color: '#f59e0b', fontSize: '18px' }}>
                Pending Bank Connections ({balancesData.pending_requisitions.length})
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {balancesData.pending_requisitions.map((pending) => (
                  <div
                    key={pending.requisition_id}
                    style={{
                      padding: 20,
                      borderRadius: 8,
                      border: '1px solid #f59e0b',
                      backgroundColor: '#2a2a2a',
                    }}
                  >
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ fontSize: 18, fontWeight: '600', color: '#e0e0e0' }}>
                        {pending.institution_name}
                      </div>
                      <div style={{ fontSize: 13, color: '#f59e0b', marginTop: 4 }}>
                        Status: {pending.status}
                      </div>
                    </div>
                    <div style={{ fontSize: 14, color: '#a0a0a0', marginBottom: 16 }}>
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
                          background: '#3b82f6',
                          color: 'white',
                          textDecoration: 'none',
                          borderRadius: 6,
                          fontSize: 14,
                          fontWeight: 600,
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
              <h4 style={{ margin: '0 0 16px 0', color: '#e0e0e0', fontSize: '18px' }}>Connected Banks</h4>
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
                            {formatCurrency(
                              balance.balanceAmount.amount,
                              balance.balanceAmount.currency
                            )}
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

          {Object.keys(balancesData.balances).length === 0 &&
           (!balancesData.pending_requisitions || balancesData.pending_requisitions.length === 0) && (
            <div style={{ color: '#888', textAlign: 'center', padding: 24 }}>
              No connected bank accounts found. Connect a bank to view your balances.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
