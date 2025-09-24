import os
import io
import time
import json
import random
import re
import pandas as pd
import streamlit as st
from datetime import datetime
from gtts import gTTS

# ===== FUNÇÕES UTILITÁRIAS =====
def normalize_text(text: str) -> str:
    """Normaliza o texto para análise."""
    if not text:
        return ""
    text = text.lower()
    # Remove pontuação comum
    text = re.sub(r'[.,?!;:"(){}[\]]', "", text)
    return text

def transcribe_bytes(audio_bytes: bytes) -> str:
    """Transcrição simulada - substitua por Whisper se disponível."""
    # Por enquanto, retorna texto placeholder
    # TODO: Implementar Whisper quando bibliotecas estiverem disponíveis
    return "Texto transcrito simulado - substitua por transcrição real"

def tts_bytes(text: str, use_openai: bool = False, use_azure: bool = False) -> bytes:
    """Converte texto em áudio usando gTTS."""
    try:
        # 1. Tenta OpenAI TTS se habilitado
        if use_openai:
            try:
                openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
                if openai_key:
                    from openai import OpenAI
                    client = OpenAI(api_key=openai_key)
                    
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=text,
                        speed=1.0
                    )
                    return response.content
            except Exception as e:
                st.warning(f"OpenAI TTS falhou: {e}")
        
        # 2. Fallback gTTS
        if not text.strip():
            return b""
        
        tts = gTTS(text=text, lang="pt", slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
        
    except Exception as e:
        st.error(f"Erro no TTS: {e}")
        return b""

# ===== CHECKLIST E SCORING =====
CHECKLIST_WEIGHTS = [
    (1, 10, "Atendeu em 5s e saudação correta com técnicas de atendimento encantador"),
    (2,  6, "Solicitou dados completos (2 telefones, nome, CPF, placa, endereço)"),
    (3,  2, "Verbalizou o script LGPD"),
    (4,  5, "Repetiu verbalmente 2 de 3 (placa, telefone, CPF) para confirmar"),
    (5,  3, "Evitou solicitações duplicadas e escutou atentamente"),
    (6,  5, "Compreendeu a solicitação e demonstrou conhecimento dos serviços"),
    (7, 10, "Confirmou informações completas do dano (data, motivo, registro, pintura, tamanho trinca)"),
    (8, 10, "Confirmou cidade e selecionou corretamente a primeira loja do sistema"),
    (9,  5, "Comunicação eficaz (sem gírias, avisou ausências/retornos)"),
    (10, 4, "Conduta acolhedora (empatia, sorriso na voz)"),
    (11,15, "Script de encerramento completo (validade, franquia, link de acompanhamento/vistoria)"),
    (12, 6, "Orientou sobre a pesquisa de satisfação")
]

class ScoreEngine:
    def __init__(self):
        self.turns = []

    def consume_turns(self, turns):
        self.turns = turns

    def _agent_text(self):
        return " ".join([t["text"] for t in self.turns if t["speaker"]=="agent"])

    def _score_item(self, idx, text: str):
        evidence = []
        points = 0
        max_points = next(m for i,m,_ in CHECKLIST_WEIGHTS if i == idx)

        # Regras simplificadas de pontuação
        if idx == 1:  # Saudação
            if re.search(r"\b(bom dia|boa tarde|boa noite)\b", text) and re.search(r"\bcarglass\b", text):
                points = max_points
                evidence.append("Saudação + Carglass encontrados")
        
        elif idx == 2:  # Dados
            dados = len(re.findall(r"\b(cpf|placa|nome|telefone|endereço)\b", text))
            points = min(max_points, dados * 2)
            evidence.append(f"{dados} tipos de dados solicitados")
        
        elif idx == 3:  # LGPD
            if re.search(r"\b(lgpd|proteção de dados)\b", text):
                points = max_points
                evidence.append("LGPD mencionado")
        
        elif idx == 6:  # Conhecimento
            if re.search(r"\b(para-brisa|vidro|seguro|franquia)\b", text):
                points = max_points
                evidence.append("Conhecimento técnico demonstrado")
        
        # Adicione mais regras conforme necessário
        
        return points, evidence

    def report(self):
        text = normalize_text(self._agent_text())
        items = []
        total = 0
        
        for idx, maxp, label in CHECKLIST_WEIGHTS:
            pts, ev = self._score_item(idx, text)
            total += pts
            items.append({
                "idx": idx, 
                "label": label, 
                "points": pts, 
                "max_points": maxp, 
                "evidence": ev
            })
        
        tips = []
        for item in items:
            if item["points"] < item["max_points"]:
                tips.append(f"Melhore item {item['idx']}: {item['label'][:50]}...")
        
        if not tips:
            tips.append("Excelente! Todos os critérios foram atendidos.")
        
        return {
            "items": items, 
            "total": total, 
            "max_total": sum(m for _,m,_ in CHECKLIST_WEIGHTS), 
            "tips": tips[:3]  # Máximo 3 dicas
        }

# ===== SIMULADOR DE CLIENTE =====
class CustomerBrain:
    def __init__(self, use_llm: bool, scenario: dict):
        self.use_llm = use_llm
        self.scenario = scenario
        self.stage = 0
        self.customer_data = {
            "name": "João Silva",
            "cpf": "123.456.789-10",
            "phone1": "11-99999-8888",
            "phone2": "11-97777-6666",
            "plate": "ABC-1234",
            "car": "Civic 2020",
            "address": "Rua das Flores, 123 - São Paulo/SP"
        }
        
        # Verifica OpenAI
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.use_llm = use_llm and (openai_key is not None)
        
        if self.use_llm:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=openai_key)
            except:
                self.use_llm = False

    def first_utterance(self):
        opcoes = [
            "Olá, bom dia! Eu sou segurado e preciso resolver um problema no para-brisa.",
            "Oi, boa tarde! Tenho um problema no vidro do meu carro.",
            "Alô? Preciso de ajuda com o para-brisa do meu veículo."
        ]
        return random.choice(opcoes)

    def reply(self, turns):
        if not turns:
            return self.first_utterance()
        
        # Pega a última fala do agente
        agent_last = ""
        for turn in reversed(turns):
            if turn["speaker"] == "agent":
                agent_last = turn["text"].lower()
                break
        
        # Usa LLM se disponível
        if self.use_llm:
            try:
                prompt = f"""
Você é {self.customer_data['name']}, um cliente brasileiro ligando para a Carglass.

SEUS DADOS:
- Nome: {self.customer_data['name']}
- CPF: {self.customer_data['cpf']}
- Telefone 1: {self.customer_data['phone1']}
- Telefone 2: {self.customer_data['phone2']}
- Placa: {self.customer_data['plate']}
- Carro: {self.customer_data['car']}
- Endereço: {self.customer_data['address']}

PROBLEMA: Trinca no para-brisa de uns 15cm, causada por pedra ontem.

Última fala do atendente: "{agent_last}"

Responda naturalmente como um cliente brasileiro real. Se perguntaram dados específicos, forneça-os. Seja breve (máximo 2 frases).
"""
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=100
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                st.warning(f"OpenAI falhou: {e}, usando resposta inteligente")
        
        # Sistema de respostas inteligentes baseado no que o agente perguntou
        
        # Detecta o que o agente está perguntando
        if any(word in agent_last for word in ["segundo", "outro", "mais um", "adicional"]) and "telefone" in agent_last:
            return f"Sim, tenho outro número: {self.customer_data['phone2']}."
        
        elif any(word in agent_last for word in ["celular", "whatsapp", "zap"]):
            return f"Meu celular é {self.customer_data['phone1']}, pode usar para WhatsApp também."
        
        elif "cpf" in agent_last and ("repetir" in agent_last or "confirma" in agent_last):
            return f"Isso mesmo, {self.customer_data['cpf']}."
        
        elif "placa" in agent_last and ("repetir" in agent_last or "confirma" in agent_last):
            return f"Exato, {self.customer_data['plate']}."
        
        elif "endereço" in agent_last or "onde" in agent_last:
            return f"Moro na {self.customer_data['address']}."
        
        elif any(word in agent_last for word in ["nome", "como", "chama"]):
            return f"Meu nome é {self.customer_data['name']}."
        
        elif "cpf" in agent_last:
            return f"Meu CPF é {self.customer_data['cpf']}."
        
        elif "placa" in agent_last:
            return f"A placa é {self.customer_data['plate']}, é um {self.customer_data['car']}."
        
        elif "telefone" in agent_last:
            return f"Meu telefone é {self.customer_data['phone1']}."
        
        elif any(word in agent_last for word in ["trinca", "dano", "problema", "aconteceu"]):
            return "A trinca tem uns 15cm, foi uma pedra que bateu ontem. Está bem no meio do para-brisa."
        
        elif any(word in agent_last for word in ["cidade", "loja", "onde", "local"]):
            return "Estou aqui em São Paulo, zona sul. Qual a loja mais próxima?"
        
        elif any(word in agent_last for word in ["email", "e-mail"]):
            return "Pode usar joao.silva@email.com"
        
        elif any(word in agent_last for word in ["obrigad", "ok", "certo", "perfeito"]):
            return "De nada! Muito obrigado pela atenção."
        
        # Respostas genéricas por contexto
        elif any(word in agent_last for word in ["ajudar", "ajuda"]):
            return "Preciso trocar o para-brisa do meu carro. Vocês fazem pelo seguro?"
        
        else:
            # Resposta padrão mais natural
            opcoes = [
                "Sim, pode me ajudar com isso?",
                "Perfeito, como funciona?",
                "Certo, e agora?",
                "Ok, entendi."
            ]
            return random.choice(opcoes)

