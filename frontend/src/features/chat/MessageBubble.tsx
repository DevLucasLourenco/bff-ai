import { AlertTriangle, CircleSlash, RefreshCw } from 'lucide-react'
import { memo } from 'react'
import type { Message } from '../../lib/types'
import { Markdown } from './Markdown'
import { ChatObjectRenderer } from './ChatObjectRenderer'

const dateTimeFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
})

function messageTimestamp(value: string | undefined): Date | null {
  if (!value) return null
  // O SQLite pode devolver o UTC sem offset; o navegador interpretaria como
  // horário local e exibiria a resposta com horas de diferença.
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? null : date
}

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
  const timestamp = messageTimestamp(message.created_at)

  return <div className={`message-wrap ${message.role}`}>
    <article className={`message ${message.role} ${interrupted ? 'interrupted' : ''}`}>
      {message.role === 'assistant' ? <Markdown text={message.content}/> : message.content}
      {message.attachment_asset_ids?.length ? <div className="message-attachments">{message.attachment_asset_ids.map(id => <img key={id} src={`/api/fashion/assets/${id}`} alt="Foto anexada da peça"/>)}</div> : null}
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
      {timestamp && <time dateTime={timestamp.toISOString()} title={timestamp.toLocaleString('pt-BR')}>{dateTimeFormatter.format(timestamp)}</time>}
      {message.latency_ms != null && <span>{(message.latency_ms / 1000).toFixed(1)}s</span>}
      {message.completion_tokens != null && <span>{message.completion_tokens} tokens</span>}
      {onRegenerate && <button type="button" className="link-button" onClick={() => onRegenerate(message.id)}>
        <RefreshCw size={13}/> regenerar
      </button>}
    </div>}
  </div>
})
