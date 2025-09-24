import os
import io
import time
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from core.scenarios import load_transcripts, build_scenarios, pick_scenario
from core.ai_brain import CustomerBrain
from core.stt_tts import transcribe_bytes, tts_bytes
from core.scorer import ScoreEngine, CHECKLIST_WEIGHTS
from core.utils import normalize_text

st.set_page_config(page_title="Voice Coach - MVP", layout="wide")

st.title("Voice Coach (MVP) — Treinador de Ligações Carglass")
st.caption("Simulador de cliente + Score automático (81 pts) baseado no seu checklist.")

# 1) Carregar transcrições reais (dataset)
with st.sidebar:
    st.header("Configurações")
    dataset_file = st.file_uploader("Transcrições (CSV)", type=["csv"])
    use_llm = st.toggle("Usar LLM p/ persona/feedback", value=False)
    use_azure_tts = st.toggle("Usar Azure TTS (se chave presente)", value=False)
    st.info("Sem chaves, o app roda com heurísticas + gTTS.")

if dataset_file:
    df = pd.read_csv(dataset_file)
else:
    sample_path = "data/transcripts_sample.csv"
    df = load_transcripts(sample_path)

# 2) Construir cenários a partir das transcrições
scenarios = build_scenarios(df)
scenario = pick_scenario(scenarios)

st.subheader("Cenário selecionado")
st.write(f"**Tipo**: {scenario['type']}  | **Contexto**: {scenario['context'][:200]}...")

# 3) Inicializar “cliente”
if "brain" not in st.session_state:
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []  # [{"speaker":"agent|customer","text":str}]
if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

# 4) Primeira fala do cliente (saudação)
if len(st.session_state.turns) == 0:
    first = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker":"customer","text":first, "ts": time.time()})

col1, col2 = st.columns([1,1])

with col1:
    st.markdown("### Diálogo")
    for t in st.session_state.turns:
        who = "🧑‍💼 Agente" if t["speaker"]=="agent" else "📞 Cliente"
        st.markdown(f"**{who}:** {t['text']}")

with col2:
    st.markdown("### Gravar fala do agente")
    # Interface simples: o agente faz upload de um áudio curto (wav) — dá para trocar por stream (streamlit-webrtc)
    audio_file = st.file_uploader("Envie um trecho de áudio (wav/mp3)", type=["wav","mp3"], key="agent_audio")
    if st.button("Transcrever e Responder", type="primary", disabled=(audio_file is None)):
        audio_bytes = audio_file.read()
        agent_text = transcribe_bytes(audio_bytes)  # Whisper local ou provedor
        agent_text = normalize_text(agent_text)
        st.session_state.turns.append({"speaker":"agent","text":agent_text, "ts": time.time()})

        # 5) Atualiza SCORES (12 itens) com base na fala do agente + contexto
        st.session_state.score.consume_turns(st.session_state.turns)

        # 6) Gera próxima fala do cliente
        reply = st.session_state.brain.reply(st.session_state.turns)
        st.session_state.turns.append({"speaker":"customer","text":reply, "ts": time.time()})

        # 7) TTS da fala do cliente
        audio_reply = tts_bytes(reply, use_azure=use_azure_tts)
        st.audio(audio_reply, format="audio/wav")

st.divider()
st.markdown("## Relatório parcial (Checklist 81 pts)")
res = st.session_state.score.report()

def pct(p, maxp): return f"{p}/{maxp} pts"

# Tabela compacta
rows = []
for i, item in enumerate(res["items"], start=1):
    rows.append({
        "Item": f"{i}",
        "Descrição": item["label"],
        "Pontuação": pct(item["points"], item["max_points"]),
        "Evidências": "; ".join(item["evidence"][:2]) if item["evidence"] else ""
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True)

st.metric("Pontuação Total", f"{res['total']}/{res['max_total']} pts")

# Recomendações de melhoria (geradas por heurística e opcionalmente LLM)
st.markdown("### Recomendações automáticas")
for tip in res["tips"]:
    st.write(f"• {tip}")

# Exportar sessão
if st.button("Exportar relatório JSON"):
    out = {
        "timestamp": datetime.utcnow().isoformat(),
        "scenario": scenario,
        "turns": st.session_state.turns,
        "score_report": res
    }
    ts = int(time.time())
    path = f"reports/session_{ts}.json"
    os.makedirs("reports", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    st.success(f"Relatório exportado em {path}")

