import { CalendarDays, Check, ChevronLeft, ChevronRight, ExternalLink, PackageSearch, Pencil, Shirt, Sparkles, Trash2, WandSparkles, X } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { api } from '../../lib/api'
import type { ChatUiObject } from '../../lib/types'

const ICONS = {
  wardrobe_view: Shirt,
  wardrobe_item: Shirt,
  outfit_carousel: WandSparkles,
  outfit_detail: WandSparkles,
  product_carousel: PackageSearch,
  trend_board: Sparkles,
  look_calendar: CalendarDays,
} as const

type KnownObjectType = keyof typeof ICONS

function isKnownObjectType(type: string): type is KnownObjectType {
  return type in ICONS
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())) : []
}

function imageUrl(item: Record<string, unknown>): string | null {
  const image = asRecord(item.image)
  return text(image.url) || null
}

function externalHttpUrl(value: unknown): string | null {
  try {
    const url = new URL(text(value))
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null
  } catch { return null }
}

function ItemVisual({ item }: { item: Record<string, unknown> }) {
  const image = imageUrl(item)
  const name = text(item.name, 'Peça')
  const detail = [text(item.color), text(item.category), text(item.style)].filter(Boolean).join(' · ')
  return <article className="fashion-chat-card">
    {image ? <img src={image} alt={name}/> : <span className="fashion-chat-placeholder"><Shirt size={28}/></span>}
    <strong>{name}</strong>
    {detail && <span>{detail}</span>}
  </article>
}

function itemEditorValues(item: Record<string, unknown>): Record<string, string> {
  return {
    name: text(item.name), category: text(item.category), subcategory: text(item.subcategory), color: text(item.color),
    material: text(item.material), brand: text(item.brand), size: text(item.size), style: text(item.style),
    seasons: strings(item.seasons).join(', '), occasions: strings(item.occasions).join(', '),
    tags: strings(item.tags).join(', '), formality: typeof item.formality === 'number' ? String(item.formality) : '',
    collection_status: text(item.collection_status, 'owned'),
  }
}

