# Plano — Fashion Module

Execução da [SPEC_FASHION_MODULE.md](SPEC_FASHION_MODULE.md). Status: entregas incrementais em andamento. A correspondência é estrita: `P01` entrega `S01`, `P02` entrega `S02`, e assim por diante até `P15`/`S15`. Cada item só está concluído quando seu aceite passa. O plano preserva as regras do README: modelo selecionado para cada turno, sem fallback silencioso, secrets cifrados, persona como dado, adapters isolados e streaming ponta a ponta.

## Leitura do estado atual e premissas

Os pontos de integração são `backend/app/services/chat.py` (turno e SSE), `backend/app/services/llm/` (adapter só texto), `backend/app/domain/models.py` e `schemas.py` (mensagem só texto), `backend/app/api/routes/conversations.py` (histórico), `frontend/src/lib/api.ts` (SSE), `frontend/src/lib/types.ts` e `frontend/src/features/chat/` (renderização). Não há contas, upload ou web search. As 301 imagens hoje em `frontend/src/assets/` são assets de reações da persona, ainda não rastreados pelo Git; não são fotos do guarda-roupa da pessoa e não devem ser movidos ou alterados por este plano.

O desenvolvimento pode usar fake adapters e busca simulada nos testes, mas **P09 e P10 só são aceitos após integração real de busca**. A escolha de serviço externo e credencial é uma dependência operacional desses itens, não uma licença para substituir resultados por invenção. Visão é uma etapa própria e o cadastro manual funciona antes dela.

| Etapa | Entrega | Depende de | Porte relativo |
|---|---|---|---|
| P01 | Fronteiras do módulo | — | P |
| P02 | Dono e schema Fashion | P01 | G |
| P03 | Upload e mídia | P02 | M |
| P04 | Tool calling nos adapters | P01 | G |
| P05 | Objetos persistidos e SSE | P02, P04 | G |
| P06 | Guarda-roupa e tools | P02, P03, P04, P05 | G |
| P07 | Perfil e sinais | P02, P06 | M |
| P08 | Looks e calendário | P06, P07 | G |
| P09 | Busca real e tendências | P04, P05, P07 | G |
| P10 | Compras inteligentes | P06, P08, P09 | G |
| P11 | Visão para foto | P03, P04, P06 | M/G |
| P12 | Componentes React | P05–P11 conforme tipo | G |
| P13 | Proteções e telemetria | P02–P12 | M |
| P14 | Contratos, rollout e aceite | P01–P13 | M |
| P15 | Coleção externa e captura segura | P03, P05, P06; P09 é opcional | G |

P = pequeno, M = médio, G = grande. São portes relativos, não estimativas de prazo.

## P01 ↔ S01 — Estabelecer a fronteira Fashion

**Objetivo.** Formalizar o fluxo LLM → registry → serviço → banco/web → objeto, separado do chat genérico e do avatar 3D.

**Como.** Criar pacote `backend/app/fashion/` com interfaces de serviço e registry; descrever uma única dependência do orquestrador em `ChatService`. Adicionar uma configuração de ativação local. Atualizar README com a diferença entre guarda-roupa pessoal e roupas de avatar.

**Aceite.** Diagrama e contratos no código espelham S01; desativar Fashion mantém os fluxos e testes atuais; nenhuma referência a VRM aparece nas entidades Fashion.

## P02 ↔ S02 — Migrar banco com dono e entidades

**Objetivo.** Criar a fonte de verdade persistente e preparar isolamento por pessoa.

**Como.** Adicionar `users` com principal local `id=1`, resolvedor em `api/deps.py`, modelos e migration Alembic para todas as entidades S02. Associar conversas e dados Fashion ao dono sem reatribuir conversas existentes incorretamente; migração preenche o dono local para o banco atual. Definir FKs, índices, revisões e regra de arquivo. Atualizar limpeza das fixtures e teste de coerência de schema.

