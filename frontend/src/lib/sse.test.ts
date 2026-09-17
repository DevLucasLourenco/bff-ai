import { describe, expect, it } from 'vitest'
import { createSseParser } from './sse'

const frame = (event: string, data: unknown) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

describe('parser SSE', () => {
  it('entrega frames completos e guarda o resto', () => {
    const parser = createSseParser()
    expect(parser.push(frame('meta', { model: 'x' }))).toEqual([{ event: 'meta', data: { model: 'x' } }])
  })

  it('remonta um frame partido entre chunks da rede', () => {
    // Este é o caso que o split('\n\n') + regex anterior perdia em silêncio.
    const parser = createSseParser()
    const inteiro = frame('token', { text: 'oi' })
    const corte = Math.floor(inteiro.length / 2)

    expect(parser.push(inteiro.slice(0, corte))).toEqual([])
    expect(parser.push(inteiro.slice(corte))).toEqual([{ event: 'token', data: { text: 'oi' } }])
  })

  it('aceita vários frames num chunk só', () => {
    const parser = createSseParser()
    const eventos = parser.push(frame('token', { text: 'a' }) + frame('token', { text: 'b' }) + frame('done', { message_id: 1 }))
    expect(eventos.map(e => e.event)).toEqual(['token', 'token', 'done'])
  })

  it('aceita CRLF', () => {
    const parser = createSseParser()
    expect(parser.push('event: token\r\ndata: {"text":"oi"}\r\n\r\n')).toEqual([
      { event: 'token', data: { text: 'oi' } },
    ])
  })

  it('junta múltiplas linhas data do mesmo frame', () => {
    const parser = createSseParser()
    const [evento] = parser.push('event: raw\ndata: linha1\ndata: linha2\n\n')
    expect(evento.data).toBe('linha1\nlinha2')
  })

  it('ignora comentários de keep-alive', () => {
    const parser = createSseParser()
    expect(parser.push(': ping\n\n')).toEqual([])
    expect(parser.push(frame('token', { text: 'ok' }))).toHaveLength(1)
  })

  it('entrega no flush um frame final sem separador', () => {
    const parser = createSseParser()
    expect(parser.push('event: done\ndata: {"message_id":7}')).toEqual([])
    expect(parser.flush()).toEqual([{ event: 'done', data: { message_id: 7 } }])
  })

  it('não quebra com data que não é JSON', () => {
    const parser = createSseParser()
    expect(parser.push('event: token\ndata: texto solto\n\n')).toEqual([
      { event: 'token', data: 'texto solto' },
    ])
  })

  it('preserva texto com espaços e acentos', () => {
    const parser = createSseParser()
    const [evento] = parser.push(frame('token', { text: '  até já 💗' }))
    expect((evento.data as { text: string }).text).toBe('  até já 💗')
  })
})