function WardrobeItemCard({ item }: { item: Record<string, unknown> }) {
  const [current, setCurrent] = useState(item)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(() => itemEditorValues(item))
  const [state, setState] = useState<'idle' | 'saving' | 'deleting' | 'error' | 'deleted'>('idle')
  const id = typeof current.id === 'number' ? current.id : null
  const revision = typeof current.revision === 'number' ? current.revision : null
  const image = imageUrl(current)
  const name = text(current.name, 'Peça')
  const externalUrl = externalHttpUrl(current.external_url)
  const detail = [text(current.color), text(current.category), text(current.style)].filter(Boolean).join(' · ')
  const setField = (field: string, value: string) => setDraft(values => ({ ...values, [field]: value }))
  const startEditing = () => { setDraft(itemEditorValues(current)); setEditing(true); setState('idle') }
  const save = async () => {
    if (!id || !revision || !draft.name.trim() || !draft.category.trim()) { setState('error'); return }
    setState('saving')
    try {
      const updated = await api.updateWardrobeItem(id, {
        expected_revision: revision,
        name: draft.name.trim(), category: draft.category.trim(),
        subcategory: draft.subcategory.trim() || null, color: draft.color.trim() || null,
        material: draft.material.trim() || null, brand: draft.brand.trim() || null, size: draft.size.trim() || null,
        style: draft.style.trim() || null, seasons: draft.seasons.split(',').map(value => value.trim()).filter(Boolean),
        occasions: draft.occasions.split(',').map(value => value.trim()).filter(Boolean),
        tags: draft.tags.split(',').map(value => value.trim()).filter(Boolean),
        formality: draft.formality ? Number(draft.formality) : null, collection_status: draft.collection_status,
      })
      setCurrent(updated as unknown as Record<string, unknown>)
      setEditing(false)
      setState('idle')
    } catch { setState('error') }
  }
  const archive = async () => {
    if (!id || !revision || !window.confirm(`Excluir “${text(current.name, 'esta peça')}” do guarda-roupa?`)) return
    setState('deleting')
    try {
      await api.archiveWardrobeItem(id, revision)
      setState('deleted')
    } catch { setState('error') }
  }

  if (state === 'deleted') return <article className="fashion-chat-card fashion-item-deleted"><Shirt size={24}/><span>Peça excluída</span></article>

  return <article className={`fashion-chat-card fashion-item-card ${editing ? 'editing' : ''}`}>
    {image ? <img src={image} alt={name}/> : <span className="fashion-chat-placeholder"><Shirt size={28}/></span>}
    <strong>{name}</strong>
    {detail && <span>{detail}</span>}
    {editing ? <div className="fashion-item-card-editor">
      <label>Nome<input value={draft.name} onChange={event => setField('name', event.target.value)}/></label>
      <label>Categoria<input value={draft.category} onChange={event => setField('category', event.target.value)}/></label>
      <label>Subcategoria<input value={draft.subcategory} onChange={event => setField('subcategory', event.target.value)}/></label>
      <label>Cor<input value={draft.color} onChange={event => setField('color', event.target.value)}/></label>
      <label>Material<input value={draft.material} onChange={event => setField('material', event.target.value)}/></label>
      <label>Marca<input value={draft.brand} onChange={event => setField('brand', event.target.value)}/></label>
      <label>Tamanho<input value={draft.size} onChange={event => setField('size', event.target.value)}/></label>
      <label>Estilo<input value={draft.style} onChange={event => setField('style', event.target.value)}/></label>
      <label>Estações<input value={draft.seasons} onChange={event => setField('seasons', event.target.value)}/></label>
      <label>Ocasiões<input value={draft.occasions} onChange={event => setField('occasions', event.target.value)}/></label>
      <label>Tags<input value={draft.tags} onChange={event => setField('tags', event.target.value)}/></label>
      <label>Formalidade<select value={draft.formality} onChange={event => setField('formality', event.target.value)}><option value="">Não informar</option>{[1, 2, 3, 4, 5].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
      <label>Estado<select value={draft.collection_status} onChange={event => setField('collection_status', event.target.value)}><option value="owned">Possuo</option><option value="wanted">Quero</option><option value="inspiration">Inspiração</option><option value="retired">Arquivei</option></select></label>
    </div> : null}
    <div className="fashion-item-card-actions">
      {editing
        ? <><button type="button" aria-label="Salvar alterações" title="Salvar" disabled={state === 'saving'} onClick={() => void save()}><Check size={14}/><span>{state === 'saving' ? 'Salvando…' : 'Salvar'}</span></button><button type="button" aria-label="Cancelar edição" title="Cancelar" disabled={state === 'saving'} onClick={() => { setEditing(false); setState('idle') }}><X size={14}/></button></>
        : <>
          {externalUrl && <a className="fashion-item-link icon-action" href={externalUrl} target="_blank" rel="noopener noreferrer" aria-label={`Acessar link de ${name}`} title="Acessar link"><ExternalLink size={14}/></a>}
          <button type="button" className="icon-action" aria-label={`Editar ${name}`} title="Editar" disabled={state === 'deleting'} onClick={startEditing}><Pencil size={14}/></button>
          <button type="button" className="icon-action danger" aria-label={state === 'deleting' ? `Excluindo ${name}` : `Excluir ${name}`} title="Excluir" disabled={state === 'deleting'} onClick={() => void archive()}><Trash2 size={14}/></button>
        </>}
    </div>
    {state === 'error' && <small className="fashion-item-card-error">Não foi possível concluir. Atualize o guarda-roupa e tente de novo.</small>}
  </article>
}

function OutfitVisual({ outfit }: { outfit: Record<string, unknown> }) {
  const pieces = Array.isArray(outfit.items) ? outfit.items.map(asRecord).map(piece => asRecord(piece.wardrobe_item)).filter(item => Object.keys(item).length) : []
  const title = text(outfit.title, 'Combinação')
  const detail = [text(outfit.style), text(outfit.occasion)].filter(Boolean).join(' · ')
  return <article className="fashion-chat-card outfit">
    <div className="fashion-chat-look-images">
      {pieces.slice(0, 3).map((item, index) => {
        const image = imageUrl(item)
        return image ? <img key={index} src={image} alt={text(item.name, 'Peça do look')}/> : <span key={index}><Shirt size={18}/></span>
      })}
      {!pieces.length && <span><WandSparkles size={22}/></span>}
    </div>
    <strong>{title}</strong>
    {detail && <span>{detail}</span>}
  </article>
}

function VisualCarousel({ children, label }: { children: ReactNode; label: string }) {
  const rail = useRef<HTMLDivElement>(null)
  const scroll = (direction: number) => rail.current?.scrollBy({ left: direction * 240, behavior: 'smooth' })
  return <div className="fashion-chat-carousel" aria-label={label}>
    <div className="fashion-chat-carousel-actions">
      <button type="button" onClick={() => scroll(-1)} aria-label="Ver itens anteriores"><ChevronLeft size={16}/></button>
      <button type="button" onClick={() => scroll(1)} aria-label="Ver próximos itens"><ChevronRight size={16}/></button>
    </div>
    <div className="fashion-chat-rail" ref={rail}>{children}</div>
  </div>
}

export function ChatObjectRenderer({ object }: { object: ChatUiObject }) {
  const envelope = asRecord(object.data)
  const payload = asRecord(envelope.data)
  const Icon = isKnownObjectType(object.type) ? ICONS[object.type] : PackageSearch
  const title = typeof envelope.title === 'string' ? envelope.title : object.type.replaceAll('_', ' ')
  const subtitle = typeof envelope.subtitle === 'string' ? envelope.subtitle : ''
  const wardrobeItems = object.type === 'wardrobe_item'
    ? [payload.item].filter(Boolean).map(asRecord)
    : Array.isArray(payload.items) ? payload.items.map(asRecord) : []
  const outfits = Array.isArray(payload.outfits) ? payload.outfits.map(asRecord)
    : object.type === 'outfit_detail' && payload.outfit ? [asRecord(payload.outfit)] : []
  const [actionState, setActionState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [savedItem, setSavedItem] = useState<Record<string, unknown> | null>(null)
  const suggestion = asRecord(payload.candidate)
  const analysis = asRecord(payload.analysis)
  const [editing, setEditing] = useState(false)
  const [edits, setEdits] = useState<Record<string, unknown>>({})
  const actions = Array.isArray(envelope.actions) ? envelope.actions.map(asRecord) : []
  const saveAction = actions.find(action => action.id === 'save_candidate')
  const saveSuggestion = async () => {
    if (!saveAction || actionState === 'saving' || actionState === 'saved') return
    if (!value('name').trim() || !value('category').trim()) { setActionState('error'); setEditing(true); return }
    setActionState('saving')
    try {
      const response = await api.runFashionAction({
        object_id: object.id, action_id: 'save_candidate', target: saveAction.target,
        edits,
        idempotency_key: `candidate-${object.id}`,
      })
      setSavedItem(asRecord(response.item))
      setActionState('saved')
    } catch { setActionState('error') }
  }
  const setField = (field: string, value: unknown) => setEdits(current => ({ ...current, [field]: value }))
  const value = (field: string) => text(edits[field] ?? suggestion[field])
  const tags = edits.tags ?? suggestion.tags
  const seasons = edits.seasons ?? suggestion.seasons
  const occasions = edits.occasions ?? suggestion.occasions
  const status = text(edits.collection_status ?? suggestion.collection_status, 'owned')
  const statusLabel = status === 'owned' ? 'Possuo' : status === 'inspiration' ? 'Inspiração' : 'Quero'
  const attachPhoto = () => window.dispatchEvent(new Event('fashion:attach'))
  const send = (message: string) => window.dispatchEvent(new CustomEvent('fashion:send', { detail: message }))
  const compose = (message: string) => window.dispatchEvent(new CustomEvent('fashion:compose', { detail: message }))

  return <section className="chat-object" aria-label={title} data-object-version={object.schema_version}>
    <header><Icon size={16}/><div><strong>{title}</strong>{subtitle && <span>{subtitle}</span>}</div></header>
    {wardrobeItems.length > 0 && <VisualCarousel label={title}>{wardrobeItems.map((item, index) => <WardrobeItemCard item={item} key={String(item.id ?? index)}/>)}</VisualCarousel>}
    {outfits.length > 0 && <VisualCarousel label={title}>{outfits.map((outfit, index) => <OutfitVisual outfit={outfit} key={String(outfit.id ?? index)}/>)}</VisualCarousel>}
    {object.type === 'wardrobe_suggestion' && Object.keys(suggestion).length > 0 && <div className="fashion-suggestion">
      <ItemVisual item={savedItem ?? { ...suggestion, ...edits }}/>
      <div className="fashion-suggestion-review">
        <span>{text(analysis.summary, 'Revise a análise antes de salvar. Campos incertos podem ficar vazios.')}</span>
        <span className="fashion-suggestion-status">Adicionar como: {statusLabel}</span>
        <dl className="fashion-suggestion-attributes">
          {value('size') && <><dt>Tamanho</dt><dd>{value('size')}</dd></>}
          {strings(seasons).length > 0 && <><dt>Estações</dt><dd>{strings(seasons).join(', ')}</dd></>}
          {strings(occasions).length > 0 && <><dt>Ocasiões</dt><dd>{strings(occasions).join(', ')}</dd></>}
          {strings(tags).length > 0 && <><dt>Tags</dt><dd>{strings(tags).join(', ')}</dd></>}
        </dl>
        {Array.isArray(analysis.uncertain_fields) && analysis.uncertain_fields.length > 0 && <span className="fashion-uncertain">Não confirmado: {analysis.uncertain_fields.filter((field): field is string => typeof field === 'string').join(', ')}</span>}
        {editing && actionState !== 'saved' && <div className="fashion-suggestion-fields">
          <label>Nome<input value={value('name')} onChange={event => setField('name', event.target.value)}/></label>
          <label>Categoria<input value={value('category')} onChange={event => setField('category', event.target.value)}/></label>
          <label>Cor<input value={value('color')} onChange={event => setField('color', event.target.value || null)}/></label>
          <label>Estilo<input value={value('style')} onChange={event => setField('style', event.target.value || null)}/></label>
          <label>Marca<input value={value('brand')} onChange={event => setField('brand', event.target.value || null)}/></label>
          <label>Material<input value={value('material')} onChange={event => setField('material', event.target.value || null)}/></label>
          <label>Tamanho<input value={value('size')} onChange={event => setField('size', event.target.value || null)}/></label>
          <label>Estações<input value={strings(seasons).join(', ')} onChange={event => setField('seasons', event.target.value.split(',').map(season => season.trim()).filter(Boolean))}/></label>
          <label>Ocasiões<input value={strings(occasions).join(', ')} onChange={event => setField('occasions', event.target.value.split(',').map(occasion => occasion.trim()).filter(Boolean))}/></label>
          <label>Estado<select value={status} onChange={event => setField('collection_status', event.target.value)}><option value="owned">Possuo</option><option value="wanted">Quero</option><option value="inspiration">Inspiração</option></select></label>
          <label>Tags<input value={strings(tags).join(', ')} onChange={event => setField('tags', event.target.value.split(',').map(tag => tag.trim()).filter(Boolean))}/></label>
        </div>}
        <div className="fashion-suggestion-actions">
          {actionState !== 'saved' && <button type="button" className="secondary" onClick={() => setEditing(open => !open)}>{editing ? 'Fechar edição' : 'Revisar campos'}</button>}
          <button type="button" disabled={actionState === 'saving' || actionState === 'saved'} onClick={() => void saveSuggestion()}>{actionState === 'saved' ? 'Peça salva' : actionState === 'saving' ? 'Salvando…' : 'Salvar peça'}</button>
          {actionState === 'saved' && <button type="button" className="secondary" onClick={() => send('Mostre meu guarda-roupa atualizado.')}>Ver guarda-roupa</button>}
        </div>
        {actionState === 'error' && <small>Não foi possível salvar. Revise os campos e tente novamente.</small>}
        {text(suggestion.source_url) && <a href={text(suggestion.source_url)} target="_blank" rel="noreferrer"><ExternalLink size={12}/> Ver fonte</a>}
      </div>
    </div>}
    {object.type === 'wardrobe_view' && <div className="fashion-chat-entry">
      {wardrobeItems.length === 0 && <p className="fashion-chat-empty">Seu guarda-roupa está vazio. Envie uma foto ou cole o link de uma peça; eu preparo o cadastro para você revisar.</p>}
      <button type="button" onClick={attachPhoto}><Shirt size={15}/> Enviar foto</button>
      <button type="button" onClick={() => compose('Quero cadastrar esta peça do link: ')}><ExternalLink size={14}/> Colar link</button>
      {wardrobeItems.length > 0 && <button type="button" onClick={() => send('Mostre combinações com as peças que eu possuo.')}>Ver conjuntos</button>}
    </div>}
    {object.source.some(source => source.url) && <footer>
      {object.source.filter(source => source.url).map(source => <a key={`${source.kind}-${source.ref_id}`} href={source.url!} target="_blank" rel="noreferrer"><ExternalLink size={12}/> fonte</a>)}
    </footer>}
  </section>
}
