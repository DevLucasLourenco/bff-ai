# BFF AI — Reações individuais

Este pacote foi montado a partir das 8 cartelas geradas nesta conversa.

## Personagens
- morena
- loira
- ruiva
- japonesa_oriental
- cabelos_brancos
- fashionista
- lobinha_spooky
- vampirinha_gotica

## Estrutura
- `00_cartelas_originais/`: cartelas completas originais.
- `por_personagem/<personagem>/`: 36 PNGs individuais para cada personagem.
- `manifesto_reacoes.csv`: informa o que cada uma das 36 imagens representa.
- `mapa_reacoes_pedidas.csv`: pega TODAS as 49 reações que você pediu e aponta a imagem gerada mais próxima para cada personagem.
- `mapa_reacoes.json`: o mesmo mapeamento em JSON, pronto para integração no backend/frontend.

## Importante
As cartelas geradas possuem 36 poses visuais por personagem, mas sua lista possui 49 estados/reações. Por isso, algumas reações solicitadas compartilham a mesma imagem quando são semanticamente próximas.

Exemplos:
- `Confusa` e `Com dúvida` → mesma pose.
- `Envergonhada` e `Tímida` → mesma pose.
- `Preocupada` e `Nervosa / ansiosa` → mesma pose.
- `Piscando / brincando`, `Travessa / provocando` e `Zoeira leve` → mesma pose.
- `Elogiando o usuário` e `Isso ficou incrível` → mesma pose.
- `Analisando` e `Pensando / processando resposta` → mesma pose.

Os PNGs permanecem com fundo transparente e foram separados diretamente das cartelas originais.
