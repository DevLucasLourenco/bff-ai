import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { Message } from '../../lib/types'
import { MessageBubble } from './MessageBubble'
import { StreamingMessage } from './StreamingMessage'
import { CharacterStage } from './CharacterStage'
import { StreamBuffer } from '../../lib/streamBuffer'
import { PersonaAvatar } from '../../components/PersonaAvatar'

const base: Message = { id: 1, role: 'assistant', content: 'Vamos por partes para resolver essa situação.', status: 'complete' }

describe('visual da persona na conversa', () => {
  it('mantém a mensagem limpa e oferece replay da reação', () => {
    const html = renderToStaticMarkup(<MessageBubble message={base} onReplayReaction={() => {}}/>)
    expect(html).not.toContain('persona-message-avatar')
    expect(html).toContain('ver reação')
    expect(html).toContain('Vamos por partes para resolver essa situação.')
  })

  it('não oferece replay na mensagem da usuária', () => {
    const html = renderToStaticMarkup(<MessageBubble message={{ ...base, role: 'user' }} onReplayReaction={() => {}}/>)
    expect(html).not.toContain('ver reação')
    expect(html).toContain('Vamos por partes')
  })

  it('mostra a foto salva antes do texto da mensagem da usuária', () => {
    const html = renderToStaticMarkup(<MessageBubble message={{ ...base, role: 'user', content: 'Minha camisa', attachment_asset_ids: [42] }}/>)
    expect(html).toContain('src="/api/fashion/assets/42"')
    expect(html).toContain('alt="Foto anexada da peça"')
    expect(html.indexOf('src="/api/fashion/assets/42"')).toBeLessThan(html.indexOf('Minha camisa'))
  })

  it('mantém o chat sem visual configurado', () => {
    const html = renderToStaticMarkup(<MessageBubble message={base}/>)
    expect(html).not.toContain('ver reação')
    expect(html).toContain('Vamos por partes')
  })

  it('mantém o stream textual e o palco em sua própria área', () => {
    const buffer = new StreamBuffer()
    const html = renderToStaticMarkup(<StreamingMessage buffer={buffer}/>)
    const stage = renderToStaticMarkup(<CharacterStage conversationId={1} name="Nina" character="morena" emoji="💗" buffer={buffer} streaming={false} pendingUserMessage={null} error={null} replay={null}/>)
    expect(html).not.toContain('28_escutando_atenta')
    expect(html).toContain('pensando')
    expect(stage).toContain('28_escutando_atenta')
    expect(stage).toContain('aria-label="Reações de Nina"')
    expect(stage).toContain('class="sr-only" role="status"')
  })

  it('reabre a conversa exibindo a reação da última resposta', () => {
    const stage = renderToStaticMarkup(<CharacterStage
      conversationId={1} name="Nina" character="morena" emoji="💗" buffer={new StreamBuffer()}
      streaming={false} pendingUserMessage={null} error={null} replay={null}
      lastAssistantMessage={{ ...base, content: 'Parabéns! Você conseguiu.' }}
    />)
    expect(stage).toContain('25_comemorando')
    expect(stage).toContain('Reação da última resposta')
  })

  it('fornece texto alternativo quando é uma prévia de galeria', () => {
    const html = renderToStaticMarkup(<PersonaAvatar character="morena" emoji="💗" imageAlt="Prévia da personagem Morena"/>)
    expect(html).toContain('alt="Prévia da personagem Morena"')
    expect(html).not.toContain('aria-hidden="true"')
  })

  it('mantém os metadados em resposta interrompida', () => {
    const html = renderToStaticMarkup(<MessageBubble message={{
      ...base, status: 'cancelled', created_at: '2026-09-20T12:30:00', latency_ms: 1200, completion_tokens: 42,
    }}/>)
    expect(html).toContain('20/09/2026')
    expect(html).toContain('1.2s')
    expect(html).toContain('42 tokens')
  })
})