# ===== INTERFACE STREAMLIT =====
st.set_page_config(page_title="Voice Coach - MVP", layout="wide")

st.title("🎯 Voice Coach (MVP) — Treinador de Ligações Carglass")
st.caption("Simulador de cliente + Score automático (81 pts) baseado no checklist.")

# Verificar APIs
def check_api_status():
    status = {}
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if openai_key else "❌ Não configurado"
    except:
        status["openai"] = "❌ Não configurado"
    return status

# Sidebar
with st.sidebar:
    st.header("⚙️ Configurações")
    
    api_status = check_api_status()
    st.subheader("Status das APIs")
    st.write(f"**OpenAI:** {api_status['openai']}")
    
    use_llm = st.toggle("Usar OpenAI para cliente inteligente", 
                       value=(api_status["openai"] == "✅ Configurado"))
    use_openai_tts = st.toggle("Usar OpenAI TTS (voz de qualidade)", 
                              value=(api_status["openai"] == "✅ Configurado"))
    
    if not api_status["openai"] == "✅ Configurado":
        st.info("💡 Configure OpenAI em Settings → Secrets")

# Cenário
scenario = {
    "type": "Troca de Para-brisa",
    "context": "Cliente liga reportando trinca no para-brisa causada por pedra",
    "source_id": "default"
}

