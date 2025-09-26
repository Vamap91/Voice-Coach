import os
import streamlit as st
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json

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

# ==================== CONFIGURAÇÃO GPT ====================

def get_openai_client():
    """Retorna cliente OpenAI configurado"""
    try:
        # Tenta pegar do secrets do Streamlit primeiro
        api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        if api_key:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
    except:
        pass
    return None

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
    """Estado da conversa"""
    provided_info: Dict[str, bool] = field(default_factory=lambda: {
        'name': False,
        'cpf': False, 
        'phone1': False,
        'phone2': False,
        'plate': False,
        'address': False,
        'problem': False
    })
    
    questions_asked: List[str] = field(default_factory=list)
    repetitions: int = 0
    patience: int = 100
    
    def mark_provided(self, key: str):
        if key in self.provided_info:
            self.provided_info[key] = True
    
    def check_if_already_provided(self, key: str) -> bool:
        return self.provided_info.get(key, False)

# ==================== SISTEMA DE AVALIAÇÃO CORRIGIDO ====================

class EvaluationSystem:
    """Sistema de avaliação com pontuação real funcionando"""
    
    def __init__(self):
        self.criteria = {
            'greeting': {'name': 'Saudação', 'weight': 10, 'score': 0, 'checks': ['bom dia', 'boa tarde', 'boa noite', 'olá', 'carglass', 'meu nome']},
            'data_collection': {'name': 'Coleta de Dados', 'weight': 6, 'score': 0, 'checks': ['nome', 'cpf', 'telefone', 'placa', 'endereço', 'cep']},
            'lgpd': {'name': 'LGPD', 'weight': 2, 'score': 0, 'checks': ['lgpd', 'lei geral', 'proteção de dados', 'autoriza', 'compartilhar']},
            'confirmation': {'name': 'Confirmação ECO', 'weight': 5, 'score': 0, 'checks': ['confirma', 'correto', 'isso mesmo', 'confere', 'certo']},
            'listening': {'name': 'Escuta Atenta', 'weight': 3, 'score': 3, 'checks': []},  # Começa com pontos
            'technical': {'name': 'Conhecimento Técnico', 'weight': 5, 'score': 0, 'checks': ['para-brisa', 'parabrisa', 'franquia', 'seguro', 'vistoria', 'sinistro']},
            'damage': {'name': 'Informações do Dano', 'weight': 10, 'score': 0, 'checks': ['quando', 'como', 'tamanho', 'onde', 'aconteceu', 'ocorreu']},
            'location': {'name': 'Cidade/Loja', 'weight': 10, 'score': 0, 'checks': ['cidade', 'loja', 'unidade', 'localização', 'endereço para']},
            'professional': {'name': 'Comunicação Profissional', 'weight': 5, 'score': 0, 'checks': ['posso ajudar', 'por favor', 'aguarde', 'momento']},
            'empathy': {'name': 'Empatia', 'weight': 4, 'score': 0, 'checks': ['entendo', 'compreendo', 'vamos resolver', 'tranquilo', 'preocupação']},
            'closing': {'name': 'Encerramento', 'weight': 15, 'score': 0, 'checks': ['protocolo', 'prazo', 'validade', 'franquia', 'link', 'acompanhamento']},
            'satisfaction': {'name': 'Pesquisa', 'weight': 6, 'score': 0, 'checks': ['pesquisa', 'satisfação', 'avaliação', 'feedback']}
        }
        
        self.all_messages = []  # Guarda TODAS as mensagens para avaliação completa
        self.debug_log = []  # Log de debug
        
    def evaluate_message(self, message: str, is_agent: bool = True) -> Dict:
        """Avalia uma mensagem e ACUMULA pontos"""
        if not is_agent:
            return {}
            
        message_lower = message.lower()
        self.all_messages.append(message)
        
        results = {}
        
        for key, criterion in self.criteria.items():
            if key == 'listening':
                continue  # Tratado separadamente
                
            # Conta quantas keywords foram encontradas
            found = [check for check in criterion['checks'] if check in message_lower]
            
            if found:
                # Calcula pontos proporcionalmente
                points_earned = len(found) * (criterion['weight'] / max(3, len(criterion['checks'])))
                points_earned = min(points_earned, criterion['weight'])  # Não exceder o máximo
                
                # ACUMULA pontos (não substitui!)
                old_score = criterion['score']
                criterion['score'] = min(criterion['weight'], criterion['score'] + points_earned)
                
                self.debug_log.append(f"{key}: {old_score:.1f} -> {criterion['score']:.1f} (+{points_earned:.1f})")
                
                results[key] = {
                    'found': found,
                    'points': criterion['score'],
                    'max': criterion['weight']
                }
        
        return results
    
    def penalize_repetition(self):
        """Penaliza por repetição"""
        self.criteria['listening']['score'] = max(0, self.criteria['listening']['score'] - 1)
        self.debug_log.append("Penalização por repetição: -1 em Escuta Atenta")
    
    def get_total_score(self) -> Tuple[int, int]:
        """Retorna pontuação total REAL"""
        total = sum(c['score'] for c in self.criteria.values())
        max_score = sum(c['weight'] for c in self.criteria.values())
        return int(total), max_score
    
    def get_detailed_scores(self) -> List[Dict]:
        """Retorna breakdown detalhado"""
        detailed = []
        for key, criterion in self.criteria.items():
            percentage = (criterion['score'] / criterion['weight'] * 100) if criterion['weight'] > 0 else 0
            detailed.append({
                'name': criterion['name'],
                'score': criterion['score'],
                'max': criterion['weight'],
                'percentage': percentage
            })
        return sorted(detailed, key=lambda x: x['percentage'], reverse=True)

