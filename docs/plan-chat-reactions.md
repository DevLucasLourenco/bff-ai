# Plano: reações visuais da personagem no chat

Corresponde 1:1 a [spec-chat-reactions.md](spec-chat-reactions.md). Depende da seleção visual de [plan-persona-visual.md](plan-persona-visual.md).

| Critério da spec | Implementação | Verificação |
| --- | --- | --- |
| 1. Palco próprio | Criar `CharacterStage` dentro do corpo do chat; retirar miniaturas do cabeçalho e das mensagens | Abrir conversa vazia e conferir palco persistente e bolhas limpas |
| 2. Estados e stream | Assinar `StreamBuffer` no palco; transitar entre atenção, análise e reação ao trecho mais recente, com intervalo mínimo; manter reação final até a próxima interação | Simular espera longa e resposta de duas frases com reações diferentes; reabrir conversa e conferir reação final |
| 3. Reação contextual | Ampliar regras puras com sinais explícitos e fallback calmo; mostrar legenda da fase/reação | Testar frases de apoio, comemoração, humor, ideia e texto comum |
| 4. Layout | Reservar largura para o palco no desktop e faixa horizontal no móvel; manter scroll de mensagens independente | Conferir composer, card Fashion, aviso e viewport estreito |
| 5. Histórico | Adicionar ação discreta e acessível para reproduzir reação final no palco | Reabrir conversa, acionar replay e trocar personagem |
| 6. Fallback e movimento | Usar emoji quando faltar imagem; usar movimento leve de figura e cenário, removido por `prefers-reduced-motion` | Teste de fallback e inspeção em movimento reduzido |

## Sequência

1. Atualizar a classificação e testes da sequência de reações.
2. Implementar palco e replay, retirando miniaturas das mensagens.
3. Ajustar layout responsivo, transições e fallback.
4. Testar fluxo, executar suíte e build; inspecionar desktop e móvel quando possível.

## Pronto quando

As oito personagens resolvem as reações usadas; palco reage no mesmo turno em mais de um trecho quando há sinais diferentes; histórico pode reproduzir a reação; suíte e build passam.
