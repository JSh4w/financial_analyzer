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
      padding: '20px 60px',
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
      height: '36px',
      width: 'auto',
    },
    logoText: {
      fontSize: '22px',
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
    badge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      backgroundColor: `rgba(13, 148, 136, 0.1)`,
      border: `1px solid rgba(13, 148, 136, 0.3)`,
      borderRadius: '50px',
      fontSize: '14px',
      color: theme.accent,
      marginBottom: '24px',
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
    footer: {
      padding: '40px 60px',
      borderTop: '1px solid rgba(255, 255, 255, 0.08)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      flexWrap: 'wrap' as const,
      gap: '20px',
    },
    footerText: {
      fontSize: '14px',
      color: 'rgba(255, 255, 255, 0.5)',
      margin: 0,
    },
    footerLinks: {
      display: 'flex',
      gap: '24px',
    },
    footerLink: {
      fontSize: '14px',
      color: 'rgba(255, 255, 255, 0.5)',
      textDecoration: 'none',
      cursor: 'pointer',
      transition: 'color 0.2s ease',
    },
  }

  const features = [
    {
      icon: 'RT',
      title: 'Real-Time Stock Tracking',
      description: 'Monitor live price movements with candlestick charts. Stream real-time data for any stock in your watchlist.',
    },
    {
      icon: 'BA',
      title: 'Bank Account Integration',
      description: 'Connect your bank accounts securely via Open Banking. View all your balances in one unified dashboard.',
    },
    {
      icon: 'PA',
      title: 'Portfolio Analytics',
      description: 'Track your complete financial picture. See your investments, cash positions, and net worth at a glance.',
    },
    {
      icon: 'MN',
      title: 'Live Market News',
      description: 'Stay informed with streaming financial news. Get real-time updates on market-moving events.',
    },
    {
      icon: 'SP',
      title: 'Secure & Private',
      description: 'Bank-grade security with encrypted connections. Your financial data stays private and protected.',
    },
    {
      icon: 'LF',
      title: 'Lightning Fast',
      description: 'Built for performance with sub-second updates. No lag, no delays - just instant market data.',
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
            style={{ ...styles.navButton, backgroundColor: 'transparent', color: '#ffffff' }}
            onClick={onGetStarted}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            Log in
          </button>
          <button
            style={{ ...styles.navButton, backgroundColor: theme.primary, color: '#ffffff' }}
            onClick={onGetStarted}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = theme.primaryDark)}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = theme.primary)}
          >
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={styles.hero}>
        <div style={styles.badge}>
          <span>Your financial command center</span>
        </div>
        <h1 style={styles.headline}>
          <span style={styles.gradientText}>Track Stocks.</span>
          <br />
          <span style={styles.gradientText}>Connect Banks.</span>
          <br />
          <span style={{ color: theme.accent }}>Master Your Finances.</span>
        </h1>
        <p style={styles.subheadline}>
          Real-time stock tracking, bank account aggregation, and portfolio analytics —
          all in one powerful, unified platform built for modern investors.
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
            See How It Works
          </button>
        </div>
      </section>


      {/* Features Section */}
      <section id="features" style={styles.section}>
        <div style={styles.sectionHeader}>
          <h2 style={styles.sectionTitle}>Everything you need</h2>
          <p style={styles.sectionSubtitle}>
            Powerful tools to track, analyze, and optimize your financial life
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
        <h2 style={styles.ctaTitle}>Ready to take control?</h2>
        <p style={styles.ctaSubtitle}>
          Start tracking your portfolio and market insights today.
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
          Get Started
        </button>
      </section>

      {/* Footer */}
      <footer style={styles.footer}>
        <p style={styles.footerText}>© 2025 Lucrum Stack. All rights reserved.</p>
        <div style={styles.footerLinks}>
          <span style={styles.footerLink}>Privacy Policy</span>
          <span style={styles.footerLink}>Terms of Service</span>
          <span style={styles.footerLink}>Contact</span>
        </div>
      </footer>
    </div>
  )
}
