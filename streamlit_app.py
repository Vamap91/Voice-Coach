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

@dataclass
class ConversationState:
    """Estado da conversa com memória contextual"""
    provided_info: Dict[str, any] = field(default_factory=lambda: {
        'name': None,
        'cpf': None, 
        'phone1': None,
        'phone2': None,
        'plate': None,
        'address': None,
        'problem': None,
        'lgpd': False,
        'special_features': False
    })
    
    repetitions: int = 0
    patience: int = 100
    
    def update_info(self, key: str, value: any):
        """Atualiza informação"""
        if key in self.provided_info:
            self.provided_info[key] = value

# ==================== SISTEMA DE AVALIAÇÃO ====================

class SmartEvaluationSystem:
    """Sistema de avaliação corrigido"""
    
    def __init__(self):
        self.criteria = {
            'greeting': {
                'name': 'Saudação e identificação', 
                'weight': 10, 
                'score': 0, 
                'keywords': ['bom dia', 'boa tarde', 'boa noite', 'carglass', 'meu nome'],
                'evidence': []
            },
            'data_collection': {
                'name': 'Coleta de dados', 
                'weight': 6, 
                'score': 0,
                'items_collected': set(),
                'evidence': []
            },
            'lgpd': {
                'name': 'LGPD', 
                'weight': 2, 
                'score': 0, 
                'keywords': ['lgpd', 'lei geral', 'proteção de dados', 'autoriza'],
                'evidence': []
            },
            'confirmation': {
                'name': 'Confirmação ECO', 
                'weight': 5, 
                'score': 0, 
                'keywords': ['confirmando', 'correto', 'isso mesmo'],
                'evidence': []
            },
            'listening': {
                'name': 'Escuta atenta', 
                'weight': 3, 
                'score': 3,
                'evidence': []
            },
            'technical': {
                'name': 'Conhecimento técnico', 
                'weight': 5, 
                'score': 0, 
                'keywords': ['para-brisa', 'franquia', 'seguro', 'vistoria'],
                'evidence': []
            },
            'damage_info': {
                'name': 'Info do dano', 
                'weight': 10, 
                'score': 0, 
                'keywords': ['quando', 'como', 'tamanho', 'led', 'xenon'],
                'evidence': []
            },
            'location': {
                'name': 'Cidade/Loja', 
                'weight': 10, 
                'score': 0, 
                'keywords': ['cidade', 'loja', 'unidade'],
                'evidence': []
            },
            'professional': {
                'name': 'Comunicação', 
                'weight': 5, 
                'score': 0, 
                'keywords': ['posso ajudar', 'por favor', 'aguarde'],
                'evidence': []
            },
            'empathy': {
                'name': 'Empatia', 
                'weight': 4, 
                'score': 0, 
                'keywords': ['entendo', 'compreendo', 'vamos resolver'],
                'evidence': []
            },
            'closing': {
                'name': 'Encerramento', 
                'weight': 15, 
                'score': 0, 
                'keywords': ['protocolo', 'prazo', 'validade', 'franquia', 'link'],
                'evidence': []
            },
            'satisfaction': {
                'name': 'Pesquisa', 
                'weight': 6, 
                'score': 0, 
                'keywords': ['pesquisa', 'satisfação', 'avaliação'],
                'evidence': []
            }
        }
        self.debug_log = []
        
    def evaluate_message(self, message: str) -> None:
        """Avalia mensagem"""
        msg_lower = message.lower()
        
        # Coleta de dados especial
        data_items = ['nome', 'cpf', 'telefone', 'placa', 'endereço']
        for item in data_items:
            if item in msg_lower:
                self.criteria['data_collection']['items_collected'].add(item)
        
        items_count = len(self.criteria['data_collection']['items_collected'])
        if items_count > 0:
            new_score = (items_count / 5) * self.criteria['data_collection']['weight']
            self.criteria['data_collection']['score'] = new_score
            self.debug_log.append(f"Coleta: {items_count}/5 = {new_score:.1f}pts")
        
        # Outros critérios
        for key, crit in self.criteria.items():
            if key in ['data_collection', 'listening']:
                continue
                
            found = [kw for kw in crit.get('keywords', []) if kw in msg_lower]
            if found:
                for kw in found:
                    if kw not in crit['evidence']:
                        crit['evidence'].append(kw)
                
                pts = min(2.0, len(found) * 0.5)
                new_score = min(crit['weight'], crit['score'] + pts)
                if new_score > crit['score']:
                    self.debug_log.append(f"{crit['name']}: +{new_score - crit['score']:.1f}")
                    crit['score'] = new_score
    
    def penalize_repetition(self):
        """Penaliza repetições"""
        self.criteria['listening']['score'] = max(0, self.criteria['listening']['score'] - 1)
        self.debug_log.append("Penalização: -1pt")
    
    def get_total_score(self) -> Tuple[int, int]:
        """Pontuação total"""
        total = sum(c['score'] for c in self.criteria.values())
        max_score = sum(c['weight'] for c in self.criteria.values())
        return int(total), max_score
    
    def get_report(self) -> List[Dict]:
        """Relatório detalhado"""
        report = []
        for key, crit in self.criteria.items():
            pct = (crit['score'] / crit['weight'] * 100) if crit['weight'] > 0 else 0
            report.append({
                'name': crit['name'],
                'score': crit['score'],
                'max': crit['weight'],
                'percentage': pct,
                'evidence': crit.get('evidence', [])
            })
        return sorted(report, key=lambda x: x['percentage'], reverse=True)

