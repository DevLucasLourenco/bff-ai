# Spec — Fashion Module

Status: arquitetura e entregas incrementais. Esta spec corresponde item a item ao [PLANO_FASHION_MODULE.md](PLANO_FASHION_MODULE.md): `S01` ↔ `P01` até `S15` ↔ `P15`.

## Contexto verificado no projeto

O BFF AI é um app local React/Vite + FastAPI + SQLite. Uma conversa usa a persona e o modelo gravados nela e entrega `meta`, `token`, `ui_object`, `error` e `done` por SSE. O módulo Fashion já possui dono local, migrations, upload normalizado em WebP, guarda-roupa, perfil, looks, anexos no chat, tools, objetos visuais e ações confirmáveis. A capacidade de tools é configurada por modelo e o NIM ativo foi verificado para chamá-las. Alembic é a única fonte do schema. A primeira fatia de S15 está implementada: uma URL direta de imagem vira cópia WebP local, com fonte, status da coleção e proteção de rede; importação de páginas, busca e extensão seguem pendentes. O plano de avatar 3D em `docs/` trata de **roupas de uma persona virtual** e está não iniciado; o guarda-roupa desta spec contém **peças reais da pessoa usuária** e não depende de VRM, sprites ou WebGL.

Decisões de produto: o módulo começa com um único dono local, sem fingir que há isolamento seguro entre contas. A estrutura de dados terá `owner_id` desde o início; múltiplas contas só serão expostas após autenticação e autorização reais. O chat geral continuará funcionando com modelos que não suportem tools. O modo Fashion e suas ações terão erro de capacidade explícito nesses modelos, sem resposta que simule dados consultados. Busca de produtos e tendências só aparece quando houver integração web real configurada.

## S01 — Fronteira e fluxo do módulo

```text
mensagem da usuária
  → ChatService / orquestrador
  → adapter do modelo com capacidade de tool calling
  → FashionToolRegistry (validação, autorização, limites)
  → serviços Fashion → SQLite / mídia local / busca web real
  → ToolResult tipado → continuação do modelo
  → texto + Chat UI Objects montados pelo backend
  → SSE → componentes React
```

O modelo escolhe a intenção e solicita tools por nome. Ele não escreve SQL, não escolhe `owner_id`, não monta componentes React e não define preço, link ou ID de peça. Serviços determinísticos consultam fatos; o backend constrói objetos visuais a partir dos resultados validados. Respostas sem tools continuam no fluxo atual. Toda escrita solicitada no chat passa pela mesma camada de serviço e validação das rotas REST.

## S02 — Dono, persistência e entidades

`users(id, created_at)` terá uma linha local inicial. Um resolvedor de principal fornece o dono ao request; nenhum argumento da LLM pode substituí-lo. A versão local só habilita `id=1`. Antes de oferecer mais contas, adicionar login, escopo por dono em todas as consultas e migração das settings globais relevantes.

Entidades novas, sempre com `owner_id` quando contêm dados pessoais:

| Entidade | Campos essenciais e regra |
|---|---|
| `wardrobe_items` | ID, dono, nome, categoria/subcategoria, cor normalizada e texto original, material, marca, tamanho, estilo, estações, ocasiões, formalidade, tags, `image_asset_id?`, origem manual/visão, confiança por atributo, estado ativo/arquivado, timestamps. Campos desconhecidos são `null`, nunca inventados. |
| `fashion_assets` | ID, dono, caminho interno gerado pelo servidor, MIME validado, dimensões, hash, tamanho, timestamps. O caminho absoluto não sai na API. |
| `style_profiles` | Um por dono, preferências explícitas, restrições, orçamento/moeda padrão, revisão e timestamps. |
| `style_signals` | Dono, tipo (`saved`, `rejected`, `worn`, `purchase`, `manual`), entidade referenciada, atributo, peso, confiança, data e revogação. Derivação auditável do perfil; rejeição não some. |
| `outfits` / `outfit_items` | Look salvo, dono, título, ocasião, estilo, explicação, status; itens referenciam peça do guarda-roupa ou snapshot externo, com slot, ordem e atributos congelados. Não perder um look se uma peça for arquivada. |
| `outfit_feedback` / `wear_events` | Like/dislike, motivo opcional, data de uso, IDs de peças; frequência e últimas utilizações são agregados, não texto gerado. |
| `look_plans` | Dono, data e fuso, evento, ocasião, `outfit_id?`, status; conflito e alteração de data são explícitos. |
| `product_observations` / `trend_observations` | Snapshot de resultado externo, URL canônica, fonte, `fetched_at`, validade, dados estruturados e status de verificação; nunca confundidos com itens possuídos. |
| `tool_runs` | Conversa, turno, nome e versão da tool, argumentos saneados, status, duração, IDs dos dados usados, chave de idempotência e erro seguro. |
| `message_ui_objects` | `message_id`, posição, tipo, versão do schema, payload validado, proveniência e timestamps. FK com cascade na regeneração da última resposta. |
| `external_service_configs` | Busca web configurada, segredo cifrado com `SecretCipher`, estado e configuração não secreta. |

