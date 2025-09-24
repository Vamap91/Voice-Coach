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

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[.,?!;:"(){}[\]]', "", text)
    return text

def transcribe_bytes(audio_bytes: bytes) -> str:
    return "Texto transcrito simulado - substitua por transcrição real"

def tts_bytes(text: str, use_openai: bool = False, use_azure: bool = False) -> bytes:
    try:
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

        if idx == 1:
            if re.search(r"\b(bom dia|boa tarde|boa noite)\b", text) and re.search(r"\bcarglass\b", text):
                points = max_points
                evidence.append("Saudação + Carglass encontrados")
        
        elif idx == 2:
            dados = len(re.findall(r"\b(cpf|placa|nome|telefone|endereço)\b", text))
            points = min(max_points, dados * 2)
            evidence.append(f"{dados} tipos de dados solicitados")
        
        elif idx == 3:
            if re.search(r"\b(lgpd|proteção de dados)\b", text):
                points = max_points
                evidence.append("LGPD mencionado")
        
        elif idx == 6:
            if re.search(r"\b(para-brisa|vidro|seguro|franquia)\b", text):
                points = max_points
                evidence.append("Conhecimento técnico demonstrado")
        
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
            "tips": tips[:3]
        }

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
        
        agent_last = ""
        for turn in reversed(turns):
            if turn["speaker"] == "agent":
                agent_last = turn["text"].lower()
                break
        
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
        
        if "placa" in agent_last and "cpf" in agent_last:
            return f"Claro! Minha placa é {self.customer_data['plate']} e meu CPF é {self.customer_data['cpf']}."
        
        elif ("dados" in agent_last or "informações" in agent_last) and ("cpf" in agent_last or "telefone" in agent_last):
            return f"Meu nome é {self.customer_data['name']}, CPF {self.customer_data['cpf']}, telefone {self.customer_data['phone1']}."
        
        elif ("segundo" in agent_last or "outro" in agent_last or "adicional" in agent_last or "secundário" in agent_last) and "telefone" in agent_last:
            return f"Tenho sim! O segundo número é {self.customer_data['phone2']}."
        
        elif ("celular" in agent_last or "whatsapp" in agent_last or "zap" in agent_last) and "principal" in agent_last:
            return f"Meu celular principal é {self.customer_data['phone1']}."
        
        elif "telefone" in agent_last and ("qual" in agent_last or "número" in agent_last):
            return f"Meu telefone é {self.customer_data['phone1']}."
        
        elif "placa" in agent_last and ("correto" in agent_last or "confirma" in agent_last or "certo" in agent_last):
            return f"Isso mesmo, {self.customer_data['plate']}."
        
        elif "cpf" in agent_last and ("correto" in agent_last or "confirma" in agent_last or "certo" in agent_last):
            return f"Exato, {self.customer_data['cpf']}."
        
        elif "nome" in agent_last and ("seu" in agent_last or "como" in agent_last):
            return f"Meu nome é {self.customer_data['name']}."
        
        elif "cpf" in agent_last and "seu" in agent_last:
            return f"Meu CPF é {self.customer_data['cpf']}."
        
        elif "placa" in agent_last and ("seu" in agent_last or "carro" in agent_last):
            return f"A placa do meu carro é {self.customer_data['plate']}, é um {self.customer_data['car']}."
        
        elif "endereço" in agent_last or ("onde" in agent_last and "mora" in agent_last):
            return f"Moro na {self.customer_data['address']}."
        
        elif any(word in agent_last for word in ["aconteceu", "ocorreu", "problema", "conte"]):
            return "Foi uma pedra que bateu no para-brisa ontem. A trinca tem uns 15cm e está crescendo."
        
        elif any(word in agent_last for word in ["trinca", "dano", "tamanho"]):
            return "A trinca tem uns 15cm, bem no meio do para-brisa. Aconteceu ontem quando passou um caminhão."
        
        elif any(word in agent_last for word in ["quando", "data"]):
            return "Foi ontem, dia 23. Estava dirigindo na marginal quando uma pedra bateu."
        
        elif any(word in agent_last for word in ["cidade", "onde", "região"]):
            return "Estou aqui em São Paulo, zona sul. Bairro Vila Olímpia."
        
        elif any(word in agent_last for word in ["loja", "unidade", "local"]):
            return "Pode ser na loja mais próxima de mim. Qual vocês têm na zona sul?"
        
        elif "email" in agent_last or "e-mail" in agent_last:
            return "Meu email é joao.silva@gmail.com"
        
        elif any(word in agent_last for word in ["obrigad", "agradeç"]):
            return "Eu que agradeço! Vocês são muito atenciosos."
        
        elif any(word in agent_last for word in ["ajudar", "ajuda"]):
            return "Sim, preciso trocar esse para-brisa. É coberto pelo seguro?"
        
        elif "como funciona" in agent_last:
            return "Nunca usei esse serviço. Vocês vão até minha casa ou tenho que levar na loja?"
        
        else:
            if len(turns) < 4:
                opcoes = [
                    "Perfeito! Como vocês podem me ajudar?",
                    "Ótimo! Qual o próximo passo?",
                    "Sim, pode me orientar?"
                ]
            else:
                opcoes = [
                    "Entendi. E agora?",
                    "Ok, pode continuar.",
                    "Certo, o que mais precisa?",
                    "Perfeito!"
                ]
            return random.choice(opcoes)

