import os
import io
import time
import json
import pandas as pd
import streamlit as st
from datetime import datetime

# Importações locais
try:
    from core.scenarios import load_transcripts, build_scenarios, pick_scenario
    from core.ai_brain import CustomerBrain
    from core.stt_tts import transcribe_bytes, tts_bytes
    from core.scorer import ScoreEngine, CHECKLIST_WEIGHTS
    from core.utils import normalize_text
except ImportError as e:
    st.error(f"Erro ao importar módulos: {e}")
    st.error("Certifique-se de que todos os arquivos do core/ estão presentes")
    st.stop()

st.set_page_config(page_title="Voice Coach - MVP", layout="wide")

st.title("Voice Coach (MVP) — Treinador de Ligações Carglass")
st.caption("Simulador de cliente + Score automático (81 pts) baseado no seu checklist.")

# Verificar status das APIs
def check_api_status():
    status = {}
    
    # OpenAI
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if openai_key else "❌ Não configurado"
    except:
        status["openai"] = "❌ Não configurado"
    
    # Azure Speech
    try:
        azure_key = st.secrets.get("AZURE_SPEECH_KEY", os.getenv("AZURE_SPEECH_KEY"))
        azure_region = st.secrets.get("AZURE_SPEECH_REGION", os.getenv("AZURE_SPEECH_REGION"))
        status["azure"] = "✅ Configurado" if azure_key else "❌ Não configurado"
    except:
        status["azure"] = "❌ Não configurado"
    
    return status

# Sidebar com configurações
with st.sidebar:
    st.header("Configurações")
    
    # Status das APIs
    st.subheader("Status das APIs")
    api_status = check_api_status()
    st.write(f"**OpenAI:** {api_status['openai']}")
    st.write(f"**Azure Speech:** {api_status['azure']}")
    
    # Configurações
    dataset_file = st.file_uploader("Transcrições (CSV)", type=["csv"])
    use_llm = st.toggle("Usar LLM p/ persona/feedback", value=(api_status["openai"] == "✅ Configurado"))
    
    st.subheader("🔊 Opções de TTS")
    use_openai_tts = st.toggle("Usar OpenAI TTS", value=(api_status["openai"] == "✅ Configurado"))
    use_azure_tts = st.toggle("Usar Azure TTS", value=(api_status["azure"] == "✅ Configurado"))
    
    if not any([use_openai_tts, use_azure_tts]):
        st.info("💡 Usando gTTS (Google) como padrão")
    
    if not api_status["openai"] == "✅ Configurado" and (use_llm or use_openai_tts):
        st.warning("OpenAI não configurado. Será usado fallback.")
    
    if not api_status["azure"] == "✅ Configurado" and use_azure_tts:
        st.warning("Azure Speech não configurado. Será usado fallback.")
    
    st.info("💡 **Como configurar APIs:**\n"
           "1. Vá em Settings → Secrets\n"
           "2. Adicione suas chaves de API\n"
           "3. Reinicie a aplicação")

# Carregar dataset
if dataset_file:
    df = pd.read_csv(dataset_file)
    st.success(f"Dataset carregado: {len(df)} registros")
else:
    sample_path = "data/transcripts_sample.csv"
    try:
        df = load_transcripts(sample_path)
        st.info("Usando dataset de exemplo")
    except FileNotFoundError:
        st.error("Dataset de exemplo não encontrado. Faça upload de um arquivo CSV.")
        st.stop()

# Construir cenários a partir das transcrições
scenarios = build_scenarios(df)
scenario = pick_scenario(scenarios)

st.subheader("Cenário selecionado")
with st.expander("Ver detalhes do cenário", expanded=False):
    st.write(f"**Tipo**: {scenario['type']}")
    st.write(f"**ID da fonte**: {scenario.get('source_id', 'N/A')}")
    st.write(f"**Contexto**: {scenario['context'][:500]}...")

# Inicializar sistema
if "brain" not in st.session_state:
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []

if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

# Primeira fala do cliente (saudação)
if len(st.session_state.turns) == 0:
    first = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker":"customer","text":first, "ts": time.time()})

# Layout principal
col1, col2 = st.columns([1,1])

with col1:
    st.markdown("### 💬 Diálogo")
    if len(st.session_state.turns) == 0:
        st.info("A conversa começará quando o cliente fizer a primeira ligação.")
    else:
        for i, t in enumerate(st.session_state.turns):
            who = "🧑‍💼 Agente" if t["speaker"]=="agent" else "📞 Cliente"
            with st.chat_message("assistant" if t["speaker"]=="customer" else "user"):
                st.write(f"**{who}:** {t['text']}")

