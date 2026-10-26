import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Notes from './pages/Notes'
import NotFound from './pages/NotFound'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center-note">Загрузка…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Notes />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