Usar migrations Alembic, índices `(owner_id, status/categoria/data)` e FKs; testar coerência models × migrations. JSON fica restrito a atributos flexíveis e snapshots versionados. Identidade, vínculos e fatos consultáveis ficam em colunas/tabelas. Arquivar peça preserva histórico; excluir foto pode exigir remoção física coordenada com a transação e política de retenção.

## S03 — Mídia e entrada por fotografia

Upload vinculado ao principal local para `POST /api/fashion/assets`: `multipart/form-data`, JPEG/PNG/WebP, limite inicial de 10 MB e dimensões máximas documentadas. Validar bytes e decodificação, gerar nome aleatório, remover metadados EXIF, normalizar orientação, criar miniatura e guardar em `backend/data/fashion/`; entregar mídia somente por rota que verifica o dono. O app local ainda não tem autenticação: antes de expor o servidor a outros usuários, adicioná-la. Não aceitar URL arbitrária como arquivo local. Cadastro manual aceita imagem opcional. A foto original e a sugestão da visão ficam separadas para revisão antes de gravar atributos.

## S04 — Protocolo de tools e capacidades de modelo

Evoluir `LLMAdapter` para eventos tipados `TextDelta`, `ToolCall(name, call_id, arguments)`, `Usage` e `Finish`, preservando streaming de texto. O adapter OpenAI compatível deve reconstruir argumentos fragmentados do stream e entregar apenas chamadas completas. `ProviderCapabilities` informa suporte do protocolo; `ModelConfig` registra capacidade verificada por modelo (`tools`, `vision`) e data da verificação. Não inferir suporte pelo nome ou apenas pelo provider.

O `FashionToolRegistry` fornece definições JSON Schema de input e executores tipados. O orquestrador valida nome, argumentos, permissão, limites e resultado. Cada chamada recebe no máximo uma execução por `call_id` e chave de idempotência derivada do turno e operação; operações de escrita aceitam retry sem duplicar, inclusive após regeneração. Limites iniciais: até 4 rodadas e 8 chamadas por turno, tempo máximo por tool e limite de resultados. Exceder retorna erro tipado. Cancelamento interrompe chamadas pendentes quando possível; uma escrita já confirmada no banco continua registrada e é mostrada no retorno. Nenhum fallback de provider nem de modo de execução é silencioso. O modelo selecionado é mantido durante todas as rodadas do mesmo turno. Ações e modo Fashion exigem modelo com tools verificadas; chat livre em modelo sem tools não tem acesso a dados Fashion e recebe instrução explícita de não alegar consulta ao guarda-roupa ou à web.

Contrato comum:

```json
{
  "name": "get_wardrobe",
  "version": 1,
  "input_schema": {"type": "object", "properties": {"category": {"type": "string"}, "limit": {"type": "integer"}}},
  "result": {"status": "ok|empty|unavailable|error", "data": {}, "facts": [], "source_refs": [], "ui_hints": []}
}
```

`facts` são valores apurados pelo serviço. `source_refs` aponta para registros locais ou fontes web verificáveis. `ui_hints` sugere tipo de objeto, mas o servidor decide o payload final. Erros de validação ou indisponibilidade são visíveis ao modelo e à UI, sem transformar ausência de dado em resultado positivo.

