import os, random
from core.utils import normalize_text
from core.scenarios import persona_from_scenario
from openai import OpenAI

class CustomerBrain:
    def __init__(self, use_llm: bool, scenario: dict):
        self.use_llm = use_llm and (os.getenv("OPENAI_API_KEY") is not None)
        self.scenario = scenario
        self.persona = persona_from_scenario(scenario)
        self.stage = 0
        if self.use_llm:
            self.client = OpenAI()

    def first_utterance(self):
        return "Olá, bom dia! Eu sou segurado e preciso resolver um problema no para-brisa."

    def reply(self, turns):
        # FSM simplificada por estágio (coleta dados, confirmar dano, escolher loja, encerrar)
        agent_last = normalize_text(next((t["text"] for t in reversed(turns) if t["speaker"]=="agent"), ""))
        self.stage = min(self.stage + 1, 4)

        if self.use_llm:
            prompt = f"""
Você é um cliente brasileiro. Persona: {self.persona}.
Cenário: {self.scenario['type']} - {self.scenario['context'][:300]}
Última fala do atendente: "{agent_last}"
Responda de forma curta, natural, mantendo o foco no próximo passo do fluxo (estágio {self.stage}).
"""
            rsp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.6,
            )
            return rsp.choices[0].message.content.strip()

        # Sem LLM: respostas fixas por estágio
        canned = [
            "Certo, meu CPF é 123.456.789-10 e minha placa é ABC1D23.",
            "A trinca tem uns 10 cm. Aconteceu ontem, peguei um buraco.",
            "Estou em Belo Horizonte. Pode ser a loja do bairro Funcionários?",
            "Obrigado. Pode me enviar o link de acompanhamento, por favor?"
        ]
        return canned[self.stage-1]
