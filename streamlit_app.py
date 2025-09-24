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
</style>
""", unsafe_allow_html=True)

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
Agente em Treinamento: [Nome do Agente]

=== RESUMO DA PERFORMANCE ===
Pontuação Final: {score_data['total']}/{score_data['max_total']} pontos
Percentual de Acerto: {round((score_data['total'] / score_data['max_total']) * 100, 1)}%
Itens Completos: {sum(1 for item in score_data['items'] if item['points'] == item['max_points'])}/12

=== CHECKLIST DETALHADO ===
"""
    
    for i, item in enumerate(score_data['items'], 1):
        status = "✓" if item['points'] == item['max_points'] else "⚠" if item['points'] > 0 else "✗"
        report_content += f"\n{i:2d}. [{status}] {item['label']}"
        report_content += f"\n    Pontuação: {item['points']}/{item['max_points']} pts"
        if item['evidence']:
            report_content += f"\n    Evidências: {'; '.join(item['evidence'])}"
        report_content += "\n"
    
    report_content += "\n=== RECOMENDAÇÕES DE MELHORIA ===\n"
    for i, tip in enumerate(score_data['tips'], 1):
        report_content += f"{i}. {tip}\n"
    
    report_content += f"\n=== TRANSCRIÇÃO DA CONVERSA ===\n"
    for turn in session_data.get('turns', []):
        speaker = "AGENTE" if turn['speaker'] == 'agent' else "CLIENTE"
        report_content += f"\n{speaker}: {turn['text']}\n"
    
    return report_content.encode('utf-8')

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

