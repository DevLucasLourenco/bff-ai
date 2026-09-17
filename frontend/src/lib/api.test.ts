import { describe, expect, it } from 'vitest'
import { normalizeError } from './api'

describe('normalizeError', () => {
  it('preserva o code do erro de domínio do backend', () => {
    const erro = normalizeError(
      { detail: { code: 'provider_auth', message: 'Chave recusada', provider_detail: '401' } },
      502,
    )
    expect(erro).toEqual({ code: 'provider_auth', message: 'Chave recusada', providerDetail: '401' })
  })

  it('lida com HTTPException simples (detail como string)', () => {
    expect(normalizeError({ detail: 'Conversa arquivada' }, 409)).toEqual({
      code: 'http_409', message: 'Conversa arquivada',
    })
  })

  it('lida com erro de validação do FastAPI (detail como lista)', () => {
    const erro = normalizeError({ detail: [{ msg: 'Field required', loc: ['body', 'content'] }] }, 422)
    expect(erro.code).toBe('validation_error')
    expect(erro.message).toBe('Field required')
  })

  it('tem saída utilizável para corpo inesperado', () => {
    expect(normalizeError({ qualquer: 'coisa' }, 500).code).toBe('http_500')
    expect(normalizeError(null, 500).message).toContain('500')
  })
})