with col2:
    st.markdown("### 🎤 Gravar fala do agente")
    st.info("Grave sua resposta como atendente e receba feedback instantâneo!")
    
    audio_file = st.file_uploader(
        "Envie um áudio (wav/mp3)", 
        type=["wav","mp3"], 
        key="agent_audio",
        help="Grave sua resposta e faça upload do arquivo de áudio"
    )
    
    if st.button("🚀 Transcrever e Responder", type="primary", disabled=(audio_file is None)):
        with st.spinner("Processando áudio..."):
            # Transcrever áudio do agente
            audio_bytes = audio_file.read()
            agent_text = transcribe_bytes(audio_bytes)
            
            if agent_text and agent_text != "Erro na transcrição do áudio":
                agent_text = normalize_text(agent_text)
                st.session_state.turns.append({"speaker":"agent","text":agent_text, "ts": time.time()})
                
                # Mostrar transcrição
                st.success(f"**Transcrição:** {agent_text}")
                
                # Atualizar scores
                st.session_state.score.consume_turns(st.session_state.turns)
                
                # Gerar resposta do cliente
                with st.spinner("Cliente respondendo..."):
                    reply = st.session_state.brain.reply(st.session_state.turns)
                    st.session_state.turns.append({"speaker":"customer","text":reply, "ts": time.time()})
                
                # Gerar áudio da resposta
                with st.spinner("Gerando áudio..."):
                    audio_reply = tts_bytes(reply, use_openai=use_openai_tts, use_azure=use_azure_tts)
                    if audio_reply:
                        st.audio(audio_reply, format="audio/wav")
                        st.success(f"**Cliente respondeu:** {reply}")
                    else:
                        st.error("Erro ao gerar áudio da resposta")
                
                st.rerun()
            else:
                st.error("Não foi possível transcrever o áudio. Tente novamente.")

# Relatório de avaliação
st.divider()
st.markdown("## 📊 Relatório de Avaliação (Checklist 81 pts)")

if len([t for t in st.session_state.turns if t["speaker"]=="agent"]) == 0:
    st.info("Faça sua primeira interação para ver a avaliação!")
else:
    res = st.session_state.score.report()
    
    # Métricas principais
    col_metric1, col_metric2, col_metric3 = st.columns(3)
    with col_metric1:
        st.metric("Pontuação Total", f"{res['total']}/{res['max_total']}")
    with col_metric2:
        percentage = round((res['total'] / res['max_total']) * 100, 1)
        st.metric("Percentual", f"{percentage}%")
    with col_metric3:
        items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
        st.metric("Itens Completos", f"{items_ok}/12")
    
    # Tabela detalhada
    st.subheader("Detalhamento por Item")
    rows = []
    for i, item in enumerate(res["items"], start=1):
        status = "✅" if item["points"] == item["max_points"] else "⚠️" if item["points"] > 0 else "❌"
        rows.append({
            "Status": status,
            "Item": f"{i}",
            "Descrição": item["label"][:60] + "..." if len(item["label"]) > 60 else item["label"],
            "Pontuação": f"{item['points']}/{item['max_points']}",
            "Evidências": "; ".join(item["evidence"][:2]) if item["evidence"] else "Nenhuma"
        })
    
    st.dataframe(rows, use_container_width=True, hide_index=True)
    
    # Recomendações
    st.subheader("💡 Recomendações de Melhoria")
    for tip in res["tips"]:
        st.write(f"• {tip}")

# Ações finais
st.divider()
col_export, col_reset = st.columns(2)

with col_export:
    if st.button("📄 Exportar Relatório JSON", use_container_width=True):
        res = st.session_state.score.report()
        out = {
            "timestamp": datetime.utcnow().isoformat(),
            "scenario": scenario,
            "turns": st.session_state.turns,
            "score_report": res,
            "api_status": api_status
        }
        
        # Download direto
        st.download_button(
            label="⬇️ Baixar Relatório",
            data=json.dumps(out, ensure_ascii=False, indent=2),
            file_name=f"voice_coach_report_{int(time.time())}.json",
            mime="application/json"
        )

with col_reset:
    if st.button("🔄 Nova Sessão", use_container_width=True):
        # Limpar estado
        for key in ["brain", "turns", "score"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
