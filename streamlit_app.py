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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Importações para embeddings
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    st.warning("⚠️ Bibliotecas de embeddings não instaladas. Execute: pip install sentence-transformers scikit-learn")

# Configuração da página
st.set_page_config(
    page_title="Voice Coach Inteligente - Carglass", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS aprimorado
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #1e3a8a, #3b82f6, #06b6d4);
        color: white;
        padding: 2rem 1rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        position: relative;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .intelligence-badge {
        position: absolute;
        top: 1rem;
        left: 2rem;
        background: rgba(16, 185, 129, 0.9);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
    }
    
    .timer-container {
        position: absolute;
        top: 1rem;
        right: 2rem;
        background: rgba(255,255,255,0.15);
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 1.2rem;
        font-weight: bold;
        backdrop-filter: blur(10px);
    }
    
    .conversation-container {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.05);
    }
    
    .customer-message {
        background: linear-gradient(135deg, #fef3c7, #fde68a);
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);
    }
    
    .agent-message {
        background: linear-gradient(135deg, #dbeafe, #bfdbfe);
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
    }
    
    .satisfaction-meter {
        background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981);
        height: 8px;
        border-radius: 4px;
        margin: 0.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .satisfaction-indicator {
        position: absolute;
        top: -2px;
        width: 12px;
        height: 12px;
        background: white;
        border: 2px solid #1f2937;
        border-radius: 50%;
        transform: translateX(-50%);
    }
    
    .metrics-enhanced {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #0ea5e9;
        box-shadow: 0 4px 16px rgba(14, 165, 233, 0.1);
    }
    
    .checklist-item-enhanced {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .checklist-item-enhanced:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    }
    
    .intelligence-indicator {
        display: inline-block;
        background: linear-gradient(45deg, #10b981, #059669);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    
    .context-aware-badge {
        display: inline-block;
        background: linear-gradient(45deg, #8b5cf6, #7c3aed);
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    
    .waiting-state-enhanced {
        text-align: center;
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        border: 2px solid #3b82f6;
        border-radius: 15px;
        padding: 3rem;
        margin: 2rem 0;
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.1);
    }
</style>
""", unsafe_allow_html=True)

class ConversationGoal(Enum):
    """Objetivos da conversa para guiar o fluxo"""
    INITIAL_CONTACT = "initial_contact"
    COLLECT_PERSONAL_DATA = "collect_personal_data"
    DIAGNOSE_PROBLEM = "diagnose_problem"
    SCHEDULE_SERVICE = "schedule_service"
    FINALIZE_CALL = "finalize_call"

@dataclass
class ConversationState:
    """Estado inteligente da conversa - o cérebro da memória"""
    
    # Dados coletados pelo agente
    collected_data: Dict[str, Optional[str]] = field(default_factory=lambda: {
        'nome': None,
        'cpf': None,
        'telefone1': None,
        'telefone2': None,
        'placa': None,
        'endereco': None,
        'problema_detalhes': None,
        'cidade': None,
        'loja_escolhida': None
    })
    
    # Estado emocional e comportamental do cliente
    satisfaction_level: int = 80  # 0-100, começa otimista
    patience_level: int = 70      # 0-100, diminui com repetições
    cooperation_level: int = 85   # 0-100, aumenta com empatia
    
    # Controle de fluxo
    current_goal: ConversationGoal = ConversationGoal.INITIAL_CONTACT
    repetition_count: int = 0
    empathy_received: int = 0
    
    # Histórico de interações
    agent_questions_asked: List[str] = field(default_factory=list)
    information_already_provided: List[str] = field(default_factory=list)
    
    def update_collected_data(self, key: str, value: str):
        """Atualiza dados coletados e ajusta estado emocional"""
        if self.collected_data.get(key) is None:
            self.collected_data[key] = value
            self.information_already_provided.append(key)
            # Recompensa por progresso
            self.satisfaction_level = min(100, self.satisfaction_level + 5)
            self.cooperation_level = min(100, self.cooperation_level + 3)
        else:
            # Penalidade por repetição
            self.repetition_count += 1
            self.patience_level = max(0, self.patience_level - 15)
            self.satisfaction_level = max(0, self.satisfaction_level - 10)
    
    def increase_satisfaction(self, amount: int):
        """Aumenta satisfação por empatia ou bom atendimento"""
        self.satisfaction_level = min(100, self.satisfaction_level + amount)
        self.cooperation_level = min(100, self.cooperation_level + amount // 2)
        self.empathy_received += 1
    
    def decrease_patience(self, amount: int):
        """Diminui paciência por má conduta"""
        self.patience_level = max(0, self.patience_level - amount)
        if self.patience_level < 30:
            self.cooperation_level = max(0, self.cooperation_level - 10)
    
    def advance_goal(self):
        """Avança para próximo objetivo da conversa"""
        goals = list(ConversationGoal)
        current_index = goals.index(self.current_goal)
        if current_index < len(goals) - 1:
            self.current_goal = goals[current_index + 1]
    
    def get_emotional_state(self) -> str:
        """Retorna descrição do estado emocional atual"""
        if self.satisfaction_level >= 80:
            return "satisfeito e colaborativo"
        elif self.satisfaction_level >= 60:
            return "neutro, mas disposto a ajudar"
        elif self.satisfaction_level >= 40:
            return "ligeiramente impaciente"
        elif self.satisfaction_level >= 20:
            return "frustrado e impaciente"
        else:
            return "muito irritado, considerando desligar"
    
    def get_missing_data(self) -> List[str]:
        """Retorna lista de dados ainda não coletados"""
        return [key for key, value in self.collected_data.items() if value is None]
    
    def get_collected_data_summary(self) -> str:
        """Retorna resumo dos dados já coletados"""
        collected = [f"{key}: {value}" for key, value in self.collected_data.items() if value is not None]
        return "; ".join(collected) if collected else "nenhum dado coletado ainda"

class IntelligentCustomerBrain:
    """Cliente virtual inteligente e contextualmente consciente"""
    
    def __init__(self, use_llm: bool = True):
        # Configuração da API OpenAI
        openai_key = None
        try:
            openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        except:
            openai_key = os.getenv("OPENAI_API_KEY")
        
        self.use_llm = use_llm and (openai_key is not None) and (openai_key.strip() != "")
        self.client = None
        
        if self.use_llm:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=openai_key)
            except ImportError:
                st.error("OpenAI não instalado. Execute: pip install openai")
                self.use_llm = False
            except Exception as e:
                st.warning(f"Erro ao inicializar OpenAI: {str(e)}")
                self.use_llm = False
                self.client = None
        
        # Dados do cliente simulado
        self.customer_data = {
            'name': 'João Silva',
            'cpf': '123.456.789-10',
            'phone1': '11-99999-8888',
            'phone2': '11-97777-6666',
            'plate': 'ABC-1234',
            'car': 'Honda Civic 2020',
            'address': 'Rua das Flores, 123 - Vila Olímpia, São Paulo/SP',
            'insurance': 'Porto Seguro',
            'problem': 'Trinca no para-brisa de 15cm causada por pedra na Marginal Tietê ontem'
        }
    
    def first_utterance(self) -> str:
        """Primeira fala do cliente - sempre a mesma para consistência"""
        return "Alô, bom dia! Estou ligando porque tenho um problema urgente no para-brisa do meu carro e preciso resolver hoje mesmo."
    
    def reply(self, conversation_state: ConversationState, agent_last: str, turns: List[Dict]) -> str:
        """Gera resposta inteligente baseada no estado da conversa"""
        
        if self.use_llm:
            return self._generate_intelligent_response(conversation_state, agent_last, turns)
        else:
            return self._generate_fallback_response(conversation_state, agent_last)
    
    def _generate_intelligent_response(self, state: ConversationState, agent_last: str, turns: List[Dict]) -> str:
        """Gera resposta usando IA com contexto completo"""
        
        # Construir contexto rico para o LLM
        context_prompt = f"""
Você é {self.customer_data['name']}, um cliente brasileiro ligando para a Carglass com um problema urgente no para-brisa.

**SEUS DADOS PESSOAIS:**
- Nome: {self.customer_data['name']}
- CPF: {self.customer_data['cpf']}
- Telefones: {self.customer_data['phone1']} (principal) e {self.customer_data['phone2']} (secundário)
- Placa: {self.customer_data['plate']}
- Veículo: {self.customer_data['car']}
- Endereço: {self.customer_data['address']}
- Seguro: {self.customer_data['insurance']}

**SEU PROBLEMA:** {self.customer_data['problem']}

**ESTADO ATUAL DA CONVERSA:**
- Dados que você JÁ FORNECEU: {state.get_collected_data_summary()}
- Dados ainda pendentes: {', '.join(state.get_missing_data())}
- Seu estado emocional: {state.get_emotional_state()}
- Nível de paciência: {state.patience_level}/100
- Nível de satisfação: {state.satisfaction_level}/100
- Repetições detectadas: {state.repetition_count}
- Empatia recebida: {state.empathy_received} vezes

**OBJETIVO ATUAL:** {state.current_goal.value}

**ÚLTIMA FALA DO ATENDENTE:** "{agent_last}"

**INSTRUÇÕES DE COMPORTAMENTO:**
1. Se o atendente pedir uma informação que você JÁ FORNECEU, demonstre impaciência crescente
2. Se sua paciência estiver baixa (<40), seja mais direto e questione a competência
3. Se receber empatia, torne-se mais colaborativo
4. Responda sempre como um brasileiro autêntico, com urgência mas educado
5. Máximo 2 frases por resposta
6. Se a satisfação estiver alta (>80), elogie o atendimento

Responda de forma natural e coerente com seu estado emocional atual.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": context_prompt}],
                temperature=0.8,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            st.warning(f"Erro na IA: {e}")
            return self._generate_fallback_response(state, agent_last)
    
    def _generate_fallback_response(self, state: ConversationState, agent_last: str) -> str:
        """Resposta de fallback quando IA não está disponível"""
        agent_lower = agent_last.lower()
        
        # Detectar repetições
        if state.repetition_count > 2:
            return "Olha, eu já falei isso várias vezes. Vocês não anotam as informações? Preciso resolver isso urgente!"
        
        # Respostas baseadas no que foi perguntado
        if "nome" in agent_lower and state.collected_data['nome'] is None:
            return f"Meu nome é {self.customer_data['name']}."
        elif "nome" in agent_lower and state.collected_data['nome'] is not None:
            return f"Eu já disse que meu nome é {self.customer_data['name']}. Vamos prosseguir?"
        
        elif "cpf" in agent_lower and state.collected_data['cpf'] is None:
            return f"Meu CPF é {self.customer_data['cpf']}."
        elif "cpf" in agent_lower and state.collected_data['cpf'] is not None:
            return f"Meu CPF é {self.customer_data['cpf']}, como eu já informei."
        
        elif "telefone" in agent_lower:
            if "segundo" in agent_lower or "outro" in agent_lower:
                return f"O segundo telefone é {self.customer_data['phone2']}."
            else:
                return f"Meu telefone principal é {self.customer_data['phone1']}."
        
        elif "placa" in agent_lower:
            return f"A placa do meu carro é {self.customer_data['plate']}."
        
        elif "endereço" in agent_lower:
            return f"Meu endereço é {self.customer_data['address']}."
        
        else:
            # Resposta genérica baseada no estado emocional
            if state.satisfaction_level < 40:
                return "Certo, mas vamos agilizar isso? Estou com pressa."
            else:
                return "Perfeito. Qual o próximo passo?"

class HybridScoreEngine:
    """Motor de avaliação híbrido integrado com o estado da conversa"""
    
    def __init__(self):
        self.embedding_scorer = self._initialize_embedding_scorer()
        self.use_embeddings = (self.embedding_scorer is not None)
        
        # Critérios de avaliação com pesos
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
    
    def _initialize_embedding_scorer(self):
        """Inicializa o sistema de embeddings se disponível"""
        if not EMBEDDINGS_AVAILABLE:
            return None
        
        try:
            model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            st.success("🧠 Sistema de análise semântica ativado!")
            return model
        except Exception as e:
            st.error(f"❌ Erro ao carregar modelo de embeddings: {e}")
            return None
    
    def evaluate_and_update_state(self, turns: List[Dict], state: ConversationState) -> Dict:
        """Avalia performance e atualiza estado da conversa"""
        
        agent_text = " ".join([t["text"] for t in turns if t["speaker"] == "agent"])
        items = []
        total = 0
        
        for idx, max_points, label in self.checklist_weights:
            points, evidence, method = self._score_item(idx, agent_text, state)
            total += points
            
            items.append({
                "idx": idx,
                "label": label,
                "points": points,
                "max_points": max_points,
                "evidence": evidence,
                "method": method
            })
            
            # Atualizar estado baseado na avaliação
            self._update_conversation_state(idx, points, max_points, agent_text, state)
        
        max_total = sum(m for _, m, _ in self.checklist_weights)
        tips = self._generate_intelligent_tips(items, state)
        
        return {
            "items": items,
            "total": total,
            "max_total": max_total,
            "tips": tips,
            "embedding_enabled": self.use_embeddings,
            "conversation_state": state
        }
    
    def _score_item(self, idx: int, agent_text: str, state: ConversationState) -> Tuple[int, List[str], str]:
        """Pontua item específico"""
        max_points = next(m for i, m, _ in self.checklist_weights if i == idx)
        
        # Para itens semânticos, usa embeddings se disponível
        if self.use_embeddings and idx in self.semantic_items:
            return self._score_item_semantic(idx, agent_text, max_points, state)
        else:
            return self._score_item_rule_based(idx, agent_text, max_points, state)
    
    def _score_item_semantic(self, idx: int, agent_text: str, max_points: int, state: ConversationState) -> Tuple[int, List[str], str]:
        """Avaliação semântica usando embeddings"""
        # Implementação simplificada - na prática, usaria gabarito de embeddings
        evidence = []
        points = 0
        
        text_lower = agent_text.lower()
        
        if idx == 1:  # Saudação
            if any(word in text_lower for word in ["bom dia", "boa tarde", "carglass"]):
                points = max_points
                evidence.append("Saudação profissional detectada")
            else:
                points = 0
                evidence.append("Saudação não detectada")
        
        elif idx == 10:  # Empatia
            empathy_words = ["entendo", "compreendo", "sei como", "imagino", "sinto muito"]
            empathy_count = sum(1 for word in empathy_words if word in text_lower)
            
            if empathy_count >= 2:
                points = max_points
                evidence.append(f"Alta empatia detectada: {empathy_count} expressões")
                state.increase_satisfaction(15)
            elif empathy_count >= 1:
                points = max_points // 2
                evidence.append(f"Empatia moderada: {empathy_count} expressão")
                state.increase_satisfaction(8)
            else:
                points = 0
                evidence.append("Empatia não detectada")
        
        return points, evidence, "Semântica"
    
    def _score_item_rule_based(self, idx: int, agent_text: str, max_points: int, state: ConversationState) -> Tuple[int, List[str], str]:
        """Avaliação baseada em regras"""
        evidence = []
        points = 0
        text_lower = agent_text.lower()
        
        if idx == 2:  # Coleta de dados
            data_requests = ['nome', 'cpf', 'telefone', 'placa', 'endereço']
            requested_count = sum(1 for req in data_requests if req in text_lower)
            
            # Verificar se está pedindo dados já coletados
            redundant_requests = 0
            for key, value in state.collected_data.items():
                if value is not None and key.replace('telefone1', 'telefone') in text_lower:
                    redundant_requests += 1
                    state.update_collected_data(key, value)  # Isso vai penalizar
            
            if redundant_requests > 0:
                points = max(0, max_points - (redundant_requests * 2))
                evidence.append(f"Solicitou {redundant_requests} dados já fornecidos")
            else:
                points = min(max_points, (requested_count * max_points) // len(data_requests))
                evidence.append(f"Solicitou {requested_count}/{len(data_requests)} dados necessários")
        
        elif idx == 5:  # Escuta atenta
            if state.repetition_count > 0:
                points = max(0, max_points - (state.repetition_count * 2))
                evidence.append(f"Penalizado por {state.repetition_count} repetições")
            else:
                points = max_points
                evidence.append("Demonstrou escuta atenta")
        
        return points, evidence, "Regras"
    
    def _update_conversation_state(self, idx: int, points: int, max_points: int, agent_text: str, state: ConversationState):
        """Atualiza estado da conversa baseado na avaliação"""
        
        # Detectar coleta de dados específicos
        text_lower = agent_text.lower()
        
        # Simular extração de dados (na prática, seria mais sofisticada)
        if "nome" in text_lower and "joão" in text_lower:
            state.update_collected_data('nome', 'João Silva')
        
        if "cpf" in text_lower and "123" in agent_text:
            state.update_collected_data('cpf', '123.456.789-10')
        
        if "telefone" in text_lower and "99999" in agent_text:
            state.update_collected_data('telefone1', '11-99999-8888')
        
        # Ajustar satisfação baseado na performance
        performance_ratio = points / max_points if max_points > 0 else 0
        
        if performance_ratio >= 0.8:
            state.increase_satisfaction(5)
        elif performance_ratio < 0.3:
            state.decrease_patience(5)
    
    def _generate_intelligent_tips(self, items: List[Dict], state: ConversationState) -> List[str]:
        """Gera dicas inteligentes baseadas no estado da conversa"""
        tips = []
        
        # Dicas específicas baseado no estado
        if state.repetition_count > 2:
            tips.append("🎯 CRÍTICO: Você está repetindo perguntas. O cliente já forneceu essas informações!")
        
        if state.satisfaction_level < 40:
            tips.append("😟 ATENÇÃO: Cliente frustrado. Use mais empatia e agilize o atendimento.")
        
        if state.empathy_received == 0:
            tips.append("💝 DICA: Demonstre empatia com frases como 'Entendo sua preocupação' ou 'Vamos resolver isso rapidamente'.")
        
        # Dicas baseadas nos itens com menor pontuação
        failed_items = sorted(
            [item for item in items if item["points"] < item["max_points"]], 
            key=lambda x: x["max_points"] - x["points"], reverse=True
        )
        
        for item in failed_items[:2]:
            tips.append(f"📋 Item {item['idx']}: {item['label'][:50]}... (Método: {item['method']})")
        
        if not tips:
            tips.append("🎉 Excelente! Todos os critérios atendidos e cliente satisfeito!")
        
        return tips

# Funções auxiliares
def format_timer(seconds):
    """Formata timer em MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def tts_bytes(text: str, use_openai: bool = False) -> bytes:
    """Gera áudio TTS"""
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

def check_api_status():
    """Verifica status das APIs"""
    status = {}
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if (openai_key and openai_key.strip()) else "❌ Não configurado"
    except:
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            status["openai"] = "✅ Configurado" if (openai_key and openai_key.strip()) else "❌ Não configurado"
        except:
            status["openai"] = "❌ Não configurado"
    
    status["embeddings"] = "✅ Disponível" if EMBEDDINGS_AVAILABLE else "❌ Não instalado"
    return status

# Interface principal
def main():
    # Inicialização do estado da sessão
    if "session_state" not in st.session_state:
        st.session_state.session_state = "waiting"
        st.session_state.start_time = None
        st.session_state.session_duration = 0
        st.session_state.conversation_state = ConversationState()
        st.session_state.brain = None
        st.session_state.turns = []
        st.session_state.score_engine = HybridScoreEngine()
    
    # Garantir que score_engine sempre existe
    if "score_engine" not in st.session_state:
        st.session_state.score_engine = HybridScoreEngine()
    
    # Garantir que conversation_state sempre existe
    if "conversation_state" not in st.session_state:
        st.session_state.conversation_state = ConversationState()
    
    # Garantir que turns sempre existe
    if "turns" not in st.session_state:
        st.session_state.turns = []

    # Timer dinâmico
    timer_placeholder = st.empty()
    
    if st.session_state.session_state == "active" and st.session_state.start_time:
        elapsed = time.time() - st.session_state.start_time
        st.session_state.session_duration = elapsed
        
        if elapsed >= 1200:  # 20 minutos
            st.session_state.session_state = "timeout"
            st.error("⏰ Tempo limite de 20 minutos atingido!")
        
        timer_color = "#ff4444" if elapsed > 1080 else "#ffa500" if elapsed > 900 else "#ffffff"
        timer_placeholder.markdown(f"""
        <div style="text-align: right; margin-bottom: 1rem;">
            <span style="background: {timer_color}; color: {'white' if elapsed <= 900 else 'black'}; 
                  padding: 0.5rem 1rem; border-radius: 20px; font-weight: bold;">
                ⏱️ {format_timer(elapsed)} / 20:00
            </span>
        </div>
        """, unsafe_allow_html=True)

    # Header principal
    intelligence_badge = '<div class="intelligence-badge">🧠 IA Contextual</div>'
    timer_display = ""
    
    if st.session_state.session_state == "active":
        timer_display = f'<div class="timer-container">⏱️ {format_timer(st.session_state.session_duration)} / 20:00</div>'

    st.markdown(f'''
    <div class="main-header">
        {intelligence_badge}
        <h1>Voice Coach Inteligente</h1>
        <p>Sistema de treinamento com IA contextual e memória conversacional</p>
        {timer_display}
    </div>
    ''', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações Inteligentes")
        
        api_status = check_api_status()
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <strong>🤖 OpenAI:</strong> {api_status['openai']}<br>
            <strong>🧠 Embeddings:</strong> {api_status['embeddings']}<br>
            <strong>💡 Sistema:</strong> <span style="color: #10b981; font-weight: bold;">Híbrido Inteligente</span>
        </div>
        """, unsafe_allow_html=True)
        
        use_llm = st.toggle("🧠 Cliente Inteligente", value=(api_status["openai"] == "✅ Configurado"))
        use_openai_tts = st.toggle("🎤 Voz Premium", value=(api_status["openai"] == "✅ Configurado"))
        
        st.divider()
        
        # Estado da conversa em tempo real
        if st.session_state.session_state == "active":
            st.subheader("📊 Estado da Conversa")
            state = st.session_state.conversation_state
            
            # Medidor de satisfação
            satisfaction_percent = state.satisfaction_level
            st.markdown(f"""
            <div style="margin: 1rem 0;">
                <strong>😊 Satisfação do Cliente: {satisfaction_percent}%</strong>
                <div class="satisfaction-meter">
                    <div class="satisfaction-indicator" style="left: {satisfaction_percent}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.metric("🎯 Paciência", f"{state.patience_level}%")
            st.metric("🤝 Cooperação", f"{state.cooperation_level}%")
            st.metric("🔄 Repetições", state.repetition_count)
            st.metric("💝 Empatia Recebida", state.empathy_received)
            
            # Dados coletados
            st.subheader("📋 Dados Coletados")
            for key, value in state.collected_data.items():
                if value:
                    st.success(f"✅ {key.title()}: {value}")
                else:
                    st.info(f"⏳ {key.title()}: Pendente")
        
        else:
            st.subheader("👤 Cliente Simulado")
            st.markdown("""
            **João Silva**  
            📱 11-99999-8888 / 11-97777-6666  
            🚗 ABC-1234 (Honda Civic 2020)  
            📍 Vila Olímpia - São Paulo/SP  
            🛡️ Porto Seguro  
            🔧 Trinca no para-brisa (15cm)
            """)

    # Interface principal baseada no estado
    if st.session_state.session_state == "waiting":
        st.markdown(f"""
        <div class="waiting-state-enhanced">
            <h2>🧠 Sistema de Treinamento Inteligente</h2>
            <p><strong>🎯 IA Contextual Ativa:</strong> Cliente virtual com memória e emoções</p>
            <p>✅ Reações realísticas baseadas no seu atendimento</p>
            <p>✅ Penalização automática por repetições</p>
            <p>✅ Recompensas por empatia e eficiência</p>
            <p>✅ Avaliação híbrida: semântica + regras</p>
            <p><strong>⏱️ Duração:</strong> Máximo 20 minutos</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_center = st.columns([1, 2, 1])
        with col_center[1]:
            if st.button("🚀 Iniciar Treinamento Inteligente", type="primary", use_container_width=True):
                # Inicializar sessão
                st.session_state.session_state = "active"
                st.session_state.start_time = time.time()
                st.session_state.conversation_state = ConversationState()
                st.session_state.brain = IntelligentCustomerBrain(use_llm=use_llm)
                st.session_state.turns = []
                st.session_state.score_engine = HybridScoreEngine()
                
                # Primeira fala do cliente
                first_msg = st.session_state.brain.first_utterance()
                st.session_state.turns.append({
                    "speaker": "customer", 
                    "text": first_msg, 
                    "ts": time.time()
                })
                
                st.rerun()

    elif st.session_state.session_state in ["active", "timeout"]:
        
        col_main, col_input = st.columns([2, 1])
        
        with col_main:
            st.subheader("📞 Simulação Inteligente de Atendimento")
            
            # Container da conversa
            st.markdown('<div class="conversation-container">', unsafe_allow_html=True)
            
            for turn in st.session_state.turns:
                if turn["speaker"] == "customer":
                    st.markdown(f'''
                    <div class="customer-message">
                        <strong>📞 Cliente:</strong> {turn["text"]}
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                    <div class="agent-message">
                        <strong>👤 Você:</strong> {turn["text"]}
                    </div>
                    ''', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
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
                        # Adicionar resposta do agente
                        st.session_state.turns.append({
                            "speaker": "agent", 
                            "text": agent_text, 
                            "ts": time.time()
                        })
                        
                        # Gerar resposta do cliente inteligente
                        reply = st.session_state.brain.reply(
                            st.session_state.conversation_state,
                            agent_text,
                            st.session_state.turns
                        )
                        
                        st.session_state.turns.append({
                            "speaker": "customer", 
                            "text": reply, 
                            "ts": time.time()
                        })
                        
                        # Áudio do cliente
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
                    # Reset completo
                    for key in ["session_state", "start_time", "session_duration", "conversation_state", "brain", "turns", "score_engine"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
            
            else:
                st.error("⏰ Tempo limite atingido")
                if st.button("🔄 Nova Sessão", use_container_width=True):
                    for key in ["session_state", "start_time", "session_duration", "conversation_state", "brain", "turns", "score_engine"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

        # Avaliação em tempo real
        if len([t for t in st.session_state.turns if t["speaker"] == "agent"]) > 0:
            st.divider()
            
            # Garantir que score_engine existe antes de usar
            if "score_engine" not in st.session_state:
                st.session_state.score_engine = HybridScoreEngine()
            
            # Avaliar e atualizar estado
            result = st.session_state.score_engine.evaluate_and_update_state(
                st.session_state.turns, 
                st.session_state.conversation_state
            )
            
            st.markdown("## 🧠 Avaliação Inteligente em Tempo Real")
            
            # Métricas principais
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Pontuação", f"{result['total']}")
            with col2:
                st.metric("Máximo", f"{result['max_total']}")
            with col3:
                percentage = round((result['total'] / result['max_total']) * 100, 1)
                color = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
                st.metric("Performance", f"{percentage}% {color}")
            with col4:
                items_ok = sum(1 for item in result["items"] if item["points"] == item["max_points"])
                st.metric("Completos", f"{items_ok}/12")
            with col5:
                st.metric("Cliente", f"😊 {st.session_state.conversation_state.satisfaction_level}%")
            
            # Indicadores de inteligência
            st.markdown(f"""
            <div style="text-align: center; margin: 1rem 0;">
                <span class="intelligence-indicator">🧠 IA Contextual</span>
                <span class="context-aware-badge">📊 Estado Dinâmico</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Checklist detalhado
            with st.expander("📋 Checklist Inteligente com Contexto", expanded=False):
                for item in result["items"]:
                    status = "✅" if item["points"] == item["max_points"] else "⚠️" if item["points"] > 0 else "❌"
                    method = item.get("method", "N/A")
                    
                    st.markdown(f"""
                    <div class="checklist-item-enhanced">
                        <strong>{status} Item {item['idx']}</strong>
                        <span class="intelligence-indicator">{method}</span>
                        <span style="float: right;">({item['points']}/{item['max_points']} pts)</span>
                        <br>
                        <small>{item['label']}</small><br>
                        {f"<em>Evidências: {'; '.join(item['evidence'])}</em>" if item['evidence'] else ""}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Dicas inteligentes
            if result["tips"]:
                st.subheader("🧠 Recomendações Inteligentes")
                for tip in result["tips"]:
                    if "CRÍTICO" in tip:
                        st.error(tip)
                    elif "ATENÇÃO" in tip:
                        st.warning(tip)
                    else:
                        st.info(tip)
        
        else:
            st.info("👆 Digite sua primeira resposta para ativar a avaliação inteligente!")

    elif st.session_state.session_state == "finished":
        st.success("🎉 Treinamento Inteligente Finalizado!")
        
        # Garantir que score_engine existe antes de usar
        if "score_engine" not in st.session_state:
            st.session_state.score_engine = HybridScoreEngine()
        
        # Avaliação final
        result = st.session_state.score_engine.evaluate_and_update_state(
            st.session_state.turns, 
            st.session_state.conversation_state
        )
        
        percentage = round((result['total'] / result['max_total']) * 100, 1)
        
        st.markdown("## 📋 Relatório Final - Sistema Inteligente")
        
        # Métricas finais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Pontuação Final", f"{result['total']}/{result['max_total']}")
        with col2:
            color = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
            st.metric("Performance", f"{percentage}% {color}")
        with col3:
            st.metric("Duração", format_timer(st.session_state.session_duration))
        with col4:
            st.metric("Satisfação Cliente", f"😊 {st.session_state.conversation_state.satisfaction_level}%")
        
        # Análise do comportamento do cliente
        state = st.session_state.conversation_state
        
        st.subheader("🧠 Análise Comportamental do Cliente Virtual")
        
        col_behavior1, col_behavior2 = st.columns(2)
        
        with col_behavior1:
            st.markdown("**📊 Métricas Emocionais**")
            st.metric("Satisfação Final", f"{state.satisfaction_level}%")
            st.metric("Paciência Final", f"{state.patience_level}%")
            st.metric("Cooperação Final", f"{state.cooperation_level}%")
        
        with col_behavior2:
            st.markdown("**🎯 Métricas Comportamentais**")
            st.metric("Repetições Detectadas", state.repetition_count)
            st.metric("Empatia Recebida", state.empathy_received)
            st.metric("Estado Emocional", state.get_emotional_state().title())
        
        # Dados coletados vs pendentes
        st.subheader("📋 Eficácia na Coleta de Dados")
        
        collected_count = sum(1 for v in state.collected_data.values() if v is not None)
        total_data_points = len(state.collected_data)
        
        col_data1, col_data2 = st.columns(2)
        
        with col_data1:
            st.markdown("**✅ Dados Coletados**")
            for key, value in state.collected_data.items():
                if value:
                    st.success(f"{key.title()}: {value}")
        
        with col_data2:
            st.markdown("**⏳ Dados Pendentes**")
            for key, value in state.collected_data.items():
                if not value:
                    st.warning(f"{key.title()}: Não coletado")
        
        st.metric("Taxa de Coleta", f"{collected_count}/{total_data_points} ({round(collected_count/total_data_points*100, 1)}%)")
        
        # Botões de ação
        col_new, col_download = st.columns(2)
        
        with col_new:
            if st.button("🔄 Novo Treinamento", use_container_width=True, type="primary"):
                for key in ["session_state", "start_time", "session_duration", "conversation_state", "brain", "turns", "score_engine"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        with col_download:
            # Gerar relatório detalhado
            report_data = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "duration": format_timer(st.session_state.session_duration),
                "score": f"{result['total']}/{result['max_total']} ({percentage}%)",
                "customer_satisfaction": f"{state.satisfaction_level}%",
                "repetitions": state.repetition_count,
                "empathy_received": state.empathy_received,
                "data_collection_rate": f"{collected_count}/{total_data_points}",
                "conversation": st.session_state.turns
            }
            
            report_json = json.dumps(report_data, indent=2, ensure_ascii=False)
            
            st.download_button(
                label="📄 Relatório Inteligente",
                data=report_json,
                file_name=f"relatorio_inteligente_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
