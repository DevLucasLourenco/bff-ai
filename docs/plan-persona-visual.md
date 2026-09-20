# Plano: escolher o visual de cada persona

> Plano histórico da primeira versão. Atualmente, a seleção oferece Morena ou “Somente emoji”, e nenhum recurso é carregado da pasta antiga.

Corresponde 1:1 a [spec-persona-visual.md](spec-persona-visual.md). Implementar todos os critérios antes de considerar esta etapa concluída.

| Critério da spec | Implementação | Verificação |
| --- | --- | --- |
| 1. Legado e opção visual | Adicionar `avatar_character` nullable à persona; galeria com “Somente emoji” | Abrir persona antiga e confirmar emoji e oito opções |
| 2. Persistência e recarga | Adicionar coluna via Alembic `0011`, schemas de criação/leitura/edição, tipos TS e seleção no `PersonaEditor` | Criar/editar persona pela API e recarregar o chat |
| 3. Conversas existentes | Expor `persona_character` em `ConversationRead` a partir da persona associada, sem snapshot por mensagem | Editar persona usada por conversa e consultar a mesma conversa |
| 4. Retirada do visual | Tratar `null` explícito em `PATCH /personas/{id}` sem alterar o comportamento dos outros campos opcionais | Selecionar “Somente emoji”, salvar e recarregar |
| 5. Catálogo validado | Limitar API aos oito identificadores dos diretórios; usar resolução local dos PNGs com fallback ao emoji | Enviar chave inválida e conferir HTTP 422; testar persona legada |
| 6. Acessibilidade | Implementar opções como controles de rádio, nome legível, estado selecionado e foco visível | Navegar galeria com teclado e conferir marcação acessível |

## Sequência

1. Migração, modelo e API.
2. Catálogo de imagens e galeria no editor.
3. Cabeçalho e demais pontos de identificação da persona.
4. Testes de contrato e build; migrar banco local com `alembic upgrade head` se configurado.

## Pronto quando

Backend aceita seleção, troca e remoção; frontend mantém escolha após recarga; `pytest`, testes de frontend e build passam. As imagens só são carregadas pelo navegador quando aparecem na interface.
