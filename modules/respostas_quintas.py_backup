"""
Gestão de Respostas de Quintas no Qdrant
Processa emails automaticamente de uma pasta
"""
import os
import json
import random
import email
import re
from datetime import datetime
from pathlib import Path
from email import policy
from email.parser import BytesParser
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

# Configuração
COLLECTION_RESPOSTAS = "respostas_quintas"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
EMAILS_DIR = os.path.join(BASE_DIR, "emails_quintas")  # Pasta onde colocas os .eml

# Modelo de embeddings
model = None

def get_model():
    global model
    if model is None:
        model = SentenceTransformer("intfloat/multilingual-e5-base")
    return model

def inicializar_qdrant():
    """Inicializa Qdrant"""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)
    return QdrantClient(path=os.path.join(BASE_DIR, "qdrant_data"))

client = inicializar_qdrant()

def criar_collection_respostas():
    """Cria a collection de respostas se não existir"""
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if COLLECTION_RESPOSTAS not in collection_names:
            print(f"📦 A criar collection '{COLLECTION_RESPOSTAS}'...")
            client.create_collection(
                collection_name=COLLECTION_RESPOSTAS,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
            print("✅ Collection criada!")
        else:
            print(f"✅ Collection '{COLLECTION_RESPOSTAS}' já existe.")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar collection: {e}")
        return False

def extrair_info_email(msg):
    """Extrai informações do email"""
    try:
        # Headers
        de = msg.get("From", "")
        assunto = msg.get("Subject", "")
        data = msg.get("Date", "")
        
        # Corpo do email
        corpo = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    corpo = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
        else:
            corpo = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        
        return {
            "de": de,
            "assunto": assunto,
            "data": data,
            "corpo": corpo
        }
    except Exception as e:
        print(f"⚠️ Erro ao extrair info: {e}")
        return None

def identificar_quinta_por_email(email_remetente: str, assunto: str):
    """Identifica a quinta pelo email ou assunto"""
    import sqlite3
    
    try:
        # Tenta encontrar no SQLite
        conn = sqlite3.connect(os.path.join(BASE_DIR, "data", "quintas.db"))
        cursor = conn.cursor()
        
        # Busca por email
        email_limpo = email_remetente.lower()
        if "<" in email_limpo:
            email_limpo = email_limpo.split("<")[1].split(">")[0]
        
        cursor.execute("SELECT nome, zona FROM quintas WHERE LOWER(email) LIKE ?", (f"%{email_limpo}%",))
        resultado = cursor.fetchone()
        
        if resultado:
            conn.close()
            return {"nome": resultado[0], "zona": resultado[1]}
        
        # Busca por domínio no website
        dominio = email_limpo.split("@")[1] if "@" in email_limpo else ""
        if dominio:
            cursor.execute("SELECT nome, zona FROM quintas WHERE LOWER(website) LIKE ?", (f"%{dominio}%",))
            resultado = cursor.fetchone()
            if resultado:
                conn.close()
                return {"nome": resultado[0], "zona": resultado[1]}
        
        conn.close()
        
        # Se não encontrou, tenta pelo assunto
        # Ex: "Re: Pedido de informação - Quinta do Vale"
        match = re.search(r'quinta|casa|monte|herdade|hotel|estalagem|[A-Z][a-z]+\s+[A-Z]', assunto, re.IGNORECASE)
        if match:
            return {"nome": assunto, "zona": "Desconhecida"}
        
        return None
        
    except Exception as e:
        print(f"⚠️ Erro ao identificar quinta: {e}")
        return None

def extrair_informacoes_automaticas(corpo: str):
    """Extrai informações estruturadas do texto"""
    info = {
        "disponivel": None,
        "preco_mencionado": None,
        "capacidade_mencionada": None,
        "comodidades": [],
        "refeicoes_incluidas": [],
        "localizacao_detalhes": ""
    }
    
    texto_lower = corpo.lower()
    
    # Disponibilidade
    if any(p in texto_lower for p in ["sim", "disponível", "disponivel", "temos disponibilidade"]):
        info["disponivel"] = True
    elif any(p in texto_lower for p in ["não", "nao", "indisponível", "lotado", "esgotado"]):
        info["disponivel"] = False
    
    # Preço (padrões: €4800, 4.800€, 4800 euros)
    precos = re.findall(r'€?\s*(\d{1,2}[.,]?\d{3})\s*€?', corpo)
    if precos:
        info["preco_mencionado"] = int(precos[0].replace(".", "").replace(",", ""))
    
    # Capacidade (padrões: 43 pessoas, capacidade 50)
    capacidades = re.findall(r'(\d{2,3})\s*pessoas', texto_lower)
    if capacidades:
        info["capacidade_mencionada"] = int(capacidades[0])
    
    # Comodidades
    comodidades_keywords = {
        "piscina": ["piscina"],
        "piscina aquecida": ["piscina aquecida", "piscina interior"],
        "snooker": ["snooker", "bilhar"],
        "churrasqueira": ["churrasqueira", "barbecue", "grelhador"],
        "wifi": ["wifi", "wi-fi", "internet"],
        "estacionamento": ["estacionamento", "parque", "garagem"],
        "jardim": ["jardim", "exterior"],
        "sala jogos": ["sala de jogos", "matraquilhos"]
    }
    
    for comodidade, keywords in comodidades_keywords.items():
        if any(k in texto_lower for k in keywords):
            info["comodidades"].append(comodidade)
    
    # Refeições
    if "pequeno-almoço" in texto_lower or "pequeno almoço" in texto_lower:
        info["refeicoes_incluidas"].append("pequeno-almoço")
    if "almoço" in texto_lower:
        info["refeicoes_incluidas"].append("almoço")
    if "jantar" in texto_lower:
        info["refeicoes_incluidas"].append("jantar")
    
    return info

def processar_email(filepath: str):
    """Processa um ficheiro .eml"""
    try:
        print(f"\n📧 A processar: {os.path.basename(filepath)}")
        
        # Lê o email
        with open(filepath, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        info = extrair_info_email(msg)
        if not info:
            print(f"⚠️ Não consegui extrair info do email")
            return False
        
        # Identifica a quinta
        quinta_info = identificar_quinta_por_email(info["de"], info["assunto"])
        if not quinta_info:
            print(f"⚠️ Não consegui identificar a quinta")
            print(f"   De: {info['de']}")
            print(f"   Assunto: {info['assunto']}")
            return False
        
        print(f"✓ Quinta identificada: {quinta_info['nome']}")
        
        # Extrai informações automáticas
        info_auto = extrair_informacoes_automaticas(info["corpo"])
        
        # Gera resumo simples
        resumo = f"Resposta de {quinta_info['nome']}"
        if info_auto["disponivel"] is not None:
            resumo += f" - {'Disponível' if info_auto['disponivel'] else 'Indisponível'}"
        if info_auto["preco_mencionado"]:
            resumo += f" - €{info_auto['preco_mencionado']}"
        
        # Cria payload
        payload = {
            "quinta_nome": quinta_info["nome"],
            "quinta_zona": quinta_info.get("zona", "Desconhecida"),
            "email_remetente": info["de"],
            "data_resposta": info["data"],
            "assunto": info["assunto"],
            "meio_resposta": "email",
            
            "texto_completo": info["corpo"],
            "resumo": resumo,
            
            "informacao_extraida": info_auto,
            
            "tags": info_auto["comodidades"],
            
            "metadata": {
                "ficheiro_origem": os.path.basename(filepath),
                "processado_em": datetime.now().isoformat()
            }
        }
        
        # Cria embedding do texto completo
        m = get_model()
        vector = m.encode(info["corpo"]).tolist()
        
        # Guarda no Qdrant
        ponto = models.PointStruct(
            id=random.randint(0, 1_000_000_000),
            vector=vector,
            payload=payload
        )
        
        client.upsert(collection_name=COLLECTION_RESPOSTAS, points=[ponto])
        
        print(f"✅ Email guardado no Qdrant!")
        print(f"   Resumo: {resumo}")
        if info_auto["comodidades"]:
            print(f"   Comodidades: {', '.join(info_auto['comodidades'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao processar email: {e}")
        import traceback
        traceback.print_exc()
        return False

def processar_pasta_emails():
    """Processa todos os emails na pasta"""
    try:
        # Cria a collection
        criar_collection_respostas()
        
        # Cria pasta se não existir
        os.makedirs(EMAILS_DIR, exist_ok=True)
        
        # Lista emails
        emails = list(Path(EMAILS_DIR).glob("*.eml"))
        
        if not emails:
            print(f"⚠️ Nenhum email encontrado em {EMAILS_DIR}")
            print(f"💡 Coloca ficheiros .eml nessa pasta")
            return
        
        print(f"📬 Encontrados {len(emails)} emails")
        
        sucesso = 0
        erros = 0
        
        for email_path in emails:
            if processar_email(str(email_path)):
                sucesso += 1
            else:
                erros += 1
        
        print(f"\n✅ Processamento completo!")
        print(f"   Sucesso: {sucesso}")
        print(f"   Erros: {erros}")
        
    except Exception as e:
        print(f"❌ Erro ao processar pasta: {e}")
        import traceback
        traceback.print_exc()

def buscar_respostas_quinta(nome_quinta: str):
    """Busca respostas de uma quinta específica"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_RESPOSTAS,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="quinta_nome",
                        match=models.MatchValue(value=nome_quinta)
                    )
                ]
            ),
            limit=10
        )
        
        return [r.payload for r in resultados]
    except Exception as e:
        print(f"❌ Erro ao buscar respostas: {e}")
        return []

def buscar_semantica_respostas(query: str, limit=5):
    """Busca semântica nas respostas"""
    try:
        m = get_model()
        vector = m.encode(query).tolist()
        
        resultados = client.search(
            collection_name=COLLECTION_RESPOSTAS,
            query_vector=vector,
            limit=limit
        )
        
        return [
            {
                "quinta": r.payload["quinta_nome"],
                "zona": r.payload.get("quinta_zona"),
                "resumo": r.payload.get("resumo"),
                "comodidades": r.payload.get("informacao_extraida", {}).get("comodidades", []),
                "score": r.score
            }
            for r in resultados
        ]
    except Exception as e:
        print(f"❌ Erro na busca semântica: {e}")
        return []

def listar_quintas_com_respostas():
    """Lista todas as quintas que já responderam"""
    try:
        resultados, _ = client.scroll(
            collection_name=COLLECTION_RESPOSTAS,
            limit=100
        )
        
        quintas = {}
        for r in resultados:
            nome = r.payload["quinta_nome"]
            if nome not in quintas:
                quintas[nome] = {
                    "nome": nome,
                    "zona": r.payload.get("quinta_zona"),
                    "total_respostas": 0
                }
            quintas[nome]["total_respostas"] += 1
        
        return list(quintas.values())
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

if __name__ == "__main__":
    print("🚀 Iniciando processamento de emails...")
    print(f"📂 Pasta de emails: {EMAILS_DIR}")
    print()
    processar_pasta_emails()
    
    print("\n📊 Testando busca semântica...")
    resultados = buscar_semantica_respostas("quintas com piscina aquecida")
    for r in resultados:
        print(f"  • {r['quinta']} ({r['zona']}) - Score: {r['score']:.2f}")