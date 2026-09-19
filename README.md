# BFF AI — orquestrador pessoal de LLM

Aplicação full-stack para conversar com **uma única LLM selecionada por vez**, usando Ollama local ou NVIDIA NIM. Não existe fallback silencioso: se o provedor/modelo escolhido falhar, a conversa mostra o erro e para ali.

## O que fica no banco

SQLite é a fonte de verdade do produto:

- personas e prompts de sistema;
- providers (Ollama / NVIDIA NIM), URLs e estado;
- API keys criptografadas;
- modelos e parâmetros de inferência;
- modelo ativo e persona ativa;
- nome do app, nomes de exibição e tema;
- conversas e mensagens;
- metadados de execução (modelo, provider e latência).

O Fashion Module acrescenta, na migration `0003`, um guarda-roupa pessoal local,
fotos normalizadas, looks, uso, calendário, perfil de estilo, resultados externos
datados e objetos visuais persistidos por mensagem. Ele começa com uma dona local
fixa (`users.id = 1`); não exponha o backend para mais pessoas antes de adicionar
autenticação e trocar esse resolvedor por uma sessão real.

O `.env` tem **uma única responsabilidade**: guardar a chave-mestra usada para criptografar secrets do SQLite.

## Arquitetura

```text
frontend (React + Vite)
        |
        | REST + SSE
        v
backend (FastAPI)
  ├─ API routes
  ├─ services
  │   ├─ ChatService
  │   └─ LLM adapters
  │       ├─ OllamaAdapter
  │       └─ NvidiaNimAdapter
  ├─ repositories
  ├─ domain models/schemas
  └─ SQLite
```

Ollama e NVIDIA NIM expõem APIs compatíveis com OpenAI. O projeto usa `/v1/chat/completions` com streaming e `/v1/models` para descoberta. O adapter é escolhido estritamente pelo `provider.kind` salvo no banco.

## Rodando localmente

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_master_key.py
```

Copie `.env.example` para `.env` na raiz do projeto e cole a chave gerada em `APP_MASTER_KEY`.

Crie/atualize o schema do banco. **Este passo é explícito e obrigatório** — o app
não cria mais tabelas sozinho, e recusa subir se o banco estiver atrás do código:

```bash
alembic -c alembic.ini upgrade head
```

Depois:

```bash
uvicorn app.main:app --reload
```

Na primeira inicialização o banco `backend/data/bff_ai.db` recebe:

- persona `Bestie`;
- provider Ollama em `http://localhost:11434/v1`;
- provider NVIDIA NIM;
- um modelo Ollama inicial `llama3.2`.

Se usar Ollama, instale-o e faça pull de um modelo, por exemplo:

```bash
ollama pull llama3.2
```

Se usar NVIDIA NIM hospedado, abra **Configurações → LLM**, salve sua API key e consulte os modelos disponíveis.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`.

### 3. Testes

```bash
cd backend && python -m pytest
```

```bash
cd frontend && npm test
```

Os testes do backend usam um SQLite temporário migrado por `alembic upgrade head`
e uma chave-mestra descartável: nunca tocam `backend/data/bff_ai.db` nem o `.env`.
Nenhum teste faz I/O de rede.

## Regras deliberadas do projeto

1. **Sem fallback de LLM.** `create_adapter()` retorna exatamente o provider escolhido ou lança erro.
2. **Conversa registra o modelo selecionado.** Assim o contexto não muda silenciosamente no meio de um chat.
3. **Secrets no banco, criptografados.** A chave-mestra não vai para o SQLite.
4. **Persona é dado, não código.** Prompt, greeting e identidade podem ser alterados sem editar backend.
5. **Provider é adapter.** Adicionar outro mecanismo de LLM não exige reescrever chat, banco ou UI.
6. **Streaming ponta a ponta.** O backend lê SSE do provider e envia SSE ao navegador.
7. **Schema tem fonte única: Alembic.** O app não usa `create_all` e se recusa a subir
   se o banco não estiver na revisão esperada — em vez de falhar depois com `no such column`.

## Estrutura

```text
bff-ai/
├─ .env.example
├─ README.md
├─ backend/
│  ├─ alembic/
│  ├─ app/
│  │  ├─ api/routes/
│  │  ├─ core/
│  │  ├─ db/            schema.py verifica a revisão no boot
│  │  ├─ domain/
│  │  ├─ repositories/
│  │  └─ services/
│  │     ├─ context.py  montagem do prompt, pura e testável
│  │     └─ llm/        adapters, capacidades e erros tipados
│  ├─ scripts/
│  └─ tests/
├─ docs/
└─ frontend/
   └─ src/
      ├─ components/
      ├─ features/chat/    Markdown, MessageBubble, StreamingMessage
      ├─ features/settings/
      ├─ hooks/            useConfig, useConversations, useChatStream
      └─ lib/              api, sse, streamBuffer
```

## Fashion Module

Em **Configurações → Fashion**, é possível cadastrar peças manualmente, com foto
opcional, buscar no guarda-roupa e arquivar itens. As rotas ficam sob
`/api/fashion/`; o contrato e as próximas etapas estão em
[docs/SPEC_FASHION_MODULE.md](docs/SPEC_FASHION_MODULE.md) e
[docs/PLANO_FASHION_MODULE.md](docs/PLANO_FASHION_MODULE.md).

As Fashion Tools têm schemas tipados e retornam apenas dados registrados no banco.
Pesquisa de produtos, tendências e análise visual retornam `unavailable` enquanto
nenhum serviço externo real estiver configurado. Assim o app não apresenta preços,
estoque ou atributos de roupa como se tivessem sido verificados.

## Diagnóstico e saúde

`GET /health` diz só que o processo está de pé. `GET /health/ready` checa o que
realmente quebra: o banco abre, a revisão do schema é a esperada e a
`APP_MASTER_KEY` ainda decifra os segredos guardados. Responde 503 quando algo
está degradado.

## Próximas extensões naturais

- editor visual completo de personas;
- anexos e multimodal;
- ferramentas/MCP com permissões explícitas;
- busca semântica de memórias (hoje o filtro é por escopo + teto);
- sumarização do histórico antigo (hoje ele é truncado com aviso);
- autenticação caso deixe de ser uma aplicação local;
- PostgreSQL quando sair do modo local.

O roadmap técnico que originou o estado atual, com o porquê de cada decisão, está
em [docs/PLANO_DE_MELHORIAS.md](docs/PLANO_DE_MELHORIAS.md).
