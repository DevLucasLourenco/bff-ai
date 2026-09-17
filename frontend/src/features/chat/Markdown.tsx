import { Check, Copy } from 'lucide-react'
import { Fragment, memo, useState, type ReactNode } from 'react'

/**
 * Renderizador de markdown mínimo (F7.4).
 *
 * Resposta de LLM é markdown e era exibida como texto cru (`white-space:
 * pre-wrap`), com blocos de código aparecendo com as crases.
 *
 * Escrito à mão, em vez de trazer react-markdown + sanitizador, por dois
 * motivos: o projeto é deliberadamente sem framework, e montar **elementos
 * React** (nunca `dangerouslySetInnerHTML`) elimina a superfície de XSS por
 * construção — não existe string de HTML em lugar nenhum deste arquivo.
 *
 * Suporta o que uma resposta de chat realmente usa: blocos de código com
 * linguagem, código inline, negrito, itálico, links, títulos, listas e citações.
 */

type Block =
  | { kind: 'code'; language: string; content: string }
  | { kind: 'heading'; level: number; content: string }
  | { kind: 'list'; ordered: boolean; items: string[] }
  | { kind: 'quote'; content: string }
  | { kind: 'paragraph'; content: string }

const FENCE = /^```(\w+)?\s*$/

function parseBlocks(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: Block[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]

    const fence = line.match(FENCE)
    if (fence) {
      const language = fence[1] ?? ''
      const content: string[] = []
      index++
      while (index < lines.length && !FENCE.test(lines[index])) content.push(lines[index++])
      index++ // consome a cerca de fechamento (ou o fim do texto)
      blocks.push({ kind: 'code', language, content: content.join('\n') })
      continue
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/)
    if (heading) {
      blocks.push({ kind: 'heading', level: heading[1].length, content: heading[2] })
      index++
      continue
    }

    if (/^>\s?/.test(line)) {
      const content: string[] = []
      while (index < lines.length && /^>\s?/.test(lines[index])) content.push(lines[index++].replace(/^>\s?/, ''))
      blocks.push({ kind: 'quote', content: content.join('\n') })
      continue
    }

    const bullet = /^\s*[-*+]\s+(.*)$/
    const numbered = /^\s*\d+[.)]\s+(.*)$/
    if (bullet.test(line) || numbered.test(line)) {
      const ordered = numbered.test(line)
      const pattern = ordered ? numbered : bullet
      const items: string[] = []
      while (index < lines.length && pattern.test(lines[index])) {
        items.push(lines[index++].match(pattern)![1])
      }
      blocks.push({ kind: 'list', ordered, items })
      continue
    }

    if (!line.trim()) { index++; continue }

    const paragraph: string[] = []
    while (index < lines.length && lines[index].trim() && !FENCE.test(lines[index])
      && !/^(#{1,4})\s/.test(lines[index]) && !/^>\s?/.test(lines[index])
      && !bullet.test(lines[index]) && !numbered.test(lines[index])) {
      paragraph.push(lines[index++])
    }
    blocks.push({ kind: 'paragraph', content: paragraph.join('\n') })
  }

  return blocks
}

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(\[[^\]]+\]\([^)\s]+\))/g

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let cursor = 0
  let match: RegExpExecArray | null
  INLINE.lastIndex = 0

  while ((match = INLINE.exec(text)) !== null) {
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index))
    const token = match[0]
    const key = `${keyPrefix}-${match.index}`

    if (token.startsWith('`')) {
      nodes.push(<code className="inline-code" key={key}>{token.slice(1, -1)}</code>)
    } else if (token.startsWith('**')) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>)
    } else if (token.startsWith('*')) {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>)
    } else {
      const label = token.slice(1, token.indexOf(']'))
      const href = token.slice(token.indexOf('](') + 2, -1)
      // Só http(s): impede javascript: e data: vindos do texto do modelo.
      const safe = /^https?:\/\//i.test(href)
      nodes.push(safe
        ? <a href={href} key={key} target="_blank" rel="noopener noreferrer">{label}</a>
        : <Fragment key={key}>{token}</Fragment>)
    }
    cursor = match.index + token.length
  }

  if (cursor < text.length) nodes.push(text.slice(cursor))
  return nodes
}

function CodeBlock({ language, content }: { language: string; content: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch { /* clipboard bloqueado: o texto continua selecionável */ }
  }
  return <div className="code-block">
    <div className="code-head">
      <span>{language || 'código'}</span>
      <button type="button" onClick={copy} aria-label="Copiar código">
        {copied ? <Check size={14}/> : <Copy size={14}/>}{copied ? 'copiado' : 'copiar'}
      </button>
    </div>
    <pre><code>{content}</code></pre>
  </div>
}

export const Markdown = memo(function Markdown({ text }: { text: string }) {
  const blocks = parseBlocks(text)
  return <div className="markdown">
    {blocks.map((block, i) => {
      const key = `b${i}`
      switch (block.kind) {
        case 'code':
          return <CodeBlock key={key} language={block.language} content={block.content}/>
        case 'heading': {
          const Tag = (['h3', 'h4', 'h5', 'h6'][block.level - 1] ?? 'h6') as 'h3'
          return <Tag key={key}>{renderInline(block.content, key)}</Tag>
        }
        case 'list':
          return block.ordered
            ? <ol key={key}>{block.items.map((item, j) => <li key={j}>{renderInline(item, `${key}-${j}`)}</li>)}</ol>
            : <ul key={key}>{block.items.map((item, j) => <li key={j}>{renderInline(item, `${key}-${j}`)}</li>)}</ul>
        case 'quote':
          return <blockquote key={key}>{renderInline(block.content, key)}</blockquote>
        default:
          return <p key={key}>{renderInline(block.content, key)}</p>
      }
    })}
  </div>
})