st.subheader("📋 Cenário Selecionado")
with st.expander("Ver detalhes", expanded=False):
    st.write(f"**Tipo:** {scenario['type']}")
    st.write(f"**Contexto:** {scenario['context']}")

# Inicializar sistema
if "brain" not in st.session_state:
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []

if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

# Primeira fala do cliente
if len(st.session_state.turns) == 0:
    first = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker":"customer","text":first, "ts": time.time()})

# Layout principal
col1, col2 = st.columns([1,1])

with col1:
    st.markdown("### 💬 Conversa")
    for i, turn in enumerate(st.session_state.turns):
        if turn["speaker"] == "customer":
            with st.chat_message("assistant", avatar="📞"):
                st.write(f"**Cliente:** {turn['text']}")
        else:
            with st.chat_message("user", avatar="🧑‍💼"):
                st.write(f"**Agente:** {turn['text']}")

with col2:
    st.markdown("### 🎤 Sua Resposta")
    
    # Opção 1: Texto direto (para testes rápidos)
    st.markdown("**Opção 1: Digite sua resposta**")
    agent_text = st.text_area("Digite o que você falaria:", 
                             placeholder="Ex: Bom dia! Carglass, meu nome é Maria...",
                             key="agent_input")
    
    if st.button("💬 Enviar Resposta", type="primary", disabled=not agent_text):
        # Adicionar resposta do agente
        st.session_state.turns.append({"speaker":"agent","text":agent_text, "ts": time.time()})
        
        # Atualizar score
        st.session_state.score.consume_turns(st.session_state.turns)
        
        # Resposta do cliente
        reply = st.session_state.brain.reply(st.session_state.turns)
        st.session_state.turns.append({"speaker":"customer","text":reply, "ts": time.time()})
        
        # TTS da resposta
        with st.spinner("Gerando áudio do cliente..."):
            audio_reply = tts_bytes(reply, use_openai=use_openai_tts)
            if audio_reply:
                st.audio(audio_reply, format="audio/wav")
        
        st.rerun()
    
    # Opção 2: Upload de áudio
    st.divider()
    st.markdown("**Opção 2: Upload de áudio**")
    audio_file = st.file_uploader("Grave e envie seu áudio", type=["wav","mp3"])
    
    if audio_file and st.button("🎵 Processar Áudio"):
        st.info("Funcionalidade de transcrição será implementada com Whisper")
        # audio_bytes = audio_file.read()
        # transcription = transcribe_bytes(audio_bytes)
        # st.write(f"Transcrição: {transcription}")

