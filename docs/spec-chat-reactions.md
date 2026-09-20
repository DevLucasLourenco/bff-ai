# Spec: reações visuais da personagem no chat

> Registro histórico da primeira versão. As reações ativas usam exclusivamente os 34 PNGs de `frontend/src/assets/bff_reactions/morena/`, sem recorrer à pasta antiga.

## Problema

A implementação inicial repete imagens pequenas como fotos de perfil em cada mensagem. A personagem fica pouco visível e sua reação durante o stream fica presa à primeira frase, mesmo quando o assunto ou o tom da resposta muda.

## Usuárias

Pessoas que conversam com uma persona que recebeu um visual e querem acompanhar reações perceptíveis, coerentes e contínuas.

## Proposta

Colocar a personagem na margem esquerda da coluna central, junto à origem das respostas e sem deslocar as mensagens. Ela escuta após o envio, pensa enquanto aguarda e reage a novos trechos conforme a resposta chega. Mudanças de pose têm intervalo mínimo e transição curta para não piscar. A arte fica sem nome ou legendas repetidas; a fase e a reação continuam disponíveis para leitores de tela. Uma ação discreta nas respostas permite rever a reação no histórico. As regras locais usam apenas sinais claros do texto, sem nova chamada ao modelo.

## Histórias

- Como usuária, quero ver a personagem reagir enquanto conversamos, para sentir continuidade visual sem abrir outra tela.
- Como usuária, quero ver a personagem mudar enquanto a resposta avança, inclusive em respostas longas.
- Como usuária, quero rever uma reação antiga sem imagens repetidas ao lado de cada mensagem.

## Critérios de aceitação

1. Em conversa com visual escolhido, a personagem aparece à esquerda, perto das respostas e visível sem rolar o histórico. A conversa e o composer mantêm o mesmo eixo central com ou sem personagem. Não há avatar repetido nas bolhas.
2. Após envio, o palco indica atenção e depois análise durante a espera. Ao chegar texto, a pose muda conforme trechos novos da resposta; dois trechos com sinais diferentes podem produzir duas reações no mesmo turno, com intervalo mínimo entre trocas. A reação final permanece visível até a próxima interação.
3. Sinais claros de acolhimento, celebração, dúvida, humor, ideia ou explicação selecionam poses correspondentes. Sem sinal claro, a pose é calma e coerente com a fase da conversa. O estado é anunciado para leitores de tela sem texto redundante junto da arte.
4. A personagem não cobre texto, composer, metadados, avisos ou componentes Fashion; em telas estreitas ocupa a lateral esquerda do cabeçalho. A rolagem do histórico usa trilho transparente e indicador discreto. Ao editar uma peça, o formulário ocupa a largura do card e não força rolagem horizontal.
5. Uma resposta antiga oferece uma ação acessível para reproduzir no palco sua reação final. Trocar a personagem mantém o mesmo tipo de reação e muda apenas a arte.
6. Sem personagem selecionada, o chat continua utilizável e exibe o emoji usual. Se uma imagem falhar, o palco recua para o emoji. Movimento reduzido remove flutuação e transições, sem esconder estado.

## Fora do escopo

Inferência emocional por outro modelo, pedir à LLM uma etiqueta de emoção, áudio, novos quadros desenhados e persistência de eventos por token.

## Dependências

[Spec de visual da persona](spec-persona-visual.md), os 36 PNGs por diretório, fluxo de streaming e componentes de mensagem existentes. O `mapa_reacoes.json` informa equivalências sem exigir 49 imagens distintas.

## Métrica principal

Percentual de conversas com personagem selecionada em que o palco apresenta imagem válida nas fases de espera e resposta, com objetivo funcional de 100% nos caminhos cobertos. Não há linha de base de produto; verificar por testes de catálogo, transições e inspeção visual.

## Esforço e prioridade

Médio (1–3 dias), P1. O menor incremento útil cobre palco responsivo, reação durante todo o stream, replay e fallback.
