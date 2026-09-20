import { Check, Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { PersonaAvatar } from '../../components/PersonaAvatar'
import { CHARACTERS, type AvatarCharacter } from '../../lib/personaVisuals'
import type { Persona } from '../../lib/types'

/**
 * Editor de persona por campos (F-persona).
 *
 * Antes era um único textarea com o system prompt inteiro, o que misturava
 * salvaguardas com personalidade e obrigava a usuária a escrever prompt para
 * mudar o humor da assistente. Agora cada traço tem seu campo, e o prompt final
 * é montado no servidor — mostrado aqui em "ver prompt final" para não haver
 * mistério sobre o que é enviado.
 */

type Campo = {
  nome: keyof Persona
  rotulo: string
  placeholder: string
  linhas?: number
}

// Os placeholders trazem mais de um exemplo de propósito: um exemplo só é lido
// como "o valor certo", vários deixam claro que é uma escolha.
const CAMPOS: Campo[] = [
  {
    nome: 'personality',
    rotulo: 'Personalidade',
    placeholder: 'acolhedora, próxima, divertida  ·  direta e analítica  ·  irônica e observadora',
    linhas: 2,
  },
  {
    nome: 'humor',
    rotulo: 'Humor',
    placeholder: 'leve e brincalhona, sem forçar piada  ·  humor seco e irônico  ·  quase nenhum, foco no assunto',
    linhas: 2,
  },
  {
    nome: 'tone',
    rotulo: 'Tom',
    placeholder: 'casual e caloroso, com emojis em moderação  ·  formal e preciso  ·  direto, sem rodeios',
    linhas: 2,
  },
  {
    nome: 'energy',
    rotulo: 'Energia',
    placeholder: 'adapta-se ao momento  ·  sempre calma e estável  ·  animada e entusiasmada o tempo todo',
    linhas: 2,
  },
  {
    nome: 'objective',
    rotulo: 'Objetivo',
    placeholder: 'ser companhia agradável e útil  ·  destravar decisões rápido  ·  ensinar com paciência',
    linhas: 2,
  },
  {
    nome: 'avoid',
    rotulo: 'Evitar soar',
    placeholder: 'infantil, artificial, eufórica  ·  condescendente  ·  vaga e genérica',
    linhas: 2,
  },
]

export function PersonaEditor({ persona, isDefault, onSave, onSetDefault }: {
  persona: Persona
  isDefault: boolean
  onSave: (payload: Partial<Persona>) => void
  onSetDefault: () => void
}) {
  const [promptAberto, setPromptAberto] = useState(false)
  const [character, setCharacter] = useState<AvatarCharacter | null>(persona.avatar_character ? 'morena' : null)
  useEffect(() => { setCharacter(persona.avatar_character ? 'morena' : null) }, [persona.id, persona.avatar_character])

  const salvar = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const texto = (chave: string) => String(data.get(chave) ?? '')
    onSave({
      avatar_emoji: texto('avatar_emoji') || '💗',
      avatar_character: character,
      name: texto('name'),
      description: texto('description'),
      greeting: texto('greeting'),
      extra_instructions: texto('extra_instructions'),
      ...Object.fromEntries(CAMPOS.map(campo => [campo.nome, texto(campo.nome)])),
    })
  }

  return <form className="persona-editor" key={persona.id} onSubmit={salvar}>
    <div className="inline-two">
      <label>Emoji<input name="avatar_emoji" defaultValue={persona.avatar_emoji}/></label>
      <label>Nome<input name="name" required defaultValue={persona.name} placeholder="Bestie  ·  Nina  ·  Copiloto"/></label>
    </div>
    <fieldset className="character-picker">
      <legend>Visual da persona</legend>
      <p>Escolha a personagem que aparece e reage nas conversas desta persona.</p>
      <div className="character-options">
        <label className={`character-option ${character === null ? 'selected' : ''}`}>
          <input type="radio" name="avatar_character" value="" checked={character === null} onChange={() => setCharacter(null)}/>
          <span className="character-emoji" aria-hidden="true">{persona.avatar_emoji}</span>
          <span>Somente emoji</span>
        </label>
        {CHARACTERS.map(option => <label key={option.id} className={`character-option ${character === option.id ? 'selected' : ''}`}>
          <input type="radio" name="avatar_character" value={option.id} checked={character === option.id} onChange={() => setCharacter(option.id)}/>
          <PersonaAvatar character={option.id} emoji={persona.avatar_emoji} imageAlt={`Prévia da personagem ${option.label}`}/>
          <span>{option.label}</span>
        </label>)}
      </div>
    </fieldset>
    <label>Descrição<input name="description" defaultValue={persona.description} placeholder="como você descreveria essa persona em uma linha"/></label>

    <div className="persona-traits">
      {CAMPOS.map(campo => <label key={campo.nome}>
        {campo.rotulo}
        <textarea
          name={campo.nome}
          rows={campo.linhas ?? 2}
          defaultValue={String(persona[campo.nome] ?? '')}
          placeholder={campo.placeholder}
        />
      </label>)}
    </div>

    <label>Saudação<textarea name="greeting" rows={2} defaultValue={persona.greeting} placeholder="a primeira coisa que ela diz ao abrir a conversa"/></label>

    <label>
      Instruções extras
      <textarea
        name="extra_instructions"
        rows={4}
        defaultValue={persona.extra_instructions}
        placeholder="o que não coube nos campos acima — deixe vazio se não precisar"
      />
    </label>

    <div className="prompt-preview">
      <button type="button" className="link-button" onClick={() => setPromptAberto(v => !v)}>
        {promptAberto ? '▾' : '▸'} ver prompt final gerado
      </button>
      {promptAberto && <>
        <p className="prompt-hint">
          Montado pelo servidor: regra global, depois os campos, depois as instruções extras.
          Salve para atualizar.
        </p>
        <pre>{persona.composed_prompt}</pre>
      </>}
    </div>

    <div className="editor-actions">
      <button type="button" className="secondary" onClick={onSetDefault} disabled={isDefault}>
        <Check size={15}/> {isDefault ? 'é a padrão' : 'usar como padrão'}
      </button>
      <button className="primary-small"><Save size={15}/> Salvar persona</button>
    </div>
  </form>
}