**Arquivos.** `backend/app/domain/models.py`, `schemas.py`, `db/`, `api/deps.py`, `alembic/versions/`, `tests/conftest.py`.

**Aceite.** Upgrade em banco vazio e em cópia de banco legado; `alembic compare_metadata` sem diff; peça/conversa/objeto de outro dono é inacessível; arquivar não apaga histórico; rollback e backup são documentados. Mais de uma conta continua desabilitada até existir autenticação.

## P03 ↔ S03 — Implementar upload seguro e entrega de imagens

**Objetivo.** Fotos reais de peças persistem fora do banco com metadados verificáveis.

**Como.** Adicionar decoder/normalizador de imagem, limites de formato e tamanho, armazenamento sob `backend/data/fashion/`, miniatura, rotas multipart de upload/consulta/exclusão por `asset_id`. O path é gerado pelo servidor; gravação usa arquivo temporário e rename após validação. Referências órfãs são tratadas.

**Arquivos.** `backend/app/fashion/media.py`, `api/routes/fashion_assets.py`, `frontend/src/lib/api.ts`, `frontend/src/features/fashion/`.

**Aceite.** JPEG/PNG/WebP válidos sobrevivem a restart; MIME falso, arquivo grande, imagem inválida, path traversal e acesso por outro dono falham; EXIF sensível não é servido; upload sem visão permite cadastro manual.

## P04 ↔ S04 — Adicionar chamadas de tool sem quebrar streaming

**Objetivo.** Permitir que modelos compatíveis solicitem Fashion Tools estruturadas.

**Como.** Expandir protocolo de `LLMAdapter` para eventos tipados. Adaptar parser OpenAI compatível para fragmentos de `tool_calls` e `finish_reason`, com testes de chunk arbitrário e chamada múltipla. Registrar capacidades por modelo e um teste explícito de compatibilidade na configuração; apresentar estado `unknown/supported/unsupported`. Implementar `FashionToolRegistry`, schemas de argumentos, limites, timeout, cancelamento e loop de continuação no `ChatService`. Manter o mesmo modelo em todas as rodadas do turno. Preparação deve verificar capacidade antes de qualquer execução Fashion. Implementar chave de idempotência baseada em turno + operação, com `call_id` armazenado para rastreio.

**Arquivos.** `backend/app/services/llm/base.py`, `openai_compatible.py`, `runtime.py`, `services/chat.py`, `fashion/tools/`, schemas/modelos de capacidade, testes de adapter e chat.

**Aceite.** Um provider falso executa tool, devolve resultado ao mesmo modelo e retoma texto em SSE; fragmentação não corrompe JSON; modelo sem suporte em pedido Fashion gera erro claro, chat genérico segue; limite de rodadas e cancelamento funcionam; nenhuma tool dispara duas escritas no retry; não há fallback silencioso.

## P05 ↔ S05 — Persistir Chat UI Objects e ações

**Objetivo.** Objetos são um resultado do backend, sobrevivem ao reload e têm ações verificadas.

**Como.** Criar schemas discriminados e validadores dos sete tipos, `message_ui_objects`, mapeador `ToolResult → UI Object` e associação atômica à resposta. Adicionar evento SSE `ui_object` após persistir e lista em `MessageRead`. Expandir `frontend/src/lib/api.ts` e `types.ts` para o evento. Criar rota de ações que reconsulta objeto, dono, entidade e revisão. Regeneração remove os objetos da resposta antiga por FK; ações já confirmadas continuam em `tool_runs`.

**Aceite.** Um objeto emitido em SSE é idêntico ao objeto recuperado no histórico; payload inválido nunca chega à UI; ID de peça inventado falha; reload e regeneração mantêm consistência; se o modelo falha após uma escrita, o registro confirmado fica consultável e o chat mostra seu recibo, sem publicar objeto incompleto.

## P06 ↔ S06 — Entregar guarda-roupa e tools básicas

**Objetivo.** CRUD completo de peças e uso rastreável.

