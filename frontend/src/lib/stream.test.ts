import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BffError, STREAM_IDLE_TIMEOUT_MS, streamMessage, toApiError } from './api'

const enc = new TextEncoder()

/** Resposta SSE cujo corpo é controlado pelo teste, frame a frame. */
function respostaControlada() {
  let ctrl!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({ start(c) { ctrl = c } })
  return {
    resposta: new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
    enviar: (texto: string) => ctrl.enqueue(enc.encode(texto)),
    fechar: () => ctrl.close(),
  }
}

const handlers = () => ({ onToken: vi.fn(), onDone: vi.fn(), onError: vi.fn() })

describe('vigia de inatividade do stream', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals() })

  it('desiste com erro claro quando o servidor fica mudo', async () => {
    const s = respostaControlada()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(s.resposta))

    const h = handlers()
    const promessa = streamMessage(1, 'oi', h)
    const resultado = promessa.catch(e => e)
    await vi.advanceTimersByTimeAsync(0)
    s.enviar('event: token\ndata: {"text":"Oi"}\n\n')
    await vi.advanceTimersByTimeAsync(STREAM_IDLE_TIMEOUT_MS + 10)

    const erro = await resultado
    expect(erro).toBeInstanceOf(BffError)
    expect(erro.code).toBe('stream_stalled')
    expect(h.onToken).toHaveBeenCalledWith('Oi')
  })

  it('o ping do servidor mantém o stream vivo', async () => {
    const s = respostaControlada()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(s.resposta))

    const h = handlers()
    const promessa = streamMessage(1, 'oi', h)
    await vi.advanceTimersByTimeAsync(0)
    // Um minuto e meio de "modelo pensando", com ping a cada 15s.
    for (let i = 0; i < 6; i++) {
      await vi.advanceTimersByTimeAsync(15_000)
      s.enviar(': ping\n\n')
    }
    s.enviar('event: token\ndata: {"text":"pronto"}\n\n')
    s.enviar('event: done\ndata: {"message_id":1,"latency_ms":90000}\n\n')
    s.fechar()

    await expect(promessa).resolves.toBeUndefined()
    expect(h.onToken).toHaveBeenCalledWith('pronto')
    expect(h.onDone).toHaveBeenCalled()
  })
})

describe('erro de servidor fora do ar', () => {
  afterEach(() => { vi.unstubAllGlobals() })

  it('500 sem JSON (proxy com backend caído) vira mensagem legível', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    const erro = await streamMessage(1, 'oi', handlers()).catch(e => e)
    expect(erro.code).toBe('server_unavailable')
    expect(erro.message).not.toContain('HTTP 500')
  })

  it('"Failed to fetch" do navegador também', () => {
    expect(toApiError(new TypeError('Failed to fetch')).code).toBe('server_unavailable')
  })

  it('erro do nosso backend continua com o code dele', async () => {
    const corpo = JSON.stringify({ detail: { code: 'provider_auth', message: 'Chave recusada' } })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(corpo, { status: 502 })))
    const erro = await streamMessage(1, 'oi', handlers()).catch(e => e)
    expect(erro.code).toBe('provider_auth')
  })
})
