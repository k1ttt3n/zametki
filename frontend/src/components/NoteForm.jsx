import React, { useState } from 'react'
import api from '../api'
import CategoryPicker from './CategoryPicker'
import { validateNote } from '../validation'

export default function NoteForm({ initial, onCancel, onSaved }) {
  const [form, setForm] = useState({
    title: initial?.title || '',
    text: initial?.text || '',
    category_id: initial?.category_id ?? null,
    is_pinned: !!initial?.is_pinned,
  })
  const [newCat, setNewCat] = useState({ new_category: null, new_category_parent: null })
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
      // category_id — выбранная готовая категория; new_category — создаём новую из формы
      const payload = { ...form, ...newCat }
      if (payload.new_category === undefined) delete payload.new_category
      let resp
      if (initial?.id) resp = await api.put(`/notes/${initial.id}`, payload)
      else resp = await api.post('/notes', payload)
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
      <div className="field">
        <span className="field-label">Категория</span>
        <CategoryPicker
          valueId={form.category_id}
          onChange={(patch) => {
            if ('category_id' in patch) setForm((f) => ({ ...f, category_id: patch.category_id }))
            setNewCat((prev) => ({
              new_category: 'new_category' in patch ? patch.new_category : prev.new_category,
              new_category_parent:
                patch.new_category_parent === undefined ? prev.new_category_parent : patch.new_category_parent,
            }))
          }}
        />
        {errors.category && <span className="field-error">{errors.category}</span>}
      </div>
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
