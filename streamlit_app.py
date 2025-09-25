import os
import io
import time
import json
import streamlit as st
from datetime import datetime
from gtts import gTTS
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Configuração da página com layout otimizado
st.set_page_config(
    page_title="Voice Coach Pro - Carglass", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar colapsada para mais espaço
)

# CSS responsivo e profissional
st.markdown("""
<style>
    /* Container principal */
    .stApp {
        background: linear-gradient(to bottom, #f0f2f6, #ffffff);
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #004a8f, #0066cc);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Container de chat otimizado */
    .chat-container {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        height: 500px;
        overflow-y: auto;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        scroll-behavior: smooth;
    }
    
    /* Mensagens */
    .message {
        margin: 0.75rem 0;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        max-width: 80%;
        word-wrap: break-word;
    }
    
    .customer-message {
        background: linear-gradient(135deg, #fff3cd, #ffe8a1);
        border-left: 3px solid #ffc107;
        margin-right: auto;
    }
    
    .agent-message {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        border-left: 3px solid #28a745;
        margin-left: auto;
        text-align: right;
    }
    
    /* Área de input */
    .input-area {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Métricas */
    .metrics-container {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #0066cc;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    .badge-success {
        background: #d4edda;
        color: #155724;
    }
    
    .badge-warning {
        background: #fff3cd;
        color: #856404;
    }
    
    .badge-danger {
        background: #f8d7da;
        color: #721c24;
    }
    
    /* Scrollbar customizada */
    .chat-container::-webkit-scrollbar {
        width: 8px;
    }
    
    .chat-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 10px;
    }
    
    .chat-container::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
    
    /* Timer */
    .timer-display {
        font-size: 1.25rem;
        font-weight: bold;
        color: #0066cc;
        text-align: center;
        padding: 0.5rem;
        background: #e7f3ff;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== MODELOS DE DADOS ====================

@dataclass
class CustomerData:
    """Dados do cliente para a simulação"""
    name: str = "João Silva"
    cpf: str = "123.456.789-10"
    phone1: str = "11-99999-8888"
    phone2: str = "11-97777-6666"
    plate: str = "ABC-1234"
    car: str = "Honda Civic 2020"
    address: str = "Rua das Flores, 123 - Vila Olímpia, São Paulo/SP"
    insurance: str = "Porto Seguro"
    problem: str = "trinca no para-brisa de 15cm causada por uma pedra"

@dataclass
class ConversationMemory:
    """Memória da conversa para evitar repetições"""
    provided_data: Dict[str, str] = field(default_factory=dict)
    asked_questions: List[str] = field(default_factory=list)
    repetition_count: int = 0
    patience_level: int = 100
    stage: str = "greeting"
    
    def add_provided_data(self, key: str, value: str):
        self.provided_data[key] = value
    
    def was_already_provided(self, key: str) -> bool:
        return key in self.provided_data
    
    def decrease_patience(self, amount: int = 20):
        self.patience_level = max(0, self.patience_level - amount)
        self.repetition_count += 1

# ==================== CLIENTE INTELIGENTE ====================

class SmartVirtualCustomer:
    """Cliente virtual com memória e comportamento realista"""
    
    def __init__(self):
        self.data = CustomerData()
        self.memory = ConversationMemory()
        self.responses_given = []
        
    def analyze_agent_message(self, message: str) -> Dict:
        """Analisa a mensagem do agente para entender o que foi solicitado"""
        message_lower = message.lower()
        
        analysis = {
            'asking_name': any(w in message_lower for w in ['nome', 'quem fala', 'com quem']),
            'asking_cpf': 'cpf' in message_lower,
            'asking_phone': any(w in message_lower for w in ['telefone', 'contato', 'celular']),
            'asking_second_phone': any(w in message_lower for w in ['segundo', 'outro telefone', 'adicional']),
            'asking_plate': any(w in message_lower for w in ['placa', 'veículo']),
            'asking_address': any(w in message_lower for w in ['endereço', 'onde mora', 'localização']),
            'asking_problem': any(w in message_lower for w in ['problema', 'aconteceu', 'ocorreu', 'dano']),
            'asking_city': any(w in message_lower for w in ['cidade', 'onde realizar', 'loja']),
            'confirming': any(w in message_lower for w in ['confirma', 'correto', 'isso mesmo', 'confere']),
            'greeting': any(w in message_lower for w in ['bom dia', 'boa tarde', 'boa noite', 'olá']),
            'closing': any(w in message_lower for w in ['mais alguma', 'dúvida', 'agradeço', 'obrigado']),
            'inappropriate': 'filho da puta' in message_lower or any(w in message_lower for w in ['porra', 'merda', 'caralho'])
        }
        
        return analysis
    
    def generate_response(self, agent_message: str) -> str:
        """Gera resposta inteligente baseada no contexto"""
        analysis = self.analyze_agent_message(agent_message)
        
        # Responde a conteúdo inapropriado
        if analysis['inappropriate']:
            self.memory.decrease_patience(50)
            return "Olha, não precisa falar assim. Estou tentando resolver meu problema de forma educada. Por favor, vamos manter o profissionalismo."
        
        # Se está saudando
        if analysis['greeting'] and self.memory.stage == "greeting":
            self.memory.stage = "data_collection"
            return f"Olá! Meu seguro é {self.data.insurance} e tenho um problema no vidro do meu carro. Preciso resolver isso urgente!"
        
        # Verifica repetições antes de responder
        response_parts = []
        
        # Nome
        if analysis['asking_name']:
            if self.memory.was_already_provided('name'):
                self.memory.decrease_patience()
                return f"Já falei meu nome antes, é {self.data.name}. Vocês não anotam as informações?"
            else:
                self.memory.add_provided_data('name', self.data.name)
                response_parts.append(f"Meu nome é {self.data.name}")
        
        # CPF
        if analysis['asking_cpf']:
            if self.memory.was_already_provided('cpf'):
                self.memory.decrease_patience()
                return f"Olha, já informei o CPF: {self.data.cpf}. Por favor, anote dessa vez!"
            else:
                self.memory.add_provided_data('cpf', self.data.cpf)
                response_parts.append(f"Meu CPF é {self.data.cpf}")
        
        # Telefone
        if analysis['asking_phone']:
            if analysis['asking_second_phone'] or 'segundo' in agent_message.lower():
                if self.memory.was_already_provided('phone2'):
                    self.memory.decrease_patience()
                    return "Já passei os dois telefones! Por favor, prestem atenção no que eu falo."
                else:
                    self.memory.add_provided_data('phone2', self.data.phone2)
                    response_parts.append(f"O segundo telefone é {self.data.phone2}")
            else:
                if self.memory.was_already_provided('phone1'):
                    if not self.memory.was_already_provided('phone2'):
                        # Se pedir telefone de novo mas não pediu o segundo ainda
                        self.memory.add_provided_data('phone2', self.data.phone2)
                        return f"Já informei o primeiro telefone. O segundo é {self.data.phone2}"
                    else:
                        self.memory.decrease_patience()
                        return f"Já informei os telefones: {self.data.phone1} e {self.data.phone2}"
                else:
                    self.memory.add_provided_data('phone1', self.data.phone1)
                    response_parts.append(f"Meu telefone é {self.data.phone1}")
        
        # Placa
        if analysis['asking_plate']:
            if self.memory.was_already_provided('plate'):
                self.memory.decrease_patience(30)
                return f"Já falei isso antes! Placa {self.data.plate}, é um {self.data.car}. Estou com pressa, podemos agilizar?"
            else:
                self.memory.add_provided_data('plate', self.data.plate)
                response_parts.append(f"Placa {self.data.plate}, é um {self.data.car}")
        
        # Endereço
        if analysis['asking_address']:
            if self.memory.was_already_provided('address'):
                self.memory.decrease_patience()
                return "Já informei meu endereço completo. Por favor, verifiquem suas anotações."
            else:
                self.memory.add_provided_data('address', self.data.address)
                response_parts.append(f"Meu endereço é {self.data.address}")
        
        # Problema
        if analysis['asking_problem']:
            if self.memory.was_already_provided('problem'):
                self.memory.decrease_patience()
                return "Como já expliquei, tenho uma trinca no para-brisa. Foi ontem na estrada."
            else:
                self.memory.add_provided_data('problem', self.data.problem)
                response_parts.append(f"Tenho uma {self.data.problem}. Aconteceu ontem quando estava na estrada")
        
        # Cidade/Loja
        if analysis['asking_city']:
            response_parts.append("Prefiro fazer o serviço em São Paulo, na loja mais próxima da Vila Olímpia")
        
        # Confirmações
        if analysis['confirming']:
            if self.memory.patience_level > 70:
                return "Sim, está correto. Pode prosseguir."
            else:
                return "Isso mesmo. Vamos agilizar, por favor?"
        
        # Encerramento
        if analysis['closing']:
            return "Não, está tudo esclarecido. Obrigado pelo atendimento!"
        
        # Monta resposta composta
        if response_parts:
            return ". ".join(response_parts) + "."
        
        # Resposta padrão baseada na paciência
        if self.memory.patience_level < 30:
            return "Estou com pressa, podemos agilizar? Já passei todas as informações necessárias."
        elif self.memory.repetition_count > 2:
            return "Olha, vocês precisam prestar mais atenção. Já repeti várias informações."
        else:
            return "Certo, qual a próxima informação que precisa?"

# ==================== AVALIADOR INTELIGENTE ====================

class IntelligentEvaluator:
    """Sistema de avaliação baseado no protocolo Carglass"""
    
    def __init__(self):
        self.criteria = {
            'greeting': {'weight': 10, 'score': 0, 'keywords': ['bom dia', 'boa tarde', 'carglass', 'meu nome']},
            'data_collection': {'weight': 6, 'score': 0, 'keywords': ['nome', 'cpf', 'telefone', 'placa', 'endereço']},
            'lgpd': {'weight': 2, 'score': 0, 'keywords': ['lgpd', 'proteção', 'dados', 'autoriza']},
            'confirmation': {'weight': 5, 'score': 0, 'keywords': ['confirmando', 'confere', 'correto']},
            'listening': {'weight': 3, 'score': 3, 'keywords': []},  # Começa com pontos, perde se repetir
            'knowledge': {'weight': 5, 'score': 0, 'keywords': ['franquia', 'vistoria', 'para-brisa', 'seguro']},
            'damage_info': {'weight': 10, 'score': 0, 'keywords': ['quando', 'como', 'tamanho', 'local']},
            'city_store': {'weight': 10, 'score': 0, 'keywords': ['cidade', 'loja', 'unidade']},
            'communication': {'weight': 5, 'score': 0, 'keywords': ['posso ajudar', 'aguarde', 'momento']},
            'empathy': {'weight': 4, 'score': 0, 'keywords': ['entendo', 'compreendo', 'vamos resolver']},
            'closing': {'weight': 15, 'score': 0, 'keywords': ['protocolo', 'validade', 'franquia', 'link']},
            'satisfaction': {'weight': 6, 'score': 0, 'keywords': ['pesquisa', 'satisfação', 'avaliação']}
        }
        self.penalties = 0
        
    def evaluate(self, message: str, is_repetition: bool = False) -> Dict:
        """Avalia mensagem do agente"""
        message_lower = message.lower()
        results = {}
        
        # Penaliza repetições
        if is_repetition:
            self.criteria['listening']['score'] = max(0, self.criteria['listening']['score'] - 1)
            self.penalties += 5
        
        # Avalia cada critério
        for key, criterion in self.criteria.items():
            if key == 'listening':
                continue  # Já tratado acima
                
            found = [kw for kw in criterion['keywords'] if kw in message_lower]
            if found:
                # Pontuação parcial baseada na quantidade de keywords
                score_ratio = min(1.0, len(found) / max(1, len(criterion['keywords'])))
                earned = int(criterion['weight'] * score_ratio)
                criterion['score'] = max(criterion['score'], earned)
                results[key] = {'earned': earned, 'max': criterion['weight'], 'evidence': found}
        
        return results
    
    def get_total_score(self) -> Tuple[int, int]:
        """Retorna pontuação total"""
        total = sum(c['score'] for c in self.criteria.values()) - self.penalties
        max_score = sum(c['weight'] for c in self.criteria.values())
        return max(0, total), max_score
    
    def get_report(self) -> List[Dict]:
        """Gera relatório detalhado"""
        report = []
        for key, criterion in self.criteria.items():
            report.append({
                'name': key.replace('_', ' ').title(),
                'score': criterion['score'],
                'max': criterion['weight'],
                'percentage': (criterion['score'] / criterion['weight'] * 100) if criterion['weight'] > 0 else 0
            })
        return sorted(report, key=lambda x: x['percentage'])

# ==================== INTERFACE PRINCIPAL ====================

def init_session_state():
    """Inicializa estado da sessão"""
    if 'active' not in st.session_state:
        st.session_state.active = False
        st.session_state.messages = []
        st.session_state.customer = SmartVirtualCustomer()
        st.session_state.evaluator = IntelligentEvaluator()
        st.session_state.start_time = None
        st.session_state.message_count = 0

def main():
    init_session_state()
    
    # Header compacto
    st.markdown("""
    <div class="main-header">
        <h2>🎯 Voice Coach Pro - Carglass</h2>
        <p style="margin: 0;">Sistema Inteligente de Treinamento</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.active:
        # Tela inicial
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### 📋 Protocolo de Atendimento
            
            **Objetivo:** Seguir o checklist Carglass (81 pontos)
            
            **Principais Itens:**
            1. Saudação profissional com nome
            2. Coletar todos os dados (nome, CPF, 2 telefones, placa, endereço)
            3. Confirmar informações (ECO)
            4. Demonstrar empatia
            5. Script de encerramento completo
            
            **⚠️ Atenção:** O cliente ficará impaciente se você repetir perguntas!
            """)
            
            if st.button("🚀 Iniciar Simulação", type="primary", use_container_width=True):
                st.session_state.active = True
                st.session_state.start_time = time.time()
                st.session_state.messages = [("cliente", "Alô? Preciso de ajuda com meu carro!")]
                st.rerun()
    
    else:
        # Interface de simulação ativa
        # Layout em 3 colunas: chat (2/3) e controles (1/3)
        col_chat, col_controls = st.columns([2, 1])
        
        with col_chat:
            # Timer
            if st.session_state.start_time:
                elapsed = int(time.time() - st.session_state.start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60
                st.markdown(f'<div class="timer-display">⏱️ Tempo: {minutes:02d}:{seconds:02d}</div>', 
                          unsafe_allow_html=True)
            
            # Container de chat com altura fixa
            chat_html = '<div class="chat-container">'
            for speaker, message in st.session_state.messages:
                if speaker == "cliente":
                    chat_html += f'<div class="message customer-message">🔸 <strong>Cliente:</strong> {message}</div>'
                else:
                    chat_html += f'<div class="message agent-message"><strong>Você:</strong> {message} 🔹</div>'
            chat_html += '</div>'
            
            st.markdown(chat_html, unsafe_allow_html=True)
            
            # Área de input
            st.markdown('<div class="input-area">', unsafe_allow_html=True)
            
            user_input = st.text_area(
                "Sua resposta:",
                height=80,
                placeholder="Digite aqui sua resposta ao cliente...",
                key=f"input_{st.session_state.message_count}"
            )
            
            col_send, col_end = st.columns(2)
            with col_send:
                if st.button("📤 Enviar", type="primary", use_container_width=True, disabled=not user_input):
                    # Adiciona mensagem do agente
                    st.session_state.messages.append(("agente", user_input))
                    
                    # Verifica se é repetição
                    is_repetition = st.session_state.customer.memory.repetition_count > 0
                    
                    # Avalia
                    st.session_state.evaluator.evaluate(user_input, is_repetition)
                    
                    # Gera resposta do cliente
                    customer_response = st.session_state.customer.generate_response(user_input)
                    st.session_state.messages.append(("cliente", customer_response))
                    
                    st.session_state.message_count += 1
                    st.rerun()
            
            with col_end:
                if st.button("🏁 Finalizar", type="secondary", use_container_width=True):
                    st.session_state.active = False
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col_controls:
            # Métricas em tempo real
            st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
            st.markdown("### 📊 Métricas")
            
            total, max_score = st.session_state.evaluator.get_total_score()
            percentage = (total / max_score * 100) if max_score > 0 else 0
            
            # Indicador de performance
            if percentage >= 80:
                badge_class = "badge-success"
                status = "Excelente"
            elif percentage >= 60:
                badge_class = "badge-warning"
                status = "Bom"
            else:
                badge_class = "badge-danger"
                status = "Melhorar"
            
            st.markdown(f'<div class="metric-card">'
                       f'<strong>Pontuação</strong><br>'
                       f'{total}/{max_score} pontos<br>'
                       f'<span class="status-badge {badge_class}">{percentage:.0f}% - {status}</span>'
                       f'</div>', unsafe_allow_html=True)
            
            # Estado do cliente
            patience = st.session_state.customer.memory.patience_level
            if patience > 70:
                patience_status = "😊 Satisfeito"
                patience_color = "badge-success"
            elif patience > 40:
                patience_status = "😐 Neutro"
                patience_color = "badge-warning"
            else:
                patience_status = "😤 Impaciente"
                patience_color = "badge-danger"
            
            st.markdown(f'<div class="metric-card">'
                       f'<strong>Cliente</strong><br>'
                       f'<span class="status-badge {patience_color}">{patience_status}</span><br>'
                       f'Paciência: {patience}%'
                       f'</div>', unsafe_allow_html=True)
            
            # Dados coletados
            st.markdown("### 📋 Checklist")
            memory = st.session_state.customer.memory.provided_data
            
            checklist_items = [
                ('Nome', 'name' in memory),
                ('CPF', 'cpf' in memory),
                ('Telefone 1', 'phone1' in memory),
                ('Telefone 2', 'phone2' in memory),
                ('Placa', 'plate' in memory),
                ('Endereço', 'address' in memory),
                ('Problema', 'problem' in memory)
            ]
            
            for item, collected in checklist_items:
                icon = "✅" if collected else "⏳"
                st.write(f"{icon} {item}")
            
            # Avisos
            if st.session_state.customer.memory.repetition_count > 0:
                st.warning(f"⚠️ {st.session_state.customer.memory.repetition_count} repetições detectadas!")
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Relatório final (quando não está ativo mas tem mensagens)
    if not st.session_state.active and len(st.session_state.messages) > 0:
        st.markdown("---")
        st.markdown("## 📊 Relatório Final")
        
        total, max_score = st.session_state.evaluator.get_total_score()
        percentage = (total / max_score * 100) if max_score > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pontuação Final", f"{total}/{max_score}")
        with col2:
            st.metric("Percentual", f"{percentage:.1f}%")
        with col3:
            result = "✅ APROVADO" if percentage >= 80 else "⚠️ MELHORAR"
            st.metric("Resultado", result)
        with col4:
            if st.session_state.start_time:
                duration = int(time.time() - st.session_state.start_time)
                st.metric("Duração", f"{duration//60:02d}:{duration%60:02d}")
        
        # Detalhamento por critério
        with st.expander("📋 Detalhamento por Critério"):
            report = st.session_state.evaluator.get_report()
            for item in report:
                status = "✅" if item['percentage'] >= 80 else "⚠️" if item['percentage'] >= 50 else "❌"
                st.write(f"{status} **{item['name']}**: {item['score']}/{item['max']} ({item['percentage']:.0f}%)")
        
        # Feedback do cliente
        st.markdown("### 💬 Feedback do Cliente Virtual")
        patience = st.session_state.customer.memory.patience_level
        repetitions = st.session_state.customer.memory.repetition_count
        
        if repetitions > 2:
            st.error(f"❌ Cliente ficou frustrado com {repetitions} repetições desnecessárias")
        elif patience < 40:
            st.warning("⚠️ Cliente demonstrou impaciência durante o atendimento")
        elif percentage >= 80:
            st.success("✅ Cliente satisfeito com o atendimento!")
        
        # Reiniciar
        if st.button("🔄 Nova Simulação", type="primary", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
