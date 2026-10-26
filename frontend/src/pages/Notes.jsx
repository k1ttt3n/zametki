import React, { useCallback, useEffect, useMemo, useState } from 'react'
import api from '../api'
import NoteCard from '../components/NoteCard'
import NoteForm from '../components/NoteForm'
import FileUpload from '../components/FileUpload'

const debounce = (fn, ms) => {
  let t
  return (...args) => {
    clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
}

export default function Notes() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [pinnedOnly, setPinnedOnly] = useState(false)
  const [categories, setCategories] = useState([])
  const [editing, setEditing] = useState(null) // null | {} (новая) | note
  const [fileFor, setFileFor] = useState(null) // заметка, для которой грузим файл
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState('')

  const query = useMemo(
    () => ({ page, limit: 12, search, category, pinned: pinnedOnly ? '1' : '' }),
    [page, search, category, pinnedOnly],
  )

  const debouncedSearch = useMemo(() => debounce((v) => { setSearch(v); setPage(1) }, 350), [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/notes', { params: query })
      setItems(r.data.items)
      setTotal(r.data.total)
      setPages(r.data.pages || 1)
    } catch {
      setNotice('Не удалось загрузить заметки')
    } finally {
      setLoading(false)
    }
  }, [query])

  const loadCategories = useCallback(async () => {
    try {
      const r = await api.get('/notes/categories')
      setCategories(r.data.categories)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadCategories() }, [loadCategories])

  const onSaved = (note) => {
    setEditing(null)
    setItems((prev) => {
      const i = prev.findIndex((n) => n.id === note.id)
      if (i === -1) return [note, ...prev]
      const copy = [...prev]
      copy[i] = note
      return copy
    })
    setNotice('Заметка сохранена')
    loadCategories()
  }

  const onDelete = async (note) => {
    if (!window.confirm(`Удалить заметку «${note.title}»?`)) return
    try {
      await api.delete(`/notes/${note.id}`)
      setItems((prev) => prev.filter((n) => n.id !== note.id))
      setTotal((t) => Math.max(0, t - 1))
    } catch {
      setNotice('Не удалось удалить заметку')
    }
  }

  const onPinToggle = async (note) => {
    try {
      const r = await api.put(`/notes/${note.id}`, { ...note, is_pinned: !note.is_pinned })
      setItems((prev) => prev.map((n) => (n.id === r.data.id ? r.data : n)))
      // при закреплении обновляем порядок из серверного списка
      if (r.data.is_pinned !== note.is_pinned) load()
    } catch {
      setNotice('Не удалось обновить заметку')
    }
  }

  const onFileUploaded = (noteId, fileData) => {
    setItems((prev) => prev.map((n) => (n.id === noteId ? { ...n, files: [...(n.files || []), fileData] } : n)))
    setFileFor(null)
    setNotice('Файл загружен')
  }

  const onFileDeleted = (noteId, fileId) => {
    setItems((prev) => prev.map((n) => (n.id === noteId ? { ...n, files: (n.files || []).filter((f) => f.id !== fileId) } : n)))
  }

  const exportXlsx = async () => {
    try {
      const r = await api.get('/notes/export/', { params: { search, category, pinned: pinnedOnly ? '1' : '' }, responseType: 'blob' })
      const url = URL.createObjectURL(r.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'notes.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setNotice('Не удалось выгрузить Excel')
    }
  }

  return (
    <div className="notes-page">
      <div className="toolbar">
        <input
          className="search"
          placeholder="Поиск по названию и тексту…"
          defaultValue={search}
          onChange={(e) => debouncedSearch(e.target.value)}
        />
        <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1) }}>
          <option value="">Все категории</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="checkbox inline">
          <input type="checkbox" checked={pinnedOnly} onChange={(e) => { setPinnedOnly(e.target.checked); setPage(1) }} />
          Только закреплённые
        </label>
        <button className="btn btn-ghost" onClick={exportXlsx}>Экспорт .xlsx</button>
        <button className="btn btn-primary" onClick={() => setEditing({})}>+ Новая заметка</button>
      </div>

      {notice && <div className="alert alert-info" onClick={() => setNotice('')}>{notice}</div>}

      {(editing || fileFor) && (
        <div className="overlay" onClick={() => { setEditing(null); setFileFor(null) }}>
          <div onClick={(e) => e.stopPropagation()} style={{ width: 'min(560px, 92vw)' }}>
            {editing && <NoteForm initial={editing.id ? editing : null} onCancel={() => setEditing(null)} onSaved={onSaved} />}
            {fileFor && (
              <div className="card">
                <h2>Файл к заметке «{fileFor.title}»</h2>
                <FileUpload note={fileFor} onUploaded={onFileUploaded} />
                <button className="btn btn-ghost" onClick={() => setFileFor(null)}>Закрыть</button>
              </div>
            )}
          </div>
        </div>
      )}

      {loading ? (
        <div className="center-note">Загрузка…</div>
      ) : items.length === 0 ? (
        <div className="center-note">
          <p>Заметок пока нет.</p>
          <button className="btn btn-primary" onClick={() => setEditing({})}>Создать первую заметку</button>
        </div>
      ) : (
        <>
          <div className="grid">
            {items.map((n) => (
              <NoteCard
                key={n.id}
                note={n}
                onEdit={setEditing}
                onAttach={setFileFor}
                onDelete={onDelete}
                onPinToggle={onPinToggle}
                onFileDeleted={onFileDeleted}
              />
            ))}
          </div>
          <nav className="pagination">
            <button className="btn btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Назад</button>
            <span>Стр. {page} из {pages} · всего {total}</span>
            <button className="btn btn-ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Вперёд →</button>
          </nav>
        </>
      )}
    </div>
  )
}
