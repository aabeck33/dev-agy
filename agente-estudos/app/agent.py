import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.environment import LocalEnvironment
from google.adk.skills import load_skill_from_dir
from google.adk.tools.environment import EnvironmentToolset
from google.adk.tools.skill_toolset import SkillToolset

# Carrega variáveis de ambiente locais (.env)
load_dotenv()

# Caminhos absolutos
BASE_DIR = Path(__file__).parent.resolve()
PLANOS_DIR = (BASE_DIR.parent / "planos").resolve()
PLANOS_DIR.mkdir(parents=True, exist_ok=True)

SKILL_DIR = (BASE_DIR / "skills" / "plano-de-estudos").resolve()


class FerramentasDeArquivo(EnvironmentToolset):
    """Subclasse de EnvironmentToolset que expõe exclusivamente ReadFile e WriteFile."""

    async def get_tools(self, readonly_context=None):
        tools = await super().get_tools(readonly_context)
        return [t for t in tools if t.name in ("ReadFile", "WriteFile")]


def instruction_provider(context=None) -> str:
    """Injeta a data de hoje na instrução do agente para referência temporal relativa."""
    hoje = datetime.now()
    dias_semana = [
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    ]
    dia_nome = dias_semana[hoje.weekday()]
    data_formatada = f"{dia_nome}, {hoje.strftime('%d/%m/%Y')}"

    return (
        f"Hoje é {data_formatada}.\n\n"
        "Você é o Agente de Estudos, um mentor especialista em planejar estudos de forma personalizada.\n"
        "Para organizar estudos, montar cronogramas ou preparar para provas, utilize a skill 'plano-de-estudos' "
        "através das ferramentas disponíveis no SkillToolset.\n"
        "Siga rigorosamente a Regra de Ativação (gating) e a divulgação progressiva da skill, "
        "não carregando recursos adicionais (L3) enquanto faltarem informações obrigatórias.\n"
        "Quando o plano estiver completo, utilize a ferramenta WriteFile para salvar a agenda no arquivo 'plano-de-estudos.csv'."
    )


# Carrega a skill a partir da pasta app/skills/plano-de-estudos
plano_skill = load_skill_from_dir(SKILL_DIR)
skill_toolset = SkillToolset(skills=[plano_skill])

# Toolset restrito a ReadFile e WriteFile, operando na pasta persistente planos/
file_toolset = FerramentasDeArquivo(
    environment=LocalEnvironment(working_dir=str(PLANOS_DIR))
)

# Modelo lido da variável de ambiente MODEL (padrão: gemini-3.8-flash)
model_name = os.getenv("MODEL", "gemini-3.8-flash")

root_agent = Agent(
    name="agente_estudos",
    model=model_name,
    instruction=instruction_provider,
    description="Agente mentor de estudos personalizado movido a skills.",
    tools=[skill_toolset, file_toolset],
)
