import { AlertTriangle, CircleSlash, RefreshCw } from 'lucide-react'
import { memo } from 'react'
import type { Message } from '../../lib/types'
import { Markdown } from './Markdown'
import { ChatObjectRenderer } from './ChatObjectRenderer'

/**
 * Uma mensagem já persistida. `memo` porque o pai rerenderiza a cada resposta
 * nova e o conteúdo destas não muda (F7.3).
 */
export const MessageBubble = memo(function MessageBubble({ message, onRegenerate }: {
  message: Message
  onRegenerate?: (messageId: number) => void
}) {
  const interrupted = message.status !== 'complete'
  const cancelled = message.status === 'cancelled'

  return <div className={`message-wrap ${message.role}`}>
    <article className={`message ${message.role} ${interrupted ? 'interrupted' : ''}`}>
      {message.role === 'assistant' ? <Markdown text={message.content}/> : message.content}
      {!message.content && interrupted && <span className="muted">(nada foi gerado)</span>}
    </article>
    {message.ui_objects?.map(object => <ChatObjectRenderer key={object.id} object={object}/>)}

    {interrupted && <div className="message-notice">
      {cancelled
        ? <><CircleSlash size={14}/> Resposta interrompida por você.</>
        : <><AlertTriangle size={14}/> {message.error_message || 'A resposta falhou no meio.'}</>}
      {onRegenerate && <button type="button" className="link-button" onClick={() => onRegenerate(message.id)}>
        <RefreshCw size={13}/> tentar de novo
      </button>}
    </div>}

    {message.role === 'assistant' && !interrupted && <div className="message-meta">
      {message.latency_ms != null && <span>{(message.latency_ms / 1000).toFixed(1)}s</span>}
      {message.completion_tokens != null && <span>{message.completion_tokens} tokens</span>}
      {onRegenerate && <button type="button" className="link-button" onClick={() => onRegenerate(message.id)}>
        <RefreshCw size={13}/> regenerar
      </button>}
    </div>}
  </div>
})
