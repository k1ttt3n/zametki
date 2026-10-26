import React, { useState } from 'react'
import { validateFile } from '../validation'

export default function FileUpload({ note, onUploaded, onError }) {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const pick = (e) => {
    const f = e.target.files?.[0] || null
    setError(f ? validateFile(f) || '' : '')
    setFile(f)
  }

  const upload = async (e) => {
    e.preventDefault()
    if (!file) { setError('Прикрепите файл'); return }
    setBusy(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const resp = await fetch(`/api/notes/${note.id}/files`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: fd,
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data?.errors?.file || data?.errors?.detail || 'Не удалось загрузить файл')
      }
      const data = await resp.json()
      setFile(null)
      e.target.reset && e.target.reset()
      onUploaded(note.id, data)
    } catch (err) {
      setError(err.message || 'Ошибка загрузки')
      onError && onError(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="file-upload" onSubmit={upload}>
      <input type="file" onChange={pick} accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt" />
      <button className="btn btn-small" disabled={!file || busy}>
        {busy ? 'Загрузка…' : 'Загрузить'}
      </button>
      {error && <span className="field-error">{error}</span>}
    </form>
  )
}