# ==================== CLIENTE VIRTUAL INTELIGENTE ====================

class SmartCustomer:
    """Cliente com IA ou respostas inteligentes"""
    
    def __init__(self, use_gpt: bool = False):
        self.profile = CustomerProfile()
        self.state = ConversationState()
        self.openai_client = get_openai_client() if use_gpt else None
        
    def generate_response(self, agent_message: str) -> str:
        """Gera resposta usando GPT-4 ou lógica local"""
        
        # Tenta usar GPT-4 primeiro
        if self.openai_client:
            try:
                return self._gpt_response(agent_message)
            except Exception as e:
                st.warning(f"GPT falhou, usando resposta local: {e}")
        
        # Fallback para lógica local
        return self._local_response(agent_message)
    
    def _gpt_response(self, agent_message: str) -> str:
        """Resposta via GPT-4"""
        prompt = f"""Você é {self.profile.name}, um cliente brasileiro ligando para a Carglass.
        
Seus dados:
- Nome: {self.profile.name}
- CPF: {self.profile.cpf}
- Telefones: {self.profile.phone1} e {self.profile.phone2}
- Placa: {self.profile.plate} ({self.profile.car})
- Endereço: {self.profile.address}
- Problema: {self.profile.problem}

Dados já fornecidos: {[k for k, v in self.state.provided_info.items() if v]}
Paciência atual: {self.state.patience}%

IMPORTANTE:
- Se o atendente pedir algo que você JÁ informou, demonstre impaciência
- Responda de forma natural e breve (máx 2 frases)
- Se a paciência estiver baixa, seja mais direto

Última mensagem do atendente: "{agent_message}"

Sua resposta:"""
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4",  # Usando GPT-4 para melhor compreensão
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()
    
    def _local_response(self, agent_message: str) -> str:
        """Resposta com lógica local melhorada"""
        msg_lower = agent_message.lower()
        
        # Análise da mensagem
        asking_name = any(w in msg_lower for w in ['nome', 'quem fala', 'com quem'])
        asking_cpf = 'cpf' in msg_lower
        asking_phone = any(w in msg_lower for w in ['telefone', 'contato', 'celular', 'whatsapp'])
        asking_plate = any(w in msg_lower for w in ['placa', 'veículo', 'carro'])
        asking_address = any(w in msg_lower for w in ['endereço', 'onde mora', 'cep'])
        asking_problem = any(w in msg_lower for w in ['problema', 'aconteceu', 'ocorreu'])
        
        # Nome
        if asking_name:
            if self.state.check_if_already_provided('name'):
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Já falei meu nome, é {self.profile.name}. Vocês não anotam?"
            else:
                self.state.mark_provided('name')
                return f"Meu nome é {self.profile.name}."
        
        # CPF
        if asking_cpf:
            if self.state.check_if_already_provided('cpf'):
                self.state.repetitions += 1
                self.state.patience -= 20
                return f"Já informei o CPF: {self.profile.cpf}. Por favor, prestem atenção!"
            else:
                self.state.mark_provided('cpf')
                return f"Meu CPF é {self.profile.cpf}."
        
        # Telefone (melhorado)
        if asking_phone:
            # Verifica se está pedindo especificamente o segundo
            if 'segundo' in msg_lower or 'outro' in msg_lower or 'adicional' in msg_lower:
                if self.state.check_if_already_provided('phone2'):
                    self.state.patience -= 15
                    return "Já passei os dois telefones anteriormente!"
                else:
                    self.state.mark_provided('phone2')
                    return f"O segundo telefone é {self.profile.phone2}."
            else:
                # Pedindo telefone genérico
                if not self.state.check_if_already_provided('phone1'):
                    self.state.mark_provided('phone1')
                    return f"Meu telefone principal é {self.profile.phone1}."
                elif not self.state.check_if_already_provided('phone2'):
                    self.state.mark_provided('phone2')
                    return f"Tenho também o telefone {self.profile.phone2}."
                else:
                    self.state.patience -= 20
                    return f"Já informei os dois telefones: {self.profile.phone1} e {self.profile.phone2}!"
        
        # Placa
        if asking_plate:
            if self.state.check_if_already_provided('plate'):
                self.state.repetitions += 1
                self.state.patience -= 25
                return f"Já falei isso antes! Placa {self.profile.plate}, é um {self.profile.car}. Estou com pressa, podemos agilizar?"
            else:
                self.state.mark_provided('plate')
                return f"Placa {self.profile.plate}, é um {self.profile.car}."
        
        # Endereço
        if asking_address:
            if self.state.check_if_already_provided('address'):
                self.state.patience -= 20
                return "Já informei meu endereço completo anteriormente."
            else:
                self.state.mark_provided('address')
                return f"Meu endereço é {self.profile.address}."
        
        # Problema
        if asking_problem:
            if self.state.check_if_already_provided('problem'):
                self.state.patience -= 15
                return "Como já disse, tenho uma trinca no para-brisa."
            else:
                self.state.mark_provided('problem')
                return f"Tenho uma {self.profile.problem}. Aconteceu ontem na estrada."
        
        # Confirmações
        if any(w in msg_lower for w in ['confirma', 'correto', 'isso mesmo', 'confere']):
            return "Sim, está correto." if self.state.patience > 50 else "Isso mesmo, podemos prosseguir?"
        
        # LGPD
        if 'lgpd' in msg_lower or 'proteção de dados' in msg_lower:
            return "Sim, autorizo o compartilhamento dos dados para o atendimento."
        
        # Cidade/Loja
        if any(w in msg_lower for w in ['cidade', 'loja', 'onde fazer']):
            return "Prefiro fazer em São Paulo, na loja mais próxima da Vila Olímpia."
        
        # Agradecimento/Encerramento
        if any(w in msg_lower for w in ['obrigado', 'agradeço', 'tenha um']):
            return "Obrigado pelo atendimento!"
        
        # Resposta padrão baseada na paciência
        if self.state.patience < 30:
            return "Estou com pressa, podemos agilizar?"
        elif self.state.repetitions > 2:
            return "Olha, vocês precisam prestar mais atenção. Já repeti várias informações."
        else:
            return "Certo, qual a próxima informação que precisa?"

