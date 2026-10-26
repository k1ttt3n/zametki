import React, { useState } from 'react'
import api from '../api'
import { validateNote } from '../validation'

export default function NoteForm({ initial, onCancel, onSaved }) {
  const [form, setForm] = useState({
    title: initial?.title || '',
    text: initial?.text || '',
    category: initial?.category || '',
    is_pinned: !!initial?.is_pinned,
  })
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const set = (name) => (e) =>
    setForm((f) => ({ ...f, [name]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    const errs = validateNote(form)
    setErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true)
    try {
      let resp
      if (initial?.id) resp = await api.put(`/notes/${initial.id}`, form)
      else resp = await api.post('/notes', form)
      onSaved(resp.data)
    } catch (err) {
      const data = err?.response?.data
      if (data?.errors) setErrors(data.errors)
      else setErrors({ detail: 'Не удалось сохранить заметку' })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="card note-form" onSubmit={submit} noValidate>
      <h2>{initial?.id ? 'Редактировать заметку' : 'Новая заметка'}</h2>
      {errors.detail && <div className="alert alert-error">{errors.detail}</div>}
      <label>
        Название
        <input value={form.title} onChange={set('title')} maxLength={120} placeholder="Заголовок" />
        {errors.title && <span className="field-error">{errors.title}</span>}
      </label>
      <label>
        Текст
        <textarea value={form.text} onChange={set('text')} rows={6} maxLength={10000} placeholder="Текст заметки" />
        {errors.text && <span className="field-error">{errors.text}</span>}
      </label>
      <label>
        Категория
        <input value={form.category} onChange={set('category')} maxLength={64} placeholder="Например: Работа" />
        {errors.category && <span className="field-error">{errors.category}</span>}
      </label>
      <label className="checkbox">
        <input type="checkbox" checked={form.is_pinned} onChange={set('is_pinned')} />
        Закрепить сверху
      </label>
      <div className="form-actions">
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel}>Отмена</button>
      </div>
    </form>
  )
}