# ==================== CLIENTE VIRTUAL ====================

class VirtualCustomer:
    """Cliente inteligente"""
    
    def __init__(self):
        self.profile = CustomerProfile()
        self.state = ConversationState()
    
    def respond(self, agent_msg: str) -> str:
        """Gera resposta contextual"""
        msg = agent_msg.lower()
        
        # Saudação
        if any(w in msg for w in ['bom dia', 'boa tarde', 'boa noite']):
            return f"Olá! Meu seguro é {self.profile.insurance} e tenho problema no vidro."
        
        # Nome
        if 'nome' in msg:
            if self.state.provided_info['name']:
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Já falei, é {self.profile.name}."
            self.state.update_info('name', self.profile.name)
            return f"Meu nome é {self.profile.name}."
        
        # CPF
        if 'cpf' in msg:
            if self.state.provided_info['cpf']:
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"CPF {self.profile.cpf}, já informei."
            self.state.update_info('cpf', self.profile.cpf)
            return f"Meu CPF é {self.profile.cpf}."
        
        # Telefones
        if 'telefone' in msg:
            if 'segundo' in msg or 'outro' in msg:
                if self.state.provided_info['phone2']:
                    return "Já passei os dois telefones!"
                self.state.update_info('phone2', self.profile.phone2)
                return f"Segundo telefone: {self.profile.phone2}."
            else:
                if not self.state.provided_info['phone1']:
                    self.state.update_info('phone1', self.profile.phone1)
                    return f"Telefone: {self.profile.phone1}."
                elif not self.state.provided_info['phone2']:
                    self.state.update_info('phone2', self.profile.phone2)
                    return f"Outro telefone: {self.profile.phone2}."
                else:
                    return f"Já informei: {self.profile.phone1} e {self.profile.phone2}!"
        
        # Placa
        if 'placa' in msg or 'veículo' in msg:
            if self.state.provided_info['plate']:
                self.state.repetitions += 1
                self.state.patience -= 25
                return f"Já falei! Placa {self.profile.plate}, {self.profile.car}."
            self.state.update_info('plate', self.profile.plate)
            return f"Placa {self.profile.plate}, é um {self.profile.car}."
        
        # Endereço
        if 'endereço' in msg or 'cep' in msg:
            if self.state.provided_info['address']:
                return "Já passei o endereço."
            self.state.update_info('address', self.profile.address)
            return f"Endereço: {self.profile.address}."
        
        # LGPD
        if 'lgpd' in msg or 'proteção' in msg:
            self.state.update_info('lgpd', True)
            return "Sim, autorizo o compartilhamento dos dados."
        
        # Problema
        if 'problema' in msg or 'aconteceu' in msg:
            if self.state.provided_info['problem']:
                return "Já expliquei, trinca no para-brisa."
            self.state.update_info('problem', True)
            return f"Tenho uma {self.profile.problem}. Foi ontem na estrada."
        
        # LED/Xenon
        if any(w in msg for w in ['led', 'xenon', 'sensor', 'câmera']):
            self.state.update_info('special_features', True)
            return "Não, o veículo não tem LED/Xenon ou sensor no vidro."
        
        # Tamanho
        if 'tamanho' in msg:
            return "A trinca tem uns 15cm."
        
        # Cidade
        if 'cidade' in msg or 'loja' in msg:
            return "Prefiro fazer em São Paulo, Vila Olímpia."
        
        # Confirmações
        if any(w in msg for w in ['confirma', 'correto', 'isso mesmo']):
            if self.state.patience > 50:
                return "Sim, está correto."
            return "Isso mesmo, podemos agilizar?"
        
        # Encerramento
        if 'obrigado' in msg or 'agradeço' in msg:
            return "Obrigado pelo atendimento!"
        
        # Default
        if self.state.patience < 30:
            return "Estou com pressa, podemos agilizar?"
        return "Certo, o que mais precisa?"