# ==================== INTERFACE PRINCIPAL ====================

def init_session():
    """Inicializa sessão"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        st.session_state.customer = SmartCustomer(use_gpt=True)  # Tenta usar GPT
        st.session_state.evaluator = EvaluationSystem()
        st.session_state.start_time = None
        st.session_state.active = False

def main():
    init_session()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Voice Coach Pro - Carglass</h1>
        <p>Sistema de Treinamento com IA Avançada</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Layout principal
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        if not st.session_state.active:
            # Tela inicial
            st.info("""
            ### 📋 Instruções
            1. Siga o protocolo Carglass completo
            2. Colete todos os dados necessários
            3. Demonstre empatia e profissionalismo
            4. Não repita perguntas já respondidas
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
            chat_container = st.container()
            with chat_container:
                for speaker, msg in st.session_state.messages:
                    if speaker == "cliente":
                        st.markdown(f'<div class="customer-msg">🔸 <strong>Cliente:</strong> {msg}</div>', 
                                  unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="agent-msg">🔹 <strong>Você:</strong> {msg}</div>', 
                                  unsafe_allow_html=True)
            
            # Input
            user_input = st.text_area("Sua resposta:", height=100, key="agent_input")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Enviar", type="primary", use_container_width=True):
                    if user_input:
                        # Adiciona mensagem
                        st.session_state.messages.append(("agente", user_input))
                        
                        # Avalia (IMPORTANTE: avalia ANTES da resposta do cliente)
                        eval_result = st.session_state.evaluator.evaluate_message(user_input)
                        
                        # Verifica repetições
                        if st.session_state.customer.state.repetitions > 0:
                            st.session_state.evaluator.penalize_repetition()
                        
                        # Gera resposta do cliente
                        customer_response = st.session_state.customer.generate_response(user_input)
                        st.session_state.messages.append(("cliente", customer_response))
                        
                        st.rerun()
            
            with col2:
                if st.button("🏁 Finalizar", use_container_width=True):
                    st.session_state.active = False
                    st.rerun()
    
    with col_right:
        # Métricas
        st.markdown('<div class="metrics-card">', unsafe_allow_html=True)
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
            st.error(f"⚠️ {st.session_state.customer.state.repetitions} repetições detectadas!")
        
        # Checklist
        st.markdown("### 📋 Checklist")
        for key, value in st.session_state.customer.state.provided_info.items():
            icon = "✅" if value else "⏳"
            st.write(f"{icon} {key.title()}")
        
        # Debug (para desenvolvimento)
        with st.expander("🔍 Debug"):
            st.write("**Log de Pontuação:**")
            for log in st.session_state.evaluator.debug_log[-10:]:  # Últimos 10 logs
                st.code(log)
            
            st.write("**Scores Detalhados:**")
            for item in st.session_state.evaluator.get_detailed_scores():
                st.write(f"{item['name']}: {item['score']:.1f}/{item['max']} ({item['percentage']:.0f}%)")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Relatório final
    if not st.session_state.active and len(st.session_state.messages) > 1:
        st.markdown("---")
        st.markdown("## 📊 Relatório Final Detalhado")
        
        total, max_score = st.session_state.evaluator.get_total_score()
        percentage = (total / max_score * 100) if max_score > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Pontuação Final", f"{total}/{max_score}")
        with col2:
            st.metric("Percentual", f"{percentage:.1f}%")
        with col3:
            st.metric("Resultado", "✅ APROVADO" if percentage >= 80 else "⚠️ MELHORAR")
        
        # Breakdown detalhado
        st.markdown("### 📋 Análise por Critério")
        for item in st.session_state.evaluator.get_detailed_scores():
            progress = item['percentage'] / 100
            st.write(f"**{item['name']}**")
            st.progress(progress)
            st.write(f"{item['score']:.1f}/{item['max']} pontos ({item['percentage']:.0f}%)")
        
        # Botão reset
        if st.button("🔄 Nova Simulação", type="primary", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
