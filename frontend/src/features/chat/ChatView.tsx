import { ArrowUp, Paperclip, Sparkles, Square, X } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState, type FormEvent } from 'react'
import type { StreamBuffer } from '../../lib/streamBuffer'
import type { ApiError, Conversation } from '../../lib/types'
import { MessageBubble } from './MessageBubble'
import { StreamingMessage } from './StreamingMessage'

type Props = {
  conversation: Conversation | null
  streaming: boolean
  buffer: StreamBuffer
  /** Mensagem recém-enviada, ainda não recarregada do servidor. */
  pendingUserMessage: string | null
  error: ApiError | null
  onSend: (content: string, attachment: File | null) => Promise<boolean>
  onStop: () => void
  onRegenerate: (messageId: number) => void
  onDismissError: () => void
}

/** Autoscroll que respeita quem rolou para cima e quem pediu menos movimento. */
function useAutoScroll(dependencies: unknown[], enabled: boolean) {
  const endRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLElement>(null)
  const stickRef = useRef(true)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const onScroll = () => {
      const distance = container.scrollHeight - container.scrollTop - container.clientHeight
      stickRef.current = distance < 120
    }
    container.addEventListener('scroll', onScroll, { passive: true })
    return () => container.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!enabled || !stickRef.current) return
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    endRef.current?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)

  return { endRef, containerRef }
}

