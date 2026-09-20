/** As chaves seguem os diretórios do pacote de reações já incluído no projeto. */
export const CHARACTERS = [
  { id: 'morena', label: 'Morena' },
  { id: 'loira', label: 'Loira' },
  { id: 'ruiva', label: 'Ruiva' },
  { id: 'japonesa_oriental', label: 'Japonesa oriental' },
  { id: 'cabelos_brancos', label: 'Cabelos brancos' },
  { id: 'fashionista', label: 'Fashionista' },
  { id: 'lobinha_spooky', label: 'Lobinha spooky' },
  { id: 'vampirinha_gotica', label: 'Vampirinha gótica' },
] as const

export type AvatarCharacter = typeof CHARACTERS[number]['id']

// Vite publica os PNGs como arquivos separados; o navegador só baixa os que
// aparecem na tela. O catálogo inclui as 36 poses de cada personagem.
const imageUrls = import.meta.glob<string>(
  '../assets/bff_ai_reacoes_individuais/bff_ai_reacoes_individuais/por_personagem/*/*.png',
  { eager: true, query: '?url', import: 'default' },
)
const imageCatalog = new Map<string, Map<string, string>>()
for (const [path, url] of Object.entries(imageUrls)) {
  const match = path.match(/\/por_personagem\/([^/]+)\/\d{2}_(.+)\.png$/)
  if (!match) continue
  if (!imageCatalog.has(match[1])) imageCatalog.set(match[1], new Map())
  imageCatalog.get(match[1])?.set(match[2], url)
}

export type Reaction =
  | 'feliz_sorrindo' | 'rindo' | 'muito_empolgada' | 'surpresa'
  | 'pensativa' | 'confusa' | 'pedindo_desculpas' | 'ops_erro_leve'
  | 'comemorando' | 'tive_uma_ideia' | 'explicando_algo'
  | 'escutando_atenta' | 'nao_entendi' | 'elogiando_usuario'
  | 'motivando_incentivando' | 'confortando' | 'vamos_resolver_isso'
  | 'analisando'

export function characterImage(character: AvatarCharacter | null | undefined, reaction: Reaction): string | null {
  if (!character) return null
  return imageCatalog.get(character)?.get(reaction) ?? null
}

export function characterReactionCount(character: AvatarCharacter): number {
  return imageCatalog.get(character)?.size ?? 0
}

export function characterLabel(character: AvatarCharacter): string {
  return CHARACTERS.find(option => option.id === character)?.label ?? character
}
