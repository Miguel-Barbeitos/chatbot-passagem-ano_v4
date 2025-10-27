# ─────────────────────────────────────────────────────────────────────────────
# services/learning_qdrant.py — versão alinhada e otimizada
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import random
import numpy as np
from qdrant_client import QdrantClient, models

# =====================================================
# ⚙️ CONFIGURAÇÃO GERAL
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # raiz do projeto
DATA_DIR = os.path.join(BASE_DIR, "data")
QDRANT_PATH = os.path.join(BASE_DIR, "qdrant_data")
DATA_PATH = os.path.join(DATA_DIR, "event.json")
COLLECTION_NAME = "chatbot_festa"

print(f"📂 Qdrant ativo em: {QDRANT_PATH}")
print(f"📄 Ficheiro de contexto: {DATA_PATH}")

# =====================================================
# 🧠 MODELO DE EMBEDDINGS (LAZY LOADING)
# =====================================================
_model = None

def get_model():
    global _model
    if _model is None:
        print("🧠 A inicializar modelo de embeddings...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("intfloat/multilingual-e5-base")
        print("✅ Modelo carregado com sucesso.")
    return _model

# =====================================================
# 💾 CONEXÃO AO QDRANT
# =====================================================
def inicializar_qdrant():
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if qdrant_url and qdrant_key:
        print("☁️ Conectado ao Qdrant Cloud.")
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)

    print("💾 A usar Qdrant local (modo desenvolvimento).")
    return QdrantClient(path=QDRANT_PATH)

# =====================================================
# 🧱 CRIAR COLEÇÃO SE NÃO EXISTIR
# =====================================================
client = inicializar_qdrant()

try:
    colecoes_existentes = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in colecoes_existentes:
        print(f"🆕 A criar coleção '{COLLECTION_NAME}' no Qdrant...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
        )
        print("✅ Coleção criada com sucesso!")
    else:
        print(f"ℹ️ Coleção '{COLLECTION_NAME}' já existe.")
except Exception as e:
    print(f"⚠️ Erro ao criar/verificar coleção: {e}")

# =====================================================
# 📂 CONTEXTO BASE (event.json)
# =====================================================
def get_contexto_base(raw: bool = False):
    """
    Lê o contexto base a partir do ficheiro DATA_PATH (event.json por defeito).
    raw=True devolve o dicionário original; raw=False devolve um texto amigável.
    """
    try:
        if not os.path.exists(DATA_PATH):
            print(f"⚠️ Ficheiro não encontrado: {DATA_PATH}")
            return {} if raw else "Informações da festa indisponíveis."

        with open(DATA_PATH, "r", encoding="utf-8") as f:
            dados = json.load(f)

        if raw:
            return dados

        # Converte dicionário em texto legível
        linhas = []
        for k, v in dados.items():
            key = k.replace("_", " ")
            if isinstance(v, bool):
                linhas.append(f"{key}: {'sim' if v else 'não'}")
            elif isinstance(v, list):
                linhas.append(f"{key}: {', '.join(str(x) for x in v)}")
            elif isinstance(v, dict):
                sub = ", ".join(f"{sk}: {sv}" for sk, sv in v.items())
                linhas.append(f"{key}: {sub}")
            else:
                linhas.append(f"{key}: {v}")
        return "\n".join(linhas)

    except Exception as e:
        print(f"⚠️ Erro ao carregar contexto base: {e}")
        return {} if raw else "Informações da festa indisponíveis."

# =====================================================
# 💾 GUARDAR MENSAGEM E CONFIRMAÇÕES
# =====================================================
def guardar_mensagem(user, pergunta, resposta, contexto="geral", perfil=None):
    try:
        model = get_model()
        vector = model.encode(pergunta).tolist()
        payload = {
            "user": user,
            "pergunta": pergunta,
            "resposta": resposta,
            "contexto": contexto,
            "perfil": perfil.get("personalidade", "desconhecida") if perfil else "desconhecido",
        }
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=random.randint(0, 1_000_000_000),
                    vector=vector,
                    payload=payload
                )
            ],
        )
        print(f"💾 Mensagem guardada para {user} ({contexto})")
    except Exception as e:
        print(f"❌ Erro ao guardar mensagem: {e}")

