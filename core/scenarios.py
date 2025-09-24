import pandas as pd
import random

def load_transcripts(path: str) -> pd.DataFrame:
    """Carrega e normaliza as transcrições de um arquivo CSV."""
    df = pd.read_csv(path)
    # Adicione aqui a normalização de colunas se necessário
    return df

def build_scenarios(df: pd.DataFrame) -> list:
    """Constrói cenários de treinamento a partir do DataFrame de transcrições."""
    scenarios = []
    # Agrupa por um ID de chamada ou similar, se disponível
    if "IdAnalysis" in df.columns:
        for _, group in df.groupby("IdAnalysis"):
            context = " ".join(group["Transcrição da Ligação"].astype(str))
            # Tenta extrair um "tipo" de cenário (ex: troca de para-brisa, problema com tag)
            scenario_type = "Não definido"
            if "para-brisa" in context.lower():
                scenario_type = "Troca de Para-brisa"
            elif "retrovisor" in context.lower():
                scenario_type = "Troca de Retrovisor"
            elif "tag" in context.lower():
                scenario_type = "Problema com Tag de Pedágio"

            scenarios.append({
                "type": scenario_type,
                "context": context,
                "source_id": group["IdAnalysis"].iloc[0]
            })
    return scenarios

def pick_scenario(scenarios: list) -> dict:
    """Seleciona um cenário aleatório da lista."""
    return random.choice(scenarios) if scenarios else {
        "type": "Padrão",
        "context": "O cliente liga para relatar um problema com o veículo.",
        "source_id": "default"
    }

def persona_from_scenario(scenario: dict) -> str:
    """Gera uma persona de cliente simples com base no contexto do cenário."""
    context = scenario.get("context", "").lower()
    if "corretor" in context:
        return "Corretor de seguros agindo em nome do cliente, focado em resolver o problema rapidamente."
    if "caminhão" in context:
        return "Motorista de caminhão, prático e direto, preocupado com o tempo de parada do veículo."
    if "não estou conseguindo pagar" in context:
        return "Cliente frustrado com um problema de pagamento, um pouco impaciente."
    return "Cliente segurado padrão, buscando resolver um problema com seu veículo de forma clara e objetiva."

