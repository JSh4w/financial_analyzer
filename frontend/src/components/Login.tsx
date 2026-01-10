import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '../lib/supabase'

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
      backgroundColor: '#0a0a0a'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        padding: '40px',
        backgroundColor: '#1a1a1a',
        borderRadius: '16px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        border: '1px solid rgba(255,255,255,0.1)'
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
              color: 'rgba(255,255,255,0.6)',
              fontSize: '14px',
              cursor: 'pointer',
              padding: '0',
              marginBottom: '20px',
              transition: 'color 0.2s ease'
            }}
            onMouseOver={(e) => (e.currentTarget.style.color = '#ffffff')}
            onMouseOut={(e) => (e.currentTarget.style.color = 'rgba(255,255,255,0.6)')}
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
          background: 'linear-gradient(135deg, #0d9488 0%, #2dd4bf 100%)',
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
                  brand: '#0d9488',
                  brandAccent: '#0f766e',
                  inputBackground: '#0a0a0a',
                  inputText: '#ffffff',
                  inputBorder: 'rgba(255,255,255,0.2)',
                  inputBorderFocus: '#0d9488',
                  inputBorderHover: 'rgba(255,255,255,0.3)',
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