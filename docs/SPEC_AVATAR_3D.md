# Spec — Avatar 3D por persona

Status: **proposta**, aguardando decisão. Nada foi implementado.
Pesquisa feita em 2026-09-18. Origem: a ideia registrada em [IDEIAS_FUTURAS.md](IDEIAS_FUTURAS.md).

## 1. O que se quer

Cada persona ganha um corpo: um personagem 3D estilo anime que a usuária pode
vestir. A aparência passa a ser parte da identidade da persona, no mesmo nível do
nome e do jeito de falar — hoje duas personas são visualmente idênticas, mudando
só um emoji no cabeçalho.

O pedido original fala em "modelo 3D real, bem detalhado, parecendo personagem de
anime". Esta spec trata **como produzir esse modelo** e **como o guarda-roupa
funciona**, que são problemas diferentes e que puxam para lados opostos.

## 2. Restrições descobertas nesta máquina

Levantadas antes de recomendar qualquer coisa, porque três delas eliminam opções
inteiras:

| Restrição | Consequência |
|---|---|
| **GPU NVIDIA MX110** (entrada, ~2 GB) | Geração 3D local (Hunyuan3D, TRELLIS, TripoSR) está fora — pedem 8–24 GB. Também limita o alvo de render em tempo real. |
| **Blender não instalado** | As skills `blender-toolkit`, `blender-threejs-export` e `image-to-3d` não rodam hoje. |
| **`MESHY_API_KEY` não configurada** | A skill `image-to-3d` depende dela e da Blender MCP na porta 9876. |
| **Bundle atual: 261 kB (81 kB gzip)** | three.js + three-vrm somam ~180–250 kB gzip. Triplicaria o bundle se carregado junto com o chat. |

## 3. O achado que decide a arquitetura

**Geração 3D por IA e troca de roupa são incompatíveis.**

Meshy, Tripo e Rodin produzem uma **malha única e fundida**, com a textura
assada. A roupa não é um objeto separado: é geometria e pixels do mesmo corpo.
Auto-rigging, quando existe, adiciona um esqueleto — não separa as peças.

O efeito prático é fatal para o objetivo: para trocar a roupa seria preciso
**regerar o personagem inteiro**, e cada geração devolve um rosto e um corpo
levemente diferentes. A persona mudaria de cara a cada troca de roupa, que é
exatamente o contrário de "aparência da persona".

Ou seja: gerar por IA resolve "modelo detalhado" e destrói "guarda-roupa".

O que resolve os dois é o formato **VRM**, que nasceu para avatares humanoides:
esqueleto humanoide padronizado, blend shapes de expressão nomeadas, e **cada
peça de roupa como um grupo de malha separado**. Vestir vira ligar e desligar
grupos, não regerar nada.

> Verificar antes de fechar: gerar um personagem de teste no Meshy e confirmar
> que a saída é mesmo fundida. A conclusão acima vem da documentação dos
> serviços, não de um teste nosso.

## 4. Pipeline recomendado

```
VRoid Studio (grátis, desktop)
        │  modelagem do personagem + roupas
        ▼
    arquivo .vrm
        │  otimização: reduzir atlas de textura, remover o que não se usa
        ▼
   .vrm servido como asset estático
        │
        ▼
frontend: three.js + @pixiv/three-vrm
        │  guarda-roupa = alternar visibilidade de grupos de malha
        ▼
   aparência da persona
```

**Por que VRoid Studio.** É gratuito, feito pela pixiv especificamente para
avatares estilo anime, e desde a v2.0 tem um recurso de **dress-up** com formato
XWear — ou seja, o guarda-roupa que queremos é funcionalidade nativa da
ferramenta, não algo que precisamos inventar. Exporta VRM direto. Tem ecossistema
grande de roupas e acessórios de terceiros.

**Por que não gerar por IA.** Explicado na seção 3. Gerar continua útil, mas para
outra coisa: **texturas e estampas** de roupas já modeladas, não a geometria.

**Sobre o Higgsfield.** Foi investigado por ter sido citado no pedido. Não serve
para este caso: é uma suíte criativa de **imagem e vídeo** (Veo, Sora, Kling,
Soul). O suporte a 3D existe, mas é *blockout* — geometria bruta para compor
enquadramento de vídeo no Blender, não malha de personagem com roupas separáveis.
Tem MCP e plugin de Blender, mas resolveria um problema que não é o nosso.
Poderia entrar depois, se algum dia quisermos vídeo promocional ou arte 2D da
persona.

## 5. Alternativas descartadas

| Alternativa | Por que não |
|---|---|
| **Meshy / Tripo / Rodin** (gerar o personagem) | Malha fundida: sem troca de roupa sem regerar o personagem inteiro. |
| **Modelar à mão no Blender** | Trabalho de artista, semanas, e o Blender nem está instalado. Custo desproporcional. |
| **Ready Player Me / Avaturn** | Têm sistema de roupas, mas o estilo é semi-realista; não entregam anime/chibi. |
| **Comprar base mesh pronta (Booth, VRoid Hub)** | Viável e mais rápido que modelar. Fica como plano B se o VRoid não agradar. |
| **Sprites 2D em camadas** | Muito mais barato e roda em qualquer GPU. Descartado por não atender o pedido de 3D — mas é o fallback honesto se a performance inviabilizar. |

