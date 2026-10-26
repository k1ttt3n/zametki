import React from 'react'
import api from '../api'

export default function NoteCard({ note, onEdit, onDelete, onFileDeleted, onPinToggle, onAttach }) {
  const fmtDate = (iso) => {
    try {
      return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    } catch {
      return iso
    }
  }

  const fmtSize = (bytes) => {
    if (!bytes && bytes !== 0) return ''
    if (bytes < 1024) return `${bytes} Б`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`
    return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
  }

  const deleteFile = async (id) => {
    try {
      await api.delete(`/files/${id}`)
      onFileDeleted(note.id, id)
    } catch { /* ignore */ }
  }

  return (
    <article className={`card note-card ${note.is_pinned ? 'pinned' : ''}`}>
      <div className="note-head">
        <h3>{note.title}</h3>
        <div className="note-actions">
          <button
            className={`btn btn-icon ${note.is_pinned ? 'active' : ''}`}
            title={note.is_pinned ? 'Открепить' : 'Закрепить'}
            onClick={() => onPinToggle(note)}
          >📌</button>
          <button className="btn btn-icon" title="Редактировать" onClick={() => onEdit(note)}>✏️</button>
          <button className="btn btn-icon" title="Прикрепить файл" onClick={() => onAttach(note)}>📎</button>
          <button className="btn btn-icon danger" title="Удалить" onClick={() => onDelete(note)}>🗑️</button>
        </div>
      </div>
      {note.category && <span className="tag">{note.category}</span>}
      {note.text && <p className="note-text">{note.text}</p>}
      {note.files?.length > 0 && (
        <ul className="file-list">
          {note.files.map((f) => (
            <li key={f.id}>
              {f.url ? <a href={f.url} target="_blank" rel="noreferrer">{f.original_name}</a> : f.original_name}
              <span className="muted"> ({fmtSize(f.size_bytes)})</span>
              <button className="btn btn-icon danger" title="Удалить файл" onClick={() => deleteFile(f.id)}>✕</button>
            </li>
          ))}
        </ul>
      )}
      <footer className="muted small">Обновлено: {fmtDate(note.updated_at)}</footer>
    </article>
  )
}
