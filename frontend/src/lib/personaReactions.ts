import type { Reaction } from './personaVisuals'

/** Só frases explícitas mudam para poses expressivas; o restante usa explicação. */
const RULES: { reaction: Reaction; pattern: RegExp }[] = [
  { reaction: 'confortando', pattern: /sinto muito|lamento|estou aqui com voce|que situacao dificil|voce nao esta sozinha|imagino como isso (doi|pesa)/ },
  { reaction: 'pedindo_desculpas', pattern: /me desculp|peco desculp|perdao/ },
  { reaction: 'ops_erro_leve', pattern: /\bops\b|cometi um erro|errei|vou corrigir/ },
  { reaction: 'comemorando', pattern: /parabens|voce conseguiu|conseguimos|vamos comemorar|que conquista/ },
  { reaction: 'elogiando_usuario', pattern: /ficou incrivel|ficou lindo|arrasou|amei (seu|sua)|mandou muito bem/ },
  { reaction: 'motivando_incentivando', pattern: /voce consegue|vai dar certo|acredito em voce|nao desista/ },
  { reaction: 'vamos_resolver_isso', pattern: /vamos resolver|vamos por partes|encontrar uma solucao|vamos consertar/ },
  { reaction: 'nao_entendi', pattern: /nao entendi|pode esclarecer|me explica melhor/ },
  { reaction: 'segredo_sussurro', pattern: /entre nos|um segredinho|vou te contar um segredo/ },
  { reaction: 'tive_uma_ideia', pattern: /tive uma ideia|que tal se|uma ideia (e|seria)|pensei numa coisa/ },
  { reaction: 'chocada', pattern: /estou chocada|que choque|nao acredito nisso/ },
  { reaction: 'surpresa', pattern: /\buau\b|\bnossa\b|que surpresa/ },
  { reaction: 'muito_empolgada', pattern: /mal posso esperar|estou muito animada|que empolgante/ },
  { reaction: 'rindo', pattern: /hahaha|kkkk|rsrs/ },
  { reaction: 'piscando_brincando', pattern: /brincadeira|to brincando|so pra provocar/ },
  { reaction: 'carinhosa_fofa', pattern: /com carinho|um abraco|que fof[ao]/ },
  { reaction: 'apaixonada_encantada', pattern: /apaixonada|encantada|amei demais/ },
  { reaction: 'aprovando_concordando', pattern: /concordo|exatamente isso|boa escolha/ },
  { reaction: 'entendi', pattern: /entendi agora|agora entendi|faz sentido/ },
  { reaction: 'confusa', pattern: /isso me confundiu|fiquei confusa|nao faz sentido/ },
  { reaction: 'pensativa', pattern: /nao tenho certeza|talvez|depende do contexto|deixa eu pensar/ },
  { reaction: 'curiosa', pattern: /me conta mais|fiquei curiosa|como assim/ },
  { reaction: 'concentrada_seria', pattern: /precisamos ter cuidado|isso e serio|vamos examinar/ },
  { reaction: 'negando_desaprovando', pattern: /nao posso concordar|nao recomendo|melhor evitar/ },
  { reaction: 'envergonhada_timida', pattern: /fiquei sem graca|que vergonha/ },
  { reaction: 'triste_chateada', pattern: /estou triste|fiquei chateada/ },
  { reaction: 'brava_irritada', pattern: /isso me irrita|fiquei brava/ },
  { reaction: 'frustrada', pattern: /que frustrante|isso e frustrante/ },
  { reaction: 'preocupada_ansiosa', pattern: /estou preocupada|isso me preocupa/ },
  { reaction: 'com_medo_assustada', pattern: /fiquei assustada|isso assusta/ },
  { reaction: 'cansada_com_sono', pattern: /estou cansada|que sono/ },
  { reaction: 'entediada', pattern: /que tedio|estou entediada/ },
  { reaction: 'analisando', pattern: /vou analisar|estou analisando|deixa eu verificar/ },
  { reaction: 'explicando_algo', pattern: /vou explicar|funciona assim|passo a passo|em resumo|primeiro,/ },
  { reaction: 'feliz_sorrindo', pattern: /que bom|que otimo|adorei/ },
]

function normalize(value: string): string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
}

/** Fragmentos são separados por fim de frase ou linha; URLs não são cortadas. */
function segments(text: string): string[] {
  return text.replace(/```[\s\S]*?```/g, ' ').replace(/[#*_`>\[\]]/g, '')
    .split(/(?<=[.!?])\s+|\n+/).map(part => part.trim()).filter(Boolean)
}

function explicitReaction(text: string): Reaction | null {
  const sample = normalize(text)
  return RULES.find(rule => rule.pattern.test(sample))?.reaction ?? null
}

/** Trecho atual: o stream pode mudar de pose várias vezes numa resposta longa. */
export function reactionText(text: string): string | null {
  return segments(text).at(-1) ?? null
}

/** Um trecho curto sem sinal explícito conserva a pose anterior durante o stream. */
export function streamingReaction(text: string): Reaction | null {
  const latest = reactionText(text)
  if (!latest) return null
  return explicitReaction(latest) ?? (latest.length >= 32 ? 'explicando_algo' : null)
}

/** Reproduz no histórico a última reação relevante do turno. */
export function classifyReaction(text: string): Reaction {
  const parts = segments(text)
  const latest = parts.at(-1) ?? ''
  const current = explicitReaction(latest)
  if (current) return current
  if (latest.length >= 32) return 'explicando_algo'
  for (let index = parts.length - 2; index >= 0; index--) {
    const previous = explicitReaction(parts[index])
    if (previous) return previous
  }
  return 'feliz_sorrindo'
}

/** Reação imediata à mensagem, somente para sinais explícitos da usuária. */
export function listeningReaction(text: string | null): Reaction {
  if (!text) return 'escutando_atenta'
  const sample = normalize(text)
  if (/consegui|deu certo|passei|parabens/.test(sample)) return 'comemorando'
  if (/estou triste|to triste|chateada|ansiosa|com medo|perdi alguem/.test(sample)) return 'confortando'
  if (/hahaha|kkkk|rsrs/.test(sample)) return 'rindo'
  if (/me ajuda|preciso de ajuda|deu errado|nao funciona/.test(sample)) return 'vamos_resolver_isso'
  if (/\?/.test(sample)) return 'curiosa'
  return 'escutando_atenta'
}
