# Agente de Estudos

Agente de estudos personalizado construído com **Google ADK** (Python), orientado por skills para montagem de planos com revisão espaçada, checkpoints de autoavaliação e exportação de agenda em CSV para o Google Agenda.

## Como Executar Localmente

1. Configure as variáveis em `.env` (a partir de `.env.example`):
   ```env
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   GEMINI_API_KEY=<sua-api-key>
   MODEL=gemini-3.8-flash
   ```

2. Instale as dependências:
   ```bash
   uv sync
   ```

3. Inicie a interface web do ADK:
   ```bash
   uv run adk web --allow_origins="*"
   ```
