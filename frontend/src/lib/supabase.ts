import { createClient } from '@supabase/supabase-js'
import { Database } from '../types/supabase'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string 
const supabaseKey = import.meta.env.VITE_SUPABASE_KEY as string 

export const supabase = createClient<Database>(supabaseUrl, supabaseKey, {
    auth: {
        flowType: 'pkce',
        autoRefreshToken: true,
        persistSession: true
    }
})