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
BASE_DIR = os.path.dirname(os.path.dirname(__file__)) # raiz do projeto
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


client = inicializar_qdrant()
# Criar coleção se não existir
try:
    if COLLECTION_NAME not in [c.name for c in client.get_collections().collections]:
        print(f"🆕 A criar coleção '{COLLECTION_NAME}' no Qdrant Cloud...")
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
def get_contexto_base(raw=False):
try:
with open(DATA_PATH, "r", encoding="utf-8") as f:
dados = json.load(f)
if raw:
return dados
texto = []
for k, v in dados.items():
if isinstance(v, bool):
texto.append(f"{k.replace('_', ' ')}: {'sim' if v else 'não'}")
elif isinstance(v, dict):
subtxt = ", ".join(f"{sk}: {sv}" for sk, sv in v.items())
texto.append(f"{k.replace('_', ' ')}: {subtxt}")
elif isinstance(v, list):
texto.append(f"{k.replace('_', ' ')}: {', '.join(v)}")
else:
texto.append(f"{k.replace('_', ' ')}: {v}")
return "\n".join(texto)
except Exception as e:
print(f"⚠️ Erro ao ler contexto base: {e}")
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
points=[models.PointStruct(id=random.randint(0, 1_000_000_000), vector=vector, payload=payload)],
)
print(f"💾 Mensagem guardada para {user} ({contexto})")
except Exception as e:
print(f"❌ Erro ao guardar mensagem: {e}")

def guardar_confirmacao(nome: str):
try:
existentes, _ = client.scroll(
collection_name=COLLECTION_NAME,
scroll_filter=models.Filter(
must=[models.FieldCondition(key="contexto", match=models.MatchValue(value="confirmacoes")),
models.FieldCondition(key="user", match=models.MatchValue(value=nome))]
),
limit=1,
)
if existentes:
print(f"ℹ️ {nome} já estava confirmado.")
return
vector = np.zeros(768).tolist()
payload = {"user": nome, "resposta": f"{nome} confirmou presença 🎉", "contexto": "confirmacoes"}
client.upsert(
collection_name=COLLECTION_NAME,
points=[models.PointStruct(id=random.randint(0, 1_000_000_000), vector=vector, payload=payload)],
)
print(f"✅ {nome} registado como confirmado no Qdrant.")
except Exception as e:
print(f"⚠️ Erro ao guardar confirmação: {e}")


def get_confirmacoes():
try:
pontos, _ = client.scroll(
collection_name=COLLECTION_NAME,
scroll_filter=models.Filter(must=[models.FieldCondition(key="contexto", match=models.MatchValue(value="confirmacoes"))]),
limit=200,
)
confirmados = sorted({p.payload.get("user") for p in pontos if p.payload.get("user")})
print(f"📋 Confirmados no Qdrant: {confirmados}")
return confirmados
except Exception as e:
print(f"⚠️ Erro ao obter confirmações: {e}")
return []


def exportar_confirmacoes_json(caminho=None):
try:
if caminho is None:
os.makedirs(DATA_DIR, exist_ok=True)
caminho = os.path.join(DATA_DIR, "confirmados.json")
confirmados = get_confirmacoes()
dados = {"total_confirmados": len(confirmados), "confirmados": confirmados}
with open(caminho, "w", encoding="utf-8") as f:
json.dump(dados, f, ensure_ascii=False, indent=2)
print(f"💾 Exportação concluída: {caminho}")
except Exception as e:
print(f"⚠️ Erro ao exportar confirmações: {e}")

# =====================================================
# 🧠 DETEÇÃO SIMPLES DE INTENÇÃO
# =====================================================
def identificar_intencao(pergunta: str) -> str:
p = pergunta.lower()
if any(t in p for t in ["olá", "ola", "bom dia", "boa tarde", "boa noite"]):
return "saudacao"
if any(t in p for t in ["quem vai", "confirmou", "confirmacoes", "quantas pessoas"]):
return "confirmacoes"
if any(t in p for t in ["onde", "local", "sitio", "morada"]):
return "local"
if any(t in p for t in ["hora", "quando", "que horas", "começa"]):
return "hora"
if any(t in p for t in ["wifi", "internet", "rede"]):
return "wifi"
if any(t in p for t in ["roupa", "dress", "vestir", "codigo", "cor"]):
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