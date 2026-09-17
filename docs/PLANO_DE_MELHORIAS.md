# Plano de melhorias — BFF AI

Roadmap técnico derivado da leitura completa do código em 2026-09-17. O objetivo é
tratar dívida **estrutural**, não cosmética: cada fase remove uma classe inteira de
problema, não um sintoma.

## Status da execução

As fases 0 a 7 foram executadas. A fase 8 continua condicional e não foi iniciada.

| Item | Status | Onde conferir |
|---|---|---|
| F0.1 Controle de versão | ✅ | `git log` |
| F0.2 `.gitignore` | ✅ | [.gitignore](../.gitignore), [.gitattributes](../.gitattributes) |
| F0.3 Defaults com fonte única | ✅ | [bootstrap.py](../backend/app/services/bootstrap.py) |
| F0.4 Injeção de sessão | ✅ | [deps.py](../backend/app/api/deps.py) |
| F1.1 Alembic no lugar de `create_all` | ✅ | [schema.py](../backend/app/db/schema.py) |
| F1.2 URL e batch do Alembic | ✅ | [env.py](../backend/alembic/env.py) |
| F1.3 Trava models × migrations | ✅ | `test_schema_coherence.py` |
| F2.1 Capacidades no adapter | ✅ | [base.py](../backend/app/services/llm/base.py) |
| F2.2 Registry de adapters | ✅ | [factory.py](../backend/app/services/llm/factory.py) |
| F3.1 Resposta parcial persistida | ✅ | [chat.py](../backend/app/services/chat.py) |
| F3.2 Cancelamento ponta a ponta | ✅ | `useChatStream.ts`, `chat.py` |
| F3.3 Tokens de uso | ⚠️ | só NVIDIA NIM — ver ressalva abaixo |
| F3.4 I/O fora do event loop | ✅ | `prepare()` + `run_in_threadpool` |
| F3.5 Regenerar | ✅ | `POST .../messages/{id}/regenerate` |
| F4.1 ContextBuilder | ✅ | [context.py](../backend/app/services/context.py) |
| F4.2 Orçamento de contexto | ✅ | `context_window` por modelo |
| F4.3 Escopo de memória | ✅ | `Memory.scope` |
| F5.1 Erro tipado | ✅ | [errors.py](../backend/app/services/llm/errors.py) |
| F5.2 Logging | ✅ | [main.py](../backend/app/main.py) |
| F5.3 Health honesto | ✅ | `GET /health/ready` |
| F6.1 Infra de teste | ✅ | `tests/conftest.py` |
| F6.2 Comportamento crítico | ✅ | 49 testes no backend |
| F6.3 Parser SSE testado | ✅ | 20 testes no frontend |
| F7.1–F7.4 Frontend | ✅ | `src/hooks/`, `Markdown.tsx` |
| F8.x Sair do modo local | ⬜ | condicional, não iniciado |

### Achado extra, fora do plano original

Rodando o app contra um provider falso apareceu um defeito que a leitura estática
não tinha revelado: **um provider que fecha a conexão no meio da resposta era
gravado como `complete`**. `httpx.aiter_lines` apenas termina a iteração, sem
levantar, então a resposta truncada era indistinguível de uma que acabou. O
adapter passou a exigir a marca de fim do protocolo (`[DONE]` ou `finish_reason`).

### Ressalva sobre F3.3

`stream_options: {"include_usage": true}` está **ligado só para NVIDIA NIM** e
desligado para Ollama. Nenhum dos dois pôde ser verificado contra um servidor
real nesta execução (o Ollama local não estava rodando), e pedir um campo que o
servidor rejeita derrubaria o chat — a regra 1 proíbe tentar de novo sem ele.
Ligar para Ollama é trocar `supports_usage_in_stream` para `True` em
[ollama.py](../backend/app/services/llm/ollama.py), depois de conferir na sua versão.

## Como ler

Cada item tem **Problema** (com evidência no código), **Proposta**, **Arquivos**,
**Aceite** (como saber que terminou) e **Esforço** (P ≈ menos de 1h, M ≈ meio dia,
G ≈ 1–3 dias). O texto de cada item foi mantido como registro do **porquê** de
cada mudança, mesmo depois de executada.

