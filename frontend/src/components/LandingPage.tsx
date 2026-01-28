import { CSSProperties } from 'react'
import logoLight from '../assets/LucrumStackLight.jpg'
import { colors, borderRadius, typography } from '../theme'

interface LandingPageProps {
  onGetStarted: () => void
}

// Theme colors - Blue accent
const theme = {
  primary: colors.accent.primary,
  primaryLight: '#60a5fa',  // Blue-400
  primaryDark: colors.accent.hover,
  accent: '#60a5fa',        // Blue-400
  glow: colors.accent.glow,
  glowStrong: 'rgba(59, 130, 246, 0.5)',
  gradientStart: colors.accent.primary,
  gradientEnd: colors.accent.hover,
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  const styles: Record<string, CSSProperties> = {
    container: {
      minHeight: '100vh',
      backgroundColor: colors.bg.primary,
      color: colors.text.primary,
      overflowY: 'auto',
      overflowX: 'hidden',
    },
    nav: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '20px 60px',
      position: 'fixed' as const,
      top: 0,
      left: 0,
      right: 0,
      backgroundColor: 'rgba(12, 12, 12, 0.85)',
      backdropFilter: 'blur(12px)',
      zIndex: 1000,
      borderBottom: `1px solid ${colors.border.subtle}`,
    },
    logoContainer: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      cursor: 'pointer',
    },
    logoImage: {
      height: '40px',
      width: 'auto',
      borderRadius: borderRadius.md,
    },
    logoText: {
      fontSize: '22px',
      fontWeight: typography.fontWeight.bold,
      color: colors.text.primary,
    },
    navButtons: {
      display: 'flex',
      gap: '12px',
    },
    navButton: {
      padding: '10px 20px',
      borderRadius: borderRadius.lg,
      border: 'none',
      cursor: 'pointer',
      fontSize: '14px',
      fontWeight: typography.fontWeight.medium,
      transition: 'all 0.2s ease',
    },
    hero: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center' as const,
      padding: '160px 20px 100px',
      minHeight: '100vh',
      background: `radial-gradient(ellipse at top, rgba(59, 130, 246, 0.1) 0%, transparent 60%)`,
    },
    headline: {
      fontSize: 'clamp(40px, 6vw, 72px)',
      fontWeight: typography.fontWeight.bold,
      lineHeight: 1.1,
      margin: '0 0 24px',
      maxWidth: '900px',
    },
    gradientText: {
      background: `linear-gradient(135deg, ${colors.text.primary} 0%, ${colors.text.secondary} 100%)`,
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
    },
    subheadline: {
      fontSize: '18px',
      color: colors.text.secondary,
      maxWidth: '600px',
      margin: '0 0 40px',
      lineHeight: 1.7,
    },
    ctaGroup: {
      display: 'flex',
      gap: '16px',
      flexWrap: 'wrap' as const,
      justifyContent: 'center',
    },
    primaryCta: {
      padding: '14px 28px',
      fontSize: '15px',
      fontWeight: typography.fontWeight.semibold,
      borderRadius: borderRadius.lg,
      border: 'none',
      cursor: 'pointer',
      background: `linear-gradient(135deg, ${theme.primary} 0%, ${theme.gradientEnd} 100%)`,
      color: '#ffffff',
      transition: 'all 0.2s ease',
      boxShadow: `0 4px 20px ${theme.glow}`,
    },
    secondaryCta: {
      padding: '14px 28px',
      fontSize: '15px',
      fontWeight: typography.fontWeight.semibold,
      borderRadius: borderRadius.lg,
      border: `1px solid ${colors.border.hover}`,
      cursor: 'pointer',
      backgroundColor: 'transparent',
      color: colors.text.primary,
      transition: 'all 0.2s ease',
    },
    section: {
      padding: '100px 60px',
      maxWidth: '1200px',
      margin: '0 auto',
    },
    sectionHeader: {
      textAlign: 'center' as const,
      marginBottom: '60px',
    },
    sectionTitle: {
      fontSize: typography.fontSize['4xl'],
      fontWeight: typography.fontWeight.bold,
      margin: '0 0 16px',
      color: colors.text.primary,
    },
    sectionSubtitle: {
      fontSize: typography.fontSize.md,
      color: colors.text.secondary,
      maxWidth: '600px',
      margin: '0 auto',
      lineHeight: 1.6,
    },
    featuresGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
      gap: '20px',
    },
    featureCard: {
      padding: '28px',
      backgroundColor: colors.bg.secondary,
      border: `1px solid ${colors.border.default}`,
      borderRadius: borderRadius.xl,
      transition: 'all 0.2s ease',
    },
    featureIcon: {
      width: '44px',
      height: '44px',
      borderRadius: borderRadius.lg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: '16px',
      backgroundColor: colors.accent.muted,
      color: colors.accent.primary,
      fontSize: '14px',
      fontWeight: typography.fontWeight.bold,
      fontFamily: typography.fontFamily.mono,
      letterSpacing: '-0.5px',
    },
    featureTitle: {
      fontSize: typography.fontSize.lg,
      fontWeight: typography.fontWeight.semibold,
      margin: '0 0 10px',
      color: colors.text.primary,
    },
    featureDesc: {
      fontSize: typography.fontSize.sm,
      color: colors.text.secondary,
      lineHeight: 1.6,
      margin: 0,
    },
    ctaSection: {
      padding: '100px 60px',
      textAlign: 'center' as const,
      background: `radial-gradient(ellipse at bottom, rgba(59, 130, 246, 0.08) 0%, transparent 60%)`,
    },
    ctaTitle: {
      fontSize: typography.fontSize['3xl'],
      fontWeight: typography.fontWeight.bold,
      margin: '0 0 16px',
      color: colors.text.primary,
    },
    ctaSubtitle: {
      fontSize: typography.fontSize.md,
      color: colors.text.secondary,
      margin: '0 0 32px',
    },
  }

  const features = [
    {
      icon: 'WS',
      title: 'WebSocket Streaming',
      description: 'Live market data via Alpaca WebSocket API with tick-to-candle aggregation and SSE delivery to frontend.',
    },
    {
      icon: 'OB',
      title: 'Open Banking',
      description: 'GoCardless integration for bank account aggregation. OAuth flow with secure token handling.',
    },
    {
      icon: 'DB',
      title: 'DuckDB Storage',
      description: 'Columnar database for efficient OHLCV data storage and fast analytical queries.',
    },
    {
      icon: 'ML',
      title: 'Regime Detection',
      description: 'Hidden Markov Model classifying market conditions into 9 volatility/trend regimes.',
    },
    {
      icon: 'NLP',
      title: 'Sentiment Analysis',
      description: 'FinBERT-based sentiment scoring on financial news with Modal serverless inference.',
    },
    {
      icon: 'JWT',
      title: 'Auth & Security',
      description: 'Supabase authentication with RS256 JWT validation via JWKS endpoint.',
    },
  ]

  return (
    <div style={styles.container}>
      {/* Navigation */}
      <nav style={styles.nav}>
        <div style={styles.logoContainer}>
          <img src={logoLight} alt="Lucrum Stack" style={styles.logoImage} />
          <span style={styles.logoText}>Lucrum Stack</span>
        </div>
        <div style={styles.navButtons}>
          <button
            style={{ ...styles.navButton, backgroundColor: theme.primary, color: '#ffffff' }}
            onClick={onGetStarted}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = theme.primaryDark)}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = theme.primary)}
          >
            Launch App
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={styles.hero}>
        <h1 style={styles.headline}>
          <span style={styles.gradientText}>Track Stocks.</span>
          <br />
          <span style={styles.gradientText}>Connect Banks.</span>
          <br />
          <span style={{ color: theme.accent }}>Analyse Markets.</span>
        </h1>
        <p style={styles.subheadline}>
          A full-stack application featuring live market data streaming,
          bank account integration via Open Banking, and portfolio tracking.
        </p>
        <div style={styles.ctaGroup}>
          <button
            style={styles.primaryCta}
            onClick={onGetStarted}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = `0 6px 30px ${theme.glowStrong}`
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = `0 4px 20px ${theme.glow}`
            }}
          >
            Get Started
          </button>
          <button
            style={styles.secondaryCta}
            onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            View Features
          </button>
        </div>
      </section>


      {/* Features Section */}
      <section id="features" style={styles.section}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>Features</h2>
          <p style={styles.sectionSubtitle}>
            Built with FastAPI, React, WebSockets, and real-time data streaming
          </p>
        </div>
        <div style={styles.featuresGrid}>
          {features.map((feature, index) => (
            <div
              key={index}
              style={styles.featureCard}
              onMouseOver={(e) => {
                e.currentTarget.style.backgroundColor = colors.bg.tertiary
                e.currentTarget.style.borderColor = colors.border.hover
                e.currentTarget.style.transform = 'translateY(-2px)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = colors.bg.secondary
                e.currentTarget.style.borderColor = colors.border.default
                e.currentTarget.style.transform = 'translateY(0)'
              }}
            >
              <div style={styles.featureIcon}>
                {feature.icon}
              </div>
              <h3 style={styles.featureTitle}>{feature.title}</h3>
              <p style={styles.featureDesc}>{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section style={styles.ctaSection}>
        <h2 style={styles.ctaTitle}>Try the Demo</h2>
        <p style={styles.ctaSubtitle}>
          Explore the platform and see the features in action.
        </p>
        <button
          style={styles.primaryCta}
          onClick={onGetStarted}
          onMouseOver={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = `0 6px 30px ${theme.glowStrong}`
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = `0 4px 20px ${theme.glow}`
          }}
        >
          Launch App
        </button>
      </section>

    </div>
  )
}
