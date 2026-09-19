import { Archive, ImagePlus, Link, MessageCircle, Plus, RefreshCw, Shirt, WandSparkles } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../../lib/api'
import type { StyleProfile, WardrobeItem, WardrobePage } from '../../lib/types'

function splitValues(value: string): string[] {
  return value.split(',').map(entry => entry.trim()).filter(Boolean)
}

export function FashionPanel({ onAsk }: { onAsk: (message: string) => void }) {
  const [page, setPage] = useState<WardrobePage | null>(null)
  const [profile, setProfile] = useState<StyleProfile | null>(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<WardrobeItem | null>(null)
  const [outfits, setOutfits] = useState<Array<Record<string, unknown>>>([])

  const load = async (search = query) => {
    setBusy(true); setError('')
    try {
      const params = new URLSearchParams()
      if (search.trim()) params.set('query', search.trim())
      const [wardrobe, style] = await Promise.all([api.wardrobe(params.toString()), api.styleProfile()])
      setPage(wardrobe); setProfile(style)
      setSelected(current => wardrobe.items.find(item => item.id === current?.id) ?? null)
      setOutfits([])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally { setBusy(false) }
  }

  useEffect(() => { void load('') }, []) // initial local inventory

  const addItem = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try {
      const image = data.get('image')
      const asset = image instanceof File && image.size ? await api.uploadFashionAsset(image) : null
      await api.createWardrobeItem({
        name: String(data.get('name') || ''), category: String(data.get('category') || ''),
        color: String(data.get('color') || '') || null, style: String(data.get('style') || '') || null,
        seasons: splitValues(String(data.get('seasons') || '')),
        occasions: splitValues(String(data.get('occasions') || '')),
        tags: splitValues(String(data.get('tags') || '')),
        image_asset_id: asset?.id ?? null,
      })
      event.currentTarget.reset()
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally { setBusy(false) }
  }

  const importImage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    setBusy(true); setError('')
    try {
      await api.importExternalImage({
        image_url: String(data.get('image_url') || ''), name: String(data.get('name') || ''),
        category: String(data.get('category') || ''), color: String(data.get('color') || '') || null,
        brand: String(data.get('brand') || '') || null, style: String(data.get('style') || '') || null,
        collection_status: String(data.get('collection_status') || 'wanted'),
        tags: splitValues(String(data.get('tags') || '')),
      })
      event.currentTarget.reset()
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally { setBusy(false) }
  }

  const archive = async (item: WardrobeItem) => {
    setBusy(true); setError('')
    try {
      await api.archiveWardrobeItem(item.id, item.revision)
      await load()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally { setBusy(false) }
  }

  const showOutfits = async (item: WardrobeItem) => {
    setBusy(true); setError('')
    try {
      const result = await api.fashionTool('mix_and_match', { anchor_item_id: item.id, limit: 6 })
      const drafts = result.data.outfits
      setOutfits(Array.isArray(drafts) ? drafts.filter((entry): entry is Record<string, unknown> => entry !== null && typeof entry === 'object') : [])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally { setBusy(false) }
  }

  return <div className="fashion-panel">
    <div className="fashion-title">
      <div><h3>Guarda-roupa no chat</h3><p>Visualize, cadastre e use suas peças sem sair da conversa.</p></div>
      <button className="secondary" disabled={busy} onClick={() => void load()}><RefreshCw size={15}/> Atualizar</button>
    </div>
    {error && <div className="error-box">{error}</div>}

    <form className="fashion-add" onSubmit={addItem}>
      <strong><Plus size={15}/> Cadastrar peça</strong>
      <div className="fashion-fields">
        <label>Nome<input required name="name" placeholder="Jaqueta jeans"/></label>
        <label>Categoria<input required name="category" placeholder="casaco, calça, calçado…"/></label>
        <label>Cor<input name="color" placeholder="azul"/></label>
        <label>Estilo<input name="style" placeholder="casual"/></label>
        <label>Estações<input name="seasons" placeholder="outono, inverno"/></label>
        <label>Ocasiões<input name="occasions" placeholder="trabalho, noite"/></label>
        <label>Tags<input name="tags" placeholder="denim, oversized"/></label>
        <label>Foto<input name="image" type="file" accept="image/jpeg,image/png,image/webp"/></label>
      </div>
      <button className="primary-small" disabled={busy}><ImagePlus size={15}/> Salvar peça</button>
    </form>

    <form className="fashion-add" onSubmit={importImage}>
      <strong><Link size={15}/> Salvar imagem da internet</strong>
      <p className="fashion-help">A imagem é baixada, validada e salva localmente. A fonte fica vinculada à peça.</p>
      <div className="fashion-fields">
        <label>URL da imagem<input required name="image_url" type="url" placeholder="https://site.com/peca.jpg"/></label>
        <label>Nome<input required name="name" placeholder="Blazer bege"/></label>
        <label>Categoria<input required name="category" placeholder="casaco, calça, calçado…"/></label>
        <label>Estado<select name="collection_status" defaultValue="wanted"><option value="wanted">Quero</option><option value="owned">Possuo</option><option value="inspiration">Inspiração</option></select></label>
        <label>Marca<input name="brand" placeholder="opcional"/></label>
        <label>Cor<input name="color" placeholder="opcional"/></label>
        <label>Estilo<input name="style" placeholder="opcional"/></label>
        <label>Tags<input name="tags" placeholder="denim, oversized"/></label>
      </div>
      <button className="primary-small" disabled={busy}><ImagePlus size={15}/> Salvar na coleção</button>
    </form>

    <div className="fashion-toolbar">
      <label>Buscar<input value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); void load(query) } }} placeholder="nome, cor, marca ou tag"/></label>
      <span>{page?.total ?? 0} peças</span>
    </div>

    <div className="wardrobe-grid">
      {page?.items.map(item => <button className={`wardrobe-card ${selected?.id === item.id ? 'active' : ''}`} key={item.id} onClick={() => setSelected(item)}>
        {item.image ? <img src={item.image.url} alt=""/> : <span className="wardrobe-placeholder"><Shirt size={26}/></span>}
        <strong>{item.name}</strong><small>{[item.collection_status === 'owned' ? 'Possuo' : item.collection_status === 'wanted' ? 'Quero' : 'Inspiração', item.color, item.category].filter(Boolean).join(' · ')}</small>
      </button>)}
      {page && page.items.length === 0 && <div className="fashion-empty">Nenhuma peça encontrada.</div>}
    </div>

    {selected && <article className="wardrobe-detail">
      <div>{selected.image ? <img src={selected.image.url} alt=""/> : <Shirt size={30}/>}<div><h4>{selected.name}</h4><p>{selected.category}{selected.style ? ` · ${selected.style}` : ''}</p></div></div>
      <p>{selected.tags.length ? selected.tags.join(' · ') : 'Sem tags'} · usada {selected.wear_count} vez(es)</p>
      {selected.external_url && <a href={selected.external_url} target="_blank" rel="noreferrer">Abrir fonte{selected.external_domain ? ` · ${selected.external_domain}` : ''}</a>}
      <div className="wardrobe-detail-actions">
        {selected.collection_status === 'owned' && <button className="secondary" disabled={busy} onClick={() => void showOutfits(selected)}><WandSparkles size={15}/> Ver conjuntos</button>}
        <button className="secondary" disabled={busy} onClick={() => onAsk(`Quero ajuda com a peça “${selected.name}” do meu guarda-roupa.`)}><MessageCircle size={15}/> Perguntar à assistente</button>
        <button className="secondary" disabled={busy} onClick={() => void archive(selected)}><Archive size={15}/> Arquivar</button>
      </div>
    </article>}

    {outfits.length > 0 && <section className="fashion-outfit-results" aria-label="Conjuntos sugeridos">
      <strong><WandSparkles size={15}/> Conjuntos com {selected?.name}</strong>
      <div>{outfits.map((outfit, index) => {
        const pieces = Array.isArray(outfit.items) ? outfit.items.filter((piece): piece is Record<string, unknown> => piece !== null && typeof piece === 'object') : []
        const names = pieces.map(piece => {
          const wardrobe = piece.wardrobe_item
          return wardrobe !== null && typeof wardrobe === 'object' && 'name' in wardrobe && typeof wardrobe.name === 'string' ? wardrobe.name : ''
        }).filter(Boolean)
        return <article key={String(outfit.title ?? index)}><strong>{typeof outfit.title === 'string' ? outfit.title : 'Combinação'}</strong><span>{names.join(' + ')}</span></article>
      })}</div>
    </section>}

    {profile && <div className="fashion-profile"><strong>Perfil de estilo</strong><span>{Object.keys(profile.explicit_preferences).length ? 'Preferências explícitas salvas.' : 'Ainda sem preferências explícitas.'}</span></div>}
  </div>
}