## 6. Restrição de licença que muda o escopo

As diretrizes do VRoid são generosas: modelos que você cria são seus, incluindo
uso comercial, e os meshes/texturas que a pixiv fornece podem ser usados e até
vendidos dentro do modelo.

**Mas existe uma cláusula que bate direto no que queremos construir:**

> Não é permitido criar uma aplicação capaz de gerar ou exportar modelos 3D,
> avatares ou itens compostos de meshes e texturas deformados ou combinados
> criados no VRoid Studio, sem aceitar uma licença separada da pixiv.

Como isso nos afeta:

- **Uso pessoal, modelo feito por você, roupas alternadas só na tela, nada
  exportado** → dentro do permitido. É este o escopo do BFF AI hoje.
- **Se um dia o app deixar de ser local e permitir que outras pessoas montem e
  exportem avatares** → cai na cláusula e exige licença separada da pixiv.

Isto é mais uma razão para o guarda-roupa ser **visibilidade de malha em runtime**
e não geração/exportação de um modelo novo a cada troca.

## 7. Modelo de dados

A aparência é da UI, não do comportamento. **Não entra no system prompt** —
descrição de roupa gastaria contexto sem melhorar a conversa (ver
IDEIAS_FUTURAS).

Proposta para a v1, uma coluna JSON em `personas`:

```jsonc
// personas.appearance
{
  "model": "bestie-v1",        // qual .vrm carregar
  "outfit": {                   // slot → id da peça (null = nada)
    "top":    "hoodie-rosa",
    "bottom": "saia-plissada",
    "shoes":  "tenis-branco",
    "hair":   "longo-ondulado",
    "acessorio": null
  },
  "colors": { "hoodie-rosa": "#c6407d" }  // tinta por peça, via MToon
}
```

Coluna JSON e não tabela porque os slots são poucos e mudam juntos; se surgir
histórico de looks ou peças desbloqueáveis, aí vira tabela.

O catálogo de peças disponíveis é **estático no frontend** (o que existe no .vrm),
não dado de banco — o banco guarda só a escolha.

## 8. Arquitetura de runtime

- **Carregamento tardio.** O bundle 3D só é baixado quando a aba de aparência
  abre. `React.lazy` + import dinâmico. O chat não pode ficar 3× mais pesado por
  uma tela que talvez nunca abra.
- **Uma instância só.** Um VRM por vez na cena, descartado ao fechar.
- **Render sob demanda.** Nada de `requestAnimationFrame` contínuo: redesenhar
  só quando algo muda (rotação, troca de peça). Numa MX110 isso é a diferença
  entre usável e ventoinha ligada.
- **Orçamento de polígonos.** Alvo ≤ 40k triângulos, atlas ≤ 1024². VRoid padrão
  costuma passar disso; a etapa de otimização não é opcional aqui.
- **`prefers-reduced-motion`** desliga rotação automática.
- **Degradação honesta.** Sem WebGL ou em GPU fraca: mostrar retrato 2D
  renderizado do avatar em vez de tentar e travar.

## 9. Critérios de aceite

1. Abrir a aba de aparência de uma persona carrega o avatar em ≤ 3 s numa MX110.
2. Trocar uma peça reflete na tela em ≤ 100 ms, sem recarregar o modelo.
3. A escolha persiste no banco e reaparece ao reabrir o app.
4. O bundle do chat **não** cresce: o código 3D só é baixado ao abrir a aba.
5. Duas personas com roupas diferentes ficam visualmente distintas no cabeçalho
   da conversa (retrato 2D, barato).
6. Sem WebGL, o app continua inteiro funcional.

## 10. Perguntas em aberto

- **Quem modela?** O pipeline recomendado exige alguém operando o VRoid Studio.
  Não é trabalho que eu consiga fazer por você (ver seção 11).
- Um modelo base compartilhado por todas as personas, ou um modelo por persona?
  Compartilhado é muito mais barato — muda roupa, cabelo e cor, não o corpo.
- Retrato 2D no cabeçalho: renderizado uma vez e cacheado, ou canvas vivo? O
  primeiro é claramente mais barato nesta GPU.
- Expressão reagindo ao estado do chat (pensando / atento / neutro) entra na v1
  ou fica para depois? É o que separaria de um boneco estático, mas custa tempo.

## 11. O que eu consigo e o que não consigo fazer

Sendo direto, porque isso muda o planejamento:

**Não consigo** produzir a malha do personagem. Um personagem de anime detalhado
é trabalho de modelagem artística — escrever código Blender à mão produziria um
boneco de primitivas, não o que você pediu. E as ferramentas que fariam isso
(Meshy via `image-to-3d`, Blender via `blender-toolkit`) não estão disponíveis
nesta máquina, além de a via generativa ter o problema da malha fundida.

**Consigo** fazer todo o resto: o runtime three.js/three-vrm com troca de peças,
o modelo de dados, a integração com persona, a otimização do .vrm, a aba de
aparência, o retrato 2D e os testes. Tudo isso funciona contra **qualquer** .vrm
— basta o arquivo existir.
