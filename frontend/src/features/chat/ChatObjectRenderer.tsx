import { CalendarDays, ExternalLink, PackageSearch, Shirt, Sparkles, WandSparkles } from 'lucide-react'
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

export function ChatObjectRenderer({ object }: { object: ChatUiObject }) {
  const envelope = asRecord(object.data)
  const payload = asRecord(envelope.data)
  const Icon = isKnownObjectType(object.type) ? ICONS[object.type] : PackageSearch
  const title = typeof envelope.title === 'string' ? envelope.title : object.type.replaceAll('_', ' ')
  const subtitle = typeof envelope.subtitle === 'string' ? envelope.subtitle : ''
  const items = Array.isArray(payload.items) ? payload.items : Array.isArray(payload.outfits) ? payload.outfits : []

  return <section className="chat-object" aria-label={title} data-object-version={object.schema_version}>
    <header><Icon size={16}/><div><strong>{title}</strong>{subtitle && <span>{subtitle}</span>}</div></header>
    {items.length > 0 && <div className="chat-object-list">
      {items.slice(0, 6).map((entry, index) => {
        const row = asRecord(entry)
        const name = typeof row.name === 'string' ? row.name : typeof row.title === 'string' ? row.title : `Item ${index + 1}`
        const detail = typeof row.category === 'string' ? row.category : typeof row.style === 'string' ? row.style : ''
        return <div key={index}><strong>{name}</strong>{detail && <span>{detail}</span>}</div>
      })}
    </div>}
    {object.source.some(source => source.url) && <footer>
      {object.source.filter(source => source.url).map(source => <a key={`${source.kind}-${source.ref_id}`} href={source.url!} target="_blank" rel="noreferrer"><ExternalLink size={12}/> fonte</a>)}
    </footer>}
  </section>
}
