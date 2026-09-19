import { CalendarDays, ChevronLeft, ChevronRight, ExternalLink, PackageSearch, Shirt, Sparkles, WandSparkles } from 'lucide-react'
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

function imageUrl(item: Record<string, unknown>): string | null {
  const image = asRecord(item.image)
  return text(image.url) || null
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
  const suggestion = asRecord(payload.candidate)
  const actions = Array.isArray(envelope.actions) ? envelope.actions.map(asRecord) : []
  const saveAction = actions.find(action => action.id === 'save_candidate')
  const saveSuggestion = async () => {
    if (!saveAction || actionState !== 'idle') return
    setActionState('saving')
    try {
      await api.runFashionAction({
        object_id: object.id, action_id: 'save_candidate', target: saveAction.target,
        idempotency_key: `candidate-${object.id}`,
      })
      setActionState('saved')
    } catch { setActionState('error') }
  }
  const openFashion = () => window.dispatchEvent(new Event('fashion:open'))

  return <section className="chat-object" aria-label={title} data-object-version={object.schema_version}>
    <header><Icon size={16}/><div><strong>{title}</strong>{subtitle && <span>{subtitle}</span>}</div></header>
    {wardrobeItems.length > 0 && <VisualCarousel label={title}>{wardrobeItems.map((item, index) => <ItemVisual item={item} key={String(item.id ?? index)}/>)}</VisualCarousel>}
    {outfits.length > 0 && <VisualCarousel label={title}>{outfits.map((outfit, index) => <OutfitVisual outfit={outfit} key={String(outfit.id ?? index)}/>)}</VisualCarousel>}
    {object.type === 'wardrobe_suggestion' && Object.keys(suggestion).length > 0 && <div className="fashion-suggestion"><ItemVisual item={suggestion}/><button type="button" disabled={actionState === 'saving' || actionState === 'saved'} onClick={() => void saveSuggestion()}>{actionState === 'saved' ? 'Adicionada' : actionState === 'saving' ? 'Salvando…' : 'Adicionar ao guarda-roupa'}</button>{actionState === 'error' && <small>Não foi possível salvar. Tente de novo.</small>}</div>}
    {object.type === 'wardrobe_view' && <div className="fashion-chat-entry">
      {wardrobeItems.length === 0 && <p className="fashion-chat-empty">Ainda não há peças cadastradas. Você pode adicionar uma foto, uma peça manual ou uma referência da internet aqui no chat.</p>}
      <button type="button" onClick={openFashion}><Shirt size={15}/> {wardrobeItems.length ? 'Abrir meu guarda-roupa' : 'Adicionar ao guarda-roupa'}</button>
    </div>}
    {object.source.some(source => source.url) && <footer>
      {object.source.filter(source => source.url).map(source => <a key={`${source.kind}-${source.ref_id}`} href={source.url!} target="_blank" rel="noreferrer"><ExternalLink size={12}/> fonte</a>)}
    </footer>}
  </section>
}
