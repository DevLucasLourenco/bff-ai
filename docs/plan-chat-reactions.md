# Plano: reações visuais da personagem no chat

Corresponde 1:1 a [spec-chat-reactions.md](spec-chat-reactions.md). Depende da seleção visual de [plan-persona-visual.md](plan-persona-visual.md).

| Critério da spec | Implementação | Verificação |
| --- | --- | --- |
| 1. Saudação e respostas | Criar avatar reutilizável; integrar em saudação, `MessageBubble` e `StreamingMessage` | Abrir conversa vazia, enviar mensagem e conferir somente respostas da assistente |
| 2. Estados durante geração | Mostrar pose de atenção ao enviar e pose de análise sem texto; selecionar reação ao surgir conteúdo, estabilizando a escolha durante o stream | Simular stream lento, primeiros tokens e resposta completa |
| 3. Reação contextual | Criar função pura de seleção com prioridades explícitas: acolhimento, desculpa/erro, celebração, dúvida, explicação e padrão neutro | Testes unitários com frases representativas e ambíguas |
| 4. Falha e componentes | Colocar avatar ao lado do conteúdo, fora dos cards e avisos; preservar layout móvel | Testar resposta interrompida e card Fashion |
| 5. Histórico e troca visual | Calcular reação a partir do texto completo em uma função compartilhada; resolver arquivo por personagem e chave de reação | Reabrir conversa e trocar personagem, comparando a pose |
| 6. Fallback e movimento | Usar emoji se personagem/arquivo faltar; imagens decorativas no chat, foco visível na galeria e transições condicionadas a movimento reduzido | Teste de catálogo e inspeção com modo de movimento reduzido |

## Sequência

1. Catálogo tipado das 36 imagens por personagem e função pura de classificação.
2. Componente de avatar e integração no chat.
3. Estilos responsivos e fallback.
4. Testes de catálogo/classificação, testes de backend afetados e build.

## Pronto quando

Todas as oito personagens resolvem as reações usadas; estados de espera, streaming e histórico aparecem no chat; nenhuma dependência de ferramenta da LLM é introduzida; suíte e build passam.

