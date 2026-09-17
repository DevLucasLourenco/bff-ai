import { LoaderCircle } from 'lucide-react'
import { useSyncExternalStore } from 'react'
import type { StreamBuffer } from '../../lib/streamBuffer'
import { Markdown } from './Markdown'

/**
 * A bolha que está sendo preenchida (F7.3).
 *
 * Assina o StreamBuffer direto: quando um token chega, **só este componente**
 * rerenderiza. Antes, cada token recriava o array de mensagens no App e a lista
 * inteira era reconstruída.
 */
export function StreamingMessage({ buffer }: { buffer: StreamBuffer }) {
  const text = useSyncExternalStore(buffer.subscribe, buffer.getSnapshot, buffer.getSnapshot)

  return <div className="message-wrap assistant">
    <article className="message assistant" aria-busy="true">
      {text ? <Markdown text={text}/> : <span className="typing"><LoaderCircle className="spin" size={16}/> pensando…</span>}
    </article>
  </div>
}
