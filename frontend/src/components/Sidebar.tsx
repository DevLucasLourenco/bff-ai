import { Heart, MessageCircleMore, Plus, Settings, Trash2 } from 'lucide-react'
import type { Conversation } from '../lib/types'

type Props = {
  conversations: Conversation[]
  activeId: number | null
  appName: string
  onNew: () => void
  onSelect: (id: number) => void
  onArchive: (id: number) => void
  onOpenSettings: () => void
}

export function Sidebar({ conversations, activeId, appName, onNew, onSelect, onArchive, onOpenSettings }: Props) {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark"><Heart size={18} fill="currentColor"/></span><strong>{appName}</strong></div>
    <button className="new-chat" onClick={onNew}><Plus size={18}/> Nova conversa</button>
    <div className="conversation-list">
      {conversations.map(c => <div className={`conversation-row ${activeId === c.id ? 'active' : ''}`} key={c.id}>
        <button onClick={() => onSelect(c.id)} className="conversation-main">
          <MessageCircleMore size={16}/><span>{c.title}</span>
        </button>
        <button className="icon-button subtle" aria-label="Arquivar conversa" onClick={() => onArchive(c.id)}><Trash2 size={15}/></button>
      </div>)}
      {conversations.length === 0 && <div className="empty-sidebar">Suas conversas vão aparecer aqui.</div>}
    </div>
    <button className="settings-link" onClick={onOpenSettings}><Settings size={18}/> Configurações</button>
  </aside>
}
