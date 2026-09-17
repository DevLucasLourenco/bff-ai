import { ArrowUp, LoaderCircle, Sparkles } from 'lucide-react'
import { FormEvent, useEffect, useRef, useState } from 'react'
import type { Conversation, Message } from '../../lib/types'

export function ChatView({ conversation, sending, onSend }: {
  conversation: Conversation | null
  sending: boolean
  onSend: (content: string) => Promise<void>
}) {
  const [draft, setDraft] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages, sending])
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const content = draft.trim()
    if (!content || sending || !conversation) return
    setDraft('')
    await onSend(content)
  }
  if (!conversation) return <main className="chat-view empty-state"><div className="empty-orb"><Sparkles size={28}/></div><h1>Uma conversa só de vocês.</h1><p>Crie uma conversa e escolha a personalidade e o modelo nas configurações.</p></main>

  return <main className="chat-view">
    <header className="chat-header">
      <div><div className="persona-title"><span>{conversation.persona_emoji}</span><strong>{conversation.persona_name}</strong></div><span className="model-caption">{conversation.model_display_name} · {conversation.provider_kind}</span></div>
    </header>
    <section className="messages">
      {conversation.messages.length === 0 && <div className="greeting-bubble">Comece falando qualquer coisa. A persona escolhida já está pronta para conversar. 💗</div>}
      {conversation.messages.map((message: Message) => <div className={`message-wrap ${message.role}`} key={message.id}>
        <article className={`message ${message.role}`}>{message.content}</article>
      </div>)}
      {sending && <div className="message-wrap assistant"><article className="message assistant typing"><LoaderCircle className="spin" size={16}/> pensando…</article></div>}
      <div ref={bottomRef}/>
    </section>
    <form className="composer" onSubmit={submit}>
      <textarea value={draft} onChange={e => setDraft(e.target.value)} placeholder="Fala comigo…" rows={1} onKeyDown={e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit() }
      }}/>
      <button aria-label="Enviar" disabled={!draft.trim() || sending}><ArrowUp size={20}/></button>
    </form>
  </main>
}
