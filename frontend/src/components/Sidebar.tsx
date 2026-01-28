import { colors, borderRadius, typography } from '../theme'
import logoLight from '../assets/LucrumStackLight.jpg'

type View = 'stocks' | 'portfolio'

interface StockSubscription {
  symbol: string
  status: 'loading' | 'streaming' | 'paused' | 'error'
  isPermanent: boolean
}

interface SidebarProps {
  currentView: View
  onViewChange: (view: View) => void
  activeStocks: Map<string, StockSubscription>
  selectedStock: string | null
  onStockSelect: (symbol: string) => void
  onStockRemove: (symbol: string) => void
  onLogout: () => void
}

export default function Sidebar({
  currentView,
  onViewChange,
  activeStocks,
  selectedStock,
  onStockSelect,
  onStockRemove,
  onLogout,
}: SidebarProps) {
  const navItemStyle = (isActive: boolean) => ({
    width: '100%',
    padding: '12px 20px',
    border: 'none',
    backgroundColor: isActive ? colors.bg.tertiary : 'transparent',
    color: isActive ? colors.accent.primary : colors.text.secondary,
    cursor: 'pointer',
    textAlign: 'left' as const,
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    transition: 'all 0.2s ease',
    borderLeft: isActive ? `3px solid ${colors.accent.primary}` : '3px solid transparent',
  })

  const stockItemStyle = (isSelected: boolean) => ({
    padding: '10px 16px',
    cursor: 'pointer',
    backgroundColor: isSelected ? colors.bg.tertiary : 'transparent',
    borderLeft: isSelected ? `3px solid ${colors.accent.primary}` : '3px solid transparent',
    transition: 'all 0.2s ease',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  })

  const getStatusIndicator = (status: string) => {
    switch (status) {
      case 'streaming':
        return <span style={{ color: colors.status.success }}>● Live</span>
      case 'paused':
        return <span style={{ color: colors.status.warning }}>◉ Paused</span>
      case 'loading':
        return <span style={{ color: colors.status.warning }}>○ Loading</span>
      case 'error':
        return <span style={{ color: colors.status.error }}>● Error</span>
      default:
        return null
    }
  }

  return (
    <div
      style={{
        width: '220px',
        backgroundColor: colors.bg.secondary,
        borderRight: `1px solid ${colors.border.default}`,
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        height: '100%',
      }}
    >
      {/* Logo/Header */}
      <div
        style={{
          padding: '20px',
          borderBottom: `1px solid ${colors.border.default}`,
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <img
          src={logoLight}
          alt="LucrumStack"
          style={{
            width: '32px',
            height: '32px',
            borderRadius: borderRadius.md,
            objectFit: 'cover',
          }}
        />
        <span
          style={{
            fontSize: typography.fontSize.md,
            fontWeight: typography.fontWeight.semibold,
            color: colors.text.primary,
          }}
        >
          LucrumStack
        </span>
      </div>

      {/* Navigation Menu */}
      <div style={{ padding: '8px 0' }}>
        <button onClick={() => onViewChange('stocks')} style={navItemStyle(currentView === 'stocks')}>
          Stocks
        </button>
        <button onClick={() => onViewChange('portfolio')} style={navItemStyle(currentView === 'portfolio')}>
          Portfolio
        </button>
      </div>

      {/* Stock List */}
      {currentView === 'stocks' && activeStocks.size > 0 && (
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            borderTop: `1px solid ${colors.border.default}`,
          }}
        >
          <div
            style={{
              padding: '12px 16px 8px',
              fontSize: typography.fontSize.xs,
              color: colors.text.tertiary,
              fontWeight: typography.fontWeight.semibold,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Watching
          </div>
          {Array.from(activeStocks.entries()).map(([symbol, stock]) => (
            <div
              key={symbol}
              onClick={() => onStockSelect(symbol)}
              style={stockItemStyle(selectedStock === symbol)}
            >
              <div>
                <div
                  style={{
                    fontSize: typography.fontSize.sm,
                    fontWeight: typography.fontWeight.medium,
                    color: colors.text.primary,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  {symbol}
                  {stock.isPermanent && (
                    <span title="Saved to watchlist" style={{ color: colors.accent.primary, fontSize: '10px' }}>
                      ★
                    </span>
                  )}
                </div>
                <div style={{ fontSize: typography.fontSize.xs, color: colors.text.tertiary, marginTop: '2px' }}>
                  {getStatusIndicator(stock.status)}
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onStockRemove(symbol)
                }}
                style={{
                  padding: '4px 8px',
                  fontSize: '11px',
                  backgroundColor: 'transparent',
                  color: colors.text.tertiary,
                  border: `1px solid ${colors.border.default}`,
                  borderRadius: borderRadius.sm,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.borderColor = colors.status.error
                  e.currentTarget.style.color = colors.status.error
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.borderColor = colors.border.default
                  e.currentTarget.style.color = colors.text.tertiary
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Bottom - Sign Out */}
      <div
        style={{
          marginTop: 'auto',
          padding: '16px',
          borderTop: `1px solid ${colors.border.default}`,
        }}
      >
        <button
          onClick={onLogout}
          style={{
            width: '100%',
            padding: '10px',
            backgroundColor: 'transparent',
            color: colors.text.secondary,
            border: `1px solid ${colors.border.default}`,
            borderRadius: borderRadius.md,
            cursor: 'pointer',
            fontSize: typography.fontSize.sm,
            fontWeight: typography.fontWeight.medium,
            transition: 'all 0.2s ease',
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.borderColor = colors.border.hover
            e.currentTarget.style.backgroundColor = colors.bg.tertiary
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.borderColor = colors.border.default
            e.currentTarget.style.backgroundColor = 'transparent'
          }}
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}
