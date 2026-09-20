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

export const REACTION_LABELS = {
  feliz_sorrindo: 'Sorrindo',
  rindo: 'Rindo',
  muito_empolgada: 'Muito animada',
  piscando_brincando: 'Brincando',
  carinhosa_fofa: 'Carinhosa',
  apaixonada_encantada: 'Encantada',
  aprovando_concordando: 'Concordando',
  surpresa: 'Surpresa',
  chocada: 'Chocada',
  confusa: 'Confusa',
  pensativa: 'Pensativa',
  curiosa: 'Curiosa',
  concentrada_seria: 'Concentrada',
  negando_desaprovando: 'Discordando',
  envergonhada_timida: 'Tímida',
  triste_chateada: 'Chateada',
  brava_irritada: 'Irritada',
  frustrada: 'Frustrada',
  preocupada_ansiosa: 'Preocupada',
  com_medo_assustada: 'Assustada',
  cansada_com_sono: 'Cansada',
  entediada: 'Entediada',
  pedindo_desculpas: 'Pedindo desculpas',
  ops_erro_leve: 'Ops!',
  comemorando: 'Comemorando',
  tive_uma_ideia: 'Tive uma ideia',
  explicando_algo: 'Explicando',
  escutando_atenta: 'Ouvindo você',
  entendi: 'Entendi',
  nao_entendi: 'Não entendi',
  elogiando_usuario: 'Te elogiando',
  motivando_incentivando: 'Te incentivando',
  confortando: 'Te acolhendo',
  vamos_resolver_isso: 'Vamos resolver',
  analisando: 'Analisando',
  segredo_sussurro: 'Contando um segredo',
} as const

export type Reaction = keyof typeof REACTION_LABELS

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
