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
import numpy as np

st.set_page_config(page_title="Voice Coach - Real Time", layout="wide")

def load_system_prompt():
    try:
        with open("data/prompts/system_ptbr.md", "r", encoding="utf-8") as f:
            base_prompt = f.read().strip()
    except FileNotFoundError:
        base_prompt = """
Você é um assistente de treinamento de atendimento ao cliente. Seu objetivo é simular um cliente em uma ligação de suporte, seguindo o cenário e a persona definidos. Responda de forma natural e realista, como um cliente brasileiro faria.
        """.strip()
    return base_prompt

def build_customer_prompt(customer_data, agent_last, base_prompt):
    return f"""
{base_prompt}

VOCÊ É: {customer_data['name']}, cliente brasileiro ligando para a Carglass.

SEUS DADOS PESSOAIS:
- Nome: {customer_data['name']}
- CPF: {customer_data['cpf']}
- Telefone principal: {customer_data['phone1']}
- Telefone secundário: {customer_data['phone2']}
- Placa do veículo: {customer_data['plate']}
- Modelo do carro: {customer_data['car']}
- Endereço: {customer_data['address']}

SEU PROBLEMA:
Você tem uma trinca no para-brisa de aproximadamente 15cm, causada por uma pedra que bateu ontem. A trinca está no meio do vidro e está incomodando a visão.

ÚLTIMA FALA DO ATENDENTE:
"{agent_last}"

INSTRUÇÕES:
1. Responda de forma natural como um cliente brasileiro real
2. Se perguntaram dados específicos, forneça as informações corretas dos seus dados acima
3. Se perguntaram sobre o problema, descreva a trinca no para-brisa
4. Seja cordial mas direto
5. Máximo 2 frases por resposta
6. Use linguagem informal mas respeitosa

RESPONDA AGORA:
"""

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[.,?!;:"(){}[\]]', "", text)
    return text

def transcribe_audio_placeholder():
    return "Transcrição automática será implementada com Whisper"

def tts_bytes(text: str, use_openai: bool = False) -> bytes:
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
        for item in items[:3]:
            if item["points"] < item["max_points"]:
                tips.append(f"Melhore item {item['idx']}: {item['label'][:50]}...")
        
        if not tips:
            tips.append("Excelente! Continue assim!")
        
        return {
            "items": items, 
            "total": total, 
            "max_total": sum(m for _,m,_ in CHECKLIST_WEIGHTS), 
            "tips": tips
        }

class CustomerBrain:
    def __init__(self, use_llm: bool, scenario: dict):
        self.use_llm = use_llm
        self.scenario = scenario
        self.system_prompt = load_system_prompt()
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
        return "Olá, bom dia! Eu sou segurado e preciso resolver um problema no para-brisa do meu carro."

    def reply(self, agent_text):
        if self.use_llm:
            try:
                prompt = build_customer_prompt(self.customer_data, agent_text, self.system_prompt)
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=100
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                st.warning(f"OpenAI falhou: {e}")
        
        agent_lower = agent_text.lower()
        
        if "placa" in agent_lower and "cpf" in agent_lower:
            return f"Claro! Minha placa é {self.customer_data['plate']} e meu CPF é {self.customer_data['cpf']}."
        
        elif ("segundo" in agent_lower or "outro" in agent_lower) and "telefone" in agent_lower:
            return f"Tenho sim! O segundo número é {self.customer_data['phone2']}."
        
        elif "nome" in agent_lower:
            return f"Meu nome é {self.customer_data['name']}."
        
        elif "cpf" in agent_lower:
            return f"Meu CPF é {self.customer_data['cpf']}."
        
        elif "placa" in agent_lower:
            return f"A placa é {self.customer_data['plate']}, um {self.customer_data['car']}."
        
        elif "telefone" in agent_lower:
            return f"Meu telefone é {self.customer_data['phone1']}."
        
        elif any(word in agent_lower for word in ["trinca", "problema", "aconteceu"]):
            return "A trinca tem uns 15cm no meio do para-brisa. Foi uma pedra que bateu ontem."
        
        elif any(word in agent_lower for word in ["cidade", "onde", "loja"]):
            return "Estou em São Paulo, zona sul. Qual a loja mais próxima?"
        
        elif "ajudar" in agent_lower:
            return "Preciso trocar esse para-brisa. É coberto pelo seguro?"
        
        else:
            return random.choice([
                "Perfeito, pode continuar.",
                "Ok, entendi.",
                "Certo, e agora?",
                "Sim, pode me ajudar com isso?"
            ])

st.title("🎤 Voice Coach - Conversa em Tempo Real")
st.caption("Treine atendimento com conversas por áudio realísticas")

def check_api_status():
    status = {}
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if openai_key else "❌ Não configurado"
    except:
        status["openai"] = "❌ Não configurado"
    return status

with st.sidebar:
    st.header("🎯 Configurações")
    
    api_status = check_api_status()
with st.sidebar:
    st.header("🎯 Configurações")
    
    api_status = check_api_status()
    st.write(f"**OpenAI:** {api_status['openai']}")
    
    use_llm = st.toggle("Cliente Inteligente (OpenAI)", 
                       value=(api_status["openai"] == "✅ Configurado"))
    use_openai_tts = st.toggle("Voz Premium (OpenAI TTS)", 
                              value=(api_status["openai"] == "✅ Configurado"))
    
    st.divider()
    st.subheader("📋 Cliente Simulado")
    st.write("**João Silva**")
    st.caption("CPF: 123.456.789-10")
    st.caption("Placa: ABC-1234 (Civic 2020)")
    st.caption("Problema: Trinca no para-brisa")

if "brain" not in st.session_state:
    scenario = {"type": "Troca de Para-brisa", "context": "Cliente com trinca no para-brisa"}
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []
    first_msg = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker": "customer", "text": first_msg, "ts": time.time()})

if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

if "last_customer_audio" not in st.session_state:
    st.session_state.last_customer_audio = None

col_chat, col_controls = st.columns([2, 1])

with col_chat:
    st.markdown("### 🎧 Conversa Telefônica")
    
    chat_container = st.container(height=400)
    with chat_container:
        for turn in st.session_state.turns:
            if turn["speaker"] == "customer":
                with st.chat_message("assistant", avatar="📞"):
                    st.write(f"**Cliente:** {turn['text']}")
            else:
                with st.chat_message("user", avatar="🧑‍💼"):
                    st.write(f"**Você:** {turn['text']}")

with col_controls:
    st.markdown("### 🎤 Controles")
    
    st.markdown("**Modo Texto (Teste)**")
    agent_input = st.text_area("Sua fala:", 
                              placeholder="Ex: Bom dia! Carglass, meu nome é Maria...",
                              height=100,
                              key="text_input")
    
    if st.button("💬 Falar", type="primary", use_container_width=True):
        if agent_input:
            st.session_state.turns.append({
                "speaker": "agent", 
                "text": agent_input, 
                "ts": time.time()
            })
            
            st.session_state.score.consume_turns(st.session_state.turns)
            
            with st.spinner("Cliente respondendo..."):
                customer_reply = st.session_state.brain.reply(agent_input)
                st.session_state.turns.append({
                    "speaker": "customer", 
                    "text": customer_reply, 
                    "ts": time.time()
                })
                
                audio_data = tts_bytes(customer_reply, use_openai=use_openai_tts)
                if audio_data:
                    st.session_state.last_customer_audio = audio_data
            
            st.session_state.text_input = ""
            st.rerun()
    
    if st.session_state.last_customer_audio:
        st.markdown("**🔊 Última resposta do cliente:**")
        st.audio(st.session_state.last_customer_audio, format="audio/wav")
    
    st.divider()
    
    st.markdown("**🎙️ Modo Áudio (Em breve)**")
    st.info("📱 Em desenvolvimento:\n- Gravação por voz\n- Transcrição automática\n- Resposta instantânea")
    
    if st.button("🔄 Nova Conversa", use_container_width=True):
        for key in ["brain", "turns", "score", "last_customer_audio"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

st.divider()
st.markdown("## 📊 Pontuação em Tempo Real")

if len([t for t in st.session_state.turns if t["speaker"]=="agent"]) == 0:
    st.info("👆 Comece a conversa para ver sua pontuação!")
else:
    res = st.session_state.score.report()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pontos", f"{res['total']}")
    with col2:
        st.metric("Total", f"/{res['max_total']}")
    with col3:
        percentage = round((res['total'] / res['max_total']) * 100, 1)
        st.metric("%", f"{percentage}")
    with col4:
        items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
        st.metric("✅", f"{items_ok}/12")
    
    if res["tips"]:
        st.markdown("**💡 Dicas principais:**")
        for tip in res["tips"]:
            st.write(f"• {tip}")

st.markdown("---")
st.markdown("🎯 **Voice Coach Real-Time** - Conversas realísticas para treinamento Carglass")AI:** {api_status['openai']}")
    
    use_llm = st.toggle("Cliente Inteligente (OpenAI)", 
                       value=(api_status["openai"] == "✅ Configurado"))
    use_openai_tts = st.toggle("Voz Premium (OpenAI TTS)", 
                              value=(api_status["openai"] == "✅ Configurado"))
    
    st.divider()
    st.subheader("📋 Cliente Simulado")
    st.write("**João Silva**")
    st.caption("CPF: 123.456.789-10")
    st.caption("Placa: ABC-1234 (Civic 2020)")
    st.caption("Problema: Trinca no para-brisa")

if "brain" not in st.session_state:
    scenario = {"type": "Troca de Para-brisa", "context": "Cliente com trinca no para-brisa"}
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []
    first_msg = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker": "customer", "text": first_msg, "ts": time.time()})

if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

if "last_customer_audio" not in st.session_state:
    st.session_state.last_customer_audio = None

col_chat, col_controls = st.columns([2, 1])

with col_chat:
    st.markdown("### 🎧 Conversa Telefônica")
    
    chat_container = st.container(height=400)
    with chat_container:
        for turn in st.session_state.turns:
            if turn["speaker"] == "customer":
                with st.chat_message("assistant", avatar="📞"):
                    st.write(f"**Cliente:** {turn['text']}")
            else:
                with st.chat_message("user", avatar="🧑‍💼"):
                    st.write(f"**Você:** {turn['text']}")

with col_controls:
    st.markdown("### 🎤 Controles")
    
    st.markdown("**Modo Texto (Teste)**")
    agent_input = st.text_area("Sua fala:", 
                              placeholder="Ex: Bom dia! Carglass, meu nome é Maria...",
                              height=100,
                              key="text_input")
    
    if st.button("💬 Falar", type="primary", use_container_width=True):
        if agent_input:
            st.session_state.turns.append({
                "speaker": "agent", 
                "text": agent_input, 
                "ts": time.time()
            })
            
            st.session_state.score.consume_turns(st.session_state.turns)
            
            with st.spinner("Cliente respondendo..."):
                customer_reply = st.session_state.brain.reply(agent_input)
                st.session_state.turns.append({
                    "speaker": "customer", 
                    "text": customer_reply, 
                    "ts": time.time()
                })
                
                audio_data = tts_bytes(customer_reply, use_openai=use_openai_tts)
                if audio_data:
                    st.session_state.last_customer_audio = audio_data
            
            st.session_state.text_input = ""
            st.rerun()
    
    if st.session_state.last_customer_audio:
        st.markdown("**🔊 Última resposta do cliente:**")
        st.audio(st.session_state.last_customer_audio, format="audio/wav")
    
    st.divider()
    
    st.markdown("**🎙️ Modo Áudio (Em breve)**")
    st.info("📱 Em desenvolvimento:\n- Gravação por voz\n- Transcrição automática\n- Resposta instantânea")
    
    if st.button("🔄 Nova Conversa", use_container_width=True):
        for key in ["brain", "turns", "score", "last_customer_audio"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

st.divider()
st.markdown("## 📊 Pontuação em Tempo Real")

if len([t for t in st.session_state.turns if t["speaker"]=="agent"]) == 0:
    st.info("👆 Comece a conversa para ver sua pontuação!")
else:
    res = st.session_state.score.report()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pontos", f"{res['total']}")
    with col2:
        st.metric("Total", f"/{res['max_total']}")
    with col3:
        percentage = round((res['total'] / res['max_total']) * 100, 1)
        st.metric("%", f"{percentage}")
    with col4:
        items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
        st.metric("✅", f"{items_ok}/12")
    
    if res["tips"]:
        st.markdown("**💡 Dicas principais:**")
        for tip in res["tips"]:
            st.write(f"• {tip}")

st.markdown("---")
st.markdown("🎯 **Voice Coach Real-Time** - Conversas realísticas para treinamento Carglass")AI:** {api_status['openai']}")
    
    use_llm = st.toggle("Cliente Inteligente (OpenAI)", 
                       value=(api_status["openai"] == "✅ Configurado"))
    use_openai_tts = st.toggle("Voz Premium (OpenAI TTS)", 
                              value=(api_status["openai"] == "✅ Configurado"))
    
    st.divider()
    st.subheader("📋 Cliente Simulado")
    st.write("**João Silva**")
    st.caption("CPF: 123.456.789-10")
    st.caption("Placa: ABC-1234 (Civic 2020)")
    st.caption("Problema: Trinca no para-brisa")

# Inicializar sistema
if "brain" not in st.session_state:
    scenario = {"type": "Troca de Para-brisa", "context": "Cliente com trinca no para-brisa"}
    st.session_state.brain = CustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []
    # Primeira fala do cliente automaticamente
    first_msg = st.session_state.brain.first_utterance()
    st.session_state.turns.append({"speaker": "customer", "text": first_msg, "ts": time.time()})

if "score" not in st.session_state:
    st.session_state.score = ScoreEngine()

if "last_customer_audio" not in st.session_state:
    st.session_state.last_customer_audio = None

# Layout principal
col_chat, col_controls = st.columns([2, 1])

with col_chat:
    st.markdown("### 🎧 Conversa Telefônica")
    
    # Exibir conversa
    chat_container = st.container(height=400)
    with chat_container:
        for turn in st.session_state.turns:
            if turn["speaker"] == "customer":
                with st.chat_message("assistant", avatar="📞"):
                    st.write(f"**Cliente:** {turn['text']}")
            else:
                with st.chat_message("user", avatar="🧑‍💼"):
                    st.write(f"**Você:** {turn['text']}")

with col_controls:
    st.markdown("### 🎤 Controles")
    
    # Modo texto para testes rápidos
    st.markdown("**Modo Texto (Teste)**")
    agent_input = st.text_area("Sua fala:", 
                              placeholder="Ex: Bom dia! Carglass, meu nome é Maria...",
                              height=100,
                              key="text_input")
    
    if st.button("💬 Falar", type="primary", use_container_width=True):
        if agent_input:
            # Adiciona fala do agente
            st.session_state.turns.append({
                "speaker": "agent", 
                "text": agent_input, 
                "ts": time.time()
            })
            
            # Atualiza score
            st.session_state.score.consume_turns(st.session_state.turns)
            
            # Resposta do cliente
            with st.spinner("Cliente respondendo..."):
                customer_reply = st.session_state.brain.reply(agent_input)
                st.session_state.turns.append({
                    "speaker": "customer", 
                    "text": customer_reply, 
                    "ts": time.time()
                })
                
                # Gera áudio da resposta
                audio_data = tts_bytes(customer_reply, use_openai=use_openai_tts)
                if audio_data:
                    st.session_state.last_customer_audio = audio_data
            
            # Limpa input e atualiza
            st.session_state.text_input = ""
            st.rerun()
    
    # Player de áudio da última resposta
    if st.session_state.last_customer_audio:
        st.markdown("**🔊 Última resposta do cliente:**")
        st.audio(st.session_state.last_customer_audio, format="audio/wav")
    
    st.divider()
    
    # Modo áudio (placeholder para desenvolvimento futuro)
    st.markdown("**🎙️ Modo Áudio (Em breve)**")
    st.info("📱 Em desenvolvimento:\n- Gravação por voz\n- Transcrição automática\n- Resposta instantânea")
    
    if st.button("🔄 Nova Conversa", use_container_width=True):
        for key in ["brain", "turns", "score", "last_customer_audio"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Score em tempo real
st.divider()
st.markdown("## 📊 Pontuação em Tempo Real")

if len([t for t in st.session_state.turns if t["speaker"]=="agent"]) == 0:
    st.info("👆 Comece a conversa para ver sua pontuação!")
else:
    res = st.session_state.score.report()
    
    # Métricas compactas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pontos", f"{res['total']}")
    with col2:
        st.metric("Total", f"/{res['max_total']}")
    with col3:
        percentage = round((res['total'] / res['max_total']) * 100, 1)
        st.metric("%", f"{percentage}")
    with col4:
        items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
        st.metric("✅", f"{items_ok}/12")
    
    # Dicas principais
    if res["tips"]:
        st.markdown("**💡 Dicas principais:**")
        for tip in res["tips"]:
            st.write(f"• {tip}")

# Footer
st.markdown("---")
st.markdown("🎯 **Voice Coach Real-Time** - Conversas realísticas para treinamento Carglass")
