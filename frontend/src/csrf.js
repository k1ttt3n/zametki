// CSRF-токен читается из не-httpOnly куки csrftoken (Django отдаёт её в том же origin)
export function getCsrfToken() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}