As fases são ordenadas por dependência, não por importância. Fase 0 e 1 desbloqueiam
todo o resto — fazer Fase 6 antes da Fase 1 significa escrever testes sobre um schema
que ainda tem duas fontes de verdade.

## Princípios inegociáveis

O plano inteiro preserva as seis regras deliberadas do README. Nenhum item abaixo pode:

1. introduzir fallback silencioso entre providers;
2. deixar a conversa trocar de modelo no meio do caminho;
3. mover secrets para fora do banco cifrado;
4. transformar persona em código;
5. acoplar chat/banco/UI a um provider específico;
6. quebrar streaming ponta a ponta.

O item **F2.1** existe justamente porque a regra 5 já está sendo violada hoje.

## Visão geral

| Fase | Tema | Itens | Esforço |
|---|---|---|---|
| 0 | Fundação e higiene do repositório | 4 | P–M |
| 1 | Schema com fonte única (Alembic) | 3 | M |
| 2 | Providers realmente plugáveis | 2 | M |
| 3 | Robustez do fluxo de chat | 5 | G |
| 4 | Contexto e memórias com orçamento | 3 | G |
| 5 | Contrato de erro e observabilidade | 3 | M |
| 6 | Testes | 3 | G |
| 7 | Frontend estrutural | 4 | G |
| 8 | Condicional: sair do modo local | 4 | G |

---

# Fase 0 — Fundação e higiene

## F0.1 — Colocar o projeto sob controle de versão

**Problema.** O diretório se chama `Github Repo/bff-ai` mas não é um repositório git.
Todo o plano abaixo assume commits revisáveis e reversíveis; sem isso, cada refactor é
uma aposta.

**Proposta.** `git init`, commit inicial do estado atual, e só então começar a Fase 1.

**Aceite.** `git log` mostra o commit inicial; `git status` limpo.
**Esforço.** P.

## F0.2 — Corrigir o `.gitignore` antes do primeiro commit

**Problema.** O [.gitignore](../.gitignore) ignora `.venv/`, mas o ambiente real é
`backend/venv/`. Também ficam de fora os diretórios `backend/pytest-cache-files-*`
gerados por execuções anteriores e os `*.tsbuildinfo`. Sem a correção, o primeiro commit
leva junto milhares de arquivos de dependência.

**Proposta.** Adicionar `venv/`, `backend/venv/`, `pytest-cache-files-*/`,
`*.tsbuildinfo`, `backend/data/*.db-shm`, `backend/data/*.db-wal`. Apagar do disco os
diretórios `pytest-cache-files-*` órfãos.

**Aceite.** `git status --porcelain` na casa das dezenas de linhas, não dos milhares.
**Esforço.** P. **Depende de.** nada (fazer antes de F0.1 concluir o commit).

## F0.3 — Uma única fonte para os defaults de settings

**Problema.** O dicionário de defaults existe duas vezes, com o mesmo conteúdo:
[bootstrap.py](../backend/app/services/bootstrap.py) e `DEFAULT_SETTINGS` em
[repositories/settings.py](../backend/app/repositories/settings.py). Mudar o tema padrão
em um lugar e esquecer o outro produz comportamento diferente entre "banco novo" e
"banco existente sem a chave".

**Proposta.** Manter `DEFAULT_SETTINGS` no repositório como fonte única e fazer o
`bootstrap()` chamar `SettingsRepository(db).seed_defaults()`.

**Aceite.** O literal `"BFF AI"` como default aparece em exatamente um arquivo.
**Esforço.** P.

## F0.4 — Remover código morto

**Problema.** [api/deps.py:5](../backend/app/api/deps.py) define `Db = Depends(get_db)`
que nenhuma rota usa — todas fazem `Depends(get_db)` direto. É uma abstração que promete
um padrão que não existe.

**Proposta.** Decidir: ou adotar `Db` em todas as rotas, ou apagar o arquivo. Recomendo
adotar — o alias encurta seis arquivos de rota e dá um ponto único para trocar a
estratégia de sessão na Fase 3.

**Aceite.** Nenhuma rota importa `get_db` diretamente, ou `deps.py` não existe mais.
**Esforço.** P.

---

# Fase 1 — Schema com fonte única

