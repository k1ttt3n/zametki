// Клиентская валидация — те же правила, что на сервере
export function validateRegister({ email, username, password, password_confirm }) {
  const e = {}
  if (!email) e.email = 'Введите email'
  else if (email.length > 254 || !/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(email)) e.email = 'Введите корректный email'
  if (!/^[A-Za-z0-9_]{3,30}$/.test(username || '')) e.username = 'Только латиница, цифры и _, от 3 до 30 символов'
  if (!password || password.length < 8 || password.length > 64 || !/[A-Za-zА-Яа-я]/.test(password) || !/\d/.test(password))
    e.password = 'Пароль: от 8 символов, буквы и цифры'
  if (password !== password_confirm) e.password_confirm = 'Пароли не совпадают'
  return e
}

export function validateNote({ title, text, category }) {
  const e = {}
  const t = (title || '').trim()
  if (!t) e.title = 'Введите название (до 120 символов)'
  else if (t.length > 120) e.title = 'Название не длиннее 120 символов'
  if ((text || '').length > 10000) e.text = 'Текст заметки не длиннее 10000 символов'
  if ((category || '').length > 64) e.category = 'Категория не длиннее 64 символов'
  return e
}

export const ALLOWED_EXT = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.pdf', '.txt']
export const MAX_UPLOAD_MB = 10

export function validateFile(file) {
  if (!file) return 'Прикрепите файл'
  const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
  if (!ALLOWED_EXT.includes(ext)) return 'Допустимы изображения, PDF и TXT'
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `Файл больше ${MAX_UPLOAD_MB} МБ`
  return null
}
