import os
import io
import time
import json
import random
import re
import pandas as pd
import streamlit as st
import pickle
import numpy as np
from datetime import datetime
from gtts import gTTS

# Novas importações para embeddings
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    st.warning("⚠️ Bibliotecas de embeddings não instaladas. Execute: pip install sentence-transformers scikit-learn")

st.set_page_config(
    page_title="Voice Coach - Carglass", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS permanece o mesmo...
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        color: white;
        padding: 2rem 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        position: relative;
    }
    
    .timer-container {
        position: absolute;
        top: 1rem;
        right: 2rem;
        background: rgba(255,255,255,0.1);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 1.2rem;
        font-weight: bold;
    }
    
    .waiting-state {
        text-align: center;
        background: #f0f9ff;
        border: 2px solid #3b82f6;
        border-radius: 12px;
        padding: 3rem;
        margin: 2rem 0;
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
    
    .status-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .embedding-badge {
        display: inline-block;
        background: #10b981;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }

    .regex-badge {
        display: inline-block;
        background: #6b7280;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

class EmbeddingScorer:
    """Sistema de avaliação baseado em embeddings."""
    
    def __init__(self, gabarito_path: str = "gabarito_embeddings (1).pkl"):
        self.model = None
        self.gabarito = None
        self.similarity_threshold = 0.65
        
        # Carrega modelo de embeddings
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
                st.success("🧠 Modelo de embeddings carregado!")
            except Exception as e:
                st.error(f"❌ Erro ao carregar modelo: {e}")
                self.model = None
        
        # Carrega gabarito
        self._load_gabarito(gabarito_path)
    
    def _load_gabarito(self, gabarito_path):
        """Carrega o gabarito de embeddings."""
        if os.path.exists(gabarito_path):
            try:
                with open(gabarito_path, 'rb') as f:
                    self.gabarito = pickle.load(f)
                st.success(f"📚 Gabarito carregado: {len(self.gabarito)} critérios")
                
                # Debug: mostra estrutura do gabarito
                if st.sidebar.button("🔍 Debug Gabarito"):
                    st.sidebar.write("Estrutura do gabarito:")
                    for key in list(self.gabarito.keys())[:3]:  # Mostra primeiros 3
                        st.sidebar.write(f"Item {key}: {type(self.gabarito[key])}")
                
            except Exception as e:
                st.error(f"❌ Erro ao carregar gabarito: {e}")
                self.gabarito = None
        else:
            st.warning(f"⚠️ Gabarito não encontrado: {gabarito_path}")
    
    def evaluate_response(self, item_id: int, agent_text: str):
        """Avalia resposta usando similaridade semântica."""
        if not self.model or not self.gabarito or item_id not in self.gabarito:
            return 0.0, "Modelo indisponível", []
        
        if not agent_text.strip():
            return 0.0, "Resposta vazia", []
        
        try:
            # Gera embedding da resposta do agente
            agent_embedding = self.model.encode([agent_text])
            
            # Obtém embeddings do gabarito
            gabarito_item = self.gabarito[item_id]
            
            # Estrutura do gabarito pode variar, vamos adaptar
            if isinstance(gabarito_item, dict) and 'embeddings' in gabarito_item:
                gabarito_embeddings = gabarito_item['embeddings']
                exemplos = gabarito_item.get('respostas', [])
            elif isinstance(gabarito_item, np.ndarray):
                gabarito_embeddings = gabarito_item
                exemplos = [f"Exemplo {i+1}" for i in range(len(gabarito_item))]
            else:
                return 0.0, "Formato de gabarito não reconhecido", []
            
            # Calcula similaridades
            similarities = cosine_similarity(agent_embedding, gabarito_embeddings)[0]
            max_similarity = np.max(similarities)
            best_match_idx = np.argmax(similarities)
            
            # Gera evidências
            evidence = []
            if max_similarity >= self.similarity_threshold:
                evidence.append(f"✅ Alta similaridade: {max_similarity:.3f}")
                if len(exemplos) > best_match_idx:
                    evidence.append(f"Próximo de: {str(exemplos[best_match_idx])[:50]}...")
            elif max_similarity >= 0.4:
                evidence.append(f"⚠️ Similaridade moderada: {max_similarity:.3f}")
            else:
                evidence.append(f"❌ Baixa similaridade: {max_similarity:.3f}")
            
            return max_similarity, f"Melhor match (índice {best_match_idx})", evidence
            
        except Exception as e:
            st.error(f"Erro na avaliação semântica item {item_id}: {e}")
            return 0.0, "Erro na avaliação", [str(e)]

class HybridScoreEngine:
    """Engine híbrida: embeddings + regras tradicionais."""
    
    def __init__(self):
        self.turns = []
        self.embedding_scorer = EmbeddingScorer()
        self.use_embeddings = (self.embedding_scorer.model is not None and 
                              self.embedding_scorer.gabarito is not None)
        
        self.checklist_weights = [
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
        
        # Itens que se beneficiam de análise semântica
        self.semantic_items = [1, 3, 4, 5, 10, 11, 12]
    
    def consume_turns(self, turns):
        self.turns = turns
    
    def _agent_text(self):
        return " ".join([t["text"] for t in self.turns if t["speaker"]=="agent"])
    
    def _score_item_embedding(self, idx: int, agent_text: str, max_points: int):
        """Avalia item usando embeddings."""
        similarity, best_match, evidence = self.embedding_scorer.evaluate_response(idx, agent_text)
        
        # Converte similaridade em pontos
        if similarity >= 0.8:
            points = max_points
        elif similarity >= 0.7:
            points = int(max_points * 0.9)
        elif similarity >= 0.6:
            points = int(max_points * 0.7)
        elif similarity >= 0.4:
            points = int(max_points * 0.4)
        else:
            points = 0
        
        evidence.append(f"Pontos: {points}/{max_points}")
        return points, evidence, "Embedding"
    
    def _score_item_regex(self, idx: int, agent_text: str, max_points: int):
        """Avalia item usando regras tradicionais (mantém lógica original)."""
        evidence = []
        points = 0
        text = agent_text.lower()
        
        if idx == 2:  # Coleta de dados
            dados_patterns = [
                r"nome", r"cpf", r"telefone", r"segundo telefone|outro telefone", 
                r"placa", r"endereço"
            ]
            dados_ok = sum(1 for pattern in dados_patterns if re.search(pattern, text, re.IGNORECASE))
            
            if dados_ok >= 5:
                points = max_points
                evidence.append(f"Solicitou {dados_ok}/6 dados")
            else:
                points = max_points * dados_ok // 6
                evidence.append(f"Apenas {dados_ok}/6 dados")
        
        elif idx == 6:  # Conhecimento técnico
            tech_terms = ['para-brisa', 'vidro', 'franquia', 'seguro', 'vistoria']
            tech_count = sum(1 for term in tech_terms if term in text)
            
            if tech_count >= 2:
                points = max_points
                evidence.append(f"Conhecimento técnico: {tech_count} termos")
            else:
                points = max_points * tech_count // 3
                evidence.append(f"Conhecimento limitado: {tech_count} termos")
        
        elif idx == 7:  # Informações do dano
            info_patterns = ['quando', 'como', 'tamanho', 'data', 'motivo', 'led', 'xenon']
            info_count = sum(1 for pattern in info_patterns if pattern in text)
            
            if info_count >= 4:
                points = max_points
                evidence.append(f"Informações completas: {info_count} aspectos")
            else:
                points = max_points * info_count // 5
                evidence.append(f"Informações parciais: {info_count} aspectos")
        
        elif idx == 8:  # Cidade e loja
            cidade = bool(re.search(r"cidade|onde", text))
            loja = bool(re.search(r"loja|unidade|próxima", text))
            
            if cidade and loja:
                points = max_points
                evidence.append("Cidade e loja confirmadas")
            else:
                points = max_points // 2 if (cidade or loja) else 0
                evidence.append(f"Faltou: {[] if cidade else ['cidade']} {[] if loja else ['loja']}")
        
        elif idx == 9:  # Comunicação
            has_slang = bool(re.search(r"\b(mano|cara|né|tipo)\b", text))
            informed_absence = bool(re.search(r"vou verificar|momento|retorno", text))
            
            if not has_slang and informed_absence:
                points = max_points
                evidence.append("Comunicação profissional")
            elif not has_slang:
                points = max_points * 2 // 3
                evidence.append("Sem gírias, mas faltou informar ausências")
            else:
                points = 0
                evidence.append("Uso de gírias detectado")
        
        return points, evidence, "Regex"
    
    def _score_item(self, idx: int, agent_text: str):
        """Decide qual método usar para avaliar cada item."""
        max_points = next(m for i, m, _ in self.checklist_weights if i == idx)
        
        # Para itens semânticos, tenta usar embeddings
        if self.use_embeddings and idx in self.semantic_items:
            return self._score_item_embedding(idx, agent_text, max_points)
        else:
            # Para outros itens ou se embeddings não disponível, usa regex
            return self._score_item_regex(idx, agent_text, max_points)
    
    def report(self):
        """Gera relatório de avaliação híbrido."""
        agent_text = self._agent_text()
        items = []
        total = 0
        
        for idx, max_points, label in self.checklist_weights:
            points, evidence, method = self._score_item(idx, agent_text)
            total += points
            
            items.append({
                "idx": idx,
                "label": label,
                "points": points,
                "max_points": max_points,
                "evidence": evidence,
                "method": method
            })
        
        max_total = sum(m for _, m, _ in self.checklist_weights)
        tips = self._generate_tips(items)
        
        return {
            "items": items,
            "total": total,
            "max_total": max_total,
            "tips": tips,
            "embedding_enabled": self.use_embeddings
        }
    
    def _generate_tips(self, items):
        """Gera dicas personalizadas."""
        tips = []
        failed_items = sorted(
            [item for item in items if item["points"] < item["max_points"]], 
            key=lambda x: x["max_points"], reverse=True
        )
        
        for item in failed_items[:3]:
            tips.append(f"🎯 Item {item['idx']}: {item['label'][:60]}... (Método: {item['method']})")
        
        if not tips:
            tips.append("🎉 Excelente! Todos os critérios atendidos!")
        
        return tips

# Funções auxiliares permanecem as mesmas...
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[.,?!;:"(){}[\]]', "", text)
    return text

def format_timer(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

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

def generate_pdf_report(session_data, score_data):
    report_content = f"""
RELATÓRIO DE TREINAMENTO - VOICE COACH CARGLASS

Data/Hora: {datetime.now().strftime('%d/%m/%Y - %H:%M')}
Duração Total: {format_timer(session_data.get('duration', 0))}
Sistema: {'Híbrido (Embeddings + Regex)' if score_data.get('embedding_enabled') else 'Tradicional (Regex)'}

=== RESUMO DA PERFORMANCE ===
Pontuação Final: {score_data['total']}/{score_data['max_total']} pontos
Percentual de Acerto: {round((score_data['total'] / score_data['max_total']) * 100, 1)}%
Itens Completos: {sum(1 for item in score_data['items'] if item['points'] == item['max_points'])}/12

=== CHECKLIST DETALHADO ===
"""
    
    for i, item in enumerate(score_data['items'], 1):
        status = "✓" if item['points'] == item['max_points'] else "⚠" if item['points'] > 0 else "✗"
        method = item.get('method', 'N/A')
        report_content += f"\n{i:2d}. [{status}] {item['label']} ({method})"
        report_content += f"\n    Pontuação: {item['points']}/{item['max_points']} pts"
        if item['evidence']:
            report_content += f"\n    Evidências: {'; '.join(item['evidence'])}"
        report_content += "\n"
    
    report_content += "\n=== RECOMENDAÇÕES ===\n"
    for i, tip in enumerate(score_data['tips'], 1):
        report_content += f"{i}. {tip}\n"
    
    report_content += f"\n=== TRANSCRIÇÃO ===\n"
    for turn in session_data.get('turns', []):
        speaker = "AGENTE" if turn['speaker'] == 'agent' else "CLIENTE"
        report_content += f"\n{speaker}: {turn['text']}\n"
    
    return report_content.encode('utf-8')

# Cliente inteligente permanece o mesmo...
class IntelligentCustomerBrain:
    def __init__(self, use_llm: bool, scenario: dict):
        self.use_llm = use_llm
        self.scenario = scenario
        self.customer_data = {
            "name": "João Silva",
            "cpf": "123.456.789-10",
            "phone1": "11-99999-8888",
            "phone2": "11-97777-6666",
            "plate": "ABC-1234",
            "car": "Honda Civic 2020",
            "address": "Rua das Flores, 123 - Vila Olímpia - São Paulo/SP - CEP 04038-001",
            "insurance": "Porto Seguro"
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
        return "Alô, bom dia! Estou ligando porque tenho um problema no para-brisa do meu carro e preciso resolver urgente."

    def reply(self, turns):
        if not turns:
            return self.first_utterance()
        
        agent_last = ""
        for turn in reversed(turns):
            if turn["speaker"] == "agent":
                agent_last = turn["text"]
                break
        
        conversation_stage = len([t for t in turns if t["speaker"] == "agent"])
        
        if self.use_llm:
            try:
                context = self._build_conversation_context(turns, conversation_stage)
                
                prompt = f"""
Você é {self.customer_data['name']}, um cliente brasileiro ligando para a Carglass.

SEUS DADOS: Nome: {self.customer_data['name']}, CPF: {self.customer_data['cpf']}, 
Telefones: {self.customer_data['phone1']} e {self.customer_data['phone2']}, 
Placa: {self.customer_data['plate']}, Veículo: {self.customer_data['car']}, 
Endereço: {self.customer_data['address']}, Seguro: {self.customer_data['insurance']}

PROBLEMA: Trinca no para-brisa de 15cm por pedra ontem na Marginal Tietê.

CONTEXTO: {context}
ÚLTIMA FALA DO ATENDENTE: "{agent_last}"

Responda como cliente brasileiro autêntico, máximo 2 frases, colaborativo mas com urgência.
"""
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=120
                )
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                st.warning(f"OpenAI indisponível: {e}")
        
        return self._fallback_response(agent_last.lower(), conversation_stage)
    
    def _build_conversation_context(self, turns, stage):
        if stage <= 2:
            return "Início - explicou problema"
        elif stage <= 5:
            return "Coleta de dados"
        elif stage <= 8:
            return "Detalhes do dano"
        else:
            return "Finalização"
    
    def _fallback_response(self, agent_last, stage):
        # Respostas padrão como no código original...
        if "nome" in agent_last:
            return f"Meu nome é {self.customer_data['name']}."
        elif "cpf" in agent_last:
            return f"Meu CPF é {self.customer_data['cpf']}."
        elif "telefone" in agent_last:
            if "segundo" in agent_last:
                return f"O segundo é {self.customer_data['phone2']}."
            return f"Meu telefone é {self.customer_data['phone1']}."
        else:
            return "Certo. E agora, qual o próximo passo?"

def check_api_status():
    status = {}
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if openai_key else "❌ Não configurado"
    except:
        status["openai"] = "❌ Não configurado"
    
    status["embeddings"] = "✅ Disponível" if EMBEDDINGS_AVAILABLE else "❌ Não instalado"
    return status

# Interface principal
if "session_state" not in st.session_state:
    st.session_state.session_state = "waiting"
    st.session_state.start_time = None
    st.session_state.session_duration = 0

timer_placeholder = st.empty()

if st.session_state.session_state == "active" and st.session_state.start_time:
    elapsed = time.time() - st.session_state.start_time
    st.session_state.session_duration = elapsed
    
    if elapsed >= 1200:
        st.session_state.session_state = "timeout"
        st.error("Tempo limite de 20 minutos atingido!")
    
    timer_color = "#ff4444" if elapsed > 1080 else "#ffa500" if elapsed > 900 else "#ffffff"
    timer_placeholder.markdown(f"""
    <div style="text-align: right; margin-bottom: 1rem;">
        <span style="background: {timer_color}; color: {'white' if elapsed <= 900 else 'black'}; 
              padding: 0.5rem 1rem; border-radius: 20px; font-weight: bold;">
            ⏱️ {format_timer(elapsed)} / 20:00
        </span>
    </div>
    """, unsafe_allow_html=True)

header_text = "Voice Coach - Sistema Híbrido com Embeddings"
if st.session_state.session_state == "active":
    timer_display = f'<div class="timer-container">⏱️ {format_timer(st.session_state.session_duration)} / 20:00</div>'
else:
    timer_display = ""

st.markdown(f'<div class="main-header"><h1>{header_text}</h1><p>Avaliação avançada com análise semântica + regras tradicionais</p>{timer_display}</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações")
    
    api_status = check_api_status()
    st.markdown(f"""
    <div class="status-card">
        <strong>OpenAI:</strong> {api_status['openai']}<br>
        <strong>Embeddings:</strong> {api_status['embeddings']}<br>
        <small>Sistema híbrido para máxima precisão</small>
    </div>
    """, unsafe_allow_html=True)
    
    use_llm = st.toggle("Cliente Inteligente", value=(api_status["openai"] == "✅ Configurado"))
    use_openai_tts = st.toggle("Voz Premium", value=(api_status["openai"] == "✅ Configurado"))
    
    st.divider()
    st.subheader("📋 Cliente Simulado")
    st.markdown("""
    **João Silva**  
    📱 11-99999-8888 / 11-97777-6666  
    🚗 ABC-1234 (Honda Civic 2020)  
    📍 Vila Olímpia - São Paulo/SP  
    🛡️ Porto Seguro  
    🔧 Trinca no para-brisa (15cm)
    """)

scenario = {"type": "Troca de Para-brisa", "context": "Cliente com urgência por trinca no para-brisa"}

if "brain" not in st.session_state:
    st.session_state.brain = IntelligentCustomerBrain(use_llm=use_llm, scenario=scenario)

if "turns" not in st.session_state:
    st.session_state.turns = []

if "score" not in st.session_state:
    st.session_state.score = HybridScoreEngine()

# Interface principal (resto do código permanece similar, mas com melhorias na exibição)
if st.session_state.session_state == "waiting":
    embedding_status = "🧠 Ativo" if EMBEDDINGS_AVAILABLE else "⚠️ Limitado"
    st.markdown(f"""
    <div class="waiting-state">
        <h2>🎯 Sistema de Treinamento Híbrido</h2>
        <p>Avaliação inteligente: <strong>{embedding_status}</strong></p>
        <p>✅ Análise semântica para critérios subjetivos</p>
        <p>✅ Regras precisas para critérios objetivos</p>
        <p><strong>⏱️ Duração:</strong> Máximo 20 minutos</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        if st.button("🚀 Iniciar Treinamento", type="primary", use_container_width=True):
            st.session_state.session_state = "active"
            st.session_state.start_time = time.time()
            st.session_state.turns = []
            st.session_state.score = HybridScoreEngine()
            first_msg = st.session_state.brain.first_utterance()
            st.session_state.turns.append({"speaker": "customer", "text": first_msg, "ts": time.time()})
            st.rerun()

elif st.session_state.session_state in ["active", "timeout"]:
    
    if len(st.session_state.turns) == 0:
        first_msg = st.session_state.brain.first_utterance()
        st.session_state.turns.append({"speaker": "customer", "text": first_msg, "ts": time.time()})

    col_main, col_input = st.columns([2, 1])

    with col_main:
        st.subheader("📞 Simulação de Atendimento")
        
        conversation_container = st.container(height=500)
        with conversation_container:
            for turn in st.session_state.turns:
                if turn["speaker"] == "customer":
                    with st.chat_message("assistant", avatar="📞"):
                        st.write(f"**Cliente:** {turn['text']}")
                else:
                    with st.chat_message("user", avatar="👤"):
                        st.write(f"**Você:** {turn['text']}")

    with col_input:
        st.subheader("🎤 Sua Resposta")
        
        if st.session_state.session_state != "timeout":
            agent_text = st.text_area(
                "Digite sua resposta:",
                placeholder="Bom dia! Carglass, meu nome é Maria. Como posso ajudá-lo?",
                height=120,
                key="agent_input"
            )
            
            col_send, col_finish = st.columns(2)
            
            with col_send:
                if st.button("💬 Enviar", type="primary", disabled=not agent_text, use_container_width=True):
                    st.session_state.turns.append({"speaker": "agent", "text": agent_text, "ts": time.time()})
                    st.session_state.score.consume_turns(st.session_state.turns)
                    
                    reply = st.session_state.brain.reply(st.session_state.turns)
                    st.session_state.turns.append({"speaker": "customer", "text": reply, "ts": time.time()})
                    
                    with st.spinner("Cliente respondendo..."):
                        audio_reply = tts_bytes(reply, use_openai=use_openai_tts)
                        if audio_reply:
                            st.audio(audio_reply, format="audio/wav")
                    
                    st.rerun()
            
            with col_finish:
                if st.button("🏁 Finalizar", use_container_width=True):
                    st.session_state.session_state = "finished"
                    st.rerun()
            
            st.divider()
            
            if st.button("🔄 Nova Sessão", use_container_width=True):
                keys_to_clear = ["brain", "turns", "score", "session_state", "start_time", "session_duration"]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        else:
            st.error("⏰ Tempo limite atingido")
            if st.button("🔄 Nova Sessão", use_container_width=True):
                keys_to_clear = ["brain", "turns", "score", "session_state", "start_time", "session_duration"]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    st.divider()

    # Avaliação em tempo real com indicadores de método
    if len([t for t in st.session_state.turns if t["speaker"] == "agent"]) > 0:
        res = st.session_state.score.report()
        
        st.markdown("## 📊 Avaliação Híbrida em Tempo Real")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Pontuação", f"{res['total']}")
        with col2:
            st.metric("Máximo", f"{res['max_total']}")
        with col3:
            percentage = round((res['total'] / res['max_total']) * 100, 1)
            color = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
            st.metric("Performance", f"{percentage}% {color}")
        with col4:
            items_ok = sum(1 for item in res["items"] if item["points"] == item["max_points"])
            st.metric("Completos", f"{items_ok}/12")
        with col5:
            embedding_items = sum(1 for item in res["items"] if item.get("method") == "Embedding")
            method_indicator = "🧠" if res.get("embedding_enabled") else "📝"
            st.metric("Sistema", f"{method_indicator} Híbrido")
        
        # Mostrar breakdown por método
        if res.get("embedding_enabled"):
            embedding_count = sum(1 for item in res["items"] if item.get("method") == "Embedding")
            regex_count = sum(1 for item in res["items"] if item.get("method") == "Regex")
            st.info(f"🧠 Análise Semântica: {embedding_count} itens | 📝 Regras Tradicionais: {regex_count} itens")
        
        with st.expander("📋 Checklist Detalhado com Métodos de Avaliação", expanded=False):
            for item in res["items"]:
                status = "✅" if item["points"] == item["max_points"] else "⚠️" if item["points"] > 0 else "❌"
                method = item.get("method", "N/A")
                method_badge = "embedding-badge" if method == "Embedding" else "regex-badge"
                
                st.markdown(f"""
                <div class="checklist-item">
                    <strong>{status} Item {item['idx']}</strong> 
                    <span class="{method_badge}">{method}</span>
                    <span style="float: right;">({item['points']}/{item['max_points']} pts)</span>
                    <br>
                    <small>{item['label']}</small><br>
                    {f"<em>Evidências: {'; '.join(item['evidence'])}</em>" if item['evidence'] else ""}
                </div>
                """, unsafe_allow_html=True)
        
        if res["tips"]:
            st.subheader("💡 Recomendações Inteligentes")
            for tip in res["tips"]:
                if "Embedding" in tip:
                    st.success(tip)
                elif "Regex" in tip:
                    st.info(tip)
                else:
                    st.warning(tip)
    else:
        st.info("👆 Digite sua primeira resposta para iniciar a avaliação híbrida!")

elif st.session_state.session_state == "finished":
    st.success("🎉 Treinamento Finalizado!")
    
    res = st.session_state.score.report()
    percentage = round((res['total'] / res['max_total']) * 100, 1)
    
    st.markdown("## 📋 Relatório Final - Sistema Híbrido")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Pontuação Final", f"{res['total']}/{res['max_total']}")
    with col2:
        color = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
        st.metric("Performance", f"{percentage}% {color}")
    with col3:
        st.metric("Duração", format_timer(st.session_state.session_duration))
    with col4:
        system_type = "Híbrido" if res.get("embedding_enabled") else "Tradicional"
        st.metric("Sistema", f"🧠 {system_type}")
    
    # Análise detalhada por método
    if res.get("embedding_enabled"):
        embedding_items = [item for item in res["items"] if item.get("method") == "Embedding"]
        regex_items = [item for item in res["items"] if item.get("method") == "Regex"]
        
        col_emb, col_reg = st.columns(2)
        
        with col_emb:
            st.subheader("🧠 Análise Semântica")
            embedding_score = sum(item["points"] for item in embedding_items)
            embedding_max = sum(item["max_points"] for item in embedding_items)
            if embedding_max > 0:
                emb_percentage = round((embedding_score / embedding_max) * 100, 1)
                st.metric("Semântica", f"{emb_percentage}%")
                
                for item in embedding_items[:3]:  # Top 3
                    status = "✅" if item["points"] == item["max_points"] else "❌"
                    st.write(f"{status} Item {item['idx']}: {item['points']}/{item['max_points']} pts")
        
        with col_reg:
            st.subheader("📝 Regras Tradicionais")
            regex_score = sum(item["points"] for item in regex_items)
            regex_max = sum(item["max_points"] for item in regex_items)
            if regex_max > 0:
                reg_percentage = round((regex_score / regex_max) * 100, 1)
                st.metric("Regras", f"{reg_percentage}%")
                
                for item in regex_items[:3]:  # Top 3
                    status = "✅" if item["points"] == item["max_points"] else "❌"
                    st.write(f"{status} Item {item['idx']}: {item['points']}/{item['max_points']} pts")
    
    # Relatório detalhado para download
    session_data = {
        'turns': st.session_state.turns,
        'duration': st.session_state.session_duration
    }
    
    pdf_data = generate_pdf_report(session_data, res)
    
    col_pdf, col_new = st.columns(2)
    
    with col_pdf:
        st.download_button(
            label="📄 Relatório Híbrido Completo",
            data=pdf_data,
            file_name=f"relatorio_hibrido_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
            type="primary"
        )
    
    with col_new:
        if st.button("🔄 Novo Treinamento", use_container_width=True):
            keys_to_clear = ["brain", "turns", "score", "session_state", "start_time", "session_duration"]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # Insights específicos do sistema híbrido
    if res.get("embedding_enabled"):
        st.subheader("🔍 Insights do Sistema Híbrido")
        
        # Análise de critérios que mais se beneficiaram dos embeddings
        semantic_performance = []
        for item in res["items"]:
            if item.get("method") == "Embedding":
                perf = item["points"] / item["max_points"]
                semantic_performance.append((item["idx"], item["label"][:40], perf))
        
        if semantic_performance:
            best_semantic = max(semantic_performance, key=lambda x: x[2])
            worst_semantic = min(semantic_performance, key=lambda x: x[2])
            
            col_best, col_worst = st.columns(2)
            with col_best:
                st.success(f"🎯 Melhor critério semântico: Item {best_semantic[0]} ({best_semantic[2]*100:.1f}%)")
            with col_worst:
                if worst_semantic[2] < 0.7:
                    st.warning(f"⚠️ Precisa melhorar: Item {worst_semantic[0]} ({worst_semantic[2]*100:.1f}%)")

st.markdown("---")
st.markdown("**🧠 Voice Coach Híbrido** - Embeddings + Regras | Máxima precisão na avaliação Carglass")