/** Ajusta a altura real do texto até dez linhas visíveis. */
function resizeMessageInput(input: HTMLTextAreaElement) {
  const style = window.getComputedStyle(input)
  const lineHeight = Number.parseFloat(style.lineHeight)
  const padding = Number.parseFloat(style.paddingTop) + Number.parseFloat(style.paddingBottom)
  const borders = Number.parseFloat(style.borderTopWidth) + Number.parseFloat(style.borderBottomWidth)
  const maxHeight = Math.ceil(lineHeight * 10 + padding + borders)
  const previousScrollTop = input.scrollTop
  input.style.height = 'auto'
  input.style.overflowY = 'hidden'
  const needsScroll = input.scrollHeight > maxHeight
  input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`
  input.style.overflowY = needsScroll ? 'auto' : 'hidden'
  input.scrollTop = needsScroll ? previousScrollTop : 0
}

export function ChatView({ conversation, streaming, buffer, pendingUserMessage, error, onSend, onStop, onRegenerate, onDismissError }: Props) {
  const [draft, setDraft] = useState('')
  const [attachment, setAttachment] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const attachmentInput = useRef<HTMLInputElement>(null)
  const messageInput = useRef<HTMLTextAreaElement>(null)
  const messageCount = conversation?.messages.length ?? 0
  const lastMessageId = conversation?.messages.at(-1)?.id
  const { endRef, containerRef } = useAutoScroll([messageCount, streaming, pendingUserMessage], true)

  // O efeito mede também quebras por largura e rascunhos inseridos por cards.
  useLayoutEffect(() => { if (messageInput.current) resizeMessageInput(messageInput.current) }, [draft, conversation?.id])
  useEffect(() => {
    const onResize = () => { if (messageInput.current) resizeMessageInput(messageInput.current) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const attach = () => attachmentInput.current?.click()
    const compose = (event: Event) => {
      setDraft((event as CustomEvent<string>).detail)
      messageInput.current?.focus()
    }
    window.addEventListener('fashion:attach', attach)
    window.addEventListener('fashion:compose', compose)
    return () => {
      window.removeEventListener('fashion:attach', attach)
      window.removeEventListener('fashion:compose', compose)
    }
  }, [])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if ((!content && !attachment) || streaming || submitting || !conversation) return
    const currentAttachment = attachment
    setSubmitting(true)
    setDraft('')
    setAttachment(null)
    if (attachmentInput.current) attachmentInput.current.value = ''
    try {
      const accepted = await onSend(content || 'Quero cadastrar a peça desta foto no meu guarda-roupa.', currentAttachment)
      if (!accepted) { setDraft(content); setAttachment(currentAttachment) }
    } finally { setSubmitting(false) }
  }

  if (!conversation) {
    return <main className="chat-view empty-state">
      <div className="empty-orb"><Sparkles size={28}/></div>
      <h1>Uma conversa só de vocês.</h1>
      <p>Crie uma conversa e escolha a personalidade e o modelo nas configurações.</p>
    </main>
  }

  return <main className="chat-view">
    <header className="chat-header">
      <div>
        <div className="persona-title"><span>{conversation.persona_emoji}</span><strong>{conversation.persona_name}</strong></div>
        <span className="model-caption">{conversation.model_display_name} · {conversation.provider_kind}</span>
      </div>
    </header>

    <section className="messages" ref={containerRef} aria-live="polite" aria-busy={streaming}>
      {/* A saudação da persona era editável e nunca aparecia: aqui havia um texto fixo. */}
      {messageCount === 0 && !streaming && !pendingUserMessage && <div className="greeting-bubble">
        {conversation.persona_greeting.trim() || 'Comece falando qualquer coisa. 💗'}
      </div>}

      {conversation.messages.map(message => <MessageBubble
        key={message.id}
        message={message}
        // Só a última resposta pode ser regenerada: regenerar uma antiga apagaria
        // tudo o que veio depois dela. O backend recusa com 409 também.
        onRegenerate={message.id === lastMessageId && message.role === 'assistant' && !streaming ? onRegenerate : undefined}
      />)}

      {pendingUserMessage && <div className="message-wrap user">
        <article className="message user">{pendingUserMessage}</article>
      </div>}

      {streaming && <StreamingMessage buffer={buffer}/>}

      {/* F7.2: erro de conversa aparece ancorado aqui, não num toast genérico. */}
      {error && <div className="inline-error" role="alert">
        <div>
          <strong>{error.message}</strong>
          {error.code === 'provider_auth' && <p>Abra Configurações → LLM e revise a API key.</p>}
          {error.code === 'provider_unreachable' && <p>O provider não respondeu. Se for Ollama local, confira se ele está rodando.</p>}
          {error.code === 'model_not_found' && <p>Escolha outro modelo em Configurações → LLM.</p>}
          {error.code === 'stream_stalled' && <p>Pode ter sido a rede ou o servidor. Sua mensagem foi registrada; se a resposta não aparecer ao reabrir a conversa, peça de novo.</p>}
          {error.code === 'context_overflow' && <p>Defina a janela de contexto do modelo para que o histórico antigo seja cortado automaticamente.</p>}
          {error.providerDetail && <details><summary>detalhe do provider</summary><pre>{error.providerDetail}</pre></details>}
        </div>
        <button type="button" className="link-button" onClick={onDismissError}>dispensar</button>
      </div>}

      <div ref={endRef}/>
    </section>

    <form className="composer" onSubmit={submit}>
      <input ref={attachmentInput} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={event => setAttachment(event.target.files?.[0] ?? null)}/>
      <button type="button" className="attach-button" aria-label="Anexar foto de peça" disabled={streaming || submitting} onClick={() => attachmentInput.current?.click()}><Paperclip size={17}/></button>
      <textarea
        ref={messageInput}
        value={draft}
        onChange={event => setDraft(event.target.value)}
        placeholder="Escreva, cole um link ou anexe uma foto…"
        rows={1}
        aria-label="Mensagem"
        onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() }
        }}
      />
      {attachment && <span className="chat-attachment"><span>{attachment.name}</span><button type="button" aria-label="Remover anexo" onClick={() => { setAttachment(null); if (attachmentInput.current) attachmentInput.current.value = '' }}><X size={13}/></button></span>}
      {streaming
        ? <button type="button" className="stop" aria-label="Parar geração" onClick={onStop}><Square size={16} fill="currentColor"/></button>
        : <button aria-label="Enviar" disabled={submitting || (!draft.trim() && !attachment)}><ArrowUp size={20}/></button>}
    </form>
  </main>
}

