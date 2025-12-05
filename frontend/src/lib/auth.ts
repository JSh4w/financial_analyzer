import { supabase } from './supabase'

/**
 * Get the current JWT access token from Supabase session
 *
 * @returns JWT access token or null if not authenticated
 */
export async function getAuthToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token || null
}

/**
 * Get the current user session from Supabase
 *
 * @returns Supabase session object or null
 */
export async function getSession() {
  const { data: { session } } = await supabase.auth.getSession()
  return session
}

/**
 * Check if user is currently authenticated
 *
 * @returns true if user has a valid session
 */
export async function isAuthenticated(): Promise<boolean> {
  const token = await getAuthToken()
  return token !== null
}
