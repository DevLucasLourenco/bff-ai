import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import type { Conversation } from '../lib/types'

/** Lista de conversas + a conversa aberta (F7.1). */
export function useConversations(onError: (error: unknown) => void) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [active, setActive] = useState<Conversation | null>(null)

  const refreshList = useCallback(async () => setConversations(await api.conversations()), [])

  const reloadActive = useCallback(async (id: number) => {
    const fresh = await api.conversation(id)
    setActive(current => (current && current.id !== id ? current : fresh))
    return fresh
  }, [])

  const open = useCallback(async (id: number) => {
    try { setActive(await api.conversation(id)) } catch (error) { onError(error) }
  }, [onError])

  const create = useCallback(async () => {
    try {
      const created = await api.createConversation()
      await refreshList()
      setActive(created)
    } catch (error) { onError(error) }
  }, [onError, refreshList])

  const archive = useCallback(async (id: number) => {
    try {
      await api.archiveConversation(id)
      setActive(current => (current?.id === id ? null : current))
      await refreshList()
    } catch (error) { onError(error) }
  }, [onError, refreshList])

  useEffect(() => {
    let cancelled = false
    refreshList().catch(error => { if (!cancelled) onError(error) })
    return () => { cancelled = true }
  }, [refreshList, onError])

  return { conversations, active, setActive, refreshList, reloadActive, open, create, archive }
}