**Como.** Implementar serviço/queries com filtros e paginação, rotas REST e executores `get_wardrobe`, `get_wardrobe_item`, `add_wardrobe_item`, `update_wardrobe_item`, `archive_wardrobe_item`, `record_wear`. Validar taxonomia mínima (categoria e slots), aceitar atributos opcionais e desconhecidos, usar revisão otimista e chaves de idempotência. Conectar foto por `asset_id`, nunca por URL enviada pela LLM.

**Aceite.** Cadastrar, editar, filtrar, arquivar, registrar uso e recarregar funciona; limites de paginação são respeitados; contagem vem de linhas do banco; tool não acessa peça de outro dono; duas requisições idênticas de criação produzem uma peça.

## P07 ↔ S07 — Perfil explícito e aprendizado por eventos

**Objetivo.** Fazer preferências evoluírem por uso real sem confundir hipótese com decisão da pessoa.

**Como.** Criar endpoints e tools `get_style_profile`, `update_style_profile`, `record_outfit_feedback`. Derivar sinais de cadastro, looks salvos/rejeitados, uso e compra confirmada. Guardar pesos/versão do cálculo e oferecer correção/revogação. Injetar resumo curto e relevante no contexto, separado das memórias textuais atuais.

**Aceite.** Perfil inicial vazio mostra desconhecido; preferência explícita vence inferida; salvar, rejeitar e usar look mudam sinais com origem visível; regenerar texto não altera perfil por si só; sem sinal não aparece preferência fabricada.

## P08 ↔ S08 — Motor de looks, Mix & Match e agenda

**Objetivo.** Combinar peças existentes e persistir looks/planejamento.

**Como.** Implementar regras de slots e ranking versionado, drafts de look, `create_outfits`, `mix_and_match`, `swap_outfit_item`, `save_outfit`, `get_outfit`, `plan_outfit`; adicionar rotas diretas para ações na UI. Clima só entra por dado informado ou integração explícita; valores ausentes ficam indicados. Calendário usa fuso do principal.

**Aceite.** Jaqueta escolhida aparece em todas as variações ancoradas; todo `wardrobe_item_id` existe e pertence ao dono; peças faltantes são lacunas; salvar é idempotente; troca cria versão correta; agendamento persiste, retorna em `look_calendar` e sinaliza conflito de data.

## P09 ↔ S09 — Conectar busca web real e tendências

**Objetivo.** Consultar a web com fonte e data, sem alucinar atualidade.

**Como.** Selecionar um provedor de busca com API/documentação, termos de uso compatíveis, cobertura do mercado pretendido e custo aceitável; registrar a escolha e limites no README. Implementar `FashionSearchProvider` real com configuração/credencial cifrada, normalização de URL, timeout e cache datado. `search_fashion_web` retorna referências; `get_fashion_trends` cruza evidência recente com perfil/guarda-roupa e registra observações. Testes normais usam HTTP falso; smoke opt-in usa a integração real.

**Aceite.** Busca real retorna pelo menos uma fonte verificável com `fetched_at` no ambiente configurado; sem credencial/resultado, retorna indisponível ou vazio; nenhuma tendência atual sai só do conhecimento da LLM; fonte externa maliciosa não altera instruções do sistema nem faz o servidor acessar rede interna.

## P10 ↔ S10 — Fazer compras por ganho no guarda-roupa

**Objetivo.** Buscar produtos para lacunas reais e calcular compatibilidade auditável.

**Como.** Implementar `analyze_wardrobe_gaps`, `search_products`, `compare_product_to_wardrobe`. Adicionar extração de dados de produto para a integração escolhida, com observação datada, URL da loja, moeda e campos opcionais. Separar `compatible_owned_item_count` de `estimated_new_outfit_count`; guardar IDs e versão do algoritmo usados. Aplicar orçamento por moeda e preço observado. A UI recebe apenas observações reais validadas.

**Aceite.** “Tenho R$500” executa inventário → lacunas → busca real → compatibilidade; um produto sem preço mostra desconhecido e não passa por filtro de preço comprovado; contagem bate com IDs retornados; URL/preço/fonte/data são recuperáveis; sem busca, não há produto fictício no `product_carousel`.

