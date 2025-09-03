import { create } from 'zustand'
import { apiClient, type SessionStatus } from '@/lib/api'

interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
  sessionStatus: SessionStatus | null
  login: (username: string, password: string, deviceId?: string) => Promise<boolean>
  logout: () => Promise<void>
  checkSession: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  isAuthenticated: false,
  isLoading: false,
  sessionStatus: null,

  login: async (username: string, password: string, deviceId?: string) => {
    set({ isLoading: true })
    
    try {
      const result = await apiClient.login({
        username,
        password,
        device_id: deviceId,
      })
      
      if (result.success) {
        set({ isAuthenticated: true })
        await get().checkSession()
        return true
      } else {
        return false
      }
    } catch (error) {
      console.error('Login error:', error)
      return false
    } finally {
      set({ isLoading: false })
    }
  },

  logout: async () => {
    set({ isLoading: true })
    
    try {
      await apiClient.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      set({ 
        isAuthenticated: false, 
        isLoading: false,
        sessionStatus: null 
      })
    }
  },

  checkSession: async () => {
    if (!apiClient['token']) {
      set({ isAuthenticated: false, sessionStatus: null })
      return
    }

    try {
      const status = await apiClient.getSessionStatus()
      
      if (status.success) {
        set({ 
          isAuthenticated: true,
          sessionStatus: status 
        })
      } else {
        set({ 
          isAuthenticated: false,
          sessionStatus: null 
        })
        apiClient.clearToken()
      }
    } catch (error) {
      console.error('Session check error:', error)
      set({ 
        isAuthenticated: false,
        sessionStatus: null 
      })
      apiClient.clearToken()
    }
  },
}))

if (typeof window !== 'undefined') {
  const token = localStorage.getItem('auth_token')
  if (token) {
    useAuthStore.getState().checkSession()
  }
}

