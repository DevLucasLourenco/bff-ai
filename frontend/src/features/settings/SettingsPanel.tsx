import { Check, KeyRound, Plus, RefreshCw, Save, Trash2, X } from 'lucide-react'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../../lib/api'
import type { Conversation, Memory, MemoryScope, ModelConfig, Persona, Provider, Settings, ThemeName } from '../../lib/types'
import { PersonaEditor } from './PersonaEditor'
import { FashionPanel } from '../fashion/FashionPanel'

type Tab = 'general' | 'models' | 'personas' | 'memories' | 'fashion'

export function SettingsPanel({ open, onClose, settings, personas, memories, providers, models, conversations, onChanged }: {
  open: boolean
  onClose: () => void
  settings: Settings | null
  personas: Persona[]
  memories: Memory[]
  providers: Provider[]
  models: ModelConfig[]
  conversations: Conversation[]
  onChanged: () => Promise<void>
}) {
  const [tab, setTab] = useState<Tab>('general')
  const [busy, setBusy] = useState(false)
  const [remote, setRemote] = useState<Record<number, string[]>>({})
  const [providerKeys, setProviderKeys] = useState<Record<number, string>>({})
  const [error, setError] = useState('')
  const [editingPersonaId, setEditingPersonaId] = useState<number | null>(null)
  const [memoryScope, setMemoryScope] = useState<MemoryScope>('global')
  const editingPersona = useMemo(() => personas.find(p => p.id === editingPersonaId) ?? personas[0] ?? null, [editingPersonaId, personas])

  useEffect(() => {
    if (!open) { setError(''); setRemote({}); setProviderKeys({}) }
  }, [open])
  useEffect(() => {
    if (editingPersona && editingPersonaId === null) setEditingPersonaId(editingPersona.id)
  }, [editingPersona, editingPersonaId])
  if (!open || !settings) return null

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError('')
    try { await fn() } catch (e) { setError(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }
  const saveSetting = (payload: Partial<Settings>) => run(async () => { await api.updateSettings(payload); await onChanged() })
  const loadRemote = (provider: Provider) => run(async () => {
    const data = await api.remoteModels(provider.id)
    setRemote(r => ({ ...r, [provider.id]: data }))
  })
  const saveProviderKey = (provider: Provider) => run(async () => {
    const key = providerKeys[provider.id] ?? ''
    await api.updateProvider(provider.id, key ? { api_key: key } : { clear_api_key: true })
    setProviderKeys(s => ({ ...s, [provider.id]: '' }))
    await onChanged()
  })
  const createPersona = () => run(async () => {
    const created = await api.createPersona({
      name: `Nova persona ${personas.length + 1}`,
      description: 'Nova personalidade configurável.',
      greeting: 'Oi! 💗',
      avatar_emoji: '💗',
    })
    await onChanged(); setEditingPersonaId(created.id)
  })
  const savePersona = (payload: Partial<Persona>) => run(async () => {
    if (!editingPersona) return
    await api.updatePersona(editingPersona.id, payload)
    await onChanged()
  })
  const addMemory = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    const scope = String(data.get('scope') || 'global') as MemoryScope
    const alvo = data.get('target') ? Number(data.get('target')) : null
    run(async () => {
      await api.createMemory({
        category: String(data.get('category') || 'general'),
        content: String(data.get('content') || ''),
        scope,
        persona_id: scope === 'persona' ? alvo : null,
        conversation_id: scope === 'conversation' ? alvo : null,
      })
      form.reset(); setMemoryScope('global'); await onChanged()
    })
  }

  return <div className="overlay" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
    <section className="settings-panel">
      <header><div><h2>Configurações</h2><p>Comportamento, modelos e memória persistidos no SQLite.</p></div><button className="icon-button" onClick={onClose}><X/></button></header>
      <nav className="settings-tabs">
        <button className={tab==='general'?'active':''} onClick={() => setTab('general')}>Geral</button>
        <button className={tab==='models'?'active':''} onClick={() => setTab('models')}>LLM</button>
        <button className={tab==='personas'?'active':''} onClick={() => setTab('personas')}>Personas</button>
        <button className={tab==='memories'?'active':''} onClick={() => setTab('memories')}>Memórias</button>
        <button className={tab==='fashion'?'active':''} onClick={() => setTab('fashion')}>Fashion</button>
      </nav>
      <div className="settings-body">
        {error && <div className="error-box">{error}</div>}

        {tab === 'general' && <div className="settings-stack">
          <label>Nome do app<input defaultValue={settings.app_name} onBlur={e => saveSetting({ app_name: e.target.value })}/></label>
          <label>Como chamar a usuária<input defaultValue={settings.user_display_name} placeholder="deixe vazio para não usar nome" onBlur={e => saveSetting({ user_display_name: e.target.value.trim() })}/></label>
          <div className="theme-picker" role="radiogroup" aria-label="Tema">
            <span>Tema</span>
            <div>
              {([['system', 'Sistema'], ['light', 'Claro'], ['dark', 'Escuro']] as [ThemeName, string][]).map(([valor, rotulo]) =>
                <button
                  key={valor}
                  type="button"
                  role="radio"
                  aria-checked={settings.theme === valor}
                  className={settings.theme === valor ? 'active' : ''}
                  onClick={() => saveSetting({ theme: valor })}
                >{rotulo}</button>)}
            </div>
          </div>
        </div>}

        {tab === 'models' && <div className="settings-stack">
          {providers.map(provider => <div className="provider-card" key={provider.id}>
            <div className="provider-line"><div><strong>{provider.name}</strong><span>{provider.base_url}</span></div><span className={`provider-state ${provider.is_enabled ? 'on' : ''}`}>{provider.is_enabled ? 'ativo' : 'desativado'}</span></div>
            <div className="key-row"><KeyRound size={16}/><input type="password" value={providerKeys[provider.id] ?? ''} onChange={e => setProviderKeys(k => ({ ...k, [provider.id]: e.target.value }))} placeholder={provider.has_api_key ? '•••••••• (chave salva)' : provider.kind === 'ollama' ? 'não necessária para Ollama local' : 'cole a API key'}/><button className="secondary" onClick={() => saveProviderKey(provider)}>Salvar</button></div>
            <button className="secondary" disabled={busy} onClick={() => loadRemote(provider)}><RefreshCw size={15}/> Consultar modelos</button>
            {remote[provider.id] && <>
              <div className="remote-count">{remote[provider.id].length} modelos encontrados — role para ver todos</div>
              <div className="remote-list">{remote[provider.id].map(modelId => <button key={modelId} onClick={() => run(async () => { await api.createModel({ provider_id: provider.id, display_name: modelId.split('/').pop() || modelId, model_id: modelId, temperature: .75, max_tokens: null, top_p: .95 }); await onChanged() })}>{modelId}</button>)}</div>
            </>}
          </div>)}
          <h3>Modelos configurados</h3>
          {models.map(model => <div key={model.id} className={`model-row ${settings.active_model_config_id === model.id ? 'active' : ''}`}>
            <button className="model-choice" onClick={() => run(async () => { await api.activateModel(model.id); await onChanged() })}>
              <div>
                <strong>{model.display_name}</strong>
                <span>{model.provider_name} · {model.model_id} · temp {model.temperature} · {model.max_tokens === null ? 'tokens automáticos' : `max ${model.max_tokens} tokens`}</span>
              </div>
              {settings.active_model_config_id === model.id && <Check size={18}/>}
            </button>
            <button
              className="icon-button subtle model-remove"
              aria-label={`Excluir ${model.display_name}`}
              title="Excluir modelo"
              onClick={() => run(async () => { await api.deleteModel(model.id); await onChanged() })}
            ><Trash2 size={15}/></button>
            <label className="context-window">
              Janela de contexto
              <input
                type="number" min={0} step={1024} defaultValue={model.context_window}
                onBlur={e => run(async () => { await api.updateModel(model.id, { context_window: Number(e.target.value) || 0 }); await onChanged() })}
              />
              <small>{model.context_window > 0
                ? 'histórico antigo é cortado automaticamente para caber'
                : '0 = desconhecida: o histórico vai inteiro e pode estourar'}</small>
            </label>
            <label className="context-window">
              <input
                type="checkbox"
                checked={model.supports_tools}
                onChange={e => run(async () => { await api.updateModel(model.id, { supports_tools: e.target.checked }); await onChanged() })}
              /> Ferramentas Fashion verificadas para este modelo
            </label>
          </div>)}
        </div>}

        {tab === 'personas' && <div className="persona-stack">
          <details className="global-rules">
            <summary>Regra global — toda persona obedece</summary>
            <p>Vem antes de qualquer traço de personalidade. É aqui que ficam as salvaguardas, fora do alcance de uma edição de persona.</p>
            <textarea
              rows={8}
              defaultValue={settings.global_persona_rules}
              onBlur={e => saveSetting({ global_persona_rules: e.target.value })}
            />
          </details>

          <div className="persona-layout">
          <div className="persona-rail">
            <button className="secondary add-persona" onClick={createPersona}><Plus size={15}/> Nova</button>
            {personas.map(persona => <div key={persona.id} className={`persona-nav-row ${editingPersona?.id === persona.id ? 'active' : ''}`}>
              <button className="persona-nav" onClick={() => setEditingPersonaId(persona.id)}>
                <span>{persona.avatar_emoji}</span>
                <div><strong>{persona.name}</strong><small>{settings.active_persona_id === persona.id ? 'padrão' : 'editar'}</small></div>
              </button>
              <button
                className="icon-button subtle"
                aria-label={`Excluir ${persona.name}`}
                title="Excluir persona"
                onClick={() => run(async () => {
                  await api.deletePersona(persona.id)
                  if (editingPersonaId === persona.id) setEditingPersonaId(null)
                  await onChanged()
                })}
              ><Trash2 size={15}/></button>
            </div>)}
          </div>
          {editingPersona && <PersonaEditor
            persona={editingPersona}
            isDefault={settings.active_persona_id === editingPersona.id}
            onSave={savePersona}
            onSetDefault={() => saveSetting({ active_persona_id: editingPersona.id })}
          />}
          </div>
        </div>}

        {tab === 'memories' && <div className="settings-stack">
          <div className="setting-note">Memória é separada da persona. Só memórias ativas <strong>e dentro do escopo da conversa</strong> entram no contexto, e são tratadas como fatos explicitamente fornecidos pela usuária.</div>
          <form className="memory-form" onSubmit={addMemory}>
            <div className="inline-two">
              <label>Categoria<input name="category" placeholder="ex.: preferência" defaultValue="general"/></label>
              <label>Escopo
                <select name="scope" value={memoryScope} onChange={e => setMemoryScope(e.target.value as MemoryScope)}>
                  <option value="global">Todas as conversas</option>
                  <option value="persona">Só uma persona</option>
                  <option value="conversation">Só uma conversa</option>
                </select>
              </label>
            </div>
            {memoryScope === 'persona' && <label>Persona
              <select name="target" required>{personas.map(p => <option key={p.id} value={p.id}>{p.avatar_emoji} {p.name}</option>)}</select>
            </label>}
            {memoryScope === 'conversation' && <label>Conversa
              <select name="target" required>{conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select>
            </label>}
            <textarea name="content" required rows={3} placeholder="Ex.: Prefere respostas curtas quando estiver estudando."/>
            <button className="primary-small"><Plus size={15}/> Adicionar memória</button>
          </form>
          <div className="memory-list">{memories.map(memory => <article className={`memory-card ${memory.is_active ? '' : 'disabled'}`} key={memory.id}><div><span>{memory.category}</span><span className={`scope-tag ${memory.scope}`}>{memory.scope === 'global' ? 'todas as conversas' : memory.scope === 'persona' ? 'uma persona' : 'uma conversa'}</span><p>{memory.content}</p></div><div className="memory-actions"><button className="secondary" onClick={() => run(async () => { await api.updateMemory(memory.id, { is_active: !memory.is_active }); await onChanged() })}>{memory.is_active ? 'Pausar' : 'Ativar'}</button><button className="icon-button" aria-label="Excluir memória" onClick={() => run(async () => { await api.deleteMemory(memory.id); await onChanged() })}><Trash2 size={16}/></button></div></article>)}</div>
        </div>}

        {tab === 'fashion' && <>
          <div className="setting-note">A assistente só recebe acesso ao guarda-roupa quando este módulo e o modelo ativo estiverem habilitados.</div>
          <label className="context-window"><input type="checkbox" checked={settings.fashion_enabled} onChange={e => saveSetting({ fashion_enabled: e.target.checked })}/> Habilitar ferramentas Fashion no chat</label>
          <FashionPanel/>
        </>}
      </div>
      {busy && <div className="saving">salvando…</div>}
    </section>
  </div>
}