Esta é a fase mais urgente. Hoje existem **duas** definições de schema divergindo em
silêncio, e a segunda mudança de coluna vai custar caro.

## F1.1 — Aposentar `create_all` em favor do Alembic

**Problema.** [main.py:14](../backend/app/main.py) executa `Base.metadata.create_all()`
no lifespan. A migration `0001_initial` existe mas nunca roda. Consequências concretas:
o banco de dev foi criado pelo `create_all` e não tem a tabela `alembic_version`, então
a primeira `alembic upgrade head` vai tentar criar tabelas que já existem e falhar;
e `create_all` não altera tabelas existentes — adicionar uma coluna ao modelo hoje
simplesmente não aparece no banco, e o erro surge como `no such column` em runtime.

**Proposta.**

1. `alembic stamp 0001_initial` no banco existente, para marcá-lo como já migrado.
2. Remover `create_all` do lifespan.
3. Escolher a política de migração: `alembic upgrade head` como passo explícito de
   deploy (command do `docker-compose` ou script de start), **não** dentro do lifespan —
   migração automática no boot é armadilha quando houver mais de um processo.
4. Documentar o passo `alembic upgrade head` no README.

**Arquivos.** `app/main.py`, `backend/Dockerfile` ou script de entrada, `README.md`.
**Aceite.** Banco novo criado do zero só com `alembic upgrade head` sobe o app
funcionando; `alembic_version` existe no banco de dev.
**Esforço.** M. **Depende de.** F0.1.

## F1.2 — Alembic apontando para o banco certo

**Problema.** [alembic.ini:4](../backend/alembic.ini) tem
`sqlalchemy.url = sqlite:///data/bff_ai.db`, um caminho **relativo ao cwd**. Rodar
`alembic` de fora de `backend/` cria ou migra um banco diferente do que o app usa —
[config.py](../backend/app/core/config.py) resolve `DATA_DIR` de forma absoluta.

**Proposta.** Remover a URL do `.ini` e injetá-la em
[alembic/env.py](../backend/alembic/env.py) via
`config.set_main_option("sqlalchemy.url", DATABASE_URL)`, importando de `app.core.config`.
Habilitar também `render_as_batch=True` no `context.configure` — sem isso qualquer
`ALTER COLUMN` futuro falha no SQLite, e as Fases 3 e 4 dependem de alterar tabelas.

**Aceite.** `alembic current` devolve a mesma revisão de qualquer cwd.
**Esforço.** P. **Depende de.** F1.1.

## F1.3 — Teste de coerência entre modelos e migrations

**Problema.** Nada impede que alguém edite `domain/models.py` e esqueça a migration.
É exatamente a falha que F1.1 acaba de consertar — precisa de trava.

**Proposta.** Teste que sobe um SQLite temporário, roda `upgrade head` e chama
`alembic.autogenerate.compare_metadata`; falha se houver qualquer diff.

**Aceite.** Teste verde hoje, vermelho ao adicionar uma coluna sem migration.
**Esforço.** M. **Depende de.** F1.2, F6.1.

---

# Fase 2 — Providers realmente plugáveis

## F2.1 — Mover conhecimento específico de provider para o adapter

**Problema.** A regra 5 do README ("provider é adapter") já está furada. Existe lógica
de NVIDIA NIM em dois lugares que não são o adapter:

- [chat.py:78](../backend/app/services/chat.py) — `max_tokens=None if provider.kind == "nvidia_nim" ...`
- [chat.py:80](../backend/app/services/chat.py) — `reasoning_effort="none" if provider.kind == "nvidia_nim" ...`
- [models.py:21](../backend/app/api/routes/models.py) — a mesma regra de `max_tokens`, duplicada na serialização

Adicionar um terceiro provider hoje exige editar o `ChatService` e uma rota — que é
precisamente o que a regra prometia evitar.

**Proposta.** Dar ao adapter uma descrição declarativa de capacidades:

```python
@dataclass(frozen=True)
class ProviderCapabilities:
    honors_max_tokens: bool          # NIM: False — reasoning divide o orçamento
    default_reasoning_effort: str | None
    supports_usage_in_stream: bool
```

O `ChatService` passa a perguntar `adapter.capabilities` em vez de comparar strings, e a
rota `/models` usa a mesma função de normalização. O `if kind == "nvidia_nim"` some do
código de aplicação.

