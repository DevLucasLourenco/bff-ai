import { createSseParser } from './sse'
import type { ApiError, Conversation, Memory, ModelConfig, Persona, Provider, Settings } from './types'

/** Erro tipado: carrega o `code` do backend para a UI decidir o que oferecer. */
export class BffError extends Error {
  code: string
  providerDetail?: string | null
  status?: number

  constructor({ code, message, providerDetail }: ApiError, status?: number) {
    super(message)
    this.name = 'BffError'
    this.code = code
    this.providerDetail = providerDetail
    this.status = status
  }
}

/**
 * O backend responde de três formas: `{detail: {code, message, ...}}` para erros
 * de domínio, `{detail: "texto"}` para HTTPException simples e `{detail: [...]}`
 * para erro de validação. Esta função dá um formato único a todas.
 */
export function normalizeError(body: unknown, status: number): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && 'code' in detail) {
    const typed = detail as { code: string; message: string; provider_detail?: string | null }
    return { code: typed.code, message: typed.message, providerDetail: typed.provider_detail }
  }
  if (typeof detail === 'string') return { code: `http_${status}`, message: detail }
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    return { code: 'validation_error', message: first?.msg ?? 'Dados inválidos.' }
  }
  return { code: `http_${status}`, message: `Falha na requisição (HTTP ${status}).` }
}

const SERVIDOR_FORA: ApiError = {
  code: 'server_unavailable',
  message: 'O servidor do BFF AI não respondeu. Confira se o backend está rodando.',
}

async function readError(response: Response): Promise<BffError> {
  const text = await response.text()
  let parsed: unknown = null
  try { parsed = JSON.parse(text) } catch { /* corpo não-JSON */ }
  if (parsed) return new BffError(normalizeError(parsed, response.status), response.status)
  // 5xx sem corpo JSON não veio do nosso backend (que sempre responde JSON), e
  // sim de quem está na frente dele — o proxy devolvendo 500 porque o backend
  // caiu. Antes isso aparecia na tela como um "HTTP 500" sem explicação.
  if (response.status >= 500) return new BffError(SERVIDOR_FORA, response.status)
  return new BffError({ code: `http_${response.status}`, message: text || `HTTP ${response.status}` }, response.status)
}

/** Converte qualquer falha em ApiError. `TypeError` é o "Failed to fetch" do navegador. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof BffError) return { code: error.code, message: error.message, providerDetail: error.providerDetail }
  if (error instanceof TypeError) return SERVIDOR_FORA
  return { code: 'unknown', message: error instanceof Error ? error.message : String(error) }
}

async function json<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!response.ok) throw await readError(response)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  settings: () => json<Settings>('/api/settings'),
  updateSettings: (payload: Partial<Settings>) => json<Settings>('/api/settings', { method: 'PATCH', body: JSON.stringify(payload) }),
  personas: () => json<Persona[]>('/api/personas'),
  memories: () => json<Memory[]>('/api/memories'),
  createMemory: (payload: Partial<Memory> & { content: string }) => json<Memory>('/api/memories', { method: 'POST', body: JSON.stringify(payload) }),
  updateMemory: (id: number, payload: Partial<Memory>) => json<Memory>(`/api/memories/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteMemory: (id: number) => json<void>(`/api/memories/${id}`, { method: 'DELETE' }),
  createPersona: (payload: Partial<Persona> & { name: string }) => json<Persona>('/api/personas', { method: 'POST', body: JSON.stringify(payload) }),
  updatePersona: (id: number, payload: Partial<Persona>) => json<Persona>(`/api/personas/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deletePersona: (id: number) => json<void>(`/api/personas/${id}`, { method: 'DELETE' }),
  providers: () => json<Provider[]>('/api/providers'),
  updateProvider: (id: number, payload: Record<string, unknown>) => json<Provider>(`/api/providers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  remoteModels: (id: number) => json<string[]>(`/api/providers/${id}/remote-models`),
  models: () => json<ModelConfig[]>('/api/models'),
  createModel: (payload: Record<string, unknown>) => json<ModelConfig>('/api/models', { method: 'POST', body: JSON.stringify(payload) }),
  updateModel: (id: number, payload: Record<string, unknown>) => json<ModelConfig>(`/api/models/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteModel: (id: number) => json<void>(`/api/models/${id}`, { method: 'DELETE' }),
  activateModel: (id: number) => json<ModelConfig>(`/api/models/${id}/activate`, { method: 'POST' }),
  conversations: () => json<Conversation[]>('/api/conversations'),
  conversation: (id: number) => json<Conversation>(`/api/conversations/${id}`),
  createConversation: (payload: Record<string, unknown> = {}) => json<Conversation>('/api/conversations', { method: 'POST', body: JSON.stringify(payload) }),
  updateConversation: (id: number, payload: Record<string, unknown>) => json<Conversation>(`/api/conversations/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  archiveConversation: (id: number) => json<void>(`/api/conversations/${id}`, { method: 'DELETE' }),
}

export type StreamHandlers = {
  onMeta?: (meta: { model: string; provider: string; context_trimmed: number }) => void
  onToken: (token: string) => void
  onDone: (done: { message_id: number; latency_ms: number }) => void
  onError: (error: ApiError) => void
}

/**
 * Tempo máximo sem receber NADA do servidor antes de desistir do stream.
 *
 * O backend manda um sinal de vida a cada 15s enquanto espera o provider, então
 * 45s de silêncio = três sinais perdidos = conexão morta. Sem este limite, uma
 * conexão que morria em silêncio (proxy, wi-fi) deixava a UI em "gerando" para
 * sempre, e a única saída era apertar "parar".
 */
