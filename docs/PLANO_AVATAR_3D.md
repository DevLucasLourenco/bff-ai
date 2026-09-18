# Plano — Avatar 3D por persona

Execução da [SPEC_AVATAR_3D.md](SPEC_AVATAR_3D.md). Status: **nada iniciado**,
aguardando as decisões da Fase 0.

Formato igual ao do [PLANO_DE_MELHORIAS.md](PLANO_DE_MELHORIAS.md): cada item tem
**Objetivo**, **Como**, **Aceite** e **Esforço** (P ≈ menos de 1h, M ≈ meio dia,
G ≈ 1–3 dias). "Você" marca o que depende de ação humana e eu não consigo fazer.

## Visão geral

| Fase | Tema | Depende de você | Esforço |
|---|---|---|---|
| 0 | Decisões e preparo de ferramenta | **sim** | M |
| 1 | O modelo base | **sim** | G |
| 2 | Otimização do .vrm | não | M |
| 3 | Runtime 3D isolado | não | G |
| 4 | Guarda-roupa | não | G |
| 5 | Integração com persona | não | M |
| 6 | Retrato 2D no chat | não | M |
| 7 | Expressão reativa | não | M |

---

# Fase 0 — Decisões e preparo

Nada abaixo pode começar sem isto. São as quatro perguntas da seção 10 da spec.

## A0.1 — Confirmar o pipeline

**Objetivo.** Fechar VRoid Studio como caminho, ou escolher outro conscientemente.

**Como.** Ler a seção 3 da spec (malha fundida) e a 6 (licença pixiv). Se a
conclusão da malha fundida gerar dúvida, vale gastar um teste no Meshy antes —
é a única forma de verificar de fato, e eu não tenho a chave para fazer isso.

**Aceite.** Decisão registrada aqui no plano.
**Esforço.** P. **Você.**

## A0.2 — Decidir modelo compartilhado × por persona

**Objetivo.** Saber se todas as personas usam um corpo só (mudando cabelo, roupa
e cor) ou se cada uma tem modelo próprio.

**Por que importa agora.** Muda o esquema de dados, o custo de modelagem e o peso
dos assets. Compartilhado é muito mais barato e é a recomendação.

**Aceite.** Decisão registrada.
**Esforço.** P. **Você.**

## A0.3 — Instalar o VRoid Studio

**Como.** Baixar de vroid.com (grátis, Windows). Não precisa de GPU forte para
modelar — a MX110 dá conta do editor; o gargalo seria renderizar cena pesada,
que não é o caso.

**Aceite.** VRoid abre e exporta um .vrm de teste.
**Esforço.** P. **Você.**

## A0.4 — Decidir o que fazer com Blender e Meshy

**Objetivo.** Saber se instalamos Blender.

**Contexto.** As skills `blender-toolkit`, `blender-threejs-export` e
`image-to-3d` estão instaladas mas inertes: falta o Blender e, no caso da
`image-to-3d`, a `MESHY_API_KEY` e a Blender MCP na porta 9876.

**Recomendação: não instalar agora.** O pipeline VRoid → VRM → web não precisa de
Blender. Instalar só se a Fase 2 mostrar que a otimização do .vrm exige mais do
que ferramenta de linha de comando dá.

**Aceite.** Decisão registrada.
**Esforço.** P. **Você.**

---

# Fase 1 — O modelo base

## A1.1 — Modelar o personagem no VRoid

**Objetivo.** Um .vrm de personagem estilo anime que sirva de base.

**Como.** No VRoid: partir de um preset, ajustar rosto, cabelo, corpo e
proporções. Para chibi, reduzir altura e aumentar a cabeça nos parâmetros de
corpo. Exportar em VRM 1.0.

**Aceite.** `.vrm` abre num visualizador VRM sem erro.
**Esforço.** G. **Você.** — é o item que eu não consigo fazer (spec, seção 11).

## A1.2 — Modelar o guarda-roupa inicial

**Objetivo.** De 3 a 5 peças por slot, para o sistema ter o que trocar.

**Como.** Usar as roupas do próprio VRoid e o recurso de dress-up/XWear da v2.0.
Slots sugeridos: `top`, `bottom`, `shoes`, `hair`, `acessorio`.