**Arquivos.** `services/llm/base.py`, `ollama.py`, `nvidia_nim.py`, `chat.py`,
`api/routes/models.py`.
**Aceite.** Uma busca por `nvidia_nim` em `app/` só encontra ocorrências dentro de
`services/llm/` e dos schemas de validação.
**Esforço.** M.

## F2.2 — Registry de adapters no lugar do `if/elif`

**Problema.** [factory.py](../backend/app/services/llm/factory.py) é um `if/elif`, e o
`Literal["ollama", "nvidia_nim"]` do [schemas.py](../backend/app/domain/schemas.py)
repete a lista. Dois pontos para editar a cada provider novo.

**Proposta.** Registry `dict[str, type[LLMAdapter]]` populado no módulo, com os
`Literal` derivados das chaves. **Sem** autodiscovery mágico — a regra "sem fallback"
exige que provider desconhecido continue levantando `UnsupportedProviderError`, o que o
registry preserva naturalmente.

**Aceite.** Adicionar um provider fictício em teste exige tocar um único arquivo; o teste
existente de "sem fallback" continua verde.
**Esforço.** P. **Depende de.** F2.1.

---

# Fase 3 — Robustez do fluxo de chat

Hoje o caminho feliz funciona bem e todo caminho infeliz perde dados.

## F3.1 — Persistir resposta parcial em erro ou desconexão

**Problema.** Em [chat.py](../backend/app/services/chat.py), se o `adapter.stream()`
levantar no meio, o `except` emite o evento `error` e dá `return` — os chunks já
acumulados são descartados. A mensagem do usuário **já foi commitada**, então a conversa
fica com um turno pendurado sem resposta. O frontend agrava: o `catch` em
[App.tsx](../frontend/src/App.tsx) recarrega a conversa do servidor, apagando da tela o
texto parcial que a usuária estava lendo.

**Proposta.** Dar estado explícito à mensagem do assistente:

- adicionar `Message.status` (`complete` | `failed` | `cancelled`) e `Message.error`;
- gravar a mensagem parcial com o status correspondente **antes** de emitir `error`;
- o frontend renderiza a bolha parcial com marca visual de "interrompida" e um botão
  de regenerar.

**Arquivos.** `domain/models.py` (+ migration), `schemas.py`, `services/chat.py`,
`ChatView.tsx`, `App.tsx`.
**Aceite.** Derrubar o Ollama no meio de uma resposta deixa o texto parcial visível e
persistido, marcado como interrompido, com o erro acessível.
**Esforço.** M. **Depende de.** F1.1.

## F3.2 — Cancelamento de ponta a ponta

**Problema.** Não existe `AbortController` no [api.ts](../frontend/src/lib/api.ts).
Trocar de conversa ou fechar a aba no meio de um stream deixa o `fetch` e a geração no
provider rodando até o fim. Não há botão de parar.

**Proposta.** `AbortController` no cliente, botão "parar" no composer, e no backend
tratar `asyncio.CancelledError` / cliente desconectado gravando a mensagem como
`cancelled` (reaproveita F3.1).

**Aceite.** Botão de parar interrompe a geração; a mensagem fica salva como cancelada.
**Esforço.** M. **Depende de.** F3.1.

## F3.3 — Preencher `prompt_tokens` e `completion_tokens`

**Problema.** As colunas existem em [models.py](../backend/app/domain/models.py) e o
`MessageRead` as expõe, mas **nada nunca as escreve**. São sempre `null` — um campo que
mente sobre existir.

**Proposta.** Pedir `stream_options: {"include_usage": true}` no payload quando
`capabilities.supports_usage_in_stream` (F2.1) e ler o frame final de `usage`. Onde o
provider não suportar, manter `null` conscientemente e documentar. Alternativa honesta
se nenhum provider cooperar: apagar as colunas em vez de deixá-las decorativas.

**Aceite.** Mensagens novas via NIM trazem contagem de tokens na resposta da API.
**Esforço.** M. **Depende de.** F2.1.

## F3.4 — Tirar I/O bloqueante do event loop

