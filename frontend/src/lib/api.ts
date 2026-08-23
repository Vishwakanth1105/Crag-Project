import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
})

export function readCookie(name: string): string | undefined {
  const row = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${name}=`))
  return row?.split('=').slice(1).join('=')
}

api.interceptors.request.use(async (config) => {
  const method = (config.method ?? 'get').toLowerCase()
  if (method === 'get' || method === 'head' || method === 'options') {
    return config
  }
  let token = readCookie('rag_csrf')
  if (!token) {
    const { data } = await api.get<{ csrf_token: string }>('/auth/csrf')
    token = data.csrf_token
  }
  config.headers['X-CSRF-Token'] = token
  return config
})