import { useState } from 'react'
import { characterImage, type AvatarCharacter, type Reaction } from '../lib/personaVisuals'

export function PersonaAvatar({ character, emoji, reaction = 'feliz_sorrindo', className = '' }: {
  character: AvatarCharacter | null | undefined
  emoji: string
  reaction?: Reaction
  className?: string
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const url = characterImage(character, reaction)
  return <span className={`persona-avatar ${className}`} aria-hidden="true">
    {url && failedUrl !== url
      ? <img src={url} alt="" draggable={false} onError={() => setFailedUrl(url)}/>
      : <span className="persona-avatar-emoji">{emoji}</span>}
  </span>
}
