# Ideias futuras

Ideias registradas para pesquisa, ainda sem decisão de implementar. Cada uma
guarda o **porquê** e as perguntas em aberto, para não precisar redescobrir o
raciocínio depois.

---

## Aparência da persona: avatar chibi vestível

> **Saiu da fase de ideia.** Pesquisado em 2026-09-18 e virou
> [SPEC_AVATAR_3D.md](SPEC_AVATAR_3D.md) + [PLANO_AVATAR_3D.md](PLANO_AVATAR_3D.md).
> O texto abaixo fica como registro do raciocínio original — vale notar que a
> intuição de "camadas em SVG" foi substituída por VRM/three.js, e que a pesquisa
> encontrou um impedimento que a ideia não previa: malha gerada por IA vem fundida
> e não permite trocar roupa.

**A ideia.** Cada persona ganha um corpo — um personagem chibi que a usuária pode
vestir e customizar. A aparência passa a ser parte da identidade da persona, no
mesmo nível do nome e do jeito de falar, em vez de só um emoji.

**Por que é interessante.** O projeto já trata persona como *dado, não código*
(regra 4 do README): prompt, nome e greeting são editáveis sem tocar no backend.
Aparência é a extensão natural disso. E resolve um problema real de produto: hoje
duas personas diferentes são visualmente idênticas — muda um emoji e o nome no
cabeçalho, e só. Um avatar dá peso à escolha de persona e torna o app mais dela.

**O ponto difícil, e onde está a graça.** Fazer "de um jeito interessante" quer
dizer não cair no gerador de avatar genérico. Algumas direções que valem
pesquisa:

- **Camadas em SVG.** Corpo base + camadas de roupa/cabelo/acessório como SVG
  sobrepostos, com cores trocáveis via `currentColor` e variáveis CSS. Barato,
  nítido em qualquer tamanho, versionável em texto e combina com o projeto ser
  sem framework pesado. A customização vira um JSON pequeno guardado na persona.
- **Expressão ligada ao estado da conversa.** O avatar reagir ao que está
  acontecendo — pensando enquanto o stream roda, atento quando faz uma pergunta,
  neutro em assunto sério. Isso conversa com a diretriz da Bestie de "adaptar o
  nível de energia ao momento", e é o que separaria de um boneco estático.
- **Guarda-roupa como coleção.** Peças desbloqueáveis ou sazonais, com a ressalva
  de não transformar em mecânica de engajamento: o README é explícito em não
  querer uma companhia possessiva ou que substitua relações humanas. Vestir tem
  que ser expressão, não vício.
- **Coerência entre aparência e personalidade.** Se a persona é formal, o
  guarda-roupa sugerido deveria refletir isso. Há espaço para o mesmo conjunto de
  campos que descreve o jeito de falar também sugerir o visual.

**Perguntas em aberto.**

- Arte: SVG desenhado à mão, conjunto de peças de terceiros, ou geração? Licença
  importa se o projeto sair do uso pessoal.
- Onde mora o estado da customização: coluna JSON em `personas` ou tabela própria?
  Depende de quantas camadas e se haverá histórico de looks.
- O avatar entra no prompt? Provavelmente **não** — aparência é da UI, e enfiar
  descrição de roupa no system prompt gasta contexto sem melhorar a conversa.
  Vale testar se mencionar o visual muda a percepção de personalidade.
- Quanto isso pesa no bundle, dado que hoje o app inteiro tem ~260 kB.

**Pré-requisitos.** Nenhum bloqueante. Fica mais fácil depois que as personas
tiverem campos estruturados, porque aí existe um vocabulário de personalidade em
que o visual pode se apoiar.
