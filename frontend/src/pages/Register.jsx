import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { validateRegister } from '../validation'

const FIELDS = [
  { name: 'email', label: 'Email', type: 'email', autoComplete: 'email' },
  { name: 'username', label: 'Логин', type: 'text', autoComplete: 'username', hint: 'латиница, цифры, _ (3–30)' },
  { name: 'password', label: 'Пароль', type: 'password', autoComplete: 'new-password', hint: 'от 8 символов, буквы и цифры' },
  { name: 'password_confirm', label: 'Повторите пароль', type: 'password', autoComplete: 'new-password' },
]

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', username: '', password: '', password_confirm: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (name) => (e) => setForm((f) => ({ ...f, [name]: e.target.value }))

  const onSubmit = async (e) => {
    e.preventDefault()
    setServerError('')
    const errs = validateRegister(form)
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try {
      await register(form)
      navigate('/login')
    } catch (err) {
      const data = err?.response?.data
      const detail = data?.errors?.detail || data?.detail
      if (detail) setServerError(detail)
      else if (data?.errors) setErrors(data.errors)
      else setServerError('Ошибка регистрации. Попробуйте позже.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <h1>Регистрация</h1>
        {serverError && <div className="alert alert-error">{serverError}</div>}
        {FIELDS.map((f) => (
          <label key={f.name}>
            {f.label}
            <input
              type={f.type}
              value={form[f.name]}
              onChange={set(f.name)}
              autoComplete={f.autoComplete}
              aria-invalid={!!errors[f.name]}
            />
            {errors[f.name] && <span className="field-error">{errors[f.name]}</span>}
            {!errors[f.name] && f.hint && <span className="field-hint">{f.hint}</span>}
          </label>
        ))}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? 'Создаём…' : 'Создать аккаунт'}
        </button>
        <p className="muted">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  )
}