**Problema.** `stream_message` é um gerador **async** que executa `Session` **síncrona**
do SQLAlchemy (`self.db.commit()`, queries de histórico). Cada operação de banco bloqueia
o event loop enquanto o stream corre. Com uma usuária só o impacto é invisível; com duas
abas abertas, uma conversa trava a outra. Além disso o ciclo de vida da sessão fica
amarrado ao término do streaming, que pode durar minutos.

**Proposta.** Separar claramente as três etapas: (a) preparar contexto e persistir a
mensagem do usuário — síncrono, antes de abrir o stream; (b) streamar — sem tocar no
banco; (c) persistir o resultado — em `run_in_threadpool` ou numa sessão nova e curta.
A migração completa para `AsyncSession` é possível, mas é mudança maior e pertence à
Fase 8.

**Aceite.** Nenhuma chamada de `Session` dentro do laço `async for` do stream.
**Esforço.** M. **Depende de.** F3.1.

## F3.5 — Regenerar e editar mensagem

**Problema.** Não há como refazer uma resposta ruim nem corrigir a própria pergunta —
só mandar outra mensagem, poluindo o histórico que volta ao modelo a cada turno.

**Proposta.** `POST /conversations/{id}/messages/{message_id}/regenerate` que descarta a
resposta a partir daquele ponto e re-streama. Casa naturalmente com F3.1.

**Aceite.** Regenerar substitui a última resposta sem duplicar o turno do usuário.
**Esforço.** M. **Depende de.** F3.1.

---

# Fase 4 — Contexto e memórias com orçamento

## F4.1 — Extrair um `ContextBuilder` do `ChatService`

**Problema.** A montagem do prompt está embutida em `stream_message`: persona, bloco de
memórias e histórico completo concatenados inline. É a parte do sistema que mais vai
mudar (memórias, RAG, anexos, ferramentas) e é a única sem camada própria — e é
impossível testá-la sem simular um stream inteiro.

**Proposta.** `services/context.py` com
`build_messages(conversation, memories, budget) -> list[ChatMessage]`, puro e testável.
O `ChatService` vira orquestração.

**Aceite.** Teste unitário verifica a ordem e o conteúdo do prompt sem tocar em rede.
**Esforço.** M.

## F4.2 — Orçamento de tokens e truncamento de histórico

**Problema.** O histórico **inteiro** é reenviado a cada mensagem, sem limite. Uma
conversa longa cresce até estourar a janela de contexto do modelo, e a falha aparece
como um erro cru do provider — a conversa simplesmente para de funcionar e não há como
se recuperar pela UI.

**Proposta.** Orçamento de tokens por `ModelConfig` (campo `context_window`), estimativa
de tokens, e política de truncamento explícita: manter system prompt + memórias +
as N mensagens mais recentes que couberem, sinalizando na UI que o contexto foi cortado.
Sumarização do trecho antigo fica para depois — truncar com aviso já resolve a falha.

**Aceite.** Conversa com 200 mensagens continua respondendo; a UI indica o corte.
**Esforço.** G. **Depende de.** F4.1.

## F4.3 — Escopo e limite para memórias

**Problema.** [chat.py](../backend/app/services/chat.py) carrega **todas** as memórias
ativas, sem filtro nem teto, e injeta em toda requisição. Memória é global: não há
escopo por persona nem por conversa. Cinquenta memórias viram um system prompt gigante
em cada turno, incluindo as irrelevantes.

**Proposta.** Adicionar `Memory.scope` (`global` | `persona` | `conversation`) com FK
opcional, filtrar na montagem do contexto e aplicar um teto de N memórias/tokens.
Ordenação por relevância semântica fica para uma fase futura — escopo + teto já elimina
o pior do problema.

**Aceite.** Memória marcada como de uma persona não aparece no prompt de outra.
**Esforço.** M. **Depende de.** F4.1, F1.1.

---

# Fase 5 — Contrato de erro e observabilidade

## F5.1 — Erro estruturado em vez de `str(exc)`

**Problema.** Erros vazam a representação crua da exceção para o cliente. Em
[openai_compatible.py](../backend/app/services/llm/openai_compatible.py) o `RuntimeError`
carrega **800 caracteres do corpo da resposta do provider**, que vão inteiros para o
evento SSE `error` e para a tela. Em
[providers.py](../backend/app/api/routes/providers.py), `HTTPException(502, str(exc))`
faz o mesmo. A usuária vê um JSON de erro da NVIDIA; o app não consegue distinguir
"chave inválida" de "modelo inexistente" de "Ollama desligado" para reagir de forma útil.

