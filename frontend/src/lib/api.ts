import axios from 'axios'
import type { Message } from '@/lib/types'

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

export type StreamEvent =
  | { type: 'delta'; content: string }
  | { type: 'done'; message: Message }
  | { type: 'error'; detail?: string }

/**
 * Send a chat turn and stream the answer as Server-Sent Events.
 *
 * Uses `fetch` (not axios) with manual SSE parsing so tokens can be rendered
 * as they arrive instead of waiting for the whole answer.
 */
export async function streamChat(
  conversationId: number,
  content: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  let token = readCookie('rag_csrf')
  if (!token) {
    const { data } = await api.get<{ csrf_token: string }>('/auth/csrf')
    token = data.csrf_token
  }

  let response: Response
  try {
    response = await fetch(`/api/v1/conversations/${conversationId}/messages/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': token,
      },
      body: JSON.stringify({ content }),
    })
  } catch {
    onEvent({ type: 'error', detail: 'Network error while sending the message.' })
    return
  }

  if (!response.ok) {
    let detail: string | undefined
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // ignore parse failures; fall back to generic error below
    }
    onEvent({ type: 'error', detail: detail ?? `Request failed (${response.status})` })
    return
  }

  if (!response.body) {
    onEvent({ type: 'error', detail: 'Empty response from the server.' })
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const payload = trimmed.slice(5).trim()
      if (!payload) continue
      try {
        onEvent(JSON.parse(payload) as StreamEvent)
      } catch {
        // drop malformed frames rather than killing the stream
      }
    }
  }
}