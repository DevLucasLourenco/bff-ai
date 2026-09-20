import type { Reaction } from './personaVisuals'

/**
 * Regras conservadoras sobre o texto da assistente. A primeira frase completa
 * (ou os primeiros 140 caracteres) fixa a pose, inclusive durante o stream.
 * Assim o histórico e o stream usam o mesmo trecho e a imagem não pisca.
 */
export function reactionText(text: string, complete = true): string | null {
  const clean = text.replace(/[#*_`>\[\]]/g, '').trim()
  const firstSentence = clean.match(/^.{35,}?[.!?](?=\s|$)/s)
  if (firstSentence && firstSentence[0].length <= 140) return firstSentence[0]
  if (clean.length >= 140) return clean.slice(0, 140)
  return complete ? clean : null
}

export function classifyReaction(text: string): Reaction {
  const sample = (reactionText(text) ?? '').toLocaleLowerCase('pt-BR')
  if (/sinto muito|lamento|imagino que (seja|esteja|isso)|estou aqui com você|que situação difícil|você não está sozinha/.test(sample)) return 'confortando'
  if (/me desculp|peço desculp|perdão/.test(sample)) return 'pedindo_desculpas'
  if (/ops|cometi um erro|errei|corrigindo/.test(sample)) return 'ops_erro_leve'
  if (/parabéns|conseguimos|você conseguiu|vamos comemorar|que conquista/.test(sample)) return 'comemorando'
  if (/ficou incrível|ficou lindo|amei (seu|sua)|arrasou/.test(sample)) return 'elogiando_usuario'
  if (/você consegue|vai dar certo|acredito em você/.test(sample)) return 'motivando_incentivando'
  if (/vamos resolver|vamos por partes|vamos encontrar uma solução/.test(sample)) return 'vamos_resolver_isso'
  if (/não entendi|pode esclarecer|me explica melhor/.test(sample)) return 'nao_entendi'
  if (/não tenho certeza|talvez|depende do contexto/.test(sample)) return 'pensativa'
  if (/uau|nossa|que surpresa/.test(sample)) return 'surpresa'
  if (/tive uma ideia|que tal se|uma ideia é/.test(sample)) return 'tive_uma_ideia'
  if (/hahaha|kkkk|rsrs/.test(sample)) return 'rindo'
  if (/que ótimo|que bom|adorei/.test(sample)) return 'feliz_sorrindo'
  if (/vou explicar|funciona assim|primeiro,|em resumo|passo a passo/.test(sample)) return 'explicando_algo'
  return 'feliz_sorrindo'
}

export function streamingReaction(text: string): Reaction {
  return reactionText(text, false) ? classifyReaction(text) : 'analisando'
}
