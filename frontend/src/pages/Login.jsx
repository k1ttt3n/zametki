import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!identifier.trim() || !password) {
      setError('Заполните все поля')
      return
    }
    setBusy(true)
    try {
      await login(identifier.trim(), password)
      navigate('/')
    } catch (err) {
      const data = err?.response?.data
      setError(data?.errors?.detail || data?.errors?.non_field_errors?.[0] || 'Ошибка входа. Попробуйте позже.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <h1>Вход</h1>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Email или логин
          <input
            type="text"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoComplete="username"
            placeholder="user@example.com"
          />
        </label>
        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Входим…' : 'Войти'}
        </button>
        <p className="muted">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </form>
    </div>
  )
}