export const STREAM_IDLE_TIMEOUT_MS = 45_000

async function consumeStream(response: Response, handlers: StreamHandlers) {
  if (!response.ok) throw await readError(response)
  if (!response.body) throw new BffError({ code: 'no_body', message: 'O servidor não devolveu um stream.' })

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parser = createSseParser()

  let parado = false
  let vigia: ReturnType<typeof setTimeout> | undefined
  const rearmar = () => {
    clearTimeout(vigia)
    vigia = setTimeout(() => { parado = true; void reader.cancel() }, STREAM_IDLE_TIMEOUT_MS)
  }

  const dispatch = (event: string, data: any) => {
    if (event === 'meta') handlers.onMeta?.(data)
    else if (event === 'token') handlers.onToken(data.text)
    else if (event === 'done') handlers.onDone(data)
    else if (event === 'error') {
      handlers.onError({ code: data.code ?? 'llm_error', message: data.message, providerDetail: data.provider_detail })
    }
  }

  try {
    rearmar()
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      rearmar()  // qualquer byte conta, inclusive o comentário ": ping"
      for (const { event, data } of parser.push(decoder.decode(value, { stream: true }))) dispatch(event, data)
    }
  } finally {
    clearTimeout(vigia)
  }
  // reader.cancel() encerra a leitura como se o stream tivesse acabado bem;
  // é a flag que distingue "terminou" de "desistimos por silêncio".
  if (parado) {
    throw new BffError({
      code: 'stream_stalled',
      message: 'A conexão parou de responder no meio da resposta.',
    })
  }
  for (const { event, data } of parser.flush()) dispatch(event, data)
}

/** Envia uma mensagem. `signal` permite parar a geração (F3.2). */
export async function streamMessage(conversationId: number, content: string, handlers: StreamHandlers, signal?: AbortSignal) {
  const response = await fetch(`/api/conversations/${conversationId}/messages/stream`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content }), signal,
  })
  await consumeStream(response, handlers)
}

/** Refaz uma resposta, descartando-a e tudo depois dela (F3.5). */
export async function regenerateMessage(conversationId: number, messageId: number, handlers: StreamHandlers, signal?: AbortSignal) {
  const response = await fetch(`/api/conversations/${conversationId}/messages/${messageId}/regenerate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, signal,
  })
  await consumeStream(response, handlers)
}
