import React from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const onLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="brand">📝 Заметки</span>
        <div className="user-area">
          <span className="username" title={user?.email}>{user?.username}</span>
          <button className="btn btn-ghost" onClick={onLogout}>Выйти</button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
