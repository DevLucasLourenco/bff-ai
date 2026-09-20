# Spec: escolher o visual de cada persona

> Registro histórico da primeira versão. O catálogo ativo agora contém somente `frontend/src/assets/bff_reactions/morena/`; a pasta antiga permanece no repositório apenas como referência para desenvolvimento.

## Problema

As personas já têm nome, comportamento e emoji, mas a usuária não consegue escolher uma das personagens ilustradas disponíveis para representá-las. Os arquivos em `frontend/src/assets/bff_ai_reacoes_individuais/bff_ai_reacoes_individuais/por_personagem` ainda não participam da experiência.

## Usuárias

Pessoas que criam ou editam personas no BFF AI e desejam associar um visual consistente a cada uma.

## Proposta

Adicionar ao editor da persona uma galeria de oito personagens com prévia e opção de manter o emoji. A escolha é salva na própria persona e aparece no cabeçalho do chat, na lista de personas e em todas as conversas vinculadas a ela. A aparência é uma preferência visual; não altera o prompt nem a personalidade do modelo.

## Histórias

- Como usuária, quero ver as oito personagens antes de escolher, para reconhecer o visual desejado.
- Como usuária, quero trocar ou retirar o visual depois, para ajustar a persona sem perder conversas.

## Critérios de aceitação

1. Dada uma persona sem personagem, a interface mostra seu emoji atual e a opção de escolher personagem.
2. Dada uma das oito personagens, ao selecionar e salvar a persona, a API devolve o identificador escolhido e o visual aparece no chat após recarregar.
3. Dada uma persona editada, as conversas existentes dessa persona refletem o visual atualizado sem mudar mensagens, prompt ou modelo.
4. Ao selecionar “Somente emoji”, a escolha visual é removida e o emoji reaparece.
5. Uma chave desconhecida é rejeitada pela API com erro de validação; dados legados sem visual continuam válidos.
6. A galeria é navegável por teclado, identifica a opção escolhida e oferece texto alternativo nas prévias.

## Fora do escopo

Envio de personagens personalizados, geração de novas imagens, animação 3D e criação de uma persona diferente para cada personagem.

## Dependências

Oito diretórios existentes, cada um com 36 PNGs; API de personas e conversas; migrações Alembic. Os diretórios são o catálogo permitido.

## Métrica principal

Percentual de personas ativas com personagem escolhido. A instrumentação e a linha de base não existem hoje; medir pela coluna persistida após a entrega, sem inventar meta numérica.

## Esforço e prioridade

Médio (1–3 dias), P1. A opção de escolher e ver a personagem sem reações é o menor incremento útil.
