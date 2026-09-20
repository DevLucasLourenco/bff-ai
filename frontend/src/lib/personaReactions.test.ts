import { describe, expect, it } from 'vitest'
import { classifyReaction, listeningReaction, reactionText, streamingReaction } from './personaReactions'
import { CHARACTERS, REACTION_LABELS, characterImage, characterReactionCount } from './personaVisuals'

describe('catálogo de personagens', () => {
  it('publica somente as 34 poses da nova Morena', () => {
    expect(CHARACTERS).toEqual([{ id: 'morena', label: 'Morena' }])
    expect(Object.keys(REACTION_LABELS)).toHaveLength(34)
    for (const character of CHARACTERS) {
      expect(characterReactionCount(character.id)).toBe(34)
      for (const reaction of Object.keys(REACTION_LABELS) as (keyof typeof REACTION_LABELS)[]) {
        expect(characterImage(character.id, reaction)).toMatch(/bff_reactions\/morena\/\d{2}_.+\.png/)
      }
    }
    expect(characterImage(null, 'feliz_sorrindo')).toBeNull()
    expect(characterImage('loira', 'feliz_sorrindo')).toMatch(/bff_reactions\/morena\/09_feliz_sorrindo\.png/)
  })
})

describe('reações durante a conversa', () => {
  it('acompanha a frase mais recente numa mesma resposta', () => {
    expect(streamingReaction('Lendo sua mensagem')).toBeNull()
    expect(streamingReaction('Parabéns!')).toBe('comemorando')
    expect(streamingReaction('Parabéns! Agora vamos resolver isso.')).toBe('vamos_resolver_isso')
    expect(reactionText('Parabéns! Agora vamos resolver isso.')).toBe('Agora vamos resolver isso.')
    expect(classifyReaction('Parabéns! Agora vamos resolver isso.')).toBe('vamos_resolver_isso')
  })

  it('prioriza acolhimento e usa pose neutra sem sinal claro', () => {
    expect(classifyReaction('Sinto muito que isso tenha acontecido com você.')).toBe('confortando')
    expect(classifyReaction('Parabéns! Você conseguiu terminar essa etapa.')).toBe('comemorando')
    expect(classifyReaction('Aqui está a lista solicitada.')).toBe('feliz_sorrindo')
  })

  it('troca uma resposta curta para a reação contextual assim que ela termina', () => {
    expect(streamingReaction('Parabéns!')).toBe('comemorando')
    expect(streamingReaction('Sinto muito.')).toBe('confortando')
  })

  it('usa poses existentes para erro e confidência', () => {
    expect(classifyReaction('Ops, errei.')).toBe('pedindo_desculpas')
    expect(classifyReaction('Vou te contar um segredo.')).toBe('piscando_brincando')
  })

  it('reage à mensagem recebida quando há sinais explícitos', () => {
    expect(listeningReaction('Consegui passar!')).toBe('comemorando')
    expect(listeningReaction('Estou triste hoje')).toBe('confortando')
    expect(listeningReaction('Qual você escolheria?')).toBe('curiosa')
    expect(listeningReaction('Oi')).toBe('escutando_atenta')
  })
})
