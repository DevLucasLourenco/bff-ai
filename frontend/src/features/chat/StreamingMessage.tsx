import { LoaderCircle } from 'lucide-react'
import { useEffect, useState, useSyncExternalStore } from 'react'
import type { StreamBuffer } from '../../lib/streamBuffer'
import { Markdown } from './Markdown'
import { PersonaAvatar } from '../../components/PersonaAvatar'
import { streamingReaction } from '../../lib/personaReactions'
import type { AvatarCharacter, Reaction } from '../../lib/personaVisuals'

/**
 * A bolha que está sendo preenchida (F7.3).
 *
 * Assina o StreamBuffer direto: quando um token chega, **só este componente**
 * rerenderiza. Antes, cada token recriava o array de mensagens no App e a lista
 * inteira era reconstruída.
 */
export function StreamingMessage({ buffer, personaCharacter, personaEmoji }: { buffer: StreamBuffer; personaCharacter: AvatarCharacter | null; personaEmoji: string }) {
  const text = useSyncExternalStore(buffer.subscribe, buffer.getSnapshot, buffer.getSnapshot)
  const [waitingReaction, setWaitingReaction] = useState<Reaction>('escutando_atenta')
  useEffect(() => {
    const timeout = window.setTimeout(() => setWaitingReaction('analisando'), 800)
    return () => window.clearTimeout(timeout)
  }, [])
  const reaction = text ? streamingReaction(text) : waitingReaction

  return <div className="message-wrap assistant">
    <div className={personaCharacter ? 'assistant-reaction-row' : 'message-row'}>
      {personaCharacter && <PersonaAvatar character={personaCharacter} emoji={personaEmoji} reaction={reaction} className="persona-message-avatar"/>}
      <article className="message assistant" aria-busy="true">
        {text ? <Markdown text={text}/> : <span className="typing"><LoaderCircle className="spin" size={16}/> pensando…</span>}
      </article>
    </div>
  </div>
}
