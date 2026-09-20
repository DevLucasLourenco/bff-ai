import { describe, expect, it } from 'vitest'
import { classifyReaction, listeningReaction, reactionText, streamingReaction } from './personaReactions'
import { CHARACTERS, REACTION_LABELS, characterImage, characterReactionCount } from './personaVisuals'

describe('catálogo de personagens', () => {
  it('publica as 36 poses de cada uma das oito personagens', () => {
    expect(CHARACTERS).toHaveLength(8)
    for (const character of CHARACTERS) {
      expect(characterReactionCount(character.id)).toBe(36)
      for (const reaction of Object.keys(REACTION_LABELS) as (keyof typeof REACTION_LABELS)[]) {
        expect(characterImage(character.id, reaction)).toMatch(/\.png/)
      }
    }
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

  it('reage à mensagem recebida quando há sinais explícitos', () => {
    expect(listeningReaction('Consegui passar!')).toBe('comemorando')
    expect(listeningReaction('Estou triste hoje')).toBe('confortando')
    expect(listeningReaction('Qual você escolheria?')).toBe('curiosa')
    expect(listeningReaction('Oi')).toBe('escutando_atenta')
  })
})