Convenções dos schemas mínimos abaixo: `?` = opcional; `string` tem limite de comprimento; `id` = inteiro positivo validado contra o dono; `date` = ISO 8601; `money` = `{amount: decimal-string, currency: ISO-4217}`; listas têm tamanho máximo; `cursor` é opaco. `ToolResult.data` usa uma união tipada, nunca texto livre: `WardrobePage{items: WardrobeItemSummary[], total: int, next_cursor?: string}`, `OutfitResult{outfits: OutfitDraft[]}`, `ProfileResult{explicit: object, inferred: object, evidence: SourceRef[]}`, `SearchResult{observations: WebObservation[], fetched_at: date}` ou `MutationResult{entity_id: id, revision: int}`. `WardrobeItemSummary` sempre contém `id`, `name`, `category`, `owned: true`; `OutfitDraft` contém slots e IDs de peças; `WebObservation` contém URL, fonte e data, com preço opcional. O schema de cada tool restringe campos adicionais e valida tipos, enumerações e limites antes da execução.

## S05 — Contrato e ciclo de vida dos Chat UI Objects

Envelope versionado comum:

```json
{
  "schema_version": 1,
  "type": "wardrobe_view",
  "id": "uuid-do-objeto",
  "title": "Meu guarda-roupa",
  "subtitle": "24 peças",
  "data": {},
  "actions": [{"id": "open_item", "label": "Ver peça", "target": {"item_id": 42}}],
  "source": [{"kind": "wardrobe", "ref_id": "42", "observed_at": "2026-09-19T12:00:00Z"}],
  "metadata": {"created_at": "2026-09-19T12:00:00Z", "state": "snapshot"}
}
```

Cada `type` tem schema próprio, validado no backend e discriminated union no TypeScript. `data`, `actions` e `source` não são JSON sem contrato. Os tipos v1 são `wardrobe_view`, `wardrobe_item`, `outfit_carousel`, `outfit_detail`, `product_carousel`, `trend_board` e `look_calendar`. Uma listagem pode ter filtros, paginação e estado vazio; um snapshot antigo pode indicar que os dados mudaram e oferecer atualização. O objeto é persistido ligado à mensagem do assistente e volta em `GET /conversations/{id}`. No SSE, `ui_object` só é enviado após validação e persistência; `done` contém IDs da mensagem e dos objetos. Falha/cancelamento preserva texto parcial com status atual e não publica objeto incompleto; uma mutação já confirmada fica visível em recibo de tool no histórico, mesmo se a continuação da LLM falhar. Regenerar remove a resposta anterior e seus objetos, preservando entidades Fashion já confirmadas, com execução idempotente.

Ações são comandos permitidos pelo servidor, não URLs ou código fornecidos pelo modelo. `POST /api/fashion/actions` recebe `object_id`, `action_id`, alvo e chave de idempotência; revalida dono, estado e revisão antes de alterar dados. Links externos usam apenas URL HTTP(S) validada.

## S06 — Tools de guarda-roupa

| Tool | Input mínimo | Output mínimo / responsabilidade |
|---|---|---|
| `get_wardrobe` | filtros `category?`, `color?`, `style?`, `season?`, `occasion?`, `query?`, `cursor?`, `limit<=50` | IDs e resumo de peças reais, total, próximo cursor; gera `wardrobe_view`. |
| `get_wardrobe_item` | `item_id` | peça, mídia, atributos confirmados, uso agregado e looks ligados; `wardrobe_item`. |
| `add_wardrobe_item` | `name`, `category`, atributos opcionais, `asset_id?`, `idempotency_key` | ID criado e atributos efetivos; falha se mídia não pertence ao dono. |
| `update_wardrobe_item` | `item_id`, patch permitido, `expected_revision` | peça atualizada ou conflito 409; histórico preservado. |
| `archive_wardrobe_item` | `item_id`, `expected_revision` | estado arquivado; ação destrutiva no chat pede confirmação explícita na UI. |
| `record_wear` | `item_ids` ou `outfit_id`, data, `idempotency_key` | evento gravado e novas contagens. |

O frontend também usa rotas REST equivalentes para grid, busca, filtros, cadastro e edição, sem depender da LLM para operações diretas. Combinações e número de looks são calculados a partir de itens vinculados, nunca por texto livre.

## S07 — Perfil de estilo que evolui

| Tool | Input mínimo | Output mínimo / responsabilidade |
|---|---|---|
| `get_style_profile` | nenhum | preferências explícitas, inferidas, restrições e evidências com confiança. |
| `update_style_profile` | campos explícitos e revisão | salva escolha da pessoa; preferência explícita prevalece sobre inferência. |
| `record_outfit_feedback` | `outfit_id`, `liked|rejected`, motivo opcional | sinal auditável e perfil recalculado. |

