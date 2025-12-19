import { useEffect, useMemo, useState } from 'react'
import { BankClientDatafeed } from '../services/bankclient-datafeed'

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

export default function SelectBank({ onSelect }: { onSelect?: (inst: Institution) => void }) {
  const [institutions, setInstitutions] = useState<Institution[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  return (
    <div style={{ padding: 16 }}>
      <h3 style={{ margin: '0 0 8px 0' }}>Select your bank</h3>
      <p style={{ margin: '0 0 12px 0', color: '#888' }}>
        Choose the bank you want to connect. This makes the Open Banking flow quicker and
        more reliable.
      </p>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: '#666' }}>{institutions.length} banks available</div>
      </div>

      {loading && <div>Loading banks…</div>}
      {error && <div style={{ color: 'red' }}>Error loading banks: {error}</div>}

      {!loading && !error && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
          {institutionsSorted.map((inst) => (
            <button
              key={inst.id}
              onClick={() => onSelect?.(inst)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: 12,
                textAlign: 'left',
                borderRadius: 8,
                border: '1px solid #e6e6e6',
                background: 'white',
                cursor: 'pointer'
              }}
            >
              <div style={{ width: 48, height: 48, flex: '0 0 48px' }}>
                {inst.logo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={inst.logo} alt={inst.name} style={{ width: 48, height: 48, objectFit: 'contain' }} />
                ) : (
                  <div style={{ width: 48, height: 48, background: '#f0f0f0', borderRadius: 6 }} />
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#333' }}>{inst.name}</div>
              </div>
            </button>
          ))}

          {institutionsSorted.length === 0 && (
            <div style={{ gridColumn: '1 / -1', color: '#666' }}>No banks found.</div>
          )}
        </div>
      )}
    </div>
  )
}
