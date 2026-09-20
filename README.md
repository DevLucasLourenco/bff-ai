# BFF AI

O BFF AI é um chat pessoal com inteligência artificial. Nele, você escolhe uma persona e um modelo do Ollama ou da NVIDIA NIM para conversar em tempo real. As conversas, personas e configurações ficam salvas localmente.

O projeto também reúne um guarda-roupa dentro do chat. Você pode enviar a foto ou o link de uma peça, revisar os dados sugeridos pela IA e salvá-la. As peças e combinações aparecem em componentes visuais na conversa, onde também é possível editar ou excluir itens. A personagem escolhida reage durante o diálogo.

## Rodar localmente

1. Instale as dependências do backend em um ambiente Python:

   ```bash
   cd backend
   pip install -r requirements.txt
   python scripts/generate_master_key.py
   ```

2. Na raiz do projeto, copie `.env.example` para `.env` e coloque a chave gerada em `APP_MASTER_KEY`. Depois, ainda em `backend`, prepare o banco e inicie a API:

   ```bash
   alembic -c alembic.ini upgrade head
   uvicorn app.main:app --reload
   ```

3. Em outro terminal, inicie a interface:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

Abra `http://localhost:5173`. Configure o modelo em **Configurações → LLM**; para usar Ollama, ele precisa estar em execução com o modelo instalado.
