import type { Conversation, Memory, ModelConfig, Persona, Provider, Settings } from './types'

async function json<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!response.ok) throw new Error((await response.text()) || `HTTP ${response.status}`)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  settings: () => json<Settings>('/api/settings'),
  updateSettings: (payload: Partial<Settings>) => json<Settings>('/api/settings', { method: 'PATCH', body: JSON.stringify(payload) }),
  personas: () => json<Persona[]>('/api/personas'),
  memories: () => json<Memory[]>('/api/memories'),
  createMemory: (payload: { category: string; content: string; is_active?: boolean }) => json<Memory>('/api/memories', { method: 'POST', body: JSON.stringify(payload) }),
  updateMemory: (id: number, payload: Partial<Memory>) => json<Memory>(`/api/memories/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteMemory: (id: number) => json<void>(`/api/memories/${id}`, { method: 'DELETE' }),
  createPersona: (payload: Omit<Persona, 'id'>) => json<Persona>('/api/personas', { method: 'POST', body: JSON.stringify(payload) }),
  updatePersona: (id: number, payload: Partial<Persona>) => json<Persona>(`/api/personas/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  providers: () => json<Provider[]>('/api/providers'),
  updateProvider: (id: number, payload: Record<string, unknown>) => json<Provider>(`/api/providers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  remoteModels: (id: number) => json<string[]>(`/api/providers/${id}/remote-models`),
  models: () => json<ModelConfig[]>('/api/models'),
  createModel: (payload: Record<string, unknown>) => json<ModelConfig>('/api/models', { method: 'POST', body: JSON.stringify(payload) }),
  activateModel: (id: number) => json<ModelConfig>(`/api/models/${id}/activate`, { method: 'POST' }),
  conversations: () => json<Conversation[]>('/api/conversations'),
  conversation: (id: number) => json<Conversation>(`/api/conversations/${id}`),
  createConversation: (payload: Record<string, unknown> = {}) => json<Conversation>('/api/conversations', { method: 'POST', body: JSON.stringify(payload) }),
  updateConversation: (id: number, payload: Record<string, unknown>) => json<Conversation>(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  archiveConversation: (id: number) => json<void>(`/api/conversations/${id}`, { method: 'DELETE' }),
}

export async function streamMessage(
  conversationId: number,
  content: string,
  handlers: { onToken: (token: string) => void; onDone: () => void; onError: (message: string) => void },
) {
  const response = await fetch(`/api/conversations/${conversationId}/messages/stream`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content })
  })
  if (!response.ok || !response.body) throw new Error((await response.text()) || `HTTP ${response.status}`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() || ''
    for (const frame of frames) {
      const event = frame.match(/^event: (.+)$/m)?.[1]
      const dataRaw = frame.match(/^data: (.+)$/m)?.[1]
      if (!event || !dataRaw) continue
      const data = JSON.parse(dataRaw)
      if (event === 'token') handlers.onToken(data.text)
      if (event === 'error') handlers.onError(data.message)
      if (event === 'done') handlers.onDone()
    }
  }
}