# Avaliação
st.divider()
st.markdown("## 📊 Avaliação em Tempo Real")

if len([t for t in st.session_state.turns if t["speaker"]=="agent"]) == 0:
    st.info("👆 Faça sua primeira interação para ver a avaliação!")
else:
    res = st.session_state.score.report()
    
    # Métricas
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("📈 Pontuação", f"{res['total']}/{res['max_total']}")
    with col_m2:
        percentage = round((res['total'] / res['max_total']) * 100, 1)
        st.metric("📊 Percentual", f"{percentage}%")
    with col_m3:
        items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
        st.metric("✅ Completos", f"{items_ok}/12")
    
    # Detalhamento
    st.subheader("📋 Checklist Detalhado")
    for i, item in enumerate(res["items"], 1):
        col_status, col_desc, col_points = st.columns([1, 8, 2])
        
        with col_status:
            if item["points"] == item["max_points"]:
                st.success("✅")
            elif item["points"] > 0:
                st.warning("⚠️")
            else:
                st.error("❌")
        
        with col_desc:
            st.write(f"**{i}.** {item['label']}")
            if item["evidence"]:
                st.caption(f"Evidências: {'; '.join(item['evidence'])}")
        
        with col_points:
            st.write(f"`{item['points']}/{item['max_points']}`")
    
    # Dicas
    st.subheader("💡 Dicas de Melhoria")
    for tip in res["tips"]:
        st.write(f"• {tip}")

# Ações finais
st.divider()
col_exp, col_reset = st.columns(2)

with col_exp:
    if st.button("📄 Exportar Sessão"):
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario,
            "turns": st.session_state.turns,
            "final_score": st.session_state.score.report()
        }
        
        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(report_data, ensure_ascii=False, indent=2),
            file_name=f"voice_coach_{int(time.time())}.json",
            mime="application/json"
        )

with col_reset:
    if st.button("🔄 Nova Sessão"):
        for key in ["brain", "turns", "score"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Footer
st.markdown("---")
st.markdown("🚀 **Voice Coach MVP** - Treinamento inteligente para equipes Carglass")
