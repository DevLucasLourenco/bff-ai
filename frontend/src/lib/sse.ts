/**
 * Parser incremental de frames SSE (F6.3).
 *
 * Estava embutido em api.ts como split('\n\n') + regex, sem cobertura nenhuma:
 * frágil a frame partido entre chunks da rede, a `\r\n` e a frames com mais de
 * uma linha `data:`. Extraído para poder ser testado sem servidor.
 */

export type SseEvent = { event: string; data: unknown }

const FRAME_SEPARATOR = /\r?\n\r?\n/

function parseFrame(frame: string): SseEvent | null {
  let event = 'message'
  const dataLines: string[] = []

  for (const rawLine of frame.split(/\r?\n/)) {
    // Linha iniciada por ':' é comentário/keep-alive.
    if (!rawLine || rawLine.startsWith(':')) continue
    const separator = rawLine.indexOf(':')
    const field = separator === -1 ? rawLine : rawLine.slice(0, separator)
    // O espaço após os dois-pontos é opcional e não faz parte do valor.
    let value = separator === -1 ? '' : rawLine.slice(separator + 1)
    if (value.startsWith(' ')) value = value.slice(1)

    if (field === 'event') event = value
    else if (field === 'data') dataLines.push(value)
  }

  if (dataLines.length === 0) return null
  // Várias linhas `data:` no mesmo frame se juntam com \n (spec do SSE).
  const raw = dataLines.join('\n')
  try {
    return { event, data: JSON.parse(raw) }
  } catch {
    return { event, data: raw }
  }
}

export function createSseParser() {
  let buffer = ''
  return {
    /** Consome um pedaço do stream e devolve os frames já completos. */
    push(chunk: string): SseEvent[] {
      buffer += chunk
      const parts = buffer.split(FRAME_SEPARATOR)
      // O último pedaço pode estar incompleto: volta para o buffer.
      buffer = parts.pop() ?? ''
      return parts.map(parseFrame).filter((e): e is SseEvent => e !== null)
    },
    /** Fecha o stream, entregando um frame final sem separador, se houver. */
    flush(): SseEvent[] {
      const rest = buffer.trim()
      buffer = ''
      if (!rest) return []
      const parsed = parseFrame(rest)
      return parsed ? [parsed] : []
    },
  }
}
