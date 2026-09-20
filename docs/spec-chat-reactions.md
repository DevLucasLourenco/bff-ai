# Spec: reações visuais da personagem no chat

## Problema

Mesmo depois de escolher uma personagem, o chat continuaria estático. O pacote contém 36 poses por personagem, mas nenhuma reação aparece ao escutar, preparar ou responder.

## Usuárias

Pessoas que conversam com uma persona que recebeu um visual e querem perceber sinais visuais discretos e coerentes com o andamento da conversa.

## Proposta

Exibir uma reação da personagem junto das respostas da assistente. Ao enviar uma mensagem, a personagem mostra uma pose de atenção e, enquanto aguarda a geração, uma pose de análise. Durante a resposta e no histórico, a pose é escolhida por regras locais transparentes baseadas no texto da resposta. Assuntos sensíveis recebem uma reação acolhedora; respostas sem sinal forte usam uma pose neutra. A mesma regra é aplicada ao stream e às mensagens carregadas depois, sem depender de suporte a ferramentas pelo modelo.

## Histórias

- Como usuária, quero ver a personagem reagir enquanto conversamos, para sentir continuidade visual sem abrir outra tela.
- Como usuária, quero que uma resposta de apoio tenha uma pose adequada e que uma resposta comum não receba uma reação exagerada.
- Como usuária, quero rever a conversa e encontrar a mesma reação da resposta concluída.

## Critérios de aceitação

1. Em conversa com visual escolhido, a saudação e cada resposta da assistente mostram imagem da personagem; mensagens da usuária não recebem avatar da assistente.
2. Após enviar mensagem e antes dos primeiros tokens, a personagem mostra atenção/análise; ao receber texto, a reação acompanha a resposta sem piscar a cada token.
3. Respostas com sinais claros de acolhimento, celebração, dúvida ou explicação usam poses adequadas; texto sem sinal claro usa pose neutra.
4. Respostas interrompidas mantêm um visual coerente, sem esconder aviso de falha, metadados nem componentes Fashion.
5. Reabrir a conversa reproduz a reação de cada resposta concluída; trocar a personagem preserva o tipo de reação e troca apenas a arte.
6. Em persona sem visual, o chat permanece utilizável com emoji; imagens ausentes não quebram o texto. Movimento respeita `prefers-reduced-motion`.

## Fora do escopo

Inferência emocional por outro modelo, pedir à LLM uma etiqueta de emoção, áudio, animações contínuas, interpretação da emoção da usuária e persistência de eventos por token.

## Dependências

[Spec de visual da persona](spec-persona-visual.md), os 36 PNGs por diretório, fluxo de streaming e componentes de mensagem existentes. O `mapa_reacoes.json` informa equivalências sem exigir 49 imagens distintas.

## Métrica principal

Percentual de respostas da assistente em conversas com visual escolhido que exibem um arquivo de reação válido, com objetivo funcional de 100% nos caminhos cobertos. Não há linha de base de produto; verificar por testes de catálogo e inspeção do chat.

## Esforço e prioridade

Médio (1–3 dias), P1. O menor incremento útil cobre estado de espera, resposta concluída, histórico e fallback.

