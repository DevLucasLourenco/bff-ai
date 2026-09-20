import { describe, expect, it } from 'vitest'
import { classifyReaction, reactionText, streamingReaction } from './personaReactions'
import { CHARACTERS, characterImage, characterReactionCount } from './personaVisuals'

describe('catálogo de personagens', () => {
  it('publica as 36 poses de cada uma das oito personagens', () => {
    expect(CHARACTERS).toHaveLength(8)
    for (const character of CHARACTERS) {
      expect(characterReactionCount(character.id)).toBe(36)
      for (const reaction of ['feliz_sorrindo', 'escutando_atenta', 'analisando', 'confortando'] as const) {
        expect(characterImage(character.id, reaction)).toMatch(/\.png/)
      }
    }
  })
})

describe('reações durante a conversa', () => {
  it('usa uma pose estável quando a primeira frase se completa', () => {
    const sentence = 'Vamos por partes para resolver essa situação.'
    expect(reactionText(sentence.slice(0, 20), false)).toBeNull()
    expect(streamingReaction(sentence.slice(0, 20))).toBe('analisando')
    expect(streamingReaction(sentence)).toBe('vamos_resolver_isso')
    expect(classifyReaction(`${sentence} Depois explico os detalhes.`)).toBe(streamingReaction(sentence))
  })

  it('prioriza acolhimento e usa pose neutra sem sinal claro', () => {
    expect(classifyReaction('Sinto muito que isso tenha acontecido com você.')).toBe('confortando')
    expect(classifyReaction('Parabéns! Você conseguiu terminar essa etapa.')).toBe('comemorando')
    expect(classifyReaction('Aqui está a lista solicitada.')).toBe('feliz_sorrindo')
  })
})
