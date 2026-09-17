import { useCallback, useMemo, useRef, useState } from 'react'
import { BffError, regenerateMessage, streamMessage } from '../lib/api'
import { StreamBuffer } from '../lib/streamBuffer'
import type { ApiError } from '../lib/types'

export type StreamState = 'idle' | 'streaming'

type Options = {
  /** Chamado ao terminar (sucesso, erro ou parada) para recarregar a conversa. */
  onSettled: (conversationId: number) => Promise<void> | void
  onError: (error: ApiError) => void
}

/**
 * Envio, parada e regeneração (F7.1, F3.2, F3.5).
 *
 * O texto em andamento fica no StreamBuffer, não no estado da conversa: só a
 * bolha que o assina rerenderiza enquanto os tokens chegam.
 */
export function useChatStream({ onSettled, onError }: Options) {
  const [state, setState] = useState<StreamState>('idle')
  // O que a usuária acabou de mandar, para aparecer na hora: a conversa só é
  // recarregada do servidor quando o stream termina, e sem isto a mensagem dela
  // sumiria da tela durante toda a resposta.
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null)
  const buffer = useMemo(() => new StreamBuffer(), [])
  const abortRef = useRef<AbortController | null>(null)

  const run = useCallback(async (
    conversationId: number,
    call: (handlers: Parameters<typeof streamMessage>[2], signal: AbortSignal) => Promise<void>,
  ) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    buffer.reset()
    setState('streaming')

    let failed: ApiError | null = null
    try {
      await call({
        onToken: token => buffer.append(token),
        onDone: () => {},
        onError: error => { failed = error },
      }, controller.signal)
    } catch (error) {
      // AbortError é parada pedida pela usuária, não falha: o backend já gravou
      // a resposta parcial como "cancelled".
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        failed = error instanceof BffError
          ? { code: error.code, message: error.message, providerDetail: error.providerDetail }
          : { code: 'network', message: error instanceof Error ? error.message : String(error) }
      }
    } finally {
      abortRef.current = null
      // Recarrega a conversa **antes** de desmontar a UI de streaming: invertido,
      // há um piscar em que nem a bolha em andamento nem a persistida aparecem.
      await onSettled(conversationId)
      setState('idle')
      setPendingUserMessage(null)
      buffer.reset()
      if (failed) onError(failed)
    }
  }, [buffer, onSettled, onError])

  const send = useCallback(
    (conversationId: number, content: string) => {
      setPendingUserMessage(content)
      return run(conversationId, (handlers, signal) => streamMessage(conversationId, content, handlers, signal))
    },
    [run],
  )

  const regenerate = useCallback(
    (conversationId: number, messageId: number) =>
      run(conversationId, (handlers, signal) => regenerateMessage(conversationId, messageId, handlers, signal)),
    [run],
  )

  const stop = useCallback(() => abortRef.current?.abort(), [])

  return { state, buffer, send, regenerate, stop, pendingUserMessage, isStreaming: state === 'streaming' }
}
