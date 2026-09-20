import { useCallback, useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ChatView } from './features/chat/ChatView'
import { SettingsPanel } from './features/settings/SettingsPanel'
import { useChatStream } from './hooks/useChatStream'
import { useConfig } from './hooks/useConfig'
import { useConversations } from './hooks/useConversations'
import { api, toApiError } from './lib/api'
import { applyTheme } from './lib/theme'
import type { ApiError } from './lib/types'
import './styles.css'

/**
 * Composição (F7.1). O estado saiu daqui para hooks por domínio — este arquivo
 * concentrava sete useState, o carregamento, o streaming e o tratamento de erro.
 */
export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatError, setChatError] = useState<ApiError | null>(null)
  const [configError, setConfigError] = useState<ApiError | null>(null)

  const reportConfigError = useCallback((error: unknown) => setConfigError(toApiError(error)), [])
  const config = useConfig(reportConfigError)
  const theme = config.settings?.theme
  useEffect(() => { if (theme) applyTheme(theme) }, [theme])
  const conversations = useConversations(reportConfigError)
  const { reloadActive, refreshList, setActive } = conversations
  const refreshConfiguration = useCallback(async () => {
    await config.refresh()
    await refreshList()
    if (conversations.active?.id) await reloadActive(conversations.active.id)
  }, [config.refresh, refreshList, reloadActive, conversations.active?.id])

  const onSettled = useCallback(async (conversationId: number) => {
    // Recarrega do servidor: é lá que está a verdade sobre o que foi persistido,
    // inclusive uma resposta parcial marcada como interrompida.
    const fresh = await reloadActive(conversationId)
    setActive(current => (current?.id === conversationId ? fresh : current))
    await refreshList()
  }, [reloadActive, refreshList, setActive])

  const chat = useChatStream({ onSettled, onError: setChatError })
  // O stream só aparece na conversa a que pertence. Em outra conversa, o
  // composer fica livre: mandar ali interrompe o stream anterior, que é salvo
  // como "cancelled" (nada se perde).
  const streamingHere = chat.isStreaming && chat.streamingConversationId === conversations.active?.id

  const send = useCallback(async (content: string, attachment: File | null) => {
    if (!conversations.active) return false
    setChatError(null)
    if (attachment && config.models?.find(model => model.id === conversations.active?.model_config_id)?.supports_tools === false) {
      setChatError({ code: 'fashion_tools_disabled', message: 'Ative as ferramentas Fashion neste modelo para analisar fotos pelo chat.' })
      return false
    }
    try {
      const asset = attachment ? await api.uploadFashionAsset(attachment) : null
      const error = await chat.send(conversations.active.id, content, asset ? [asset.id] : [])
      return !error || !['http_422', 'http_409', 'http_404', 'validation_error'].includes(error.code)
    } catch (error) { setChatError(toApiError(error)); return false }
  }, [chat, config.models, conversations.active])

  const regenerate = useCallback((messageId: number) => {
    if (!conversations.active) return
    setChatError(null)
    void chat.regenerate(conversations.active.id, messageId)
  }, [chat, conversations.active])

  return <div className="app-shell">
    <Sidebar
      conversations={conversations.conversations}
      activeId={conversations.active?.id ?? null}
      appName={config.settings?.app_name || 'BFF AI'}
      onNew={conversations.create}
      onSelect={conversations.open}
      onArchive={conversations.archive}
      onOpenSettings={() => setSettingsOpen(true)}
    />

    <ChatView
      conversation={conversations.active}
      streaming={streamingHere}
      buffer={chat.buffer}
      pendingUserMessage={streamingHere ? chat.pendingUserMessage : null}
      error={chatError}
      onSend={send}
      onStop={chat.stop}
      onRegenerate={regenerate}
      onDismissError={() => setChatError(null)}
    />

    <SettingsPanel
      open={settingsOpen}
      onClose={() => setSettingsOpen(false)}
      settings={config.settings}
      personas={config.personas}
      memories={config.memories}
      providers={config.providers}
      models={config.models}
      conversations={conversations.conversations}
      onChanged={refreshConfiguration}
    />

    {/* Toast só para o que não pertence a uma conversa; erro de chat fica ancorado na bolha. */}
    {configError && <div className="toast" role="status" onClick={() => setConfigError(null)}>{configError.message}</div>}
  </div>
}
