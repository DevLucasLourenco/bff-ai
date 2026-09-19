import { useCallback, useMemo, useRef, useState } from 'react'
import { regenerateMessage, streamMessage, toApiError } from '../lib/api'
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
  // A qual conversa o stream em andamento pertence. Sem isto a bolha em
  // andamento aparecia em qualquer conversa aberta — trocar de conversa no meio
  // de uma resposta a levava junto para a conversa errada.
  const [streamingConversationId, setStreamingConversationId] = useState<number | null>(null)
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
    setStreamingConversationId(conversationId)
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
        failed = toApiError(error)
      }
    } finally {
      // Este stream ainda é o atual? Se a usuária mandou outra mensagem enquanto
      // este encerrava, o abortRef já aponta para o controller do stream novo —
      // zerá-lo aqui quebrava o botão "parar" do novo.
      const aindaAtual = () => abortRef.current === controller
      // Recarrega a conversa **antes** de desmontar a UI de streaming: invertido,
      // há um piscar em que nem a bolha em andamento nem a persistida aparecem.
      // O recarregamento tem try próprio: se ele falhar (backend caiu no fim do
      // stream), o resto do finally precisa rodar mesmo assim — antes a UI
      // ficava presa no estado "gerando", com o botão de parar e o composer
      // travados até recarregar a página.
      try {
        await onSettled(conversationId)
      } catch (error) {
        failed ??= toApiError(error)
      }
      if (aindaAtual()) {
        abortRef.current = null
        setState('idle')
        setPendingUserMessage(null)
        setStreamingConversationId(null)
        buffer.reset()
      }
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

  return {
    state, buffer, send, regenerate, stop, pendingUserMessage, streamingConversationId,
    isStreaming: state === 'streaming',
  }
}
