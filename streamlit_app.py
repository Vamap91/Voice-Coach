import os
import io
import time
import json
import random
import streamlit as st
from datetime import datetime
from gtts import gTTS
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Configuração da página
st.set_page_config(
    page_title="Voice Coach Pro - Carglass", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS profissional
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #004a8f, #0066cc);
        color: white;
        padding: 2rem 1rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .conversation-box {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
    }
    
    .customer-msg {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .agent-msg {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .score-card {
        background: white;
        border: 2px solid #0066cc;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .checklist-item {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    
    .timer-display {
        font-size: 1.5rem;
        font-weight: bold;
        color: #dc3545;
        text-align: center;
        padding: 0.5rem;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== MODELOS DE DADOS ====================

@dataclass
class CustomerProfile:
    """Perfil do cliente simulado"""
    name: str = "João Silva"
    cpf: str = "123.456.789-10"
    phone1: str = "11-99999-8888"
    phone2: str = "11-97777-6666"
    plate: str = "ABC-1234"
    car_model: str = "Honda Civic 2020"
    address: str = "Rua das Flores, 123, Vila Olímpia - São Paulo/SP"
    insurance: str = "Porto Seguro"
    problem: str = "Trinca no para-brisa de aproximadamente 15cm"
    urgency: str = "alta"
    
    def get_random_variation(self) -> 'CustomerProfile':
        """Gera uma variação aleatória do perfil"""
        variations = [
            CustomerProfile(
                name="Maria Santos",
                cpf="987.654.321-00",
                phone1="21-98888-7777",
                phone2="21-96666-5555",
                plate="XYZ-9876",
                car_model="Toyota Corolla 2021",
                address="Av. Atlântica, 456, Copacabana - Rio de Janeiro/RJ",
                insurance="Bradesco",
                problem="Pedra atingiu o vidro na rodovia",
                urgency="média"
            ),
            CustomerProfile(
                name="Carlos Oliveira",
                cpf="555.444.333-22",
                phone1="31-97777-6666",
                phone2="31-95555-4444",
                plate="MNO-5432",
                car_model="Volkswagen Golf 2019",
                address="Rua da Bahia, 789, Centro - Belo Horizonte/MG",
                insurance="Allianz",
                problem="Rachadura no retrovisor lateral",
                urgency="baixa"
            )
        ]
        return random.choice(variations) if random.random() > 0.7 else self

@dataclass
class ConversationContext:
    """Contexto da conversa para manter estado"""
    data_collected: Dict[str, bool] = field(default_factory=lambda: {
        'greeting': False,
        'name': False,
        'cpf': False,
        'phone1': False,
        'phone2': False,
        'plate': False,
        'address': False,
        'problem': False,
        'lgpd': False,
        'confirmation': False,
        'city': False,
        'closing': False
    })
    
    questions_asked: List[str] = field(default_factory=list)
    agent_mistakes: List[str] = field(default_factory=list)
    empathy_shown: int = 0
    efficiency_score: int = 100
    
    def mark_collected(self, item: str):
        """Marca um item como coletado"""
        if item in self.data_collected:
            self.data_collected[item] = True
    
    def add_mistake(self, mistake: str):
        """Adiciona um erro detectado"""
        self.agent_mistakes.append(mistake)
        self.efficiency_score = max(0, self.efficiency_score - 5)
    
    def check_repetition(self, question: str) -> bool:
        """Verifica se está repetindo perguntas"""
        similar = any(q for q in self.questions_asked if question.lower() in q.lower())
        self.questions_asked.append(question)
        return similar

# ==================== MOTOR DE AVALIAÇÃO ====================

class EvaluationEngine:
    """Motor de avaliação baseado no checklist Carglass"""
    
    CHECKLIST = [
        {"id": 1, "peso": 10, "nome": "Saudação e identificação", 
         "keywords": ["bom dia", "boa tarde", "boa noite", "carglass", "meu nome"]},
        
        {"id": 2, "peso": 6, "nome": "Coleta de dados completos",
         "keywords": ["nome", "cpf", "telefone", "placa", "endereço"]},
        
        {"id": 3, "peso": 2, "nome": "Script LGPD",
         "keywords": ["lgpd", "proteção de dados", "autoriza", "compartilhar"]},
        
        {"id": 4, "peso": 5, "nome": "Confirmação verbal (ECO)",
         "keywords": ["confirmando", "correto", "isso mesmo", "exato"]},
        
        {"id": 5, "peso": 3, "nome": "Escuta atenta",
         "keywords": ["entendi", "compreendo", "certo", "ok"]},
        
        {"id": 6, "peso": 5, "nome": "Conhecimento técnico",
         "keywords": ["franquia", "para-brisa", "vistoria", "seguro"]},
        
        {"id": 7, "peso": 10, "nome": "Informações sobre o dano",
         "keywords": ["quando", "como aconteceu", "tamanho", "localização"]},
        
        {"id": 8, "peso": 10, "nome": "Confirmação de cidade/loja",
         "keywords": ["cidade", "loja", "unidade", "endereço para atendimento"]},
        
        {"id": 9, "peso": 5, "nome": "Comunicação profissional",
         "keywords": ["posso ajudar", "momento", "aguarde"]},
        
        {"id": 10, "peso": 4, "nome": "Empatia e acolhimento",
         "keywords": ["entendo", "compreendo", "vamos resolver", "pode ficar tranquilo"]},
        
        {"id": 11, "peso": 15, "nome": "Script de encerramento",
         "keywords": ["validade", "prazo", "link", "acompanhamento", "número protocolo"]},
        
        {"id": 12, "peso": 6, "nome": "Pesquisa de satisfação",
         "keywords": ["pesquisa", "avaliação", "satisfação", "feedback"]}
    ]
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reinicia a avaliação"""
        self.scores = {item["id"]: 0 for item in self.CHECKLIST}
        self.evidence = {item["id"]: [] for item in self.CHECKLIST}
    
    def evaluate_message(self, message: str, context: ConversationContext) -> Dict:
        """Avalia uma mensagem do agente"""
        message_lower = message.lower()
        results = {}
        
        for item in self.CHECKLIST:
            found_keywords = [kw for kw in item["keywords"] if kw in message_lower]
            
            if found_keywords:
                # Pontuação parcial baseada em quantos keywords foram encontrados
                score_ratio = len(found_keywords) / len(item["keywords"])
                earned_points = int(item["peso"] * score_ratio)
                
                self.scores[item["id"]] = max(self.scores[item["id"]], earned_points)
                self.evidence[item["id"]].extend(found_keywords)
                
                results[item["nome"]] = {
                    "pontos": earned_points,
                    "máximo": item["peso"],
                    "evidências": found_keywords
                }
        
        # Verificações especiais
        if context.check_repetition(message):
            context.add_mistake("Repetição de pergunta detectada")
            self.scores[5] = max(0, self.scores[5] - 1)  # Penaliza escuta atenta
        
        return results
    
    def get_total_score(self) -> Tuple[int, int]:
        """Retorna pontuação total e máxima"""
        total = sum(self.scores.values())
        max_score = sum(item["peso"] for item in self.CHECKLIST)
        return total, max_score
    
    def get_detailed_report(self) -> List[Dict]:
        """Gera relatório detalhado"""
        report = []
        for item in self.CHECKLIST:
            report.append({
                "id": item["id"],
                "nome": item["nome"],
                "pontos": self.scores[item["id"]],
                "máximo": item["peso"],
                "percentual": (self.scores[item["id"]] / item["peso"] * 100) if item["peso"] > 0 else 0,
                "evidências": list(set(self.evidence[item["id"]]))
            })
        return report

# ==================== CLIENTE VIRTUAL ====================

class VirtualCustomer:
    """Cliente virtual inteligente"""
    
    def __init__(self, profile: CustomerProfile = None):
        self.profile = profile or CustomerProfile()
        self.conversation_stage = 0
        self.patience = 100
        self.satisfaction = 70
        
        # Respostas pré-definidas por estágio
        self.responses = {
            "greeting": [
                f"Olá! Preciso de ajuda com o {self.profile.problem}.",
                f"Oi, estou com um problema no meu carro e preciso resolver urgente!",
                f"Bom dia! Meu seguro é {self.profile.insurance} e tenho um problema no vidro."
            ],
            "provide_name": [
                f"Meu nome é {self.profile.name}.",
                f"Sou {self.profile.name}, cliente do seguro {self.profile.insurance}."
            ],
            "provide_cpf": [
                f"Meu CPF é {self.profile.cpf}.",
                f"CPF: {self.profile.cpf}"
            ],
            "provide_phone": [
                f"Meu telefone é {self.profile.phone1}.",
                f"Telefone principal: {self.profile.phone1}, e tenho outro: {self.profile.phone2}"
            ],
            "provide_plate": [
                f"A placa é {self.profile.plate}.",
                f"Placa {self.profile.plate}, é um {self.profile.car_model}."
            ],
            "provide_address": [
                f"Moro em {self.profile.address}.",
                f"Endereço: {self.profile.address}"
            ],
            "describe_problem": [
                f"{self.profile.problem}. Aconteceu ontem na estrada.",
                f"É uma trinca grande, {self.profile.problem}. Estou preocupado que possa piorar."
            ],
            "confirm": [
                "Sim, está correto.",
                "Isso mesmo, pode prosseguir.",
                "Exato, está tudo certo."
            ],
            "impatient": [
                "Olha, já falei isso antes. Vocês anotam as informações?",
                "Estou com pressa, podemos agilizar?",
                "Já informei esses dados, vamos prosseguir?"
            ],
            "satisfied": [
                "Ótimo, obrigado pela agilidade!",
                "Perfeito, vocês são muito eficientes.",
                "Excelente atendimento, parabéns!"
            ]
        }
    
    def get_response(self, agent_message: str, context: ConversationContext) -> str:
        """Gera resposta baseada na mensagem do agente e contexto"""
        agent_lower = agent_message.lower()
        
        # Detecta o que o agente está perguntando
        if any(word in agent_lower for word in ["nome", "quem fala", "com quem"]):
            if context.data_collected.get('name'):
                self.patience -= 20
                return random.choice(self.responses["impatient"])
            context.mark_collected('name')
            return random.choice(self.responses["provide_name"])
        
        elif "cpf" in agent_lower:
            if context.data_collected.get('cpf'):
                self.patience -= 20
                return random.choice(self.responses["impatient"])
            context.mark_collected('cpf')
            return random.choice(self.responses["provide_cpf"])
        
        elif "telefone" in agent_lower:
            if context.data_collected.get('phone1'):
                self.patience -= 15
                return random.choice(self.responses["impatient"])
            context.mark_collected('phone1')
            context.mark_collected('phone2')
            return random.choice(self.responses["provide_phone"])
        
        elif "placa" in agent_lower:
            if context.data_collected.get('plate'):
                self.patience -= 15
                return random.choice(self.responses["impatient"])
            context.mark_collected('plate')
            return random.choice(self.responses["provide_plate"])
        
        elif "endereço" in agent_lower or "onde" in agent_lower:
            if context.data_collected.get('address'):
                self.patience -= 15
                return random.choice(self.responses["impatient"])
            context.mark_collected('address')
            return random.choice(self.responses["provide_address"])
        
        elif any(word in agent_lower for word in ["problema", "aconteceu", "dano", "o que houve"]):
            context.mark_collected('problem')
            return random.choice(self.responses["describe_problem"])
        
        elif any(word in agent_lower for word in ["confirma", "correto", "confere"]):
            self.satisfaction += 10
            return random.choice(self.responses["confirm"])
        
        elif any(word in agent_lower for word in ["obrigado", "agradeço", "tenha um"]):
            return random.choice(self.responses["satisfied"])
        
        # Resposta padrão baseada no humor
        elif self.patience < 50:
            return random.choice(self.responses["impatient"])
        elif self.satisfaction > 80:
            return random.choice(self.responses["satisfied"])
        else:
            return random.choice(self.responses["confirm"])
    
    def get_initial_message(self) -> str:
        """Primeira mensagem do cliente"""
        return random.choice(self.responses["greeting"])

# ==================== INTERFACE PRINCIPAL ====================

def initialize_session():
    """Inicializa variáveis de sessão"""
    if 'started' not in st.session_state:
        st.session_state.started = False
        st.session_state.conversation = []
        st.session_state.context = ConversationContext()
        st.session_state.evaluator = EvaluationEngine()
        st.session_state.customer = VirtualCustomer()
        st.session_state.start_time = None
        st.session_state.elapsed_time = 0

def format_time(seconds: int) -> str:
    """Formata tempo em MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def generate_audio(text: str) -> bytes:
    """Gera áudio do texto"""
    try:
        tts = gTTS(text=text, lang='pt-br', slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except:
        return b""

def main():
    initialize_session()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Voice Coach Pro - Carglass</h1>
        <p>Sistema Avançado de Treinamento de Atendimento</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar com informações
    with st.sidebar:
        st.header("📊 Painel de Controle")
        
        if st.session_state.started:
            # Timer
            if st.session_state.start_time:
                elapsed = time.time() - st.session_state.start_time
                st.markdown(f"""
                <div class="timer-display">
                    ⏱️ {format_time(elapsed)}
                </div>
                """, unsafe_allow_html=True)
            
            # Métricas em tempo real
            total, max_score = st.session_state.evaluator.get_total_score()
            percentage = (total / max_score * 100) if max_score > 0 else 0
            
            st.metric("Pontuação", f"{total}/{max_score}")
            st.metric("Percentual", f"{percentage:.1f}%")
            st.metric("Satisfação Cliente", f"{st.session_state.customer.satisfaction}%")
            st.metric("Paciência Cliente", f"{st.session_state.customer.patience}%")
            
            # Status dos dados coletados
            st.subheader("📋 Dados Coletados")
            for key, collected in st.session_state.context.data_collected.items():
                icon = "✅" if collected else "⏳"
                st.write(f"{icon} {key.title()}")
        
        else:
            st.info("Clique em 'Iniciar Simulação' para começar")
            
            # Informações do cliente
            st.subheader("👤 Cliente do Cenário")
            customer = st.session_state.customer.profile
            st.write(f"**Nome:** {customer.name}")
            st.write(f"**Seguro:** {customer.insurance}")
            st.write(f"**Problema:** {customer.problem}")
            st.write(f"**Urgência:** {customer.urgency.title()}")
    
    # Área principal
    if not st.session_state.started:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### 🎓 Instruções de Treinamento
            
            1. **Objetivo**: Atender o cliente seguindo o protocolo Carglass
            2. **Duração**: Máximo 20 minutos
            3. **Avaliação**: Baseada em 12 critérios (81 pontos)
            4. **Meta**: Atingir no mínimo 80% de aproveitamento
            
            #### Checklist Principal:
            - ✅ Saudação profissional e identificação
            - ✅ Coleta completa de dados
            - ✅ Menção ao LGPD
            - ✅ Confirmação verbal (ECO)
            - ✅ Demonstração de empatia
            - ✅ Script de encerramento completo
            """)
            
            if st.button("🚀 Iniciar Simulação", type="primary", use_container_width=True):
                st.session_state.started = True
                st.session_state.start_time = time.time()
                
                # Primeira mensagem do cliente
                initial_msg = st.session_state.customer.get_initial_message()
                st.session_state.conversation.append(("cliente", initial_msg))
                st.rerun()
    
    else:
        # Área de conversa
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("💬 Conversa")
            
            # Container de mensagens
            chat_container = st.container()
            with chat_container:
                st.markdown('<div class="conversation-box">', unsafe_allow_html=True)
                
                for speaker, message in st.session_state.conversation:
                    if speaker == "cliente":
                        st.markdown(f'<div class="customer-msg">🔸 <strong>Cliente:</strong> {message}</div>', 
                                  unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="agent-msg">🔹 <strong>Você:</strong> {message}</div>', 
                                  unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.subheader("✍️ Sua Resposta")
            
            # Input do agente
            agent_response = st.text_area(
                "Digite sua resposta:",
                height=100,
                placeholder="Ex: Bom dia! Carglass, meu nome é [seu nome]. Como posso ajudá-lo?",
                key="agent_input"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("📤 Enviar", type="primary", use_container_width=True, 
                           disabled=not agent_response):
                    
                    # Adiciona resposta do agente
                    st.session_state.conversation.append(("agente", agent_response))
                    
                    # Avalia a resposta
                    eval_results = st.session_state.evaluator.evaluate_message(
                        agent_response, 
                        st.session_state.context
                    )
                    
                    # Gera resposta do cliente
                    customer_response = st.session_state.customer.get_response(
                        agent_response,
                        st.session_state.context
                    )
                    
                    st.session_state.conversation.append(("cliente", customer_response))
                    
                    # Áudio do cliente (opcional)
                    audio_data = generate_audio(customer_response)
                    if audio_data:
                        st.audio(audio_data, format="audio/mp3")
                    
                    st.rerun()
            
            with col_btn2:
                if st.button("🏁 Finalizar", use_container_width=True):
                    st.session_state.started = False
                    
                    # Mostra relatório final
                    st.balloons()
                    st.success("Simulação Finalizada!")
                    
                    # Relatório
                    total, max_score = st.session_state.evaluator.get_total_score()
                    percentage = (total / max_score * 100) if max_score > 0 else 0
                    
                    st.markdown(f"""
                    ### 📊 Relatório Final
                    - **Pontuação Total:** {total}/{max_score} pontos
                    - **Percentual:** {percentage:.1f}%
                    - **Resultado:** {'✅ APROVADO' if percentage >= 80 else '⚠️ PRECISA MELHORAR'}
                    - **Duração:** {format_time(time.time() - st.session_state.start_time)}
                    """)
                    
                    # Detalhamento
                    with st.expander("📋 Ver Detalhamento"):
                        for item in st.session_state.evaluator.get_detailed_report():
                            status = "✅" if item["percentual"] >= 80 else "⚠️" if item["percentual"] >= 50 else "❌"
                            st.write(f"{status} **{item['nome']}**: {item['pontos']}/{item['máximo']} ({item['percentual']:.0f}%)")
                            if item["evidências"]:
                                st.write(f"   Evidências: {', '.join(item['evidências'])}")
                    
                    # Botão para reiniciar
                    if st.button("🔄 Nova Simulação", use_container_width=True):
                        for key in ['started', 'conversation', 'context', 'evaluator', 'customer', 'start_time']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()

if __name__ == "__main__":
    main()
