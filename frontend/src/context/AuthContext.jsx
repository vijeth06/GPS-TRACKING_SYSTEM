import React, { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { getAuthToken, getCurrentUser, login as apiLogin, logout as apiLogout } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      const token = getAuthToken()
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const currentUser = await getCurrentUser()
        setUser(currentUser)
      } catch {
        apiLogout()
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    init()
  }, [])

  const login = async (username, password) => {
    const result = await apiLogin(username, password)
    setUser(result.user)
    return result.user
  }

  const logout = () => {
    apiLogout()
    setUser(null)
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      logout,
    }),
    [user, loading]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
