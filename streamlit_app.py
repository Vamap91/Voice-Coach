import streamlit as st
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import random

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(
    page_title="Voice Coach - Sistema de Treinamento Carglass",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS PROFISSIONAL ====================
st.markdown("""
<style>
    /* Header Principal */
    .main-header {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    /* Container de Chat */
    .chat-wrapper {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        height: 550px;
        overflow-y: auto;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }
    
    /* Mensagens */
    .customer-message {
        background: linear-gradient(135deg, #fff8dc, #ffd700);
        border-left: 4px solid #ff9800;
        padding: 12px 16px;
        margin: 10px 0;
        border-radius: 0 10px 10px 0;
        animation: slideIn 0.3s ease;
    }
    
    .agent-message {
        background: linear-gradient(135deg, #e8f5e9, #a5d6a7);
        border-right: 4px solid #4caf50;
        padding: 12px 16px;
        margin: 10px 0;
        border-radius: 10px 0 0 10px;
        text-align: right;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    /* Métricas */
    .metrics-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #e0e0e0;
    }
    
    .score-display {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }
    
    .timer-display {
        font-size: 1.8rem;
        font-weight: bold;
        text-align: center;
        color: #1976d2;
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    /* Checklist */
    .checklist-item {
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 8px;
        background: #f5f5f5;
        border-left: 3px solid #2196f3;
        transition: all 0.3s ease;
    }
    
    .checklist-item:hover {
        background: #e3f2fd;
        transform: translateX(5px);
    }
    
    /* Botões */
    .stButton > button {
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    /* Input Area */
    .input-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        margin-top: 1rem;
    }
    
    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 2px;
    }
    
    .badge-success { background: #4caf50; color: white; }
    .badge-warning { background: #ff9800; color: white; }
    .badge-danger { background: #f44336; color: white; }
    .badge-info { background: #2196f3; color: white; }
</style>
""", unsafe_allow_html=True)

# ==================== CHECKLIST OFICIAL CARGLASS (81 PONTOS) ====================
OFFICIAL_CHECKLIST = [
    {
        "id": 1,
        "description": "Atendeu em 5s e saudação correta com técnicas de atendimento encantador",
        "points": 10,
        "keywords": ["bom dia", "boa tarde", "boa noite", "carglass", "meu nome", "posso ajudar"],
        "required": True
    },
    {
        "id": 2,
        "description": "Solicitou dados completos (2 telefones, nome, CPF, placa, endereço)",
        "points": 6,
        "keywords": ["nome", "cpf", "telefone", "segundo telefone", "placa", "endereço"],
        "required": True
    },
    {
        "id": 3,
        "description": "Verbalizou o script LGPD",
        "points": 2,
        "keywords": ["lgpd", "proteção de dados", "autoriza", "compartilhar"],
        "required": False
    },
    {
        "id": 4,
        "description": "Repetiu verbalmente 2 de 3 (placa, telefone, CPF) para confirmar",
        "points": 5,
        "keywords": ["confirmando", "repito", "correto"],
        "required": True
    },
    {
        "id": 5,
        "description": "Evitou solicitações duplicadas e escutou atentamente",
        "points": 3,
        "keywords": ["entendi", "compreendo", "anotado"],
        "required": False
    },
    {
        "id": 6,
        "description": "Compreendeu a solicitação e demonstrou conhecimento dos serviços",
        "points": 5,
        "keywords": ["para-brisa", "franquia", "seguro", "cobertura"],
        "required": True
    },
    {
        "id": 7,
        "description": "Confirmou informações completas do dano (data, motivo, tamanho, LED/Xenon)",
        "points": 10,
        "keywords": ["quando", "como aconteceu", "tamanho", "led", "xenon", "sensor"],
        "required": True
    },
    {
        "id": 8,
        "description": "Confirmou cidade e selecionou primeira loja do sistema",
        "points": 10,
        "keywords": ["cidade", "loja", "unidade", "localização"],
        "required": True
    },
    {
        "id": 9,
        "description": "Comunicação eficaz (sem gírias, avisou ausências/retornos)",
        "points": 5,
        "keywords": ["aguarde", "momento", "retornei", "voltei"],
        "required": False
    },
    {
        "id": 10,
        "description": "Conduta acolhedora (empatia, sorriso na voz)",
        "points": 4,
        "keywords": ["entendo", "compreendo", "vamos resolver", "pode ficar tranquilo"],
        "required": False
    },
    {
        "id": 11,
        "description": "Script de encerramento completo (validade, franquia, link, aguardar contato)",
        "points": 15,
        "keywords": ["protocolo", "validade", "franquia", "link", "acompanhamento", "documentos", "prazo"],
        "required": True
    },
    {
        "id": 12,
        "description": "Orientou sobre a pesquisa de satisfação",
        "points": 6,
        "keywords": ["pesquisa", "satisfação", "avaliação", "nota"],
        "required": False
    }
]

# ==================== MODELOS DE DADOS ====================
@dataclass
class CustomerProfile:
    """Perfil do cliente para simulação"""
    name: str = "João Silva"
    cpf: str = "123.456.789-10"
    phone1: str = "11-99999-8888"
    phone2: str = "11-97777-6666"
    plate: str = "ABC-1234"
    car: str = "Honda Civic 2020"
    address: str = "Rua das Flores, 123 - Vila Olímpia, São Paulo/SP"
    insurance: str = "Porto Seguro"
    problem: str = "trinca no para-brisa de 15cm"
    problem_date: str = "ontem"
    has_special: bool = False  # LED/Xenon

@dataclass
class ConversationState:
    """Estado da conversa"""
    collected_data: Dict[str, bool] = field(default_factory=lambda: {
        'greeting': False,
        'name': False,
        'cpf': False,
        'phone1': False,
        'phone2': False,
        'plate': False,
        'address': False,
        'lgpd': False,
        'problem': False,
        'damage_details': False,
        'city': False,
        'closing': False
    })
    
    patience: int = 100
    satisfaction: int = 70
    repetitions: int = 0
    stage: str = "initial"

# ==================== SISTEMA DE AVALIAÇÃO ====================
class EvaluationSystem:
    """Sistema de avaliação baseado no checklist oficial"""
    
    def __init__(self):
        self.checklist_scores = {item["id"]: 0 for item in OFFICIAL_CHECKLIST}
        self.evidence = {item["id"]: [] for item in OFFICIAL_CHECKLIST}
        self.messages_history = []
        
    def evaluate_message(self, message: str) -> Dict:
        """Avalia mensagem do agente baseado no checklist"""
        message_lower = message.lower()
        self.messages_history.append(message)
        
        results = {}
        
        for item in OFFICIAL_CHECKLIST:
            # Verifica keywords
            found = [kw for kw in item["keywords"] if kw in message_lower]
            
            if found:
                # Adiciona evidências
                for kw in found:
                    if kw not in self.evidence[item["id"]]:
                        self.evidence[item["id"]].append(kw)
                
                # Calcula pontos (progressivo, não substitui)
                if self.checklist_scores[item["id"]] < item["points"]:
                    earned = min(item["points"], len(found) * (item["points"] / max(3, len(item["keywords"]))))
                    self.checklist_scores[item["id"]] = min(item["points"], self.checklist_scores[item["id"]] + earned)
                    
                    results[item["id"]] = {
                        "description": item["description"],
                        "earned": self.checklist_scores[item["id"]],
                        "max": item["points"],
                        "evidence": self.evidence[item["id"]]
                    }
        
        # Item 5 (Escuta atenta) começa com pontos totais
        if self.checklist_scores[5] == 0:
            self.checklist_scores[5] = 3
        
        return results
    
    def penalize_repetition(self):
        """Penaliza por repetição (Item 5)"""
        self.checklist_scores[5] = max(0, self.checklist_scores[5] - 1)
    
    def get_total_score(self) -> Tuple[int, int]:
        """Retorna pontuação total atual"""
        total = sum(self.checklist_scores.values())
        return int(total), 81
    
    def get_detailed_report(self) -> List[Dict]:
        """Relatório detalhado por item do checklist"""
        report = []
        for item in OFFICIAL_CHECKLIST:
            score = self.checklist_scores[item["id"]]
            percentage = (score / item["points"] * 100) if item["points"] > 0 else 0
            
            report.append({
                "id": item["id"],
                "description": item["description"],
                "score": score,
                "max": item["points"],
                "percentage": percentage,
                "evidence": self.evidence[item["id"]],
                "status": "✅" if percentage >= 80 else "⚠️" if percentage >= 50 else "❌"
            })
        
        return report

# ==================== CLIENTE VIRTUAL INTELIGENTE ====================
class VirtualCustomer:
    """Cliente virtual com comportamento realista"""
    
    def __init__(self):
        self.profile = CustomerProfile()
        self.state = ConversationState()
        self.responses_given = set()
        
    def generate_response(self, agent_message: str) -> str:
        """Gera resposta contextual baseada na mensagem do agente"""
        msg_lower = agent_message.lower()
        
        # Análise da mensagem
        analysis = {
            'greeting': any(w in msg_lower for w in ['bom dia', 'boa tarde', 'boa noite', 'olá']),
            'asking_name': 'nome' in msg_lower and any(w in msg_lower for w in ['seu', 'qual', 'pode', 'informar']),
            'asking_cpf': 'cpf' in msg_lower,
            'asking_phone': 'telefone' in msg_lower or 'contato' in msg_lower,
            'asking_second_phone': any(w in msg_lower for w in ['outro', 'segundo', 'adicional']) and 'telefone' in msg_lower,
            'asking_plate': 'placa' in msg_lower or 'veículo' in msg_lower,
            'asking_address': 'endereço' in msg_lower or 'onde mora' in msg_lower,
            'asking_problem': any(w in msg_lower for w in ['problema', 'aconteceu', 'ocorreu']),
            'asking_when': 'quando' in msg_lower,
            'asking_special': any(w in msg_lower for w in ['led', 'xenon', 'sensor', 'câmera']),
            'asking_city': 'cidade' in msg_lower or 'loja' in msg_lower,
            'lgpd': 'lgpd' in msg_lower or 'proteção de dados' in msg_lower,
            'confirming': any(w in msg_lower for w in ['confirma', 'correto', 'isso mesmo']),
            'closing': any(w in msg_lower for w in ['protocolo', 'validade', 'franquia'])
        }
        
        # Respostas baseadas no contexto
        
        # Saudação inicial
        if analysis['greeting'] and not self.state.collected_data['greeting']:
            self.state.collected_data['greeting'] = True
            return f"Olá! Meu seguro é {self.profile.insurance} e tenho um problema no vidro do meu carro. Preciso resolver isso urgente!"
        
        # Nome
        if analysis['asking_name']:
            if self.state.collected_data['name']:
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Já informei meu nome: {self.profile.name}. Vocês não anotam as informações?"
            else:
                self.state.collected_data['name'] = True
                return f"Meu nome é {self.profile.name}."
        
        # CPF
        if analysis['asking_cpf']:
            if self.state.collected_data['cpf']:
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Já falei o CPF: {self.profile.cpf}. Por favor, prestem atenção!"
            else:
                self.state.collected_data['cpf'] = True
                return f"Meu CPF é {self.profile.cpf}."
        
        # Telefones
        if analysis['asking_phone']:
            if analysis['asking_second_phone']:
                if self.state.collected_data['phone2']:
                    self.state.patience -= 15
                    return "Já passei os dois telefones anteriormente!"
                else:
                    self.state.collected_data['phone2'] = True
                    return f"O segundo telefone é {self.profile.phone2}."
            else:
                if not self.state.collected_data['phone1']:
                    self.state.collected_data['phone1'] = True
                    return f"Meu telefone é {self.profile.phone1}."
                elif not self.state.collected_data['phone2']:
                    self.state.collected_data['phone2'] = True
                    return f"Tenho também o {self.profile.phone2} como segundo telefone."
                else:
                    self.state.patience -= 20
                    return f"Já informei os dois telefones: {self.profile.phone1} e {self.profile.phone2}!"
        
        # Placa
        if analysis['asking_plate']:
            if self.state.collected_data['plate']:
                self.state.repetitions += 1
                self.state.patience -= 25
                return f"Já falei isso antes! Placa {self.profile.plate}, é um {self.profile.car}. Estou com pressa, podemos agilizar?"
            else:
                self.state.collected_data['plate'] = True
                return f"Placa {self.profile.plate}, é um {self.profile.car}."
        
        # Endereço
        if analysis['asking_address']:
            if self.state.collected_data['address']:
                self.state.patience -= 20
                return "Já informei meu endereço completo anteriormente."
            else:
                self.state.collected_data['address'] = True
                return f"Meu endereço é {self.profile.address}."
        
        # LGPD
        if analysis['lgpd']:
            self.state.collected_data['lgpd'] = True
            return "Sim, autorizo o compartilhamento dos dados para o atendimento."
        
        # Problema
        if analysis['asking_problem']:
            if not self.state.collected_data['problem']:
                self.state.collected_data['problem'] = True
                return f"Tenho uma {self.profile.problem}. Aconteceu {self.profile.problem_date} na estrada."
            else:
                return "Como já disse, é uma trinca no para-brisa de 15cm."
        
        # Quando aconteceu
        if analysis['asking_when']:
            return f"Aconteceu {self.profile.problem_date} quando estava dirigindo na estrada."
        
        # LED/Xenon
        if analysis['asking_special']:
            self.state.collected_data['damage_details'] = True
            return "Não, o veículo não tem LED, Xenon ou sensor no vidro."
        
        # Cidade/Loja
        if analysis['asking_city']:
            self.state.collected_data['city'] = True
            return "Prefiro fazer em São Paulo, na loja mais próxima da Vila Olímpia."
        
        # Confirmações
        if analysis['confirming']:
            if self.state.patience > 50:
                return "Sim, está correto."
            else:
                return "Isso mesmo, podemos prosseguir?"
        
        # Encerramento
        if analysis['closing']:
            self.state.collected_data['closing'] = True
            return "Ok, anotei as informações. Preciso levar algum documento?"
        
        # Pesquisa
        if 'pesquisa' in msg_lower:
            return "Sim, responderei a pesquisa de satisfação."
        
        # Agradecimento
        if any(w in msg_lower for w in ['obrigado', 'agradeço', 'tenha um']):
            return "Obrigado pelo atendimento!"
        
        # Resposta padrão baseada no estado emocional
        if self.state.patience < 30:
            return "Estou com pressa, podemos agilizar?"
        elif self.state.repetitions > 2:
            return "Olha, vocês precisam prestar mais atenção. Já repeti várias informações."
        else:
            return "Certo, qual a próxima informação que precisa?"

# ==================== INTERFACE PRINCIPAL ====================
def init_session_state():
    """Inicializa o estado da sessão"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.session_active = False
        st.session_state.messages = []
        st.session_state.customer = None
        st.session_state.evaluator = None
        st.session_state.start_time = None
        st.session_state.session_duration = 0

def login_screen():
    """Tela de login"""
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Voice Coach - Sistema de Treinamento Carglass</h1>
        <p>Sistema Inteligente de Avaliação e Treinamento</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Acesso ao Sistema")
        
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        password = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Entrar", type="primary", use_container_width=True):
                if username and password:  # Validação simples
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Por favor, preencha todos os campos!")
        
        with col_btn2:
            if st.button("📝 Registrar", use_container_width=True):
                st.info("Função de registro em desenvolvimento")

def main_interface():
    """Interface principal após login"""
    
    # Header com informações do usuário
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        st.markdown(f"### 👤 Olá, {st.session_state.username}!")
    with col3:
        if st.button("🚪 Sair"):
            st.session_state.logged_in = False
            st.session_state.session_active = False
            st.rerun()
    
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Voice Coach - Carglass</h1>
        <p>Treinamento com Avaliação Baseada no Checklist Oficial (81 pontos)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Layout principal
    if not st.session_state.session_active:
        # Tela inicial de preparação
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### 📋 Protocolo de Atendimento Carglass")
            
            # Mostra o checklist oficial
            st.markdown("#### Checklist de Avaliação (81 pontos)")
            
            for item in OFFICIAL_CHECKLIST[:6]:
                st.markdown(f"""
                <div class="checklist-item">
                    <strong>{item['id']}.</strong> {item['description']} 
                    <span class="status-badge badge-info">{item['points']} pts</span>
                </div>
                """, unsafe_allow_html=True)
            
            with st.expander("Ver checklist completo"):
                for item in OFFICIAL_CHECKLIST[6:]:
                    st.markdown(f"""
                    <div class="checklist-item">
                        <strong>{item['id']}.</strong> {item['description']} 
                        <span class="status-badge badge-info">{item['points']} pts</span>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 🎮 Configurações da Simulação")
            
            st.info("""
            **Cliente Virtual:**
            - João Silva
            - Seguro: Porto Seguro
            - Problema: Trinca no para-brisa (15cm)
            - Urgência: Alta
            
            **Objetivo:**
            - Seguir protocolo completo
            - Atingir mínimo 65/81 pontos (80%)
            - Tempo máximo: 20 minutos
            """)
            
            if st.button("🚀 INICIAR SIMULAÇÃO", type="primary", use_container_width=True):
                st.session_state.session_active = True
                st.session_state.customer = VirtualCustomer()
                st.session_state.evaluator = EvaluationSystem()
                st.session_state.start_time = time.time()
                st.session_state.messages = [
                    ("cliente", "Alô? Preciso falar com a Carglass sobre um problema no meu carro!")
                ]
                st.rerun()
    
    else:
        # Interface de simulação ativa
        col_left, col_right = st.columns([3, 1])
        
        with col_left:
            # Timer
            if st.session_state.start_time:
                elapsed = time.time() - st.session_state.start_time
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                
                timer_color = "#f44336" if elapsed > 1080 else "#ff9800" if elapsed > 900 else "#2196f3"
                st.markdown(f"""
                <div class="timer-display" style="color: {timer_color};">
                    ⏱️ Tempo: {minutes:02d}:{seconds:02d} / 20:00
                </div>
                """, unsafe_allow_html=True)
                
                if elapsed > 1200:  # 20 minutos
                    st.error("⏰ Tempo limite atingido!")
                    st.session_state.session_active = False
            
            # Chat container
            st.markdown("### 💬 Conversa")
            chat_html = '<div class="chat-wrapper">'
            
            for speaker, message in st.session_state.messages:
                if speaker == "cliente":
                    chat_html += f'<div class="customer-message">🔸 <strong>Cliente:</strong> {message}</div>'
                else:
                    chat_html += f'<div class="agent-message"><strong>Você:</strong> {message} 🔹</div>'
            
            chat_html += '</div>'
            st.markdown(chat_html, unsafe_allow_html=True)
            
            # Input area
            st.markdown('<div class="input-container">', unsafe_allow_html=True)
            
            user_input = st.text_area(
                "Sua resposta:",
                height=100,
                placeholder="Ex: Bom dia! Carglass, meu nome é [seu nome]. Como posso ajudá-lo?",
                key="agent_input"
            )
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("📤 Enviar", type="primary", use_container_width=True, disabled=not user_input):
                    if user_input:
                        # Adiciona mensagem do agente
                        st.session_state.messages.append(("agente", user_input))
                        
                        # Avalia a mensagem
                        st.session_state.evaluator.evaluate_message(user_input)
                        
                        # Verifica repetições
                        old_repetitions = st.session_state.customer.state.repetitions
                        
                        # Gera resposta do cliente
                        customer_response = st.session_state.customer.generate_response(user_input)
                        st.session_state.messages.append(("cliente", customer_response))
                        
                        # Penaliza se houve repetição
                        if st.session_state.customer.state.repetitions > old_repetitions:
                            st.session_state.evaluator.penalize_repetition()
                        
                        st.rerun()
            
            with col2:
                if st.button("🏁 Finalizar Atendimento", use_container_width=True):
                    st.session_state.session_active = False
                    st.rerun()
            
            with col3:
                if st.button("🔄 Reset", use_container_width=True):
                    st.session_state.session_active = False
                    st.session_state.messages = []
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_right:
            # Métricas em tempo real
            st.markdown("### 📊 Métricas")
            
            total, max_score = st.session_state.evaluator.get_total_score()
            percentage = (total / 81 * 100)
            
            # Display de pontuação
            if percentage >= 80:
                score_color = "#4caf50"
                status = "✅ Excelente"
            elif percentage >= 60:
                score_color = "#ff9800"
                status = "⚠️ Bom"
            else:
                score_color = "#f44336"
                status = "❌ Melhorar"
            
            st.markdown(f"""
            <div class="metrics-card">
                <div style="text-align: center;">
                    <h1 style="color: {score_color}; margin: 0;">{total}/81</h1>
                    <p style="font-size: 1.2rem; margin: 0;">{percentage:.1f}%</p>
                    <p style="margin: 0;">{status}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Estado do cliente
            st.markdown("### 😊 Cliente")
            patience = st.session_state.customer.state.patience
            
            if patience > 70:
                st.success(f"Satisfeito ({patience}%)")
            elif patience > 40:
                st.warning(f"Impaciente ({patience}%)")
            else:
                st.error(f"Frustrado ({patience}%)")
            
            if st.session_state.customer.state.repetitions > 0:
                st.error(f"⚠️ {st.session_state.customer.state.repetitions} repetições detectadas!")
            
            # Checklist de dados coletados
            st.markdown("### 📋 Checklist")
            
            checklist_items = [
                ("Nome", st.session_state.customer.state.collected_data.get('name', False)),
                ("CPF", st.session_state.customer.state.collected_data.get('cpf', False)),
                ("Telefone 1", st.session_state.customer.state.collected_data.get('phone1', False)),
                ("Telefone 2", st.session_state.customer.state.collected_data.get('phone2', False)),
                ("Placa", st.session_state.customer.state.collected_data.get('plate', False)),
                ("Endereço", st.session_state.customer.state.collected_data.get('address', False)),
                ("Problema", st.session_state.customer.state.collected_data.get('problem', False)),
                ("LGPD", st.session_state.customer.state.collected_data.get('lgpd', False)),
                ("LED/Xenon", st.session_state.customer.state.collected_data.get('damage_details', False))
            ]
            
            for item, collected in checklist_items:
                icon = "✅" if collected else "⏳"
                st.write(f"{icon} {item}")
            
            # Debug (expandível)
            with st.expander("🔍 Debug"):
                st.write("**Pontuação por Item:**")
                for item in st.session_state.evaluator.get_detailed_report():
                    st.write(f"{item['status']} Item {item['id']}: {item['score']:.1f}/{item['max']} pts")

def results_screen():
    """Tela de resultados após finalizar"""
    st.markdown("""
    <div class="main-header">
        <h1>📊 Relatório Final de Atendimento</h1>
        <p>Avaliação baseada no Checklist Oficial Carglass</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Pontuação geral
    total, max_score = st.session_state.evaluator.get_total_score()
    percentage = (total / 81 * 100)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pontuação Total", f"{total}/81")
    
    with col2:
        st.metric("Percentual", f"{percentage:.1f}%")
    
    with col3:
        if percentage >= 80:
            st.metric("Resultado", "✅ APROVADO")
        else:
            st.metric("Resultado", "❌ REPROVADO")
    
    with col4:
        if st.session_state.start_time:
            duration = int(time.time() - st.session_state.start_time)
            st.metric("Duração", f"{duration//60:02d}:{duration%60:02d}")
    
    # Análise detalhada por item do checklist
    st.markdown("### 📋 Análise Detalhada do Checklist")
    
    report = st.session_state.evaluator.get_detailed_report()
    
    # Divide em duas colunas para melhor visualização
    col1, col2 = st.columns(2)
    
    for i, item in enumerate(report):
        with col1 if i % 2 == 0 else col2:
            # Cor baseada na performance
            if item['percentage'] >= 80:
                border_color = "#4caf50"
                status_text = "✅ Completo"
            elif item['percentage'] >= 50:
                border_color = "#ff9800"
                status_text = "⚠️ Parcial"
            else:
                border_color = "#f44336"
                status_text = "❌ Não atendido"
            
            st.markdown(f"""
            <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 1rem; margin: 0.5rem 0;">
                <strong>{item['id']}. {item['description'][:50]}...</strong><br>
                Pontos: {item['score']:.1f}/{item['max']} ({item['percentage']:.0f}%)<br>
                Status: {status_text}
                {f"<br>Evidências: {', '.join(item['evidence'][:3])}" if item['evidence'] else ""}
            </div>
            """, unsafe_allow_html=True)
    
    # Feedback do cliente
    st.markdown("### 💬 Feedback do Cliente Virtual")
    
    patience = st.session_state.customer.state.patience
    repetitions = st.session_state.customer.state.repetitions
    
    if repetitions > 2:
        st.error(f"❌ Cliente ficou frustrado com {repetitions} repetições desnecessárias")
    elif patience < 40:
        st.warning("⚠️ Cliente demonstrou impaciência durante o atendimento")
    elif percentage >= 80:
        st.success("✅ Cliente satisfeito com o atendimento!")
    else:
        st.info("📝 Atendimento pode ser melhorado")
    
    # Recomendações
    st.markdown("### 💡 Recomendações de Melhoria")
    
    # Identifica os 3 piores itens
    worst_items = sorted(report, key=lambda x: x['percentage'])[:3]
    
    for item in worst_items:
        if item['percentage'] < 80:
            st.warning(f"**Melhorar Item {item['id']}:** {item['description']}")
            st.write(f"   → Você obteve {item['score']:.1f} de {item['max']} pontos possíveis")
    
    # Botões de ação
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Nova Simulação", type="primary", use_container_width=True):
            st.session_state.session_active = False
            st.session_state.messages = []
            st.session_state.customer = None
            st.session_state.evaluator = None
            st.session_state.start_time = None
            st.rerun()
    
    with col2:
        if st.button("📊 Ver Histórico", use_container_width=True):
            st.info("Função de histórico em desenvolvimento")
    
    with col3:
        if st.button("📥 Exportar Relatório", use_container_width=True):
            # Gera JSON do relatório
            report_data = {
                "usuario": st.session_state.username,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pontuacao_total": total,
                "pontuacao_maxima": 81,
                "percentual": percentage,
                "aprovado": percentage >= 80,
                "duracao_segundos": int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0,
                "detalhamento": report,
                "satisfacao_cliente": patience,
                "repeticoes": repetitions
            }
            
            st.download_button(
                label="💾 Baixar JSON",
                data=json.dumps(report_data, indent=2, ensure_ascii=False),
                file_name=f"relatorio_voice_coach_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# ==================== FUNÇÃO PRINCIPAL ====================
def main():
    """Função principal do aplicativo"""
    init_session_state()
    
    # Verifica estado de login
    if not st.session_state.logged_in:
        login_screen()
    else:
        # Verifica se há uma sessão ativa ou se deve mostrar resultados
        if st.session_state.session_active:
            main_interface()
        elif len(st.session_state.messages) > 0 and st.session_state.evaluator:
            results_screen()
        else:
            main_interface()

if __name__ == "__main__":
    main()
