import { useState } from 'react'
import { characterImage, type AvatarCharacter, type Reaction } from '../lib/personaVisuals'

export function PersonaAvatar({ character, emoji, reaction = 'feliz_sorrindo', className = '', imageAlt }: {
  character: AvatarCharacter | null | undefined
  emoji: string
  reaction?: Reaction
  className?: string
  /** Nas mensagens é decorativo; na galeria a prévia descreve a personagem. */
  imageAlt?: string
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const url = characterImage(character, reaction)
  return <span className={`persona-avatar ${className}`} aria-hidden={imageAlt ? undefined : true}>
    {url && failedUrl !== url
      ? <img src={url} alt={imageAlt ?? ''} draggable={false} onError={() => setFailedUrl(url)}/>
      : <span className="persona-avatar-emoji" role={imageAlt ? 'img' : undefined} aria-label={imageAlt}>{emoji}</span>}
  </span>
}