class RigorousScoreEngine:
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
            saudacao = bool(re.search(r"\b(bom dia|boa tarde|boa noite)\b", text))
            carglass = bool(re.search(r"\bcarglass\b", text, re.IGNORECASE))
            nome = bool(re.search(r"meu nome (é|eh)\s+\w+", text))
            
            if saudacao and carglass and nome:
                points = max_points
                evidence.append("Saudação completa: horário + Carglass + nome")
            elif saudacao and carglass:
                points = max_points // 2
                evidence.append("Saudação parcial: faltou identificação pessoal")
        
        elif idx == 2:
            dados_patterns = {
                'nome': r"qual.{0,20}seu nome|me fala.{0,10}nome|nome completo",
                'cpf': r"qual.{0,20}cpf|me informa.{0,10}cpf|seu cpf",
                'telefone1': r"telefone|número.{0,10}contato",
                'telefone2': r"segundo telefone|outro telefone|telefone adicional|segundo número",
                'placa': r"placa.{0,10}veículo|qual.{0,10}placa|placa.{0,10}carro",
                'endereco': r"qual.{0,20}endereço|onde.{0,10}mora|seu endereço"
            }
            
            dados_ok = {k: bool(re.search(v, text, re.IGNORECASE)) for k, v in dados_patterns.items()}
            total_dados = sum(dados_ok.values())
            
            bradesco_excecao = bool(re.search(r"bradesco|sura|ald", text, re.IGNORECASE))
            sistema_confirmado = bool(re.search(r"já.{0,20}sistema|já.{0,20}cadastrado|já.{0,20}temos", text))
            
            if bradesco_excecao and sistema_confirmado:
                if total_dados >= 4 and dados_ok['nome'] and dados_ok['telefone1'] and dados_ok['telefone2'] and dados_ok['placa']:
                    points = max_points
                    evidence.append("Dados completos - exceção Bradesco/Sura/ALD aplicada")
            elif total_dados == 6:
                points = max_points
                evidence.append("Todos os 6 dados obrigatórios solicitados")
            else:
                faltaram = [k for k, v in dados_ok.items() if not v]
                evidence.append(f"Faltaram: {', '.join(faltaram)} ({total_dados}/6)")
        
        elif idx == 3:
            lgpd_patterns = [
                r"compartilhar.{0,50}telefone.{0,50}prestador",
                r"prestador.{0,50}acesso.{0,50}telefone",
                r"autoriza.{0,30}compartilhamento",
                r"pode.{0,20}informar.{0,20}prestador",
                r"notificações.{0,30}whatsapp"
            ]
            
            for pattern in lgpd_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    points = max_points
                    evidence.append("Script LGPD identificado")
                    break
        
        elif idx == 4:
            eco_completo = False
            
            if re.search(r"\w+\s+de\s+\w+", text):
                points = max_points
                evidence.append("Soletração fonética identificada")
                eco_completo = True
            
            if not eco_completo:
                eco_numeros = re.findall(r"\b\d{3,}\b", text)
                if len(eco_numeros) >= 2:
                    points = max_points
                    evidence.append(f"ECO múltiplo: {len(eco_numeros)} repetições")
                elif len(eco_numeros) == 1:
                    points = max_points // 2
                    evidence.append("ECO parcial identificado")
        
        elif idx == 5:
            problemas = []
            if re.search(r"não.{0,10}entendi|como assim|repete", text):
                problemas.append("Pedidos de repetição")
            if re.search(r"já.{0,10}falou|você disse", text):
                problemas.append("Solicitações duplicadas")
            
            if not problemas:
                points = max_points
                evidence.append("Escuta atenta demonstrada")
            else:
                evidence.extend(problemas)
        
        elif idx == 6:
            conhecimento_items = [
                r"para.brisa|vidro",
                r"seguro.{0,30}cobre",
                r"franquia",
                r"vistoria",
                r"loja.{0,20}próxima"
            ]
            
            conhecimento_count = sum(1 for item in conhecimento_items if re.search(item, text, re.IGNORECASE))
            if conhecimento_count >= 3:
                points = max_points
                evidence.append(f"Conhecimento técnico: {conhecimento_count} aspectos")
            elif conhecimento_count >= 1:
                points = max_points // 2
                evidence.append(f"Conhecimento parcial: {conhecimento_count} aspecto(s)")
        
        elif idx == 7:
            info_dano = {
                'data': r"quando.{0,20}aconteceu|que dia|data.{0,20}ocorreu",
                'motivo': r"como.{0,20}aconteceu|o que causou|motivo.{0,20}dano",
                'tamanho': r"tamanho.{0,20}trinca|quantos cm|tamanho.{0,20}dano",
                'led_xenon': r"led|xenon|sensor",
                'pintura': r"pintura|cor.{0,20}veículo"
            }
            
            info_coletada = sum(1 for pattern in info_dano.values() if re.search(pattern, text, re.IGNORECASE))
            
            if info_coletada >= 4:
                points = max_points
                evidence.append(f"Informações completas do dano: {info_coletada}/5")
            elif info_coletada >= 2:
                points = max_points * info_coletada // 5
                evidence.append(f"Informações parciais: {info_coletada}/5")
        
        elif idx == 8:
            cidade_ok = bool(re.search(r"qual.{0,20}cidade|onde.{0,20}você.{0,20}está|sua localização", text, re.IGNORECASE))
            loja_ok = bool(re.search(r"loja.{0,30}próxima|primeira opção|unidade.{0,20}mais perto", text, re.IGNORECASE))
            
            if cidade_ok and loja_ok:
                points = max_points
                evidence.append("Cidade confirmada E loja selecionada")
            else:
                faltou = []
                if not cidade_ok: faltou.append("cidade")
                if not loja_ok: faltou.append("loja")
                evidence.append(f"Faltou: {', '.join(faltou)}")
        
        elif idx == 9:
            penalidades = []
            base_points = max_points
            
            if re.search(r"\b(mano|cara|tipo assim|né)\b", text):
                penalidades.append("Gírias identificadas")
                base_points -= 2
            
            if not re.search(r"vou verificar|um momento|já retorno|voltei", text):
                penalidades.append("Não informou ausências")
                base_points -= 1
            
            points = max(0, base_points)
            if penalidades:
                evidence.extend(penalidades)
            else:
                evidence.append("Comunicação profissional")
        
        elif idx == 10:
            empatia_indicators = [
                r"entendo.{0,20}situação",
                r"imagino.{0,20}preocupação",
                r"vamos resolver",
                r"pode deixar",
                r"estou aqui para ajudar"
            ]
            
            empatia_count = sum(1 for indicator in empatia_indicators if re.search(indicator, text, re.IGNORECASE))
            
            if empatia_count >= 2:
                points = max_points
                evidence.append(f"Conduta acolhedora: {empatia_count} expressões")
            elif empatia_count == 1:
                points = max_points // 2
                evidence.append("Empatia parcial demonstrada")
        
        elif idx == 11:
            script_elementos = {
                'validade': r"prazo.{0,30}validade|vale por.{0,20}dias",
                'franquia': r"franquia.{0,30}\d+|valor.{0,20}franquia",
                'link': r"link.{0,30}whatsapp|acompanhamento|vistoria",
                'contato': r"aguarde.{0,20}contato|entraremos em contato"
            }
            
            elementos_ok = sum(1 for pattern in script_elementos.values() if re.search(pattern, text, re.IGNORECASE))
            
            if elementos_ok == 4:
                points = max_points
                evidence.append("Script completo: todos os 4 elementos")
            elif elementos_ok >= 2:
                points = max_points * elementos_ok // 4
                evidence.append(f"Script parcial: {elementos_ok}/4 elementos")
        
        elif idx == 12:
            if re.search(r"pesquisa.{0,30}satisfação|avaliação.{0,20}atendimento|nota.{0,20}máxima", text, re.IGNORECASE):
                points = max_points
                evidence.append("Pesquisa de satisfação mencionada")
        
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
        
        tips = self._generate_tips(items)
        
        return {
            "items": items, 
            "total": total, 
            "max_total": sum(m for _,m,_ in CHECKLIST_WEIGHTS), 
            "tips": tips
        }
    
    def _generate_tips(self, items):
        tips = []
        priority_items = sorted([item for item in items if item["points"] < item["max_points"]], 
                               key=lambda x: x["max_points"], reverse=True)
        
        for item in priority_items[:3]:
            if item["idx"] == 1:
                tips.append("Use saudação completa: 'Bom dia! Carglass, meu nome é [Nome]'")
            elif item["idx"] == 2:
                tips.append("Solicite todos os dados: nome, CPF, 2 telefones, placa e endereço")
            elif item["idx"] == 4:
                tips.append("Confirme dados com ECO: repita números ou use soletração fonética")
            elif item["idx"] == 7:
                tips.append("Colete informações completas: data, como aconteceu, tamanho, LED/Xenon")
            elif item["idx"] == 11:
                tips.append("Script completo: validade, franquia, link WhatsApp e aguardar contato")
            else:
                tips.append(f"Melhore item {item['idx']}: {item['label'][:60]}...")
        
        if not tips:
            tips.append("Excelente performance! Todos os critérios foram atendidos.")
        
        return tips

