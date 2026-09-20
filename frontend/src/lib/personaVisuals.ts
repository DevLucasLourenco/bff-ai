/** O catálogo ativo contém somente as novas reações da Morena. */
export const CHARACTERS = [
  { id: 'morena', label: 'Morena' },
] as const

export type AvatarCharacter = typeof CHARACTERS[number]['id']

// Vite publica os PNGs como arquivos separados; o navegador só baixa os que
// aparecem na tela. A pasta antiga fica no repositório, fora deste import.
const imageUrls = import.meta.glob<string>(
  '../assets/bff_reactions/morena/*.png',
  { eager: true, query: '?url', import: 'default' },
)
const imageCatalog = new Map<string, string>()
for (const [path, url] of Object.entries(imageUrls)) {
  const match = path.match(/\/morena\/\d{2}_(.+)\.png$/)
  if (!match) continue
  imageCatalog.set(match[1], url)
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
} as const

export type Reaction = keyof typeof REACTION_LABELS

export function characterImage(character: string | null | undefined, reaction: Reaction): string | null {
  // Durante uma atualização, uma resposta antiga da API ainda pode trazer outro
  // identificador. Qualquer visual ativo usa exclusivamente o catálogo novo.
  if (!character) return null
  return imageCatalog.get(reaction) ?? null
}

export function characterReactionCount(character: AvatarCharacter): number {
  return character === 'morena' ? imageCatalog.size : 0
}

export function characterLabel(character: AvatarCharacter): string {
  return CHARACTERS.find(option => option.id === character)?.label ?? character
}
