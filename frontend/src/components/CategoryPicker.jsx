import React, { useEffect, useState } from 'react'
import api from '../api'
import { flattenTree } from './CategoryTree'

// Выбор категории: готовая из дерева ИЛИ создание новой прямо из формы.
export default function CategoryPicker({ valueId, onChange }) {
  const [tree, setTree] = useState([])
  const [mode, setMode] = useState(valueId ? 'existing' : 'none') // none | existing | new

  useEffect(() => {
    let alive = true
    api.get('/categories/tree')
      .then((r) => { if (alive) setTree(r.data.tree) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  const flat = flattenTree(tree)

  return (
    <div className="cat-picker">
      <div className="cat-mode-toggle" role="radiogroup" aria-label="Режим выбора категории">
        <button
          type="button"
          role="radio" aria-checked={mode === 'existing'}
          className={`seg-btn ${mode === 'existing' ? 'active' : ''}`}
          onClick={() => { setMode('existing'); onChange({ category_id: null, new_category: null, new_category_parent: null }) }}
        >
          Из дерева
        </button>
        <button
          type="button"
          role="radio" aria-checked={mode === 'new'}
          className={`seg-btn ${mode === 'new' ? 'active' : ''}`}
          onClick={() => { setMode('new'); onChange({ category_id: null, new_category: '', new_category_parent: null }) }}
        >
          Новая
        </button>
      </div>

      {mode === 'existing' && (
        <select
          value={valueId ?? ''}
          onChange={(e) => onChange({ category_id: e.target.value ? Number(e.target.value) : null, new_category: null, new_category_parent: null })}
        >
          <option value="">Без категории</option>
          {flat.map((n) => (
            <option key={n.id} value={n.id}>{'\u00A0\u00A0'.repeat(n.depth)}{n.name}</option>
          ))}
        </select>
      )}

      {mode === 'new' && (
        <div className="cat-new">
          <input
            maxLength={64}
            placeholder="Название новой категории"
            onChange={(e) => onChange({ category_id: null, new_category: e.target.value.trim() || null, new_category_parent: undefined })}
          />
          <label className="muted">Родительская (необязательно):</label>
          <select
            defaultValue=""
            onChange={(e) => onChange({ new_category_parent: e.target.value ? Number(e.target.value) : null })}
          >
            <option value="">— без родителя (корень) —</option>
            {flat.map((n) => (
              <option key={n.id} value={n.id}>{'\u00A0\u00A0'.repeat(n.depth)}{n.name}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}