**Proposta.** Hierarquia de exceções de domínio (`ProviderUnreachable`,
`ProviderAuthError`, `ModelNotFound`, `ContextOverflow`) levantadas no adapter, com
handler no FastAPI e payload `{code, message, provider_detail}`. A UI passa a dar a ação
certa: "sua API key foi recusada — abra Configurações → LLM".

**Aceite.** Chave inválida produz `code: "provider_auth"` e uma mensagem acionável.
**Esforço.** M.

## F5.2 — Logging estruturado

**Problema.** Não há uma única chamada de log no backend. Quando um stream falha, a
única evidência é o texto que apareceu na tela — e, até F3.1, nem isso era guardado.

**Proposta.** `logging` configurado no `main.py`, com INFO por requisição de chat
(conversa, provider, modelo, latência, tokens) e ERROR com traceback nas falhas de
provider. Sem enviar nada para fora da máquina.

**Aceite.** Falha de provider deixa rastro no stdout do uvicorn com contexto suficiente
para diagnosticar sem reproduzir.
**Esforço.** P.

## F5.3 — Health check honesto

**Problema.** O [`/health`](../backend/app/main.py) devolve `{"status":"ok"}`
incondicional. Não diz se o banco abre, se a `APP_MASTER_KEY` consegue decifrar os
secrets guardados ou se o provider ativo responde — que são as três coisas que realmente
quebram. Hoje uma master key trocada só falha na hora de enviar a primeira mensagem,
com erro obscuro.

**Proposta.** `/health` raso (processo vivo) + `/health/ready` que checa banco, cipher e,
opcionalmente, o provider ativo.

**Aceite.** Trocar a master key faz `/health/ready` apontar o problema explicitamente.
**Esforço.** P.

---

# Fase 6 — Testes

Hoje são 2 testes: a factory sem fallback e o round-trip do cipher. Nenhuma rota, nenhum
fluxo de chat, nenhum parsing de SSE.

## F6.1 — Infra de teste

**Proposta.** `conftest.py` com SQLite em arquivo temporário migrado via Alembic,
override de `get_db`, `TestClient` e um `FakeAdapter` que emite chunks determinísticos
(e um que falha no meio, para F3.1). Sem rede em nenhum teste.

**Aceite.** `pytest` roda em segundos, isolado do `backend/data/bff_ai.db` real.
**Esforço.** M. **Depende de.** F1.2.

## F6.2 — Testes de comportamento crítico

Cobrir exatamente as regras que o README declara inegociáveis, porque são as que não
podem regredir em silêncio:

- provider desconhecido → erro, nunca fallback;
- conversa mantém o `model_config_id` original mesmo quando o modelo ativo global muda;
- falha no meio do stream → parcial persistido, `error` emitido, nenhuma segunda tentativa;
- `remote_models` nunca devolve a API key, nem dentro de uma mensagem de erro;
- persona/modelo em uso não podem ser apagados (409).

**Esforço.** M. **Depende de.** F6.1.

## F6.3 — Teste do parsing de SSE do cliente

**Problema.** [api.ts](../frontend/src/lib/api.ts) faz parsing manual de frames SSE com
split em `\n\n` e regex. Funciona, mas é frágil a qualquer mudança de formato e não tem
nenhuma cobertura.

**Proposta.** Vitest com casos de frame partido entre chunks, `[DONE]`, evento de erro e
frame vazio. É o único teste de frontend que recomendo agora.

**Esforço.** M.

---

# Fase 7 — Frontend estrutural

## F7.1 — Tirar o estado de dentro do `App.tsx`

**Problema.** [App.tsx](../frontend/src/App.tsx) concentra sete `useState`, todo o
carregamento, o streaming e o tratamento de erro. Cada feature nova entra no mesmo
componente.

**Proposta.** Hooks por domínio — `useConversations`, `useSettings`, `useChatStream` —
com o `App` virando composição. Sem introduzir Redux/Zustand: o app não precisa, e a
simplicidade do frontend é uma qualidade a preservar.

