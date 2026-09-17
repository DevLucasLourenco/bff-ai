import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { Markdown } from './Markdown'

// renderToStaticMarkup não precisa de DOM: dá para verificar a saída sem jsdom.
const render = (text: string) => renderToStaticMarkup(<Markdown text={text}/>)

describe('Markdown', () => {
  it('renderiza bloco de código com a linguagem', () => {
    const html = render('Olha:\n\n```python\nprint("oi")\n```')
    expect(html).toContain('<pre>')
    expect(html).toContain('print(&quot;oi&quot;)')
    expect(html).toContain('python')
  })

  it('renderiza ênfase, código inline e listas', () => {
    const html = render('**forte** e *leve* com `codigo`\n\n- um\n- dois')
    expect(html).toContain('<strong>forte</strong>')
    expect(html).toContain('<em>leve</em>')
    expect(html).toContain('class="inline-code"')
    expect(html).toContain('<li>um</li>')
  })

  it('renderiza lista numerada e citação', () => {
    expect(render('1. primeiro\n2. segundo')).toContain('<ol>')
    expect(render('> pensa nisso')).toContain('<blockquote>')
  })

  it('escapa HTML vindo do modelo em vez de executá-lo', () => {
    // O renderer monta elementos React, nunca string de HTML: não existe
    // dangerouslySetInnerHTML no componente.
    const html = render('<img src=x onerror="alert(1)">')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })

  it('só transforma em link o que for http(s)', () => {
    expect(render('[site](https://exemplo.test)')).toContain('href="https://exemplo.test"')
    const perigoso = render('[clica](javascript:alert(1))')
    expect(perigoso).not.toContain('href="javascript')
    expect(perigoso).toContain('[clica]')
  })

  it('links externos levam rel de segurança', () => {
    expect(render('[site](https://exemplo.test)')).toContain('rel="noopener noreferrer"')
  })

  it('não quebra com bloco de código ainda aberto durante o streaming', () => {
    // Enquanto os tokens chegam, a cerca de fechamento ainda não existe.
    const html = render('texto\n\n```ts\nconst a = 1')
    expect(html).toContain('const a = 1')
  })
})
