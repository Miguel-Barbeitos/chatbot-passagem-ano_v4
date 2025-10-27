# ─────────────────────────────────────────────────────────────────────────────
# services/utils.py — Utilitários, cache e logging
# ─────────────────────────────────────────────────────────────────────────────

import os
import json
import logging
import streamlit as st


# Logger simples e consistente
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)




@st.cache_data(ttl=60)
def carregar_json(path, default=None):
try:
with open(path, "r", encoding="utf-8") as f:
return json.load(f)
except Exception as e:
st.error(f"⚠️ Erro a carregar JSON em {path}: {e}")
return default or []


def normalizar(txt: str) -> str:
import re
import unicodedata
if not isinstance(txt, str):
return ""
t = txt.lower().strip()
t = unicodedata.normalize("NFKD", t)
t = "".join(c for c in t if not unicodedata.combining(c))
t = re.sub(r"[^\w\s]", " ", t)
t = re.sub(r"\s+", " ", t).strip()
return t




def exportar_historico_local(historico):
os.makedirs("data", exist_ok=True)
caminho = os.path.join("data", "chat_log.json")
with open(caminho, "w", encoding="utf-8") as f:
json.dump(historico or [], f, ensure_ascii=False, indent=2)