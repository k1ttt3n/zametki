import React, { createContext, useContext, useEffect, useState } from 'react'
import api from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) { setLoading(false); return }
    api.get('/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (identifier, password) => {
    const r = await api.post('/auth/login', { email: identifier, password })
    localStorage.setItem('token', r.data.token)
    setUser(r.data.user)
    return r.data.user
  }

  const register = async (data) => {
    await api.post('/auth/register', data)
  }

  const logout = async () => {
    try { await api.post('/auth/logout') } catch (e) { /* токен уже недействителен */ }
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
