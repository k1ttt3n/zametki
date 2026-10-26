import React, { createContext, useContext, useEffect, useState } from 'react'
import api from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // токен лежит в httpOnly-куке — проверяем сессию через /auth/me
    api.get('/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (identifier, password) => {
    const r = await api.post('/auth/login', { email: identifier, password })
    setUser(r.data.user)
    return r.data.user
  }

  const register = async (data) => {
    await api.post('/auth/register', data)
  }

  const logout = async () => {
    try { await api.post('/auth/logout') } catch (e) { /* куки уже очищены */ }
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
