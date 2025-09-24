import re
from core.utils import normalize_text

CHECKLIST_WEIGHTS = [
    (1, 10, "Atendeu em 5s e saudação correta com técnicas de atendimento encantador"),
    (2,  6, "Solicitou dados completos (2 telefones, nome, CPF, placa, endereço) — exceções Bradesco/Sura/ALD"),
    (3,  2, "Verbalizou o script LGPD"),
    (4,  5, "Repetiu verbalmente 2 de 3 (placa, telefone, CPF) para confirmar"),
    (5,  3, "Evitou solicitações duplicadas e escutou atentamente"),
    (6,  5, "Compreendeu a solicitação e demonstrou conhecimento dos serviços"),
    (7, 10, "Confirmou informações completas do dano (data, motivo, registro, pintura, tamanho trinca, LED/Xenon etc.)"),
    (8, 10, "Confirmou cidade e selecionou corretamente a primeira loja do sistema"),
    (9,  5, "Comunicação eficaz (sem gírias, avisou ausências/retornos)"),
    (10, 4, "Conduta acolhedora (empatia, sorriso na voz)"),
    (11,15, "Script de encerramento completo (validade, franquia, link de acompanhamento/vistoria, aguardar contato)"),
    (12, 6, "Orientou sobre a pesquisa de satisfação")
]

class ScoreEngine:
    def __init__(self):
        self.turns = []

    def consume_turns(self, turns):
        self.turns = turns

    def _agent_text(self):
        return " ".join([t["text"] for t in self.turns if t["speaker"]=="agent"])

    def report(self):
        text = normalize_text(self._agent_text())
        items = []
        total = 0
        for idx, maxp, label in CHECKLIST_WEIGHTS:
            pts, ev = self._score_item(idx, text)
            total += pts
            items.append({"idx": idx, "label": label, "points": pts, "max_points": maxp, "evidence": ev})
        tips = self._tips(items)
        return {"items": items, "total": total, "max_total": sum(m for _,m,_ in CHECKLIST_WEIGHTS), "tips": tips}

    # --- regras (heurísticas simples, fáceis de ajustar) ---
    def _score_item(self, idx, text: str):
        ev = []
        points = 0

        def found(patterns):
            for p in patterns:
                if re.search(p, text):
                    ev.append(p)
                    return True
            return False

        if idx == 1:
            if found([r"\b(bom dia|boa tarde|boa noite)\b"]) and found([r"\b(carglass)\b"]):
                points = 10
        elif idx == 2:
            needed = sum([bool(re.search(p, text)) for p in [
                r"\bcpf\b", r"\bplaca\b", r"\bnome\b",
                r"\bendere[cç]o\b", r"\btelefone\b", r"\boutro telefone\b|\bsegundo telefone\b"
            ]])
            points = 6 if needed >= 5 else 0
        elif idx == 3:
            if found([r"\b(LGPD|lei geral de prote[cç][aã]o de dados)\b", r"seus dados.*prote"]):
                points = 2
        elif idx == 4:
            # confirmações explícitas
            confs = sum([bool(re.search(p, text)) for p in [
                r"\bconfirmando seu cpf\b", r"\bconfirmando sua placa\b", r"\bconfirmando seu telefone\b",
                r"\bconfere\b.*(cpf|placa|telefone)"
            ]])
            points = 5 if confs >= 2 else 0
        elif idx == 5:
            # proxys: "como você informou", "entendi", ausência de "me diga de novo"
            if found([r"\bcomo voc[eê] informou\b", r"\bentendi\b"]) and not re.search(r"\b(repete|novamente|de novo)\b", text):
                points = 3
        elif idx == 6:
            if found([r"\bpara-brisa\b|\bparabrisa\b|\bvidro\b|\bseguro\b|\bfranquia\b"]):
                points = 5
        elif idx == 7:
            hits = sum([bool(re.search(p, text)) for p in [
                r"\bdata\b", r"\bmotivo\b|\baconteceu\b", r"\bregistro\b", r"\bpintura\b",
                r"\btamanho da trinca\b|\btrinca\b", r"\bled\b|\bxenon\b"
            ]])
            points = 10 if hits >= 4 else 0
        elif idx == 8:
            if found([r"\bcidade\b|\bloja\b|\bagendar na loja\b|\bprimeira op[cç][aã]o\b"]):
                points = 10
        elif idx == 9:
            if not re.search(r"\b(giria|mano|tipo assim)\b", text):
                # plus: avisos de ausência/retorno
                if found([r"\bvou verificar e j[aá] retorno\b", r"\bvoltei\b|\bretornei\b"]):
                    points = 5
                else:
                    points = 3
        elif idx == 10:
            if found([r"\bposso te ajudar\b", r"\bestou aqui para ajudar\b", r"\bentendo\b", r"\bacompanho voc[eê]\b"]):
                points = 4
        elif idx == 11:
            hits = sum([bool(re.search(p, text)) for p in [
                r"\bprazo de validade\b|\bvalidade da proposta\b",
                r"\bfranquia\b",
                r"\blink\b.*(acompanhamento|vistoria)",
                r"\baguarde o contato\b|\bentraremos em contato\b"
            ]])
            points = 15 if hits >= 3 else 0
        elif idx == 12:
            if found([r"\bpesquisa de satisfa[cç][aã]o\b"]):
                points = 6

        return points, ev

    def _tips(self, items):
        tips = []
        for item in items:
            if item["points"] < item["max_points"]:
                tips.append(f"Melhore o item {item["idx"]}: {item["label"]}. Pontuação atual: {item["points"]}/{item["max_points"]}.")
        if not tips:
            tips.append("Excelente! Todos os itens do checklist foram atendidos.")
        return tips

