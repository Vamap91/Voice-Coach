import os
import streamlit as st
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import random

# Configuração da página
st.set_page_config(
    page_title="Voice Coach Pro - Carglass", 
    page_icon="🎯", 
    layout="wide"
)

# CSS Melhorado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0052cc, #0066ff);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .chat-container {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        height: 500px;
        overflow-y: auto;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .customer-msg {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .agent-msg {
        background: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    
    .metrics-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    .score-display {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .score-good { background: #d4edda; color: #155724; }
    .score-medium { background: #fff3cd; color: #856404; }
    .score-bad { background: #f8d7da; color: #721c24; }
    
    .debug-box {
        background: #f0f0f0;
        padding: 1rem;
        border-radius: 8px;
        font-family: monospace;
        font-size: 0.85rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== MODELOS DE DADOS ====================

@dataclass
class CustomerProfile:
    """Perfil do cliente"""
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
    problem_cause: str = "pedra na estrada"
    has_special_features: str = "não"  # LED/Xenon, sensor de chuva, etc

@dataclass
class ConversationState:
    """Estado da conversa com memória contextual"""
    provided_info: Dict[str, any] = field(default_factory=lambda: {
        'greeting_received': False,
        'name': None,
        'cpf': None, 
        'phone1': None,
        'phone2': None,
        'plate': None,
        'address': None,
        'problem': None,
        'problem_details': None,
        'lgpd_authorized': False,
        'city_preference': None,
        'special_features_asked': False
    })
    
    questions_history: List[str] = field(default_factory=list)
    last_question_topic: str = ""
    repetitions: int = 0
    patience: int = 100
    conversation_stage: str = "initial"  # initial, data_collection, problem_diagnosis, closing
    
    def update_info(self, key: str, value: any):
        """Atualiza informação e rastreia o que foi fornecido"""
        self.provided_info[key] = value
    
    def was_already_asked(self, topic: str) -> bool:
        """Verifica se um tópico já foi perguntado"""
        return topic in self.questions_history
    
    def add_question(self, topic: str):
        """Adiciona pergunta ao histórico"""
        if topic not in self.questions_history:
            self.questions_history.append(topic)
        self.last_question_topic = topic

# ==================== SISTEMA DE AVALIAÇÃO INTELIGENTE ====================

class SmartEvaluationSystem:
    """Sistema de avaliação com pontuação corrigida e funcional"""
    
    def __init__(self):
        self.criteria = {
            'greeting': {
                'name': 'Saudação e identificação', 
                'weight': 10, 
                'current_score': 0, 
                'keywords': ['bom dia', 'boa tarde', 'boa noite', 'olá', 'carglass', 'meu nome é', 'me chamo'],
                'found_evidence': []
            },
            'data_collection': {
                'name': 'Coleta de dados completos', 
                'weight': 6, 
                'current_score': 0, 
                'required_items': ['nome', 'cpf', 'telefone', 'placa', 'endereço'],
                'items_requested': set(),
                'found_evidence': []
            },
            'lgpd': {
                'name': 'Script LGPD', 
                'weight': 2, 
                'current_score': 0, 
                'keywords': ['lgpd', 'lei geral', 'proteção de dados', 'proteção de dado', 'autoriza', 'compartilhar', 'compartilhamento'],
                'found_evidence': []
            },
            'confirmation': {
                'name': 'Confirmação verbal (ECO)', 
                'weight': 5, 
                'current_score': 0, 
                'keywords': ['confirmando', 'confere', 'correto', 'isso mesmo', 'está certo', 'repito'],
                'found_evidence': []
            },
            'listening': {
                'name': 'Escuta atenta', 
                'weight': 3, 
                'current_score': 3,  # Começa com pontos totais
                'found_evidence': []
            },
            'technical': {
                'name': 'Conhecimento técnico', 
                'weight': 5, 
                'current_score': 0, 
                'keywords': ['para-brisa', 'parabrisa', 'franquia', 'seguro', 'vistoria', 'sinistro', 'cobertura'],
                'found_evidence': []
            },
            'damage_info': {
                'name': 'Informações sobre o dano', 
                'weight': 10, 
                'current_score': 0, 
                'keywords': ['quando', 'como aconteceu', 'tamanho', 'onde', 'led', 'xenon', 'sensor', 'câmera', 'chuva'],
                'found_evidence': []
            },
            'location': {
                'name': 'Confirmação de cidade/loja', 
                'weight': 10, 
                'current_score': 0, 
                'keywords': ['cidade', 'loja', 'unidade', 'localização', 'onde realizar', 'agendar'],
                'found_evidence': []
            },
            'professional': {
                'name': 'Comunicação profissional', 
                'weight': 5, 
                'current_score': 0, 
                'keywords': ['posso ajudar', 'por favor', 'aguarde', 'momento', 'com prazer'],
                'found_evidence': []
            },
            'empathy': {
                'name': 'Empatia e acolhimento', 
                'weight': 4, 
                'current_score': 0, 
                'keywords': ['entendo', 'compreendo', 'vamos resolver', 'tranquilo', 'preocupação', 'pode ficar tranquilo'],
                'found_evidence': []
            },
            'closing': {
                'name': 'Script de encerramento', 
                'weight': 15, 
                'current_score': 0, 
                'keywords': ['protocolo', 'prazo', 'validade', 'franquia', 'link', 'acompanhamento', 'documento', 'levar'],
                'found_evidence': []
            },
            'satisfaction': {
                'name': 'Pesquisa de satisfação', 
                'weight': 6, 
                'current_score': 0, 
                'keywords': ['pesquisa', 'satisfação', 'avaliação', 'feedback', 'opinião'],
                'found_evidence': []
            }
        }
        
        self.total_messages_evaluated = 0
        self.debug_log = []
        
    def evaluate_message(self, message: str) -> Dict:
        """Avalia mensagem e adiciona pontos de forma correta"""
        message_lower = message.lower()
        self.total_messages_evaluated += 1
        results = {}
        
        for key, criterion in self.criteria.items():
            if key == 'listening':
                continue  # Tratado separadamente
            
            if key == 'data_collection':
                # Tratamento especial para coleta de dados
                for item in criterion['required_items']:
                    if item in message_lower:
                        criterion['items_requested'].add(item)
                
                # Calcula pontos baseado em quantos itens foram solicitados
                items_count = len(criterion['items_requested'])
                if items_count > 0:
                    new_score = (items_count / len(criterion['required_items'])) * criterion['weight']
                    if new_score > criterion['current_score']:
                        self.debug_log.append(f"Coleta de Dados: {items_count}/5 itens = {new_score:.1f} pts")
                        criterion['current_score'] = new_score
                        criterion['found_evidence'] = list(criterion['items_requested'])
            
            else:
                # Para outros critérios
                found_keywords = [kw for kw in criterion.get('keywords', []) if kw in message_lower]
                
                if found_keywords:
                    # Adiciona evidências sem duplicar
                    for kw in found_keywords:
                        if kw not in criterion['found_evidence']:
                            criterion['found_evidence'].append(kw)
                    
                    # Calcula pontos (máximo de 1 ponto por mensagem, acumulativo)
                    points_to_add = min(2.0, len(found_keywords) * 0.5)
                    new_score = min(criterion['weight'], criterion['current_score'] + points_to_add)
                    
                    if new_score > criterion['current_score']:
                        self.debug_log.append(f"{criterion['name']}: +{new_score - criterion['current_score']:.1f} pts (encontrado: {', '.join(found_keywords)})")
                        criterion['current_score'] = new_score
        
        return results
    
    def penalize_repetition(self):
        """Aplica penalização por repetição"""
        self.criteria['listening']['current_score'] = max(0, self.criteria['listening']['current_score'] - 1)
        self.debug_log.append("PENALIZAÇÃO: -1 pt em Escuta Atenta (repetição)")
    
    def get_total_score(self) -> Tuple[int, int]:
        """Retorna pontuação total atual"""
        total = sum(c['current_score'] for c in self.criteria.values())
        max_score = sum(c['weight'] for c in self.criteria.values())
        return int(total), max_score
    
    def get_detailed_report(self) -> List[Dict]:
        """Retorna relatório detalhado com evidências"""
        report = []
        for key, criterion in self.criteria.items():
            percentage = (criterion['current_score'] / criterion['weight'] * 100) if criterion['weight'] > 0 else 0
            report.append({
                'name': criterion['name'],
                'score': criterion['current_score'],
                'max': criterion['weight'],
                'percentage': percentage,
                'evidence': criterion['found_evidence']
            })
        return sorted(report, key=lambda x: x['percentage'], reverse=True)

# ==================== CLIENTE VIRTUAL INTELIGENTE ====================

class IntelligentVirtualCustomer:
    """Cliente com comportamento mais natural e contextual"""
    
    def __init__(self):
        self.profile = CustomerProfile()
        self.state = ConversationState()
        self.emotional_responses = {
            'patient': [
                "Claro, sem problemas.",
                "Sim, posso informar.",
                "Certo, vou passar a informação."
            ],
            'slightly_impatient': [
                "Ok, mas vamos agilizar?",
                "Certo, mas estou com pressa.",
                "Tá bom, mas preciso resolver isso logo."
            ],
            'impatient': [
                "Olha, já falei isso antes...",
                "Vocês não anotaram?",
                "Preciso repetir de novo?"
            ],
            'frustrated': [
                "Já informei isso várias vezes!",
                "Vocês precisam prestar mais atenção!",
                "Estou perdendo a paciência aqui!"
            ]
        }
    
    def get_emotional_state(self) -> str:
        """Determina estado emocional baseado na paciência"""
        if self.state.patience > 70:
            return 'patient'
        elif self.state.patience > 50:
            return 'slightly_impatient'
        elif self.state.patience > 30:
            return 'impatient'
        else:
            return 'frustrated'
    
    def generate_contextual_response(self, agent_message: str) -> str:
        """Gera resposta contextual e inteligente"""
        msg_lower = agent_message.lower()
        
        # Atualiza o estágio da conversa
        if any(word in msg_lower for word in ['bom dia', 'boa tarde', 'boa noite', 'olá']):
            self.state.conversation_stage = "data_collection"
            self.state.update_info('greeting_received', True)
            return f"Olá! Meu seguro é {self.profile.insurance} e tenho um problema no vidro do meu carro. Preciso resolver isso com urgência!"
        
        # COLETA DE DADOS
        if 'nome' in msg_lower and 'seu' in msg_lower:
            if self.state.provided_info['name']:
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Já informei meu nome: {self.profile.name}. Por favor, anotem as informações!"
            else:
                self.state.update_info('name', self.profile.name)
                return f"Meu nome é {self.profile.name}."
        
        if 'cpf' in msg_lower:
            if self.state.provided_info['cpf']:
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Meu CPF é {self.profile.cpf}, como já disse anteriormente."
            else:
                self.state.update_info('cpf', self.profile.cpf)
                return f"Meu CPF é {self.profile.cpf}."
        
        if 'telefone' in msg_lower or 'contato' in msg_lower:
            # Verifica se está pedindo o segundo telefone
            if 'outro' in msg_lower or 'segundo' in msg_lower or 'adicional' in msg_lower:
                if self.state.provided_info['phone2']:
                    self.state.patience -= 15
                    return "Já passei os dois telefones!"
                else:
                    self.state.update_info('phone2', self.profile.phone2)
                    return f"O segundo telefone é {self.profile.phone2}."
            else:
                # Primeira menção a telefone
                if not self.state.provided_info['phone1']:
                    self.state.update_info('phone1', self.profile.phone1)
                    return f"Meu telefone principal é {self.profile.phone1}."
                elif not self.state.provided_info['phone2']:
                    # Se já deu o primeiro mas não o segundo
                    self.state.update_info('phone2', self.profile.phone2)
                    return f"Tenho também o {self.profile.phone2} como segundo telefone."
                else:
                    self.state.patience -= 20
                    return f"Já informei os dois telefones: {self.profile.phone1} e {self.profile.phone2}!"
        
        if 'placa' in msg_lower or 'veículo' in msg_lower:
            if self.state.provided_info['plate']:
                self.state.repetitions += 1
                self.state.patience -= 25
                emotion = random.choice(self.emotional_responses['impatient'])
                return f"{emotion} Placa {self.profile.plate}, é um {self.profile.car}."
            else:
                self.state.update_info('plate', self.profile.plate)
                return f"Placa {self.profile.plate}, é um {self.profile.car}."
        
        if 'endereço' in msg_lower or 'cep' in msg_lower:
            if self.state.provided_info['address']:
                self.state.patience -= 20
                return "Já passei meu endereço completo anteriormente."
            else:
                self.state.update_info('address', self.profile.address)
                return f"Meu endereço é {self.profile.address}."
        
        # LGPD
        if 'lgpd' in msg_lower or 'lei geral' in msg_lower or 'proteção de dado' in msg_lower:
            if not self.state.provided_info['lgpd_authorized']:
                self.state.update_info('lgpd_authorized', True)
                return "Sim, autorizo o compartilhamento dos dados para o atendimento."
            else:
                return "Já autorizei o uso dos dados."
        
        # INFORMAÇÕES DO PROBLEMA
        if 'problema' in msg_lower or 'aconteceu' in msg_lower or 'ocorreu' in msg_lower:
            if not self.state.provided_info['problem']:
                self.state.update_info('problem', True)
                self.state.conversation_stage = "problem_diagnosis"
                return f"Tenho uma {self.profile.problem}. Aconteceu {self.profile.problem_date} na estrada."
            else:
                return f"Como já disse, é uma trinca no para-brisa de 15cm."
        
        if 'quando' in msg_lower and 'aconteceu' in msg_lower:
            return f"Aconteceu {self.profile.problem_date} quando estava na estrada."
        
        if any(word in msg_lower for word in ['led', 'xenon', 'sensor', 'câmera', 'chuva', 'especial']):
            if not self.state.provided_info['special_features_asked']:
                self.state.update_info('special_features_asked', True)
                return "O veículo possui sensor de chuva, câmera ou iluminação LED/Xenon no vidro?"
            else:
                return "Não, o veículo não tem esses acessórios especiais no vidro."
        
        if 'tamanho' in msg_lower or 'grande' in msg_lower:
            return "A trinca tem aproximadamente 15cm, está bem visível."
        
        # LOCALIZAÇÃO E AGENDAMENTO
        if 'cidade' in msg_lower or 'loja' in msg_lower or 'onde' in msg_lower:
            if not self.state.provided_info['city_preference']:
                self.state.update_info('city_preference', 'São Paulo')
                return "Prefiro fazer em São Paulo, na loja mais próxima da Vila Olímpia."
            else:
                return "Como disse, prefiro a loja da Vila Olímpia em São Paulo."
        
        # CONFIRMAÇÕES
        if any(word in msg_lower for word in ['confirma', 'correto', 'isso mesmo', 'confere', 'certo']):
            emotional_state = self.get_emotional_state()
            if emotional_state == 'patient':
                return "Sim, está correto."
            elif emotional_state == 'slightly_impatient':
                return "Isso mesmo, podemos prosseguir?"
            else:
                return "Sim, sim, está certo. Vamos agilizar?"
        
        # ENCERRAMENTO
        if any(word in msg_lower for word in ['protocolo', 'validade', 'prazo', 'documento']):
            self.state.conversation_stage = "closing"
            return "Ok, anotei as informações. Preciso levar algum documento específico?"
        
        if 'pesquisa' in msg_lower or 'satisfação' in msg_lower:
            return "Sim, responderei a pesquisa de satisfação."
        
        if any(word in msg_lower for word in ['obrigado', 'agradeço', 'bom dia', 'boa tarde']):
            return "Obrigado pelo atendimento. Até logo!"
        
        # RESPOSTA PADRÃO CONTEXTUAL
        emotional_state = self.get_emotional_state()
        if self.state.conversation_stage == "problem_diagnosis":
            return "Então, como vai funcionar o reparo? Qual o prazo?"
        elif emotional_state == 'frustrated':
            return random.choice(self.emotional_responses['frustrated'])
        elif emotional_state == 'impatient':
            return random.choice(self.emotional_responses['impatient'])
        else:
            return "Certo, qual a próxima informação que precisa?"

# ==================== INTERFACE PRINCIPAL ====================

def init_session():
    """Inicializa sessão"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.customer = IntelligentVirtualCustomer()
        st.session_state.evaluator = SmartEvaluationSystem()
        st.session_state.start_time = None
        st.session_state.active = False

def main():
    init_session()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Voice Coach Pro - Carglass</h1>
        <p>Sistema Inteligente de Treinamento com IA Contextual</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Layout principal
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        if not st.session_state.active:
            # Tela inicial
            st.info("""
            ### 📋 Protocolo Carglass - Checklist Completo
            
            **1. Abertura (10 pts)**
            - Saudação + Carglass + seu nome
            
            **2. Coleta de Dados (6 pts)**
            - Nome, CPF, 2 telefones, placa, endereço
            
            **3. LGPD (2 pts)**
            - Informar sobre proteção de dados
            
            **4. Confirmação ECO (5 pts)**
            - Repetir e confirmar dados
            
            **5. Diagnóstico (10 pts)**
            - Quando, como, tamanho, LED/Xenon
            
            **6. Encerramento (15 pts)**
            - Protocolo, prazo, franquia, documentos
            """)
            
            if st.button("🚀 Iniciar Simulação", type="primary", use_container_width=True):
                st.session_state.active = True
                st.session_state.start_time = time.time()
                st.session_state.messages = [
                    ("cliente", "Alô? Preciso falar com a Carglass sobre um problema no meu carro!")
                ]
                st.rerun()
        
        else:
            # Timer
            elapsed = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0
            st.markdown(f"### ⏱️ Tempo: {elapsed//60:02d}:{elapsed%60:02d}")
            
            # Chat
            chat_html = '<div class="chat-container">'
            for speaker, msg in st.session_state.messages:
                if speaker == "cliente":
                    chat_html += f'<div class="customer-msg">🔸 <strong>Cliente:</strong> {msg}</div>'
                else:
                    chat_html += f'<div class="agent-msg">🔹 <strong>Você:</strong> {msg}</div>'
            chat_html += '</div>'
            st.markdown(chat_html, unsafe_allow_html=True)
            
            # Input
            user_input = st.text_area("Sua resposta:", height=100, placeholder="Ex: Bom dia! Carglass, meu nome é...", key="agent_input")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Enviar", type="primary", use_container_width=True):
                    if user_input:
                        # Adiciona mensagem do agente
                        st.session_state.messages.append(("agente", user_input))
                        
                        # AVALIAÇÃO - IMPORTANTE: Avalia ANTES da resposta do cliente
                        st.session_state.evaluator.evaluate_message(user_input)
                        
                        # Verifica se houve repetição
                        old_repetitions = st.session_state.customer.state.repetitions
                        
                        # Gera resposta do cliente
                        customer_response = st.session_state.customer.generate_contextual_response(user_input)
                        st.session_state.messages.append(("cliente", customer_response))
                        
                        # Se aumentou repetições, penaliza
                        if st.session_state.customer.state.repetitions > old_repetitions:
                            st.session_state.evaluator.penalize_repetition()
                        
                        st.rerun()
            
            with col2:
                if st.button("🏁 Finalizar", use_container_width=True):
                    st.session_state.active = False
                    st.rerun()
    
    with col_right:
        # Métricas
        st.markdown("### 📊 Métricas")
        
        total, max_score = st.session_state.evaluator.get_total_score()
        percentage = (total / max_score * 100) if max_score > 0 else 0
        
        # Score visual
        if percentage >= 80:
            score_class = "score-good"
            status = "✅ Excelente"
        elif percentage >= 60:
            score_class = "score-medium"
            status = "⚠️ Bom"
        else:
            score_class = "score-bad"
            status = "❌ Melhorar"
        
        st.markdown(f'<div class="score-display {score_class}">{total}/{max_score}<br>{percentage:.1f}%<br>{status}</div>', 
                   unsafe_allow_html=True)
        
        # Cliente
        st.markdown("### 😊 Cliente")
        patience = st.session_state.customer.state.patience
        if patience > 70:
            st.success(f"Satisfeito ({patience}%)")
        elif patience > 40:
            st.warning(f"Impaciente ({patience}%)")
        else:
            st.error(f"Frustrado ({patience}%)")
        
        if st.session_state.customer.state.repetitions > 0:
            st.error(f"⚠️ {st.session_state.customer.state.repetitions} repetições!")
        
        # Checklist
        st.markdown("### 📋 Dados Coletados")
        info = st.session_state.customer.state.provided_info
        checklist = [
            ('Nome', info['name'] is not None),
            ('CPF', info['cpf'] is not None),
            ('Telefone 1', info['phone1'] is not None),
            ('Telefone 2', info['phone2'] is not None),
            ('Placa', info['plate'] is not None),
            ('Endereço', info['address'] is not None),
            ('Problema', info['problem'] is not None),
            ('LGPD', info['lgpd_authorized']),
            ('LED/Xenon', info['special_features_asked'])
        ]
        
        for item, done in checklist:
            st.write(f"{'✅' if done else '⏳'} {item}")
        
        # Debug
        with st.expander("🔍 Debug Pontuação"):
            for log in st.session_state.evaluator.debug_log[-10:]:
                st.code(log)
    
    # Relatório final
    if not st.session_state.active and len(st.session_state.messages) > 1:
        st.markdown("---")
        st.markdown("## 📊 Relatório Final")
        
        total, max_score = st.session_state.evaluator.get_total_score()
        percentage = (total / max_score * 100) if max_score > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pontuação", f"{total}/{max_score}")
        with col2:
            st.metric("Percentual", f"{percentage:.1f}%")
        with col3:
            st.metric("Resultado", "✅ APROVADO" if percentage >= 80 else "⚠️ MELHORAR")
        
        # Detalhamento
        st.markdown("### 📋 Análise Detalhada")
        for item in st.session_state.evaluator.get_detailed_report():
            st.progress(item['percentage'] / 100)
            status_icon = "✅" if item['percentage'] >= 80 else "⚠️" if item['percentage'] >= 50 else "❌"
            st.write(f"{status_icon} **{item['name']}**: {item['score']:.1f}/{item['max']} ({item['percentage']:.0f}%)")
            if item['evidence']:
                st.write(f"   Evidências encontradas: {', '.join(item['evidence'])}")
        
        # Feedback do cliente
        st.markdown("### 💬 Feedback do Cliente")
        patience = st.session_state.customer.state.patience
        repetitions = st.session_state.customer.state.repetitions
        
        if repetitions > 2:
            st.error(f"Cliente frustrado com {repetitions} repetições desnecessárias")
        elif patience < 40:
            st.warning("Cliente demonstrou impaciência durante o atendimento")
        elif percentage >= 80:
            st.success("Cliente satisfeito com o atendimento!")
        else:
            st.info("Cliente neutro - atendimento pode melhorar")
        
        # Reset
        if st.button("🔄 Nova Simulação", type="primary", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
