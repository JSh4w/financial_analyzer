import { CSSProperties } from 'react'
import logoLight from '../assets/LucrumStackLight.jpg'

interface LandingPageProps {
  onGetStarted: () => void
}

// Theme colors - green/turquoise
const theme = {
  primary: '#0d9488',       // Teal-600
  primaryLight: '#14b8a6',  // Teal-500
  primaryDark: '#0f766e',   // Teal-700
  accent: '#2dd4bf',        // Teal-400
  glow: 'rgba(13, 148, 136, 0.4)',
  glowStrong: 'rgba(13, 148, 136, 0.5)',
  gradientStart: '#0d9488',
  gradientEnd: '#059669',   // Emerald-600
}

export default function LandingPage({ onGetStarted }: LandingPageProps) {
  const styles: Record<string, CSSProperties> = {
    container: {
      minHeight: '100vh',
      backgroundColor: '#0a0a0a',
      color: '#ffffff',
      overflowY: 'auto',
      overflowX: 'hidden',
    },
    nav: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '28px 60px',
      position: 'fixed' as const,
      top: 0,
      left: 0,
      right: 0,
      backgroundColor: 'rgba(10, 10, 10, 0.9)',
      backdropFilter: 'blur(10px)',
      zIndex: 1000,
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    },
    logoContainer: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      cursor: 'pointer',
    },
    logoImage: {
      height: '48px',
      width: 'auto',
    },
    logoText: {
      fontSize: '26px',
      fontWeight: 700,
      color: '#ffffff',
    },
    navButtons: {
      display: 'flex',
      gap: '12px',
    },
    navButton: {
      padding: '10px 20px',
      borderRadius: '8px',
      border: 'none',
      cursor: 'pointer',
      fontSize: '14px',
      fontWeight: 500,
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
      background: `radial-gradient(ellipse at top, rgba(13, 148, 136, 0.15) 0%, transparent 50%)`,
    },
    headline: {
      fontSize: 'clamp(40px, 6vw, 72px)',
      fontWeight: 800,
      lineHeight: 1.1,
      margin: '0 0 24px',
      maxWidth: '900px',
    },
    gradientText: {
      background: 'linear-gradient(135deg, #ffffff 0%, #a0a0a0 100%)',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
    },
    subheadline: {
      fontSize: '20px',
      color: 'rgba(255, 255, 255, 0.7)',
      maxWidth: '600px',
      margin: '0 0 40px',
      lineHeight: 1.6,
    },
    ctaGroup: {
      display: 'flex',
      gap: '16px',
      flexWrap: 'wrap' as const,
      justifyContent: 'center',
    },
    primaryCta: {
      padding: '16px 32px',
      fontSize: '16px',
      fontWeight: 600,
      borderRadius: '10px',
      border: 'none',
      cursor: 'pointer',
      background: `linear-gradient(135deg, ${theme.primary} 0%, ${theme.gradientEnd} 100%)`,
      color: '#ffffff',
      transition: 'all 0.2s ease',
      boxShadow: `0 4px 20px ${theme.glow}`,
    },
    secondaryCta: {
      padding: '16px 32px',
      fontSize: '16px',
      fontWeight: 600,
      borderRadius: '10px',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      cursor: 'pointer',
      backgroundColor: 'transparent',
      color: '#ffffff',
      transition: 'all 0.2s ease',
    },
    section: {
      padding: '100px 60px',
      maxWidth: '1400px',
      margin: '0 auto',
    },
    sectionHeader: {
      textAlign: 'center' as const,
      marginBottom: '60px',
    },
    sectionTitle: {
      fontSize: '40px',
      fontWeight: 700,
      margin: '0 0 16px',
    },
    sectionSubtitle: {
      fontSize: '18px',
      color: 'rgba(255, 255, 255, 0.6)',
      maxWidth: '600px',
      margin: '0 auto',
    },
    featuresGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
      gap: '24px',
    },
    featureCard: {
      padding: '32px',
      backgroundColor: 'rgba(255, 255, 255, 0.03)',
      border: '1px solid rgba(255, 255, 255, 0.08)',
      borderRadius: '16px',
      transition: 'all 0.3s ease',
    },
    featureIcon: {
      width: '48px',
      height: '48px',
      borderRadius: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      marginBottom: '20px',
      backgroundColor: `rgba(13, 148, 136, 0.15)`,
      color: theme.accent,
      fontSize: '20px',
      fontWeight: 600,
    },
    featureTitle: {
      fontSize: '20px',
      fontWeight: 600,
      margin: '0 0 12px',
    },
    featureDesc: {
      fontSize: '15px',
      color: 'rgba(255, 255, 255, 0.6)',
      lineHeight: 1.6,
      margin: 0,
    },
    ctaSection: {
      padding: '100px 60px',
      textAlign: 'center' as const,
      background: `radial-gradient(ellipse at bottom, rgba(13, 148, 136, 0.15) 0%, transparent 50%)`,
    },
    ctaTitle: {
      fontSize: '36px',
      fontWeight: 700,
      margin: '0 0 16px',
    },
    ctaSubtitle: {
      fontSize: '18px',
      color: 'rgba(255, 255, 255, 0.6)',
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
                e.currentTarget.style.backgroundColor = 'rgba(13, 148, 136, 0.08)'
                e.currentTarget.style.borderColor = 'rgba(13, 148, 136, 0.3)'
                e.currentTarget.style.transform = 'translateY(-4px)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)'
                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)'
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
