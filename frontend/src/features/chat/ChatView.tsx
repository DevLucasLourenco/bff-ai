import { ArrowUp, Paperclip, Square, X } from 'lucide-react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ClipboardEvent, type FormEvent } from 'react'
import type { StreamBuffer } from '../../lib/streamBuffer'
import type { ApiError, Conversation, Message } from '../../lib/types'
import { MessageBubble } from './MessageBubble'
import { StreamingMessage } from './StreamingMessage'
import { CharacterStage, type ReactionReplay } from './CharacterStage'
import { classifyReaction } from '../../lib/personaReactions'
import bffIcon from '../../assets/bff_icon.png'

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
  const [pendingPhoto, setPendingPhoto] = useState<{ conversationId: number; content: string; url: string; afterMessageId: number } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [replay, setReplay] = useState<ReactionReplay | null>(null)
  const attachmentInput = useRef<HTMLInputElement>(null)
  const messageInput = useRef<HTMLTextAreaElement>(null)
  const messageCount = conversation?.messages.length ?? 0
  const lastMessageId = conversation?.messages.at(-1)?.id
  const lastAssistantMessage = conversation?.messages.slice().reverse().find(message => message.role === 'assistant')
  const photoForConversation = pendingPhoto?.conversationId === conversation?.id ? pendingPhoto : null
  const photoAlreadySaved = !!photoForConversation && !!conversation?.messages.some(message => message.role === 'user' && message.id > photoForConversation.afterMessageId)
  const visiblePendingPhoto = photoAlreadySaved ? null : photoForConversation
  const showPendingMessage = !photoAlreadySaved && !!(visiblePendingPhoto || pendingUserMessage)
  const { endRef, containerRef } = useAutoScroll([messageCount, streaming, pendingUserMessage, pendingPhoto], true)

  // A foto precisa continuar visível na bolha enquanto o upload e a resposta
  // acontecem. A URL local é temporária; o histórico usa a URL do asset salvo.
  useEffect(() => {
    const url = pendingPhoto?.url
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [pendingPhoto?.url])

  // O efeito mede também quebras por largura e rascunhos inseridos por cards.
  useLayoutEffect(() => { if (messageInput.current) resizeMessageInput(messageInput.current) }, [draft, conversation?.id])
  useEffect(() => {
    const onResize = () => { if (messageInput.current) resizeMessageInput(messageInput.current) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  useEffect(() => { setReplay(null) }, [conversation?.id])

  const replayReaction = useCallback((message: Message) => {
    if (!conversation) return
    setReplay(previous => ({
      conversationId: conversation.id,
      sequence: (previous?.sequence ?? 0) + 1,
      reaction: message.status === 'failed' ? 'pedindo_desculpas' : classifyReaction(message.content),
    }))
  }, [conversation?.id])

  // Ações de cards já trazem um pedido completo. Elas entram na conversa sem
  // ocupar nem apagar um rascunho que a pessoa esteja escrevendo no composer.
  const sendComponentRequest = async (content: string) => {
    if (!content.trim() || streaming || submitting || !conversation) return
    setSubmitting(true)
    try { await onSend(content, null) } finally { setSubmitting(false) }
  }

  useEffect(() => {
    const attach = () => attachmentInput.current?.click()
    const compose = (event: Event) => {
      setDraft((event as CustomEvent<string>).detail)
      messageInput.current?.focus()
    }
    const send = (event: Event) => { void sendComponentRequest((event as CustomEvent<string>).detail) }
    window.addEventListener('fashion:attach', attach)
    window.addEventListener('fashion:compose', compose)
    window.addEventListener('fashion:send', send)
    return () => {
      window.removeEventListener('fashion:attach', attach)
      window.removeEventListener('fashion:compose', compose)
      window.removeEventListener('fashion:send', send)
    }
  }, [conversation, onSend, streaming, submitting])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const content = draft.trim()
    if ((!content && !attachment) || streaming || submitting || !conversation) return
    const currentAttachment = attachment
    const sentContent = content || 'Quero cadastrar a peça desta foto no meu guarda-roupa.'
    if (currentAttachment) {
      setPendingPhoto({
        conversationId: conversation.id,
        content: sentContent,
        url: URL.createObjectURL(currentAttachment),
        afterMessageId: lastMessageId ?? 0,
      })
    }
    setSubmitting(true)
    setDraft('')
    setAttachment(null)
    if (attachmentInput.current) attachmentInput.current.value = ''
    try {
      const accepted = await onSend(sentContent, currentAttachment)
      if (!accepted) { setDraft(content); setAttachment(currentAttachment) }
    } finally { setPendingPhoto(null); setSubmitting(false) }
  }

  const pasteImage = (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const image = Array.from(event.clipboardData.files).find(file => ['image/jpeg', 'image/png', 'image/webp'].includes(file.type))
    if (!image) return
    event.preventDefault()
    setAttachment(new File([image], image.name || 'imagem-colada.png', { type: image.type }))
  }

  if (!conversation) {
    return <main className="chat-view empty-state">
      <div className="empty-orb"><img src={bffIcon} alt=""/></div>
      <h1>Uma conversa só de vocês.</h1>
      <p>Crie uma conversa e escolha a personalidade e o modelo nas configurações.</p>
    </main>
  }

  return <main className={`chat-view ${conversation.persona_character ? 'has-character' : ''}`}>
    <header className="chat-header">
      <div>
        <div className="persona-title">{!conversation.persona_character && <span aria-hidden="true">{conversation.persona_emoji}</span>}<strong>{conversation.persona_name}</strong></div>
        <span className="model-caption">{conversation.model_display_name} · {conversation.provider_kind}</span>
      </div>
    </header>

    <div className={`chat-body ${conversation.persona_character ? 'with-stage' : ''}`}>
    <section className="messages" ref={containerRef} aria-live="polite" aria-busy={streaming}>
      {/* A saudação da persona era editável e nunca aparecia: aqui havia um texto fixo. */}
      {messageCount === 0 && !streaming && !showPendingMessage && <div className="greeting-bubble">
        {conversation.persona_greeting.trim() || 'Comece falando qualquer coisa. 💗'}
      </div>}

      {conversation.messages.map(message => <MessageBubble
        key={message.id}
        message={message}
        onReplayReaction={conversation.persona_character && !streaming ? replayReaction : undefined}
        // Só a última resposta pode ser regenerada: regenerar uma antiga apagaria
        // tudo o que veio depois dela. O backend recusa com 409 também.
        onRegenerate={message.id === lastMessageId && message.role === 'assistant' && !streaming ? onRegenerate : undefined}
      />)}

      {showPendingMessage && <div className="message-wrap user">
        <div className="message-row"><article className="message user">
          {visiblePendingPhoto && <div className="message-attachments"><img src={visiblePendingPhoto.url} alt="Foto anexada à mensagem"/></div>}
          {visiblePendingPhoto?.content ?? pendingUserMessage}
        </article></div>
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
    {conversation.persona_character && <CharacterStage
      key={conversation.id}
      conversationId={conversation.id}
      name={conversation.persona_name}
      character={conversation.persona_character}
      emoji={conversation.persona_emoji}
      buffer={buffer}
      streaming={streaming}
      pendingUserMessage={pendingUserMessage}
      lastAssistantMessage={lastAssistantMessage}
      error={error}
      replay={replay}
    />}
    </div>

    <form className="composer" onSubmit={submit}>
      <input ref={attachmentInput} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={event => setAttachment(event.target.files?.[0] ?? null)}/>
      <button type="button" className="attach-button" aria-label="Anexar foto de peça" disabled={streaming || submitting} onClick={() => attachmentInput.current?.click()}><Paperclip size={17}/></button>
      <textarea
        ref={messageInput}
        value={draft}
        onChange={event => setDraft(event.target.value)}
        onPaste={pasteImage}
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