class IntelligentCustomerBrain:
    def __init__(self, use_llm: bool, scenario: dict):
        self.use_llm = use_llm
        self.scenario = scenario
        self.conversation_context = []
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
Você é {self.customer_data['name']}, um cliente brasileiro ligando para a Carglass com urgência.

SEUS DADOS PESSOAIS (forneça apenas quando solicitado):
- Nome: {self.customer_data['name']}
- CPF: {self.customer_data['cpf']}
- Telefone principal: {self.customer_data['phone1']}
- Telefone secundário: {self.customer_data['phone2']}
- Placa: {self.customer_data['plate']}
- Veículo: {self.customer_data['car']}
- Endereço: {self.customer_data['address']}
- Seguro: {self.customer_data['insurance']}

SEU PROBLEMA:
- Trinca no para-brisa de 15cm causada por pedra ontem na Marginal Tietê
- Precisa usar o carro para trabalhar
- Primeira vez usando serviço Carglass
- Tem urgência mas é colaborativo

CONTEXTO DA CONVERSA: {context}
ÚLTIMA FALA DO ATENDENTE: "{agent_last}"

INSTRUÇÕES:
1. Seja um cliente brasileiro autêntico - linguagem natural
2. Demonstre urgência apropriada (precisa trabalhar)
3. Faça perguntas relevantes: prazo, custo, como funciona
4. Só forneça dados quando especificamente perguntado
5. Reaja ao atendimento: bom = colaborativo, ruim = impaciente
6. Máximo 2 frases por resposta
7. Use "né", "tá", mas mantenha respeito

