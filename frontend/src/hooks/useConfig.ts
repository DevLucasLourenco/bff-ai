import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Memory, ModelConfig, Persona, Provider, Settings } from '../lib/types'

/**
 * Configuração do app (settings, personas, memórias, providers, modelos).
 *
 * Separado de `App.tsx` (F7.1): o componente concentrava sete useState, o
 * carregamento, o streaming e o tratamento de erro, e cada feature nova entrava
 * no mesmo arquivo.
 */
export function useConfig(onError: (error: unknown) => void) {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [providers, setProviders] = useState<Provider[]>([])
  const [memories, setMemories] = useState<Memory[]>([])
  const [models, setModels] = useState<ModelConfig[]>([])

  const refresh = useCallback(async () => {
    const [s, p, mem, pr, m] = await Promise.all([
      api.settings(), api.personas(), api.memories(), api.providers(), api.models(),
    ])
    setSettings(s); setPersonas(p); setMemories(mem); setProviders(pr); setModels(m)
  }, [])

  useEffect(() => {
    let cancelled = false
    refresh().catch(error => { if (!cancelled) onError(error) })
    return () => { cancelled = true }
    // onError é estável no App (useCallback); refresh também.
  }, [refresh, onError])

  return { settings, personas, providers, memories, models, refresh }
}
