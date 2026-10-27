import React, { useCallback, useEffect, useState } from 'react'
import api from '../api'

// Плоский список узлов дерева (для <select> «родитель» внутри формы)
export function flattenTree(nodes, depth = 0, out = []) {
  for (const n of nodes || []) {
    out.push({ id: n.id, name: n.name, depth })
    flattenTree(n.children, depth + 1, out)
  }
  return out
}

function NodeForm({ parent, onCancel, onSaved }) {
  const [name, setName] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!name.trim()) { setErr('Введите название'); return }
    setBusy(true)
    try {
      const r = await api.post('/categories', { name: name.trim(), parent: parent?.id ?? null })
      onSaved(r.data)
    } catch (error) {
      const d = error?.response?.data
      setErr(d?.errors?.name?.[0] || d?.errors?.detail || 'Не удалось создать категорию')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="cat-form" onSubmit={submit}>
      <input
        autoFocus
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={64}
        placeholder={parent ? `Подкатегория к «${parent.name}»` : 'Новая категория'}
      />
      <button className="btn btn-primary btn-sm" disabled={busy}>OK</button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>Отмена</button>
      {err && <div className="field-error">{err}</div>}
    </form>
  )
}

function RenameForm({ node, onCancel, onSaved }) {
  const [name, setName] = useState(node.name)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!name.trim()) { setErr('Введите название'); return }
    setBusy(true)
    try {
      const r = await api.patch(`/categories/${node.id}`, { name: name.trim() })
      onSaved(r.data)
    } catch (error) {
      const d = error?.response?.data
      setErr(d?.errors?.name?.[0] || d?.errors?.detail || 'Не удалось переименовать')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="cat-form" onSubmit={submit}>
      <input autoFocus value={name} onChange={(e) => setName(e.target.value)} maxLength={64} />
      <button className="btn btn-primary btn-sm" disabled={busy}>OK</button>
      <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>Отмена</button>
      {err && <div className="field-error">{err}</div>}
    </form>
  )
}

function TreeNode({ node, depth, selectedId, onSelect, expanded, toggle, reload }) {
  const [mode, setMode] = useState(null) // null | 'add' | 'rename'
  const hasChildren = (node.children || []).length > 0

  const remove = async () => {
    const extra = hasChildren ? ' Все дочерние категории также будут удалены.' : ''
    if (!window.confirm(`Удалить категорию «${node.name}»?${extra}`)) return
    try {
      await api.delete(`/categories/${node.id}`)
      if (selectedId === node.id) onSelect(null)
      reload()
    } catch { /* ignore */ }
  }

  return (
    <li>
      <div className="cat-row" style={{ paddingLeft: `${depth * 14}px` }}>
        <button
          className={`cat-twist ${hasChildren ? '' : 'invisible'}`}
          onClick={() => toggle(node.id)}
          aria-label={expanded.has(node.id) ? 'Свернуть' : 'Развернуть'}
        >
          {hasChildren ? (expanded.has(node.id) ? '▾' : '▸') : ''}
        </button>
        {mode === 'rename' ? (
          <RenameForm
            node={node}
            onCancel={() => setMode(null)}
            onSaved={() => { setMode(null); reload() }}
          />
        ) : (
          <button
            className={`cat-name ${selectedId === node.id ? 'active' : ''}`}
            onClick={() => onSelect(selectedId === node.id ? null : node.id)}
            title={`${node.note_count} заметок(и)`}
          >
            {node.name}
            <span className="cat-count">{node.note_count}</span>
          </button>
        )}
        <span className="cat-actions">
          <button className="icon-btn" title="Добавить подкатегорию" onClick={() => setMode('add')}>＋</button>
          <button className="icon-btn" title="Переименовать" onClick={() => setMode('rename')}>✎</button>
          <button className="icon-btn danger" title="Удалить" onClick={remove}>🗑</button>
        </span>
      </div>
      {mode === 'add' && (
        <div style={{ paddingLeft: `${(depth + 1) * 14}px` }}>
          <NodeForm parent={node} onCancel={() => setMode(null)} onSaved={() => { setMode(null); toggleOpen(node.id); reload() }} />
        </div>
      )}
      {hasChildren && expanded.has(node.id) && (
        <ul className="cat-children">
          {node.children.map((ch) => (
            <TreeNode
              key={ch.id}
              node={ch}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              expanded={expanded}
              toggle={toggle}
              reload={reload}
            />
          ))}
        </ul>
      )}
    </li>
  )

  function toggleOpen(id) {
    if (!expanded.has(id)) toggle(id)
  }
}

export default function CategoryTree({ selectedId, onSelect }) {
  const [tree, setTree] = useState([])
  const [expanded, setExpanded] = useState(() => new Set())
  const [adding, setAdding] = useState(false)

  const reload = useCallback(async () => {
    try {
      const r = await api.get('/categories/tree')
      setTree(r.data.tree)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { reload() }, [reload])

  const toggle = (id) =>
    setExpanded((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  return (
    <aside className="cat-tree card">
      <div className="cat-tree-head">
        <h3>Категории</h3>
        <button className="btn btn-ghost btn-sm" onClick={() => setAdding(true)}>+ категория</button>
      </div>
      {adding && (
        <NodeForm parent={null} onCancel={() => setAdding(false)} onSaved={() => { setAdding(false); reload() }} />
      )}
      {selectedId != null && (
        <button className="cat-reset" onClick={() => onSelect(null)}>✕ Сбросить фильтр</button>
      )}
      {tree.length === 0 && !adding ? (
        <p className="cat-empty">Категорий нет — создайте первую.</p>
      ) : (
        <ul className="cat-root">
          {tree.map((n) => (
            <TreeNode
              key={n.id}
              node={n}
              depth={0}
              selectedId={selectedId}
              onSelect={onSelect}
              expanded={expanded}
              toggle={toggle}
              reload={reload}
            />
          ))}
        </ul>
      )}
    </aside>
  )
}