Sinais vêm de peças cadastradas, looks salvos/rejeitados, uso e compras registradas. Uma compra só conta quando declarada ou confirmada; clicar em produto não é compra. Inferências têm peso, origem e opção de corrigir/remover. Falta de sinais deixa atributo desconhecido. Memórias de chat atuais não viram fonte de verdade para peças e preços; o perfil estruturado é lido sob orçamento de contexto e apenas quando relevante.

## S08 — Looks, Mix & Match e calendário

| Tool | Input mínimo | Output mínimo / responsabilidade |
|---|---|---|
| `create_outfits` | ocasião, estilo, estação, clima informado?, `limit<=6`, orçamento? | propostas com IDs de peças existentes, slots, razão e lacunas; `outfit_carousel`. |
| `mix_and_match` | `anchor_item_id`, variações desejadas, `limit<=6` | combinações que incluem a peça base e usam o inventário atual. |
| `swap_outfit_item` | `outfit_id` ou draft ID, slot, `replacement_item_id?` | nova versão validada do look; sem mutar outro look por acidente. |
| `save_outfit` | draft ID, título?, idempotência | `outfit_id` estável, `outfit_detail`. |
| `get_outfit` | `outfit_id` | composição, status das peças e histórico de uso. |
| `plan_outfit` | data/fuso, evento, ocasião, `outfit_id?` | entrada persistida e `look_calendar`. |

Motor determinístico valida slots obrigatórios, estação, ocasião, restrições e disponibilidade dos IDs. A LLM pode redigir o motivo estético, mas não inventa referências de peça. Variações são rankings reproduzíveis com critérios e versão do algoritmo. Peça externa aparece marcada como lacuna, nunca como possuída. Sem dados de clima, o look informa que clima não foi considerado. `look_calendar` usa data e fuso da pessoa, não previsão inventada.

## S09 — Pesquisa web e tendências

| Tool | Input mínimo | Output mínimo / responsabilidade |
|---|---|---|
| `search_fashion_web` | consulta, país/idioma, `limit` | fontes HTTP(S), título, trecho, URL, `fetched_at`; referências gerais. |
| `get_fashion_trends` | período, região, categoria? | tendência com fontes datadas, evidência e compatibilidade calculada com perfil/guarda-roupa; `trend_board`. |

Criar interface `FashionSearchProvider` e implementar ao menos um provedor de busca **real** antes de declarar estas tools disponíveis. Credencial, se houver, fica cifrada no banco. Web search não significa confiar no texto encontrado: páginas são dados não confiáveis, não instruções. Normalizar URLs, limitar domínios/redirecionamentos e volume de resposta, registrar fonte e data, evitar SSRF ao buscar metadados/imagens. Tendência sem fonte atual e data vira `unavailable`, nunca “está em alta” por conhecimento do modelo. Preferência pessoal e tendência são mostradas em campos separados; compatibilidade baixa pode resultar em não recomendar.

## S10 — Compras inteligentes e produtos reais

| Tool | Input mínimo | Output mínimo / responsabilidade |
|---|---|---|
| `analyze_wardrobe_gaps` | ocasião/estilo?, orçamento?, moeda | lacunas ranqueadas por ganho marginal calculado, itens que já combinam e explicação do método. |
| `search_products` | lacuna/categoria, país, tamanho/cor?, preço máximo? | observações reais com loja, URL, imagem?, preço+moeda?, disponibilidade?, `fetched_at`; `product_carousel`. |
| `compare_product_to_wardrobe` | `product_observation_id` | IDs de peças compatíveis, `compatible_owned_item_count`, looks novos estimados e regra de contagem. |

Fluxo padrão de “tenho R$500”: ler inventário e perfil → calcular lacunas → buscar produtos que as preencham → verificar preço e compatibilidade → mostrar opções com proveniência. `compatible_owned_item_count` conta **peças distintas** que formam ao menos uma combinação válida; `estimated_new_outfit_count` é métrica separada, com limite/algoritmo exibido. Contagem é `null` se não houver dados suficientes, não zero fabricado. Preço tem valor, moeda, loja, URL e horário de observação; não é garantia de preço atual nem de estoque. Se a busca voltar sem preço ou tamanho, mostrar “não informado”. Sem integração ou resultado verificável, não emitir `product_carousel` de produtos imaginados.