RESPONDA AGORA:
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
            return "Início - cliente explicou problema, aguarda orientação"
        elif stage <= 5:
            return "Coleta de dados - fornecendo informações solicitadas"
        elif stage <= 8:
            return "Detalhes do dano - explicando o problema"
        else:
            return "Finalização - definindo próximos passos"
    
    def _fallback_response(self, agent_last, stage):
        if "nome" in agent_last:
            return f"Meu nome é {self.customer_data['name']}."
        
        elif "cpf" in agent_last:
            if "confirma" in agent_last or "correto" in agent_last:
                return f"Isso mesmo, {self.customer_data['cpf']}."
            return f"Meu CPF é {self.customer_data['cpf']}."
        
        elif "telefone" in agent_last:
            if "segundo" in agent_last or "outro" in agent_last:
                return f"Tenho sim, o segundo é {self.customer_data['phone2']}."
            return f"Meu telefone é {self.customer_data['phone1']}."
        
        elif "placa" in agent_last:
            return f"A placa é {self.customer_data['plate']}, um {self.customer_data['car']}."
        
        elif "endereço" in agent_last or ("onde" in agent_last and "mora" in agent_last):
            return f"Moro na {self.customer_data['address']}."
        
        elif any(word in agent_last for word in ["problema", "aconteceu", "trinca"]):
            if "quando" in agent_last:
                return "Foi ontem à tarde na Marginal Tietê. Uma pedra voou de um caminhão."
            elif "tamanho" in agent_last:
                return "Uns 15 centímetros, tá bem no meio e prejudicando a visão."
            return "Uma pedra bateu e fez uma trinca grande. Preciso resolver logo porque trabalho com o carro."
        
        elif "cidade" in agent_last or "onde" in agent_last:
            return "Estou em São Paulo, trabalho na Vila Olímpia. Qual loja é mais perto?"
        
        elif "loja" in agent_last or "unidade" in agent_last:
            return "Pode ser hoje? Preciso do carro para trabalhar amanhã."
        
        elif "seguro" in agent_last:
            return f"Tenho {self.customer_data['insurance']}. Eles cobrem, né?"
        
        elif "prazo" in agent_last or "tempo" in agent_last:
            return "Quanto tempo demora? É no mesmo dia?"
        
        elif "franquia" in agent_last or "custo" in agent_last:
            return "Qual o valor? Tem alguma taxa extra?"
        
        elif "lgpd" in agent_last or ("compartilhar" in agent_last and "telefone" in agent_last):
            return "Tudo bem, pode compartilhar."
        
        else:
            stage_responses = {
                1: ["Perfeito! Como vocês podem me ajudar?", "Que bom! Qual o procedimento?"],
                2: ["Entendi. O que mais precisa saber?", "Certo. Mais alguma informação?"],
                3: ["Ok. E agora, como fica?", "Perfeito. Qual o próximo passo?"],
                4: ["Ótimo! Quando posso agendar?", "Entendi tudo. Pode ser hoje?"]
            }
            
            responses = stage_responses.get(min(stage, 4), stage_responses[4])
            return random.choice(responses)

def check_api_status():
    status = {}
    try:
        openai_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        status["openai"] = "✅ Configurado" if openai_key else "❌ Não configurado"
    except:
        status["openai"] = "❌ Não configurado"
    return status

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
        st.error("Tempo limite de 20 minutos atingido! Sessão finalizada.")
    
    timer_color = "#ff4444" if elapsed > 1080 else "#ffa500" if elapsed > 900 else "#ffffff"
    timer_placeholder.markdown(f"""
    <div style="text-align: right; margin-bottom: 1rem;">
        <span style="background: {timer_color}; color: {'white' if elapsed <= 900 else 'black'}; 
              padding: 0.5rem 1rem; border-radius: 20px; font-weight: bold;">
            ⏱️ {format_timer(elapsed)} / 20:00
        </span>
    </div>
    """, unsafe_allow_html=True)

