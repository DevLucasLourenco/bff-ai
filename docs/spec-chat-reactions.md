# Spec: reações visuais da personagem no chat

## Problema

A implementação inicial repete imagens pequenas como fotos de perfil em cada mensagem. A personagem fica pouco visível e sua reação durante o stream fica presa à primeira frase, mesmo quando o assunto ou o tom da resposta muda.

## Usuárias

Pessoas que conversam com uma persona que recebeu um visual e querem acompanhar reações perceptíveis, coerentes e contínuas.

## Proposta

Colocar a personagem em uma área visual própria, grande e sempre visível na conversa, fora das bolhas. Ela escuta após o envio, pensa enquanto aguarda e reage a novos trechos conforme a resposta chega. Mudanças de pose têm intervalo mínimo e transição curta para não piscar. O texto e os componentes Fashion preservam sua área. Uma ação discreta nas respostas permite rever a reação no histórico. As regras locais usam apenas sinais claros do texto, sem nova chamada ao modelo.

## Histórias

- Como usuária, quero ver a personagem reagir enquanto conversamos, para sentir continuidade visual sem abrir outra tela.
- Como usuária, quero ver a personagem mudar enquanto a resposta avança, inclusive em respostas longas.
- Como usuária, quero rever uma reação antiga sem imagens repetidas ao lado de cada mensagem.

## Critérios de aceitação

1. Em conversa com visual escolhido, a personagem aparece em um palco próprio, visível sem rolar o histórico. Não há avatar repetido nas bolhas nem miniatura da personagem no cabeçalho.
2. Após envio, o palco indica atenção e depois análise durante a espera. Ao chegar texto, a pose muda conforme trechos novos da resposta; dois trechos com sinais diferentes podem produzir duas reações no mesmo turno, com intervalo mínimo entre trocas. A reação final permanece visível até a próxima interação.
3. Sinais claros de acolhimento, celebração, dúvida, humor, ideia ou explicação selecionam poses correspondentes. Sem sinal claro, a pose é calma e coerente com a fase da conversa. O estado é descrito por texto visível.
4. O palco não cobre texto, composer, metadados, avisos ou componentes Fashion; em telas estreitas vira uma faixa horizontal acima do histórico.
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