## S11 — Análise de imagem por visão

| Tool | Input mínimo | Output mínimo / responsabilidade |
|---|---|---|
| `analyze_clothing_image` | `asset_id`, capacidade de visão verificada | sugestões de categoria/cor/material/estilo com confiança e campos desconhecidos; nunca grava peça automaticamente. |

Primeira entrega permite upload e cadastro manual. A visão entra como capacidade separada: adapter/modelo verificados, autorização para enviar imagem ao provider externo e revisão humana dos atributos antes de `add_wardrobe_item`. Erro ou ausência de visão mantém o fluxo manual. Não inferir tamanho, marca ou material sem evidência legível; preservar proposta e correção para avaliar qualidade, sem promover hipótese a fato.

## S12 — Interface e ações visuais

`ChatObjectRenderer` usa registry local `type → componente`; tipo/versão desconhecido mostra fallback acessível com título, texto e fonte, sem executar ações. `wardrobe_view`: grid, total, categorias, busca, filtros, paginação, seleção, cadastro/organização. `wardrobe_item`: foto, atributos, usos, looks e ações. `outfit_carousel` e `outfit_detail`: composição por slots, origem de cada peça, salvar/trocar/variar. `product_carousel`: preço/moeda, loja, data, link e contagem compatível, com imagem opcional. `trend_board`: referência, fonte, data e ajuste ao perfil. `look_calendar`: dias/eventos/status. Estados de carregamento, vazio, dado antigo e erro são parte do contrato. Navegação por teclado, nomes acessíveis e layout móvel são critérios de aceite. O chat pode abrir um detalhe ou tela Fashion completa sem duplicar regras de negócio no React.

## S13 — Integridade, segurança e observabilidade

Separar fatos `owned`, `external_observed`, `inferred` e `user_declared` nos resultados e na UI. O orquestrador só cita preço/produto/peça a partir de `source_refs`; verificar IDs e dono ao construir o objeto e novamente ao clicar. Registrar `tool_runs` sem API keys, foto em base64 ou dados pessoais desnecessários. Limitar tamanho do contexto de tools e nunca inserir uma página web inteira como instrução de sistema. Busca e visão têm timeouts, cotas e erro tipado. Mutação precisa transação, revisão otimista e idempotência; falha parcial não cria peça duplicada. Dados de foto e histórico são apagáveis e exportáveis. Conteúdo externo aparece com data e link; UI não promete disponibilidade em tempo real.

## S14 — Extensão, rollout e critérios de aceite

Adicionar tool exige: schema versionado, executor, autorização, teste de contrato e documentação. Adicionar objeto exige schema backend, tipo TS, renderer e fallback para versões antigas. O backend é dono do contrato; a LLM não injeta JSX, CSS ou JSON livre na UI. Cada modelo configurado declara se suas tools Fashion foram verificadas; essa é a única chave de habilitação. Migrações são explícitas; backend antigo não deve abrir banco novo sem compatibilidade planejada.

## S15 — Coleção externa: peças, inspirações e produtos salvos da internet

O guarda-roupa deixa de ser apenas um inventário de upload. A usuária pode salvar uma foto ou página externa como parte da sua coleção Fashion, mas o produto distingue o que ela **possui** do que ela quer comprar ou usar como referência.

### Estados e proveniência

Cada item passa a ter `collection_status`:

| Estado | Significado | Entra em looks como |
|---|---|---|
| `owned` | peça que a usuária declarou possuir | peça disponível |
| `wanted` | produto salvo para possível compra | lacuna ou alternativa externa |
| `inspiration` | referência estética, editorial ou de look | inspiração, nunca peça possuída |
| `retired` | item preservado no histórico, fora das sugestões correntes | histórico |

Um item externo preserva `origin=external`, URL original, URL canônica, domínio, título informado/extraído, data de captura, foto normalizada localmente, método de entrada (`image_url`, `product_url`, `chat_attachment`, `browser_extension`, `search_result`) e `product_observation_id?`. Preço, moeda, disponibilidade, variante e tamanho são snapshots datados; uma atualização não reescreve o snapshot sem manter `observed_at`. A transição de `wanted` para `owned` é uma ação explícita da usuária, que registra sinal de compra.

### Formas de entrada