header_text = "Voice Coach - Treinador de Ligações Carglass"
if st.session_state.session_state == "active":
    timer_display = f'<div class="timer-container">⏱️ {format_timer(st.session_state.session_duration)} / 20:00</div>'
else:
    timer_display = ""

st.markdown(f'<div class="main-header"><h1>{header_text}</h1><p>Sistema de treinamento profissional com avaliação rigorosa baseada no checklist oficial</p>{timer_display}</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações")
    
    api_status = check_api_status()
    st.markdown(f"""
    <div class="status-card">
        <strong>OpenAI:</strong> {api_status['openai']}<br>
        <small>IA avançada para cliente realístico e voz premium</small>
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
    st.session_state.score = RigorousScoreEngine()

if st.session_state.session_state == "waiting":
    st.markdown("""
    <div class="waiting-state">
        <h2>🎯 Sistema de Treinamento Profissional</h2>
        <p style="font-size: 1.1rem; margin: 1rem 0;">
            Simulação realística de atendimento Carglass com avaliação rigorosa baseada no checklist oficial de 81 pontos.
        </p>
        <p><strong>⏱️ Duração:</strong> Máximo 20 minutos</p>
        <p><strong>📊 Avaliação:</strong> 12 critérios específicos</p>
        <p><strong>🎯 Objetivo:</strong> Treinar atendimento de excelência</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_center = st.columns([1, 2, 1])
    with col_center[1]:
        if st.button("🚀 Iniciar Treinamento", type="primary", use_container_width=True):
            st.session_state.session_state = "active"
            st.session_state.start_time = time.time()
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

    if len([t for t in st.session_state.turns if t["speaker"] == "agent"]) > 0:
        res = st.session_state.score.report()
        
        st.markdown("## 📊 Avaliação em Tempo Real")
        
        col1, col2, col3, col4 = st.columns(4)
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
        
        with st.expander("📋 Checklist Detalhado", expanded=False):
            for item in res["items"]:
                status = "✅" if item["points"] == item["max_points"] else "⚠️" if item["points"] > 0 else "❌"
                st.markdown(f"""
                <div class="checklist-item">
                    <strong>{status} Item {item['idx']}</strong> ({item['points']}/{item['max_points']} pts)<br>
                    <small>{item['label']}</small><br>
                    {f"<em>Evidências: {'; '.join(item['evidence'])}</em>" if item['evidence'] else ""}
                </div>
                """, unsafe_allow_html=True)
        
        if res["tips"]:
            st.subheader("💡 Principais Recomendações")
            for tip in res["tips"]:
                st.info(tip)
    else:
        st.info("👆 Digite sua primeira resposta para iniciar a avaliação!")

elif st.session_state.session_state == "finished":
    st.success("🎉 Treinamento Finalizado!")
    
    res = st.session_state.score.report()
    percentage = round((res['total'] / res['max_total']) * 100, 1)
    
    st.markdown("## 📋 Relatório Final de Performance")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pontuação Final", f"{res['total']}/{res['max_total']}")
    with col2:
        color = "🟢" if percentage >= 80 else "🟡" if percentage >= 60 else "🔴"
        st.metric("Performance", f"{percentage}% {color}")
    with col3:
        st.metric("Duração", format_timer(st.session_state.session_duration))
    
    session_data = {
        'turns': st.session_state.turns,
        'duration': st.session_state.session_duration
    }
    
    pdf_data = generate_pdf_report(session_data, res)
    
    col_pdf, col_new = st.columns(2)
    
    with col_pdf:
        st.download_button(
            label="📄 Baixar Relatório Completo",
            data=pdf_data,
            file_name=f"relatorio_voice_coach_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
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

st.markdown("---")
st.markdown("**🎯 Voice Coach** - Sistema profissional de treinamento Carglass | Avaliação rigorosa baseada no checklist oficial")
