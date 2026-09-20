import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { Message } from '../../lib/types'
import { MessageBubble } from './MessageBubble'
import { StreamingMessage } from './StreamingMessage'
import { StreamBuffer } from '../../lib/streamBuffer'
import { PersonaAvatar } from '../../components/PersonaAvatar'

const base: Message = { id: 1, role: 'assistant', content: 'Vamos por partes para resolver essa situação.', status: 'complete' }

describe('visual da persona na conversa', () => {
  it('mostra reação na resposta da assistente e preserva a mensagem', () => {
    const html = renderToStaticMarkup(<MessageBubble message={base} personaCharacter="ruiva" personaEmoji="💗"/>)
    expect(html).toContain('34_vamos_resolver_isso')
    expect(html).toContain('Vamos por partes para resolver essa situação.')
  })

  it('não coloca o avatar da assistente na mensagem da usuária', () => {
    const html = renderToStaticMarkup(<MessageBubble message={{ ...base, role: 'user' }} personaCharacter="ruiva" personaEmoji="💗"/>)
    expect(html).not.toContain('persona-message-avatar')
    expect(html).toContain('Vamos por partes')
  })

  it('mantém o chat sem visual configurado', () => {
    const html = renderToStaticMarkup(<MessageBubble message={base} personaCharacter={null} personaEmoji="💗"/>)
    expect(html).not.toContain('persona-message-avatar')
    expect(html).toContain('Vamos por partes')
  })

  it('inicia a geração com a personagem escutando', () => {
    const html = renderToStaticMarkup(<StreamingMessage buffer={new StreamBuffer()} personaCharacter="ruiva" personaEmoji="💗"/>)
    expect(html).toContain('28_escutando_atenta')
    expect(html).toContain('pensando')
  })

  it('fornece texto alternativo quando é uma prévia de galeria', () => {
    const html = renderToStaticMarkup(<PersonaAvatar character="ruiva" emoji="💗" imageAlt="Prévia da personagem Ruiva"/>)
    expect(html).toContain('alt="Prévia da personagem Ruiva"')
    expect(html).not.toContain('aria-hidden="true"')
  })

  it('mantém os metadados em resposta interrompida', () => {
    const html = renderToStaticMarkup(<MessageBubble message={{
      ...base, status: 'cancelled', created_at: '2026-09-20T12:30:00', latency_ms: 1200, completion_tokens: 42,
    }} personaCharacter="ruiva" personaEmoji="💗"/>)
    expect(html).toContain('20/09/2026')
    expect(html).toContain('1.2s')
    expect(html).toContain('42 tokens')
  })
})