**Esforço.** M.

## F7.2 — Erro no lugar certo

**Problema.** Toda falha vira o mesmo `toast` genérico, inclusive erro de stream que
deveria aparecer ancorado na mensagem que falhou.

**Proposta.** Consumir o `{code, message}` de F5.1: erro de conversa renderiza junto da
bolha interrompida com ação de retry; erro de configuração abre o painel certo.

**Esforço.** M. **Depende de.** F5.1, F3.1.

## F7.3 — Custo de renderização durante o streaming

**Problema.** Cada token faz `setActive` recriando o array inteiro de mensagens, e o
`useEffect` do [ChatView](../frontend/src/features/chat/ChatView.tsx) dispara
`scrollIntoView({behavior:'smooth'})` a cada token. Em respostas longas isso rerenderiza
toda a lista dezenas de vezes por segundo.

**Proposta.** Buffer de streaming isolado num componente próprio (só ele rerenderiza) e
autoscroll com throttle, respeitando `prefers-reduced-motion` e parando se a usuária
rolou para cima.

**Esforço.** M.

## F7.4 — Markdown e acessibilidade

**Problema.** Resposta de LLM é markdown e hoje é renderizada como texto cru
(`white-space: pre-wrap`). Blocos de código chegam como texto com crases. Além disso não
há `aria-live`: leitor de tela não anuncia a resposta chegando.

**Proposta.** Renderizador de markdown com sanitização (nunca `dangerouslySetInnerHTML`
sem sanitizar), highlight de código, botão de copiar, e `aria-live="polite"` na região
de mensagens.

**Esforço.** M.

---

# Fase 8 — Condicional: se sair do modo local

**Só executar se o app deixar de ser single-user na própria máquina.** Enquanto for
local, estes itens são custo sem benefício — e o README já os trata como futuro.

- **F8.1 — Autenticação e modelo de usuária.** Hoje não há nenhuma; toda rota é aberta.
  Exige `user_id` em conversas, personas e memórias, o que toca o schema inteiro.
- **F8.2 — PostgreSQL + `AsyncSession`.** Resolve F3.4 na raiz e remove o limite de
  escrita concorrente do SQLite.
- **F8.3 — Rate limiting e timeouts por usuária.** Os timeouts de 120s do
  [openai_compatible.py](../backend/app/services/llm/openai_compatible.py) são
  aceitáveis para uma pessoa e insustentáveis para várias.
- **F8.4 — CORS e origens por configuração.** [main.py](../backend/app/main.py) tem
  `localhost:5173` hardcoded.

---

# Fora de escopo agora

Registrados para não serem redescobertos como "achado novo" depois:

- **Ferramentas/MCP.** Grande, e depende de a Fase 4 (orçamento de contexto) estar pronta.
- **Multimodal e anexos.** Depende de storage de arquivos, que não existe.
- **Sumarização automática de histórico.** F4.2 trunca com aviso; sumarizar é otimização.
- **Busca semântica de memórias.** Escopo + teto (F4.3) resolve o problema real primeiro.
- **`Message.role` como enum no banco.** É `String(20)` livre; incorreto, mas nada hoje
  escreve um role inválido. Vai junto da próxima migration que tocar `messages` (F3.1).

---

# Ordem de execução sugerida

```text
F0.2 → F0.1 → F0.3 → F0.4          higiene, commit inicial
F1.1 → F1.2                        schema com fonte única   ← maior risco evitado
F6.1                               infra de teste
F2.1 → F2.2                        providers plugáveis
F3.1 → F3.2 → F3.4                 chat que não perde dados
F5.1 → F5.2 → F5.3                 erros e observabilidade
F6.2 → F1.3 → F6.3                 trava de regressão
F4.1 → F4.2 → F4.3                 contexto com orçamento
F3.3 → F3.5                        tokens e regenerar
F7.1 → F7.2 → F7.3 → F7.4          frontend
```

**Primeiro corte recomendado:** Fase 0 inteira, F1.1, F1.2 e F6.1. São as quatro coisas
que tornam todo o resto seguro de mexer — sem git não há reversão, sem Alembic a próxima
coluna quebra o banco, e sem infra de teste cada refactor das fases seguintes é feito
no escuro.