## P11 ↔ S11 — Adicionar visão como revisão assistida

**Objetivo.** Sugerir atributos de foto sem gravar hipóteses como fatos.

**Como.** Verificar capacidade de imagem por modelo, adicionar envio multimodal ao adapter quando suportado e tool `analyze_clothing_image`. Guardar proposta, confiança e correções; tela de revisão chama cadastro após confirmação. Exigir consentimento claro antes de enviar foto a serviço externo. Manter caminho manual disponível.

**Aceite.** Foto gera sugestões editáveis; modelo sem visão não recebe imagem e mostra estado honesto; confirmar grava atributos escolhidos; falha de análise não perde upload; marca, tamanho e material não são preenchidos sem evidência.

## P12 ↔ S12 — Renderizar os sete tipos no React

**Objetivo.** Tornar o resultado útil no chat e em telas de detalhe.

**Como.** Criar `ChatObjectRenderer` e componentes sob `frontend/src/features/fashion/`, com registry por `type` e `schema_version`. Reutilizar API/actions para filtros, seleção, salvar/trocar look e abrir produto. Adicionar estados vazios, erro, fonte antiga, imagem ausente, fallback para tipo desconhecido, layout móvel e teclado. Carregar módulos pesados de forma tardia para preservar o chat comum.

**Aceite.** `wardrobe_view` tem grid e filtros; os demais mostram todos os campos obrigatórios da S12 e ações funcionais; um objeto desconhecido não quebra a conversa; teste de teclado e viewport móvel; reabrir conversa reproduz os mesmos cards.

## P13 ↔ S13 — Fechar integridade e segurança

**Objetivo.** Garantir proveniência, isolamento e operações previsíveis.

**Como.** Revisar todas as queries por dono, verificar URLs e redirecionamentos, limites de fetch/upload/contexto, logs saneados, erro tipado, métricas de tool e política de exclusão/exportação. Fazer testes adversariais de prompt injection em páginas, IDs alheios, preço ausente/antigo, race de revisão, retry e cancelamento após escrita. O recibo persistido deve explicar a escrita mesmo quando a continuação da LLM falha.

**Aceite.** Nenhuma credencial, imagem bruta ou dado de outro dono vaza em SSE/logs; source refs explicam cada preço, peça e contagem; mutações sob retry não duplicam; falhas externas não corrompem o banco; exportação e exclusão de dados pessoais têm caminho testado.

## P14 ↔ S14 — Gates de extensão e entrega

**Objetivo.** Deixar o módulo expansível e verificável sem acoplamento da UI ao modelo.

**Como.** Documentar template de nova tool/objeto, versionamento e compatibilidade. Adicionar testes de contrato entre Pydantic e TypeScript, testes de migration, adapter, orquestração, domínio, UI e e2e dos nove cenários S14. Atualizar README, exemplos de configuração e operacionalização de Alembic, busca e mídia. Habilitar pela capacidade verificada do modelo após os gates; registrar limitações observadas em busca e visão.

**Aceite.** Todos os nove cenários S14 passam; criar uma tool nova não exige editar `ChatView` e criar um objeto novo não exige mudar adapter; fluxo de chat antigo permanece verde; módulo pode ser desligado sem perder dados; documentação permite configurar a integração web real e explica suas limitações.

## P15 ↔ S15 — Coleção externa e captura segura

**Objetivo.** Permitir que imagens, produtos e referências salvas da internet façam parte da coleção Fashion, preservando sua origem e distinguindo itens possuídos, desejados e inspirações.

**Estado atual.** Foto anexada, URL direta e página com imagem principal identificável entram pelo chat. O backend captura a imagem, preserva a origem e envia a cópia WebP ao modelo; o resultado aparece em card editável e só é gravado após confirmação. A guia e o formulário Fashion saíram da interface. Extração sem metadados, busca de produtos e extensão permanecem como expansões posteriores.