**Cuidado que define o sucesso da Fase 4.** Cada peça precisa sair como **grupo
de malha separado e nomeado de forma previsível** (ex.: `top__hoodie-rosa`). Se
tudo vier fundido num objeto só, o guarda-roupa em runtime não funciona e a Fase
4 morre. Vale exportar um .vrm de teste com duas peças e me mandar para eu
conferir a estrutura **antes** de modelar as outras.

**Aceite.** Um .vrm com pelo menos duas peças alternáveis, verificado por mim.
**Esforço.** G. **Você.**

---

# Fase 2 — Otimização

## A2.1 — Enxugar o .vrm para a MX110

**Objetivo.** Caber no orçamento da spec: ≤ 40k triângulos, atlas ≤ 1024².

**Como.** `gltf-transform` (CLI, Node — sem Blender): redimensionar texturas,
comprimir com KTX2/Basis, remover nós e materiais não usados, `dedup` e `prune`.
Medir antes e depois.

**Aceite.** Relatório com triângulos, número de draw calls e tamanho antes/depois;
alvos atingidos sem perda visível.
**Esforço.** M.

## A2.2 — Orçamento de asset documentado

**Objetivo.** Não deixar o arquivo crescer sem ninguém perceber.

**Como.** Teste que falha se o .vrm versionado passar do teto de tamanho.

**Aceite.** Teste verde hoje, vermelho se alguém commitar um .vrm gordo.
**Esforço.** P.

---

# Fase 3 — Runtime 3D isolado

Construído e testado **fora** do app primeiro, para não arrastar regressão para o
chat enquanto estiver instável.

## A3.1 — Visualizador VRM mínimo

**Objetivo.** Página que carrega o .vrm, ilumina e deixa orbitar.

**Como.** `three` + `@pixiv/three-vrm` (v3.5.5). Sem React Three Fiber por
enquanto: o projeto é deliberadamente enxuto e R3F adicionaria ~2 MB e uma camada
de abstração para uma tela só. Reavaliar se a Fase 7 ficar complexa.

**Aceite.** Modelo aparece, orbita, e o FPS na MX110 fica anotado.
**Esforço.** M.

## A3.2 — Render sob demanda e limites

**Objetivo.** Não fritar a GPU numa tela que fica aberta parada.

**Como.** Sem loop contínuo: redesenhar só em mudança. Limitar `devicePixelRatio`
a 1.5, pausar quando a aba perde foco, respeitar `prefers-reduced-motion`.

**Aceite.** Parado, o uso de GPU cai a praticamente zero.
**Esforço.** M. **Depende de.** A3.1.

## A3.3 — Carregamento tardio

**Objetivo.** O bundle do chat não pode crescer.

**Como.** `React.lazy` + import dinâmico; o chunk 3D só baixa ao abrir a aba.

**Aceite.** O chunk principal continua em ~81 kB gzip; o 3D vem em chunk separado.
**Esforço.** P.

---

# Fase 4 — Guarda-roupa

## A4.1 — Mapear os grupos de malha

**Objetivo.** Descobrir, no .vrm, quais nós correspondem a quais peças.

**Como.** Percorrer a cena e catalogar; gerar um manifesto de slots e peças a
partir dos nomes convencionados em A1.2.

**Aceite.** Manifesto bate com o que foi modelado.
**Esforço.** M. **Depende de.** A1.2.

## A4.2 — Trocar peça por visibilidade

**Objetivo.** Vestir e desvestir sem recarregar o modelo.

**Como.** Ligar/desligar `visible` nos grupos do slot. Nada de exportar ou
recombinar malha — além de lento, é o que a cláusula da pixiv restringe (spec, §6).

**Aceite.** Troca reflete em ≤ 100 ms, sem recarregar.
**Esforço.** M. **Depende de.** A4.1.

## A4.3 — Tinta por peça

**Objetivo.** Mesma peça em cores diferentes, multiplicando o guarda-roupa sem
modelar mais nada.

**Como.** Alterar a cor do material MToon da peça.

**Aceite.** Trocar a cor não afeta outras peças.
**Esforço.** M.

---

# Fase 5 — Integração com persona

