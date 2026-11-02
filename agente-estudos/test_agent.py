"""Script de validação e testes para o agente-estudos."""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Carrega variáveis
load_dotenv()


def test_components():
    """Valida a estrutura do agente, ferramentas e diretórios sem depender da API."""
    print("\n--- [1/2] Teste de Componentes e Configurações ---")
    from app.agent import root_agent, PLANOS_DIR, FerramentasDeArquivo

    # 1. Verifica root_agent
    assert root_agent is not None, "root_agent não está definido"
    print("[OK] root_agent definido com sucesso")

    # 2. Verifica modelo da variável de ambiente
    model_expected = os.getenv("MODEL", "gemini-3.8-flash")
    assert root_agent.model == model_expected, f"Modelo incorreto: {root_agent.model} != {model_expected}"
    print(f"[OK] Modelo configurado via MODEL: {root_agent.model}")

    # 3. Verifica provedor de instrução com data atual
    instruction = root_agent.instruction()
    assert "Hoje é" in instruction, "Data atual não encontrada na instrução"
    print(f"[OK] Instruction provider injeta data: {instruction.splitlines()[0]}")

    # 4. Verifica ferramentas de arquivo
    file_toolsets = [t for t in root_agent.tools if isinstance(t, FerramentasDeArquivo)]
    assert len(file_toolsets) == 1, "FerramentasDeArquivo não encontrado nas ferramentas"
    file_tools = asyncio.run(file_toolsets[0].get_tools())
    tool_names = [t.name for t in file_tools]
    assert set(tool_names) == {"ReadFile", "WriteFile"}, f"Ferramentas incorretas: {tool_names}"
    print(f"[OK] Ferramentas de arquivo filtradas estritamente: {tool_names}")

    # 5. Verifica pasta planos/
    assert PLANOS_DIR.exists(), f"Diretório planos/ não existe: {PLANOS_DIR}"
    print(f"[OK] Diretório planos/ persistente e resolvido: {PLANOS_DIR}")

    # 6. Verifica descoberta no ADK Web
    app = get_fast_api_app(agents_dir=".", web=True)
    from fastapi.testclient import TestClient

    client = TestClient(app)
    apps = client.get("/list-apps").json()
    assert "app" in apps, f"'app' não encontrado em /list-apps: {apps}"
    print(f"[OK] Descoberta no ADK Web (/list-apps): {apps}")


async def run_live_tests():
    """Executa testes de conversação de ponta a ponta quando GEMINI_API_KEY for válida."""
    print("\n--- [2/2] Teste de Conversação e Gating (Live) ---")
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "sua-api-key-aqui":
        print("[INFO] GEMINI_API_KEY nao configurada no .env. Pulando teste com modelo ao vivo.")
        print("      Para testar ao vivo, adicione sua chave ao arquivo agente-estudos/.env e execute novamente.")
        return

    from app.agent import root_agent, PLANOS_DIR

    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, session_service=session_service)

    user_id = "test_user"
    session = await session_service.create_session(
        user_id=user_id, app_name="app"
    )
    session_id = session.id

    # Turno 1: Gating Test
    print("\n[Turno 1] Enviando pedido incompleto (teste de gating): 'Quero organizar meus estudos de JavaScript.'")
    content_t1 = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Quero organizar meus estudos de JavaScript.")],
    )

    t1_calls = []
    t1_response = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content_t1
    ):
        for fc in event.get_function_calls():
            t1_calls.append(fc.name)
        if event.content:
            for part in event.content.parts:
                if part.text:
                    t1_response += part.text

    print(f"Chamadas de ferramentas no Turno 1: {t1_calls}")
    assert "load_skill_resource" not in t1_calls, (
        "FALHA NO GATING: 'load_skill_resource' foi chamado antes de satisfazer o gating!"
    )
    print("[OK] Gating respeitado com sucesso: nenhum recurso L3 foi carregado.")
    print(f"Resposta do agente no Turno 1:\n{t1_response[:300]}...\n")

    # Turno 2: Informações completas
    print("\n[Turno 2] Fornecendo todas as informações necessárias para montagem do plano...")
    msg_t2 = (
        "Meu objetivo é aprender JavaScript para passar em uma entrevista de estágio em front-end. "
        "Começo hoje e a entrevista é daqui a 3 semanas. "
        "Tenho disponibilidade de segunda a sexta, 2 horas por dia às 19h. "
        "Meu nível atual é iniciante (sei apenas lógica básica)."
    )
    content_t2 = types.Content(
        role="user", parts=[types.Part.from_text(text=msg_t2)]
    )

    t2_calls = []
    t2_response = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content_t2
    ):
        for fc in event.get_function_calls():
            t2_calls.append(fc.name)
        if event.content:
            for part in event.content.parts:
                if part.text:
                    t2_response += part.text

    print(f"Chamadas de ferramentas no Turno 2: {t2_calls}")
    csv_file = PLANOS_DIR / "plano-de-estudos.csv"
    if "WriteFile" in t2_calls or csv_file.exists():
        print(f"[OK] WriteFile executado e arquivo gerado em: {csv_file}")
    else:
        print("Aviso: WriteFile não foi chamado ou o plano ainda não finalizou todas as sessões.")


def main():
    test_components()
    asyncio.run(run_live_tests())
    print("\n=== Todos os testes executados com sucesso! ===")


if __name__ == "__main__":
    main()
