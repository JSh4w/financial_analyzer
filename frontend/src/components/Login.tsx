import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '../lib/supabase'
import { colors, borderRadius } from '../theme'

interface LoginProps {
  onBack?: () => void
}

export default function Login({ onBack }: LoginProps) {
  // Get the current URL for redirect after password reset
  const redirectUrl = window.location.origin

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      backgroundColor: colors.bg.primary
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        padding: '40px',
        backgroundColor: colors.bg.secondary,
        borderRadius: borderRadius['2xl'],
        boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
        border: `1px solid ${colors.border.default}`
      }}>
        {onBack && (
          <button
            onClick={onBack}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'none',
              border: 'none',
              color: colors.text.secondary,
              fontSize: '14px',
              cursor: 'pointer',
              padding: '0',
              marginBottom: '20px',
              transition: 'color 0.2s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = colors.text.primary)}
            onMouseOut={(e) => (e.currentTarget.style.color = colors.text.secondary)}
          >
            ← Back to home
          </button>
        )}
        <h2 style={{
          textAlign: 'center',
          marginBottom: '24px',
          color: '#ffffff',
          fontSize: '24px',
          fontWeight: 700,
          background: `linear-gradient(135deg, ${colors.accent.primary} 0%, #60a5fa 100%)`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          Lucrum Stack
        </h2>
        <Auth
          supabaseClient={supabase}
          appearance={{
            theme: ThemeSupa,
            variables: {
              default: {
                colors: {
                  brand: colors.accent.primary,
                  brandAccent: colors.accent.hover,
                  inputBackground: colors.bg.primary,
                  inputText: colors.text.primary,
                  inputBorder: colors.border.default,
                  inputBorderFocus: colors.accent.primary,
                  inputBorderHover: colors.border.hover,
                }
              }
            }
          }}
          providers={[]}
          redirectTo={redirectUrl}
          view="sign_in"
        />
      </div>
    </div>
  )
}