def guardar_confirmacao(nome: str):
    try:
        # Evitar duplicados
        existentes, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="contexto",
                        match=models.MatchValue(value="confirmacoes")
                    ),
                    models.FieldCondition(
                        key="user",
                        match=models.MatchValue(value=nome)
                    ),
                ]
            ),
            limit=1,
        )
        if existentes:
            print(f"ℹ️ {nome} já estava confirmado.")
            return

        # Guardar confirmação (vector 'dummy' de zeros)
        vector = np.zeros(768).tolist()
        payload = {
            "user": nome,
            "resposta": f"{nome} confirmou presença 🎉",
            "contexto": "confirmacoes",
        }
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=random.randint(0, 1_000_000_000),
                    vector=vector,
                    payload=payload
                )
            ],
        )
        print(f"✅ {nome} registado como confirmado no Qdrant.")
    except Exception as e:
        print(f"⚠️ Erro ao guardar confirmação: {e}")

def get_confirmacoes():
    """
    Devolve lista de nomes confirmados (ordenada e sem duplicados).
    """
    try:
        pontos, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="contexto",
                        match=models.MatchValue(value="confirmacoes")
                    )
                ]
            ),
            limit=1000,
        )
        nomes = sorted({p.payload.get("user") for p in pontos if p.payload and p.payload.get("user")})
        print(f"📋 Confirmados no Qdrant: {nomes}")
        return nomes
    except Exception as e:
        print(f"⚠️ Erro ao carregar confirmações: {e}")
        return []

def exportar_confirmacoes_json(output_path=os.path.join(DATA_DIR, "confirmados.json")):
    try:
        confirmados = get_confirmacoes()
        dados = {"total_confirmados": len(confirmados), "confirmados": confirmados}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"✅ Exportadas {len(confirmados)} confirmações para {output_path}")
    except Exception as e:
        print(f"⚠️ Erro ao exportar confirmações: {e}")

# =====================================================
# 🧠 DETEÇÃO SIMPLES DE INTENÇÃO
# =====================================================
def identificar_intencao(pergunta: str) -> str:
    p = (pergunta or "").lower()
    if any(t in p for t in ["olá", "ola", "bom dia", "boa tarde", "boa noite"]):
        return "saudacao"
    if any(t in p for t in ["quem vai", "confirmou", "confirmacoes", "confirmações", "quantas pessoas"]):
        return "confirmacoes"
    if any(t in p for t in ["onde", "local", "sitio", "sítio", "morada"]):
        return "local"
    if any(t in p for t in ["hora", "quando", "que horas", "começa", "inicio", "início"]):
        return "hora"
    if any(t in p for t in ["wifi", "internet", "rede"]):
        return "wifi"
    if any(t in p for t in ["roupa", "dress", "vestir", "codigo", "código", "cor"]):
        return "roupa"
    if any(t in p for t in ["levar", "trazer", "preciso levar"]):
        return "logistica"
    if any(t in p for t in ["futebol", "benfica", "porto", "sporting", "jogo"]):
        return "futebol"
    if any(t in p for t in ["piada", "anedota", "brincadeira"]):
        return "piadas"
    if any(t in p for t in ["comida", "jantar", "menu", "sobremesa"]):
        return "comida"
    if any(t in p for t in ["bebida", "cerveja", "vinho", "champanhe", "cocktail"]):
        return "bebida"
    return "geral"


    # =====================================================
# 🔍 PROCURA DE RESPOSTAS SEMELHANTES
# =====================================================
def procurar_resposta_semelhante(pergunta: str, limite: int = 3):
    """
    Procura no Qdrant as respostas mais semelhantes à pergunta do utilizador.
    Retorna a melhor resposta encontrada ou None.
    """
    try:
        model = get_model()
        vector = model.encode(pergunta).tolist()

        resultados = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=limite,
        )

        if not resultados:
            print("ℹ️ Nenhuma resposta semelhante encontrada.")
            return None

        melhor = resultados[0]
        resposta = melhor.payload.get("resposta")
        similaridade = melhor.score
        print(f"🔍 Resposta semelhante encontrada (score={similaridade:.3f}) → {resposta}")
        return resposta

    except Exception as e:
        print(f"⚠️ Erro ao procurar resposta semelhante: {e}")
        return None
