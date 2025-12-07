import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '../lib/supabase'

export default function Login() {
  // Get the current URL for redirect after password reset
  const redirectUrl = window.location.origin

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      backgroundColor: '#505050'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '400px',
        padding: '40px',
        backgroundColor: 'white',
        borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(1,1,1,0.5)'
      }}>
        <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>Stock Analyzer</h2>
        <Auth
          supabaseClient={supabase}
          appearance={{ theme: ThemeSupa }}
          providers={[]}
          redirectTo={redirectUrl}
          view="sign_in"
        />
      </div>
    </div>
  )
}