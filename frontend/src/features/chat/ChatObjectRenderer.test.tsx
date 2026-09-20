import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import type { ChatUiObject } from '../../lib/types'
import { ChatObjectRenderer } from './ChatObjectRenderer'

describe('componente do guarda-roupa na conversa', () => {
  it('mostra as peças e as fotos recebidas no snapshot da tool', () => {
    const object: ChatUiObject = {
      id: 7, type: 'wardrobe_view', schema_version: 1, created_at: '2026-09-20T12:00:00Z', source: [],
      data: {
        title: 'Meu guarda-roupa', subtitle: 'Dados atualizados agora',
        data: { total: 2, items: [
          { id: 1, revision: 1, name: 'Camiseta azul', category: 'camiseta', image: { url: '/api/fashion/assets/8' }, external_url: 'https://loja.example.com/camiseta' },
          { id: 2, revision: 1, name: 'Saia preta', category: 'saia', image: null, external_url: 'javascript:alert(1)' },
        ] },
      },
    }

    const html = renderToStaticMarkup(<ChatObjectRenderer object={object}/>)
    expect(html).toContain('Meu guarda-roupa')
    expect(html).toContain('Camiseta azul')
    expect(html).toContain('Saia preta')
    expect(html).toContain('src="/api/fashion/assets/8"')
    expect(html).toContain('aria-label="Editar Camiseta azul"')
    expect(html).toContain('aria-label="Excluir Camiseta azul"')
    expect(html).not.toContain('<span>Editar</span>')
    expect(html).not.toContain('<span>Excluir</span>')
    expect(html).toContain('href="https://loja.example.com/camiseta"')
    expect(html).toContain('aria-label="Acessar link de Camiseta azul"')
    expect(html).not.toContain('<span>Acessar</span>')
    expect(html).not.toContain('javascript:alert')
  })
})