# ==================== INTERFACE ====================

def init_session():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.customer = VirtualCustomer()
        st.session_state.evaluator = SmartEvaluationSystem()
        st.session_state.start_time = None
        st.session_state.active = False

def main():
    init_session()
    
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Voice Coach Pro - Carglass</h1>
        <p>Sistema de Treinamento Inteligente</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        if not st.session_state.active:
            st.info("### 📋 Siga o protocolo Carglass completo para máxima pontuação")
            if st.button("🚀 Iniciar", type="primary", use_container_width=True):
                st.session_state.active = True
                st.session_state.start_time = time.time()
                st.session_state.messages = [("cliente", "Alô? Preciso falar com a Carglass!")]
                st.rerun()
        else:
            # Timer
            elapsed = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0
            st.markdown(f"### ⏱️ {elapsed//60:02d}:{elapsed%60:02d}")
            
            # Chat
            chat_html = '<div class="chat-container">'
            for speaker, msg in st.session_state.messages:
                css_class = "customer-msg" if speaker == "cliente" else "agent-msg"
                icon = "🔸" if speaker == "cliente" else "🔹"
                chat_html += f'<div class="{css_class}">{icon} <b>{speaker.title()}:</b> {msg}</div>'
            chat_html += '</div>'
            st.markdown(chat_html, unsafe_allow_html=True)
            
            # Input
            user_input = st.text_area("Sua resposta:", height=80, key="input")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Enviar", type="primary", use_container_width=True):
                    if user_input:
                        st.session_state.messages.append(("agente", user_input))
                        st.session_state.evaluator.evaluate_message(user_input)
                        
                        old_reps = st.session_state.customer.state.repetitions
                        response = st.session_state.customer.respond(user_input)
                        st.session_state.messages.append(("cliente", response))
                        
                        if st.session_state.customer.state.repetitions > old_reps:
                            st.session_state.evaluator.penalize_repetition()
                        
                        st.rerun()
            
            with col2:
                if st.button("🏁 Finalizar", use_container_width=True):
                    st.session_state.active = False
                    st.rerun()
    
    with col_right:
        st.markdown("### 📊 Métricas")
        
        total, max_score = st.session_state.evaluator.get_total_score()
        pct = (total / max_score * 100) if max_score > 0 else 0
        
        score_class = "score-good" if pct >= 80 else "score-medium" if pct >= 60 else "score-bad"
        status = "✅" if pct >= 80 else "⚠️" if pct >= 60 else "❌"
        
        st.markdown(f'<div class="score-display {score_class}">{total}/{max_score}<br>{pct:.1f}%<br>{status}</div>', 
                   unsafe_allow_html=True)
        
        # Cliente
        patience = st.session_state.customer.state.patience
        if patience > 70:
            st.success(f"😊 Satisfeito ({patience}%)")
        elif patience > 40:
            st.warning(f"😐 Impaciente ({patience}%)")
        else:
            st.error(f"😤 Frustrado ({patience}%)")
        
        # Checklist
        st.markdown("### 📋 Checklist")
        info = st.session_state.customer.state.provided_info
        for key, value in info.items():
            done = value is not None and value != False
            st.write(f"{'✅' if done else '⏳'} {key.replace('_', ' ').title()}")
        
        # Debug
        with st.expander("Debug"):
            for log in st.session_state.evaluator.debug_log[-5:]:
                st.code(log)
    
    # Relatório final
    if not st.session_state.active and len(st.session_state.messages) > 1:
        st.markdown("---")
        st.markdown("## Relatório Final")
        
        total, max_score = st.session_state.evaluator.get_total_score()
        pct = (total / max_score * 100) if max_score > 0 else 0
        
        st.metric("Resultado", f"{total}/{max_score} ({pct:.1f}%)")
        
        for item in st.session_state.evaluator.get_report():
            st.write(f"**{item['name']}**: {item['score']:.1f}/{item['max']}")
        
        if st.button("🔄 Nova Simulação", type="primary"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
