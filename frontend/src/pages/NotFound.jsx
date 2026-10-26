import React from 'react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="center-note">
      <h1 style={{ fontSize: 48, margin: 0 }}>404</h1>
      <p>Страница не найдена</p>
      <Link to="/">На главную</Link>
    </div>
  )
}