## A5.1 — Persistir a aparência

**Objetivo.** A escolha vira parte da persona.

**Como.** Coluna JSON `appearance` em `personas` (spec, §7) + migration, schema e
rota. Validar contra o manifesto de A4.1: slot ou peça inexistente é 422.

**Aceite.** Escolher roupa, recarregar o app e ver a mesma roupa.
**Esforço.** M. **Depende de.** A4.2.

## A5.2 — Aba de aparência

**Objetivo.** A UI de vestir, dentro do editor de persona.

**Como.** Nova seção no `PersonaEditor`, com o visualizador e um seletor por slot.

**Aceite.** Dá para vestir a persona inteira sem sair da tela.
**Esforço.** M.

## A5.3 — Confirmar que não vaza para o prompt

**Objetivo.** Garantir a decisão da spec: aparência é UI, não comportamento.

**Como.** Teste que monta o prompt de uma persona vestida e verifica que nenhum
nome de peça aparece.

**Aceite.** Teste verde.
**Esforço.** P.

---

# Fase 6 — Retrato 2D no chat

## A6.1 — Retrato renderizado e cacheado

**Objetivo.** Mostrar a persona vestida no cabeçalho da conversa sem manter WebGL
vivo no chat.

**Como.** Ao salvar a aparência, renderizar um frame do avatar para PNG e guardar.
O chat exibe imagem comum.

**Aceite.** Cabeçalho mostra a persona vestida; nenhum custo de WebGL no chat.
**Esforço.** M. **Depende de.** A5.1.

## A6.2 — Degradação sem WebGL

**Objetivo.** App inteiro funcional sem GPU.

**Como.** Sem WebGL, a aba de aparência explica e some; o retrato 2D (se já
existir) continua aparecendo; o emoji volta como último recurso.

**Aceite.** Com WebGL desabilitado, nada quebra.
**Esforço.** P.

---

# Fase 7 — Expressão reativa

## A7.1 — Expressão conforme o estado do chat

**Objetivo.** O que separa um avatar de um boneco parado.

**Como.** Blend shapes do VRM ligadas ao estado do stream: pensando enquanto
gera, atento ao perguntar, neutro em assunto sério. Conversa com a diretriz da
Bestie de "adaptar a energia ao momento".

**Cuidado.** Isto exige WebGL vivo durante a conversa, o que a Fase 6 evitou de
propósito. Medir na MX110 antes de adotar; se pesar, fica só na aba de aparência.

**Aceite.** Expressão muda com o estado, sem queda de FPS perceptível.
**Esforço.** M.

---

# Fora de escopo por enquanto

- **Animação de corpo** (idle, gestos). Mixamo + retargeting resolveria, mas é
  peso e complexidade que não servem ao objetivo de "aparência".
- **Peças desbloqueáveis / coleção.** Registrado em IDEIAS_FUTURAS com a ressalva
  de não virar mecânica de engajamento.
- **Gerar roupa por IA.** Faz sentido para *textura e estampa* de peça já
  modelada, nunca para geometria. Depois da Fase 4.
- **Higgsfield.** Não serve para o modelo (spec, §4). Reavaliar só se quisermos
  arte 2D ou vídeo da persona.
- **Usuárias criando e exportando avatares.** Cai na cláusula da pixiv (spec, §6)
  e exigiria licença separada.

# Ordem sugerida

```
A0.1 → A0.2 → A0.3 → A0.4        decisões e ferramenta   ← você
A1.2 (teste de 2 peças)           valida a estrutura cedo ← você
A3.1 → A3.2 → A3.3                runtime isolado
A4.1 → A4.2                       guarda-roupa funcionando
A1.1 + A1.2 (resto)               modelagem completa      ← você
A2.1 → A2.2                       otimização
A5.1 → A5.2 → A5.3                integração com persona
A6.1 → A6.2                       retrato no chat
A7.1                              expressão
```

**Por que A1.2 aparece cedo e depois de novo:** exportar duas peças de teste
**antes** de modelar o guarda-roupa inteiro é o que evita o pior desperdício
possível aqui — descobrir, depois de dias modelando, que as peças saíram fundidas
e nenhuma delas pode ser trocada em runtime.
