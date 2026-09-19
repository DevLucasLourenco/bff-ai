import type { ThemeName } from './types'

/**
 * Aplicação do tema.
 *
 * A fonte da verdade é a setting `theme` no banco. O localStorage guarda só uma
 * cópia para o script inline do index.html conseguir pintar o tema certo antes
 * de o React carregar e as settings chegarem da API — sem ele, quem usa o tema
 * escuro veria um lampejo claro a cada abertura.
 */

export const THEME_CACHE_KEY = 'bff-ai:theme'

const THEME_COLOR = { light: '#ece2e9', dark: '#2b2129' } as const

export function applyTheme(theme: ThemeName): void {
  const root = document.documentElement
  if (theme === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', theme)

  const efetivo = theme === 'system'
    ? (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', THEME_COLOR[efetivo])

  try {
    localStorage.setItem(THEME_CACHE_KEY, theme)
  } catch {
    // Modo privado ou armazenamento bloqueado: o tema continua certo nesta
    // sessão, só perde o pré-carregamento na próxima.
  }
}
