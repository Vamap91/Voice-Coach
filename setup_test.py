#!/usr/bin/env python3
"""
Script de setup e teste para o sistema híbrido Voice Coach
Execute este script para verificar se tudo está funcionando corretamente.
"""

import os
import sys
import pickle
import subprocess
from pathlib import Path

def check_dependencies():
    """Verifica se as dependências estão instaladas."""
    print("🔍 Verificando dependências...")
    
    required_packages = [
        'streamlit',
        'pandas', 
        'openai',
        'gtts',
        'sentence_transformers',
        'sklearn',
        'torch',
        'numpy'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - FALTANDO")
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Instalando pacotes faltando: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
    
    return len(missing) == 0

def test_gabarito():
    """Testa o carregamento do gabarito de embeddings."""
    print("\n📚 Testando gabarito de embeddings...")
    
    gabarito_files = [
        "gabarito_embeddings (1).pkl",
        "gabarito_embeddings.pkl", 
        "data/gabarito_embeddings.pkl"
    ]
    
    gabarito_found = None
    for file_path in gabarito_files:
        if os.path.exists(file_path):
            gabarito_found = file_path
            break
    
    if not gabarito_found:
        print("❌ Arquivo de gabarito não encontrado!")
        print("Procurados:", gabarito_files)
        return False
    
    try:
        with open(gabarito_found, 'rb') as f:
            gabarito = pickle.load(f)
        
        print(f"✅ Gabarito carregado: {gabarito_found}")
        print(f"📊 Itens no gabarito: {len(gabarito)}")
        
        # Mostra estrutura de exemplo
        if len(gabarito) > 0:
            first_key = next(iter(gabarito.keys()))
            first_item = gabarito[first_key]
            print(f"📋 Exemplo - Item {first_key}: {type(first_item)}")
            
            if isinstance(first_item, dict):
                print(f"   Chaves: {list(first_item.keys())}")
            elif hasattr(first_item, 'shape'):
                print(f"   Shape: {first_item.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao carregar gabarito: {e}")
        return False

def test_embeddings():
    """Testa o modelo de embeddings."""
    print("\n🧠 Testando modelo de embeddings...")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        print("Carregando modelo...")
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        
        # Teste básico
        test_text = "Bom dia! Carglass, meu nome é Maria, como posso ajudá-lo?"
        embedding = model.encode([test_text])
        
        print(f"✅ Modelo carregado com sucesso!")
        print(f"📏 Dimensão do embedding: {embedding.shape}")
        print(f"🧮 Exemplo (primeiros 5 valores): {embedding[0][:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro com modelo de embeddings: {e}")
        return False

def create_sample_gabarito():
    """Cria um gabarito de exemplo se não existir."""
    print("\n🛠️  Criando gabarito de exemplo...")
    
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        
        # Gabarito de exemplo
        sample_responses = {
            1: [  # Saudação
                "Bom dia! Carglass, meu nome é Maria, como posso ajudá-lo?",
                "Boa tarde! Carglass, meu nome é João, em que posso auxiliá-lo?",
                "Bom dia! Aqui é da Carglass, meu nome é Ana, como posso ajudá-lo hoje?"
            ],
            5: [  # Escuta atenta - problema original
                "Entendi perfeitamente sua situação",
                "Como você havia mencionado sobre a trinca",
                "Conforme você informou sobre o problema",
                "Baseado no que você me disse",
                "Pelo que compreendi da sua explicação"
            ],
            10: [  # Empatia
                "Entendo sua preocupação, vamos resolver isso rapidamente",
                "Compreendo que é urgente, vou agilizar seu atendimento", 
                "Imagino sua situação, pode deixar que vamos ajudar"
            ]
        }
        
        gabarito = {}
        for item_id, respostas in sample_responses.items():
            embeddings = model.encode(respostas)
            gabarito[item_id] = {
                'respostas': respostas,
                'embeddings': embeddings
            }
        
        # Salva o gabarito
        os.makedirs('data', exist_ok=True)
        with open('data/gabarito_embeddings.pkl', 'wb') as f:
            pickle.dump(gabarito, f)
        
        print("✅ Gabarito de exemplo criado em 'data/gabarito_embeddings.pkl'")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar gabarito: {e}")
        return False

def run_tests():
    """Executa todos os testes."""
    print("🚀 Iniciando testes do Voice Coach Híbrido\n")
    
    # 1. Dependências
    deps_ok = check_dependencies()
    
    # 2. Gabarito
    gabarito_ok = test_gabarito()
    
    # 3. Se gabarito não existe, cria um exemplo
    if not gabarito_ok and deps_ok:
        gabarito_ok = create_sample_gabarito()
    
    # 4. Modelo de embeddings
    embeddings_ok = test_embeddings() if deps_ok else False
    
    # Resultado final
    print("\n" + "="*50)
    print("📋 RESULTADO DOS TESTES:")
    print("="*50)
    print(f"Dependências: {'✅' if deps_ok else '❌'}")
    print(f"Gabarito: {'✅' if gabarito_ok else '❌'}")
    print(f"Embeddings: {'✅' if embeddings_ok else '❌'}")
    print("="*50)
    
    if all([deps_ok, gabarito_ok, embeddings_ok]):
        print("🎉 TUDO PRONTO! Sistema híbrido funcionando perfeitamente.")
        print("\nPara iniciar: streamlit run streamlit_app.py")
    else:
        print("⚠️  Alguns problemas encontrados. Verifique os erros acima.")
        
        if not deps_ok:
            print("💡 Instale as dependências: pip install -r requirements.txt")
        if not gabarito_ok:
            print("💡 Certifique-se de que o arquivo gabarito_embeddings.pkl está no diretório")
        if not embeddings_ok:
            print("💡 Verifique a instalação do sentence-transformers")
    
    return all([deps_ok, gabarito_ok, embeddings_ok])

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