1. **Colar URL de imagem:** a usuária informa foto, nome e atributos opcionais; o backend captura a imagem, normaliza para WebP e cria item externo.
2. **Colar URL de produto:** um extrator obtém título, imagem principal, marca, preço e variantes quando presentes; a tela mostra revisão antes de salvar. Falta de campo permanece “não informado”.
3. **Anexo no chat:** a pessoa envia foto, conversa com a LLM e recebe `external_piece_suggestion` ou `wardrobe_suggestion`; confirmar salva o estado escolhido.
4. **Resultado de busca:** após haver provedor de busca configurado, cada card de produto oferece “Salvar na coleção”.
5. **Extensão de navegador, posterior:** captura URL, página, seleção de variante e imagem a partir do gesto explícito da usuária. Não faz scraping silencioso nem lê páginas fora do clique dela.

### Segurança da captura remota

O servidor nunca entrega uma URL remota bruta ao navegador como imagem da coleção. Na importação, ele busca somente HTTP(S), limita redirecionamentos, tempo, bytes e dimensões, resolve DNS e bloqueia loopback, IPs privados, link-local e metadados de cloud. Valida MIME pelos bytes, remove EXIF, reencoda para WebP e armazena a cópia interna; falhas mostram erro por item. O fetch ocorre apenas após ação explícita da usuária. URL de página e créditos permanecem como link de proveniência, separados do arquivo normalizado. Base64 só pode ser usado transitoriamente para enviar anexo ao modelo multimodal, nunca em SQLite.

### Dados e deduplicação

Adicionar `external_products` ou evoluir `product_observations` para uma entidade estável com `owner_id`, URL canônica, domínio, foto/asset, título, marca, snapshots de preço, status de captura, timestamps e revisão. `wardrobe_items.external_product_id?` ou uma coleção de referências liga o item à origem sem duplicar a imagem. Dedupe usa URL canônica por dono e hash da imagem como sinal auxiliar; colisão abre revisão/mesclagem, não apaga o registro mais antigo. A usuária pode editar atributos, trocar foto, arquivar, exportar e apagar a cópia local e a origem associada.

### Objetos e tools

| Tool/objeto | Papel |
|---|---|
| `propose_external_piece` → `external_piece_suggestion` | LLM apresenta item discutido, com estado inicial, fonte e botão de confirmação; não grava por conta própria. |
| `import_external_image` | recebe URL explicitamente fornecida pela usuária e cria captura validada. |
| `import_product_page` | extrai metadados permitidos de página, produz revisão e snapshot datado. |
| `save_external_piece` | confirmação idempotente do card, com `collection_status`. |
| `refresh_product_observation` | busca novamente por gesto explícito; mostra mudança de preço/estoque, nunca afirma atualização contínua. |
| `mark_piece_owned` | muda `wanted` para `owned`, preserva origem e cria sinal de compra. |

`get_wardrobe` aceita filtro por estado e sempre exibe badge “Possuo”, “Quero” ou “Inspiração”. `mix_and_match` usa `owned` por padrão; itens `wanted` aparecem como alternativa claramente marcada. Cards externos mostram foto, marca/título, link da origem, preço observado e data, quando disponíveis.

### Critérios de aceite

- Salvar imagem externa produz cópia WebP interna e card com fonte, sem URL remota servida diretamente.
- Produto salvo como `wanted` nunca aumenta contagem de peças possuídas nem é apresentado como disponível.
- Confirmar o mesmo card duas vezes é idempotente; marcar como possuído preserva URL e snapshots anteriores.
- URL privada, redirect para rede interna, conteúdo não imagem e resposta acima do limite falham sem gravar item.
- Preço/estoque não aparecem sem fonte e data; refresh mostra quando a observação mudou.
- A LLM só cria sugestão; a usuária escolhe estado e confirma no componente.

Aceite ponta a ponta: (1) cadastrar foto e peça, recarregar e reencontrar por filtro; (2) “quero usar minha jaqueta jeans” cria looks só com IDs existentes ou lacunas marcadas; (3) salvar/rejeitar/usar altera sinais rastreáveis do perfil; (4) “tenho R$500” calcula lacunas antes de resultados web reais, com fonte e data; (5) fechar/reabrir conversa mantém objetos; (6) cancelar/regenerar não duplica escrita nem publica objeto parcial; (7) provider sem tools, busca sem credencial e visão indisponível mostram estados honestos; (8) testes não acessam rede real, exceto teste de integração opt-in com provedor de busca; (9) migrations e contratos backend/frontend passam.
