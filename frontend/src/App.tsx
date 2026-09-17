import { useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatView } from './features/chat/ChatView'
import { SettingsPanel } from './features/settings/SettingsPanel'
import { api, streamMessage } from './lib/api'
import type { Conversation, Memory, ModelConfig, Persona, Provider, Settings } from './lib/types'
import './styles.css'

export default function App() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [providers, setProviders] = useState<Provider[]>([])
  const [memories, setMemories] = useState<Memory[]>([])
  const [models, setModels] = useState<ModelConfig[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [active, setActive] = useState<Conversation | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [sending, setSending] = useState(false)
  const [toast, setToast] = useState('')

  const refreshConfig = async () => {
    const [s, p, mem, pr, m] = await Promise.all([api.settings(), api.personas(), api.memories(), api.providers(), api.models()])
    setSettings(s); setPersonas(p); setMemories(mem); setProviders(pr); setModels(m)
  }
  const refreshConversations = async () => setConversations(await api.conversations())

  useEffect(() => {
    let cancelled = false

    async function loadInitialData() {
      try {
        await Promise.all([refreshConfig(), refreshConversations()])
      } catch (e) {
        if (!cancelled) setToast(e instanceof Error ? e.message : String(e))
      }
    }

    void loadInitialData()
    return () => { cancelled = true }
  }, [])

  const openConversation = async (id: number) => setActive(await api.conversation(id))
  const createConversation = async () => {
    const c = await api.createConversation()
    await refreshConversations(); setActive(c)
  }
  const archive = async (id: number) => {
    await api.archiveConversation(id)
    if (active?.id === id) setActive(null)
    await refreshConversations()
  }
  const send = async (content: string) => {
    if (!active) return
    const optimisticUser = { id: -Date.now(), role: 'user' as const, content }
    const optimisticAssistant = { id: -(Date.now()+1), role: 'assistant' as const, content: '' }
    setActive(prev => prev ? { ...prev, messages: [...prev.messages, optimisticUser, optimisticAssistant] } : prev)
    setSending(true); setToast('')
    let generated = ''
    try {
      await streamMessage(active.id, content, {
        onToken: token => {
          generated += token
          setActive(prev => prev ? { ...prev, messages: prev.messages.map(m => m.id === optimisticAssistant.id ? { ...m, content: generated } : m) } : prev)
        },
        onDone: () => {},
        onError: message => { throw new Error(message) },
      })
      setActive(await api.conversation(active.id))
      await refreshConversations()
    } catch (e) {
      setToast(e instanceof Error ? e.message : String(e))
      setActive(await api.conversation(active.id))
    } finally { setSending(false) }
  }

  return <div className="app-shell">
    <Sidebar conversations={conversations} activeId={active?.id ?? null} appName={settings?.app_name || 'BFF AI'} onNew={createConversation} onSelect={openConversation} onArchive={archive} onOpenSettings={() => setSettingsOpen(true)}/>
    <ChatView conversation={active} sending={sending} onSend={send}/>
    <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} settings={settings} personas={personas} memories={memories} providers={providers} models={models} onChanged={refreshConfig}/>
    {toast && <div className="toast" onClick={() => setToast('')}>{toast}</div>}
  </div>
}