**Como.** Entregar em fases, sempre com revisão e gesto explícito da usuária:

1. Criar migration para a proveniência externa: estado de coleção, URL original e canônica, domínio, método de entrada, asset interno, observações de produto datadas e vínculo opcional entre item do guarda-roupa e produto externo. Indexar por dono e URL canônica; usar hash da imagem como sinal adicional de duplicidade.
2. Implementar `RemoteImageFetcher` isolado para a primeira fase de importação por URL de imagem. Antes e depois de redirects, validar HTTP(S), DNS e IP público; bloquear loopback, faixas privadas, link-local e endpoints de metadados. Aplicar timeout, limite de redirects, bytes e dimensões; validar MIME pelos bytes e reutilizar o pipeline de normalização WebP e miniatura de P03.
3. Criar rotas de revisão e persistência: importar URL de imagem, iniciar importação de URL de produto, salvar/rejeitar uma proposta, atualizar observação e marcar item desejado como possuído. A captura de página fica atrás de um adaptador de fonte configurado; a primeira versão não faz scraping genérico de qualquer loja.
4. Adicionar services e tools tipadas `propose_external_piece`, `import_external_image`, `import_product_page`, `save_external_piece`, `refresh_product_observation` e `mark_piece_owned`. A LLM pode propor e explicar, mas cards de chat exigem confirmação e escolha do estado. Cada mutação usa a mesma idempotência, autorização e revisão otimista das ações Fashion.
5. Criar `external_piece_suggestion` e evoluir cards/listagens para foto local, badge Possuo/Quero/Inspiração, título, marca, preço e data observados, link de origem e ação de abrir, salvar, arquivar ou declarar posse. `mix_and_match` seleciona apenas `owned` por padrão e deixa alternativas externas explicitamente marcadas.
6. Integrar resultados de busca configurada como entrada de coleção e preparar contrato da extensão de navegador, ambos posteriores à captura direta. A extensão envia somente dados da página escolhida pela usuária e passa pelo mesmo endpoint de validação.
7. Cobrir com testes de migration, deduplicação, permissão, ações repetidas, limpeza/remoção de origem, renderer e um cliente HTTP falso que testa redirects, hosts privados, conteúdo inválido e limites sem acessar a internet real.

**Arquivos.** `backend/alembic/versions/`, `backend/app/domain/models.py`, `backend/app/fashion/media.py`, novo `backend/app/fashion/external_collection.py`, `backend/app/fashion/tools.py`, `backend/app/api/routes/fashion.py`, `backend/app/services/chat.py`, `frontend/src/features/fashion/`, `frontend/src/features/chat/ChatObjectRenderer.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, testes backend e frontend.

**Aceite.** O fluxo de URL de imagem cria cópia WebP interna com proveniência e não expõe URL remota como mídia; entradas `wanted` e `inspiration` não contam como peças possuídas; confirmação repetida não duplica item; hosts privados, redirects internos, MIME inválido e arquivos acima do limite falham sem persistir; snapshots mostram fonte e data; a LLM só publica proposta confirmável; importação de página e extensão só são disponibilizadas quando seu adaptador estiver configurado e testado.

## Ordem de trabalho recomendada

```text
P01 → P02 → P03
  └── P04 → P05 → P06 → P07 → P08
  ├── P03 + P05 + P06 ──────────────→ P15
  │                    └────────────→ P09 → P10
  │                                  └────→ P12
             P03 + P04 + P06 ───────→ P11
P05–P11 + P15 → P12 → P13 → P14
```

P12 pode ser entregue por fatias junto de P06–P11 e P15, desde que o registry e o fallback de P05 existam antes. P13 é um gate final, mas seus limites de segurança entram em cada etapa de implementação. P15 começa pela URL direta de imagem e só libera importação de página, busca e extensão quando houver adaptador configurado e testado. P09 precisa de uma integração configurada e testada antes de P10 ser considerado concluído.