st.set_page_config(
    page_title="Voice Coach - Carglass", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        color: white;
        padding: 2rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .status-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .conversation-container {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        height: 500px;
        overflow-y: auto;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .input-section {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metrics-container {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .checklist-item {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .action-button {
        width: 100%;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>Voice Coach - Treinador de Ligações Carglass</h1><p>Simulador inteligente com avaliação automática baseada no checklist oficial</p></div>', unsafe_allow_html=True)

def check_api_status():
    status = {}
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if openai_key else "❌ Não configurado"
    except:
        status["openai"] = "❌ Não configurado"
    return status

with st.sidebar:
    st.header("⚙️ Configurações do Sistema")
    
    with st.container():
        st.subheader("Status das APIs")
        api_status = check_api_status()
        
        st.markdown(f"""
        <div class="status-card">
            <strong>OpenAI:</strong> {api_status['openai']}<br>
            <small>Usado para cliente inteligente e síntese de voz premium</small>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Configurações de IA")
    use_llm = st.toggle(
        "Cliente Inteligente", 
        value=(api_status["openai"] == "✅ Configurado"),
        help="Usa OpenAI para respostas mais naturais do cliente"
    )
    
    use_openai_tts = st.toggle(
        "Voz Premium", 
        value=(api_status["openai"] == "✅ Configurado"),
        help="Usa OpenAI TTS para melhor qualidade de áudio"
    )
    
    st.divider()
    
    st.subheader("Cliente Simulado")
    st.markdown("""
    **João Silva**  
    📱 11-99999-8888 / 11-97777-6666  
    🚗 ABC-1234 (Honda Civic 2020)  
    📍 São Paulo/SP  
    🔧 Trinca no para-brisa (15cm)
    """)
    
    if api_status["openai"] != "✅ Configurado":
        st.warning("⚠️ Configure a chave OpenAI em Settings → Secrets para funcionalidades avançadas")

scenario = {
    "type": "Troca de Para-brisa",
    "context": "Cliente liga reportando trinca no para-brisa causada por pedra",
    "source_id": "default"
}

if "brain" not in st.session_state:
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []

if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

if len(st.session_state.turns) == 0:
    first = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker":"customer","text":first, "ts": time.time()})

col_main, col_input = st.columns([2, 1])

with col_main:
    st.subheader("💬 Simulação de Atendimento")
    
    with st.container():
        st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
        
        for i, turn in enumerate(st.session_state.turns):
            if turn["speaker"] == "customer":
                with st.chat_message("assistant", avatar="📞"):
                    st.write(f"**Cliente:** {turn['text']}")
            else:
                with st.chat_message("user", avatar="👤"):
                    st.write(f"**Você:** {turn['text']}")
        
        st.markdown('</div>', unsafe_allow_html=True)

with col_input:
    st.subheader("🎤 Sua Interação")
    
    with st.container():
        st.markdown('<div class="input-section">', unsafe_allow_html=True)
        
        agent_text = st.text_area(
            "Digite sua resposta:",
            placeholder="Ex: Bom dia! Carglass, meu nome é Maria. Como posso ajudá-lo?",
            height=120,
            key="agent_input"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            send_button = st.button(
                "💬 Enviar", 
                type="primary", 
                disabled=not agent_text,
                use_container_width=True
            )
        
        with col_btn2:
            if st.button("🔄 Reiniciar", use_container_width=True):
                for key in ["brain", "turns", "score"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        if send_button and agent_text:
            st.session_state.turns.append({"speaker":"agent","text":agent_text, "ts": time.time()})
            st.session_state.score.consume_turns(st.session_state.turns)
            
            reply = st.session_state.brain.reply(st.session_state.turns)
            st.session_state.turns.append({"speaker":"customer","text":reply, "ts": time.time()})
            
            with st.spinner("Gerando resposta do cliente..."):
                audio_reply = tts_bytes(reply, use_openai=use_openai_tts)
                if audio_reply:
                    st.audio(audio_reply, format="audio/wav", autoplay=True)
            
            st.rerun()
        
        st.divider()
        
        st.markdown("**🎙️ Upload de Áudio**")
        audio_file = st.file_uploader(
            "Envie seu áudio", 
            type=["wav","mp3"],
            help="Grave sua resposta e envie o arquivo"
        )
        
        if audio_file:
            st.info("🔧 Transcrição automática será implementada em breve")
        
        st.markdown('</div>', unsafe_allow_html=True)

st.divider()

if len([t for t in st.session_state.turns if t["speaker"]=="agent"]) > 0:
    res = st.session_state.score.report()
    
    st.markdown("## 📊 Avaliação em Tempo Real")
    
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pontuação Total", f"{res['total']}")
    
    with col2:
        st.metric("Máximo Possível", f"{res['max_total']}")
    
    with col3:
        percentage = round((res['total'] / res['max_total']) * 100, 1)
        color = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
        st.metric("Performance", f"{percentage}% {color}")
    
    with col4:
        items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
        st.metric("Itens Completos", f"{items_ok}/12")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.expander("📋 Checklist Detalhado", expanded=True):
        for i, item in enumerate(res["items"], 1):
            status_icon = "✅" if item["points"] == item["max_points"] else "⚠️" if item["points"] > 0 else "❌"
            
            st.markdown(f"""
            <div class="checklist-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 1;">
                        <strong>{status_icon} Item {i}</strong><br>
                        <small>{item['label']}</small>
                    </div>
                    <div style="text-align: right;">
                        <strong>{item['points']}/{item['max_points']} pts</strong>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    if res["tips"]:
        st.subheader("💡 Recomendações de Melhoria")
        for tip in res["tips"][:3]:
            st.info(tip)
    
    col_export, col_report = st.columns(2)
    
    with col_export:
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "scenario": scenario,
            "turns": st.session_state.turns,
            "final_score": res
        }
        
        st.download_button(
            label="📄 Exportar Relatório",
            data=json.dumps(report_data, ensure_ascii=False, indent=2),
            file_name=f"voice_coach_report_{int(time.time())}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_report:
        st.button("📈 Ver Relatório Completo", use_container_width=True, disabled=True, help="Em desenvolvimento")

else:
    st.info("👆 Digite sua primeira resposta para iniciar a avaliação automática!")

st.markdown("---")
st.markdown("**🎯 Voice Coach** - Sistema de treinamento profissional para equipes Carglass | Versão MVP")
