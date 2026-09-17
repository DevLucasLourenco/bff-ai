/**
 * Buffer do texto que está chegando, fora da árvore de estado do React (F7.3).
 *
 * Antes, cada token fazia `setActive` recriando o array inteiro de mensagens:
 * a lista toda rerenderizava dezenas de vezes por segundo numa resposta longa.
 * Aqui o texto vive fora do React e só o componente que o assina reage — e as
 * notificações são agrupadas por frame, então a taxa de render não acompanha a
 * taxa de tokens.
 */
export class StreamBuffer {
  private text = ''
  private listeners = new Set<() => void>()
  private frame: number | null = null

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener)
    return () => { this.listeners.delete(listener) }
  }

  getSnapshot = (): string => this.text

  append(chunk: string): void {
    this.text += chunk
    this.scheduleEmit()
  }

  reset(): void {
    this.text = ''
    this.emitNow()
  }

  private scheduleEmit(): void {
    if (this.frame !== null) return
    const schedule = typeof requestAnimationFrame === 'function'
      ? requestAnimationFrame
      : (cb: FrameRequestCallback) => setTimeout(() => cb(0), 16) as unknown as number
    this.frame = schedule(() => { this.frame = null; this.emitNow() })
  }

  private emitNow(): void {
    for (const listener of this.listeners) listener()
  }
}
