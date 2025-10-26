import os
import re
import sqlite3
import pandas as pd
from datetime import datetime

EXCEL_PATH = "data/locais_com_quintas_destacadas_ATUALIZADO_v2.xlsx"
DB_PATH = "data/quintas.db"
TABLE = "quintas"

os.makedirs("data", exist_ok=True)

def to_bool(x):
    if pd.isna(x): return None
    s = str(x).strip().lower()
    return 1 if s in ["sim","yes","true","✓","✔"] else 0 if s in ["não","nao","no","false","✗","x"] else None

def to_money(x):
    if pd.isna(x): return None
    s = str(x).replace("€","").replace(".","").replace(",","").replace(" ","")
    return float(re.sub(r"[^\d.]", "", s)) if re.search(r"\d", s) else None

def to_int(x):
    if pd.isna(x): return None
    m = re.search(r"\d+", str(x))
    return int(m.group(0)) if m else None

def to_date_iso(x):
    if pd.isna(x): return None
    try:
        d = pd.to_datetime(x, dayfirst=True, errors="coerce")
        return d.date().isoformat() if pd.notna(d) else None
    except: return None

print("📖 A carregar Excel...")
df = pd.read_excel(EXCEL_PATH)

# Renomear colunas para nomes curtos
mapeamento = {
    "Nome": "nome",
    "Zona": "zona",
    "Morada": "morada",
    "Email": "email",
    "Telefone": "telefone",
    "Website": "website",
    "Estado": "estado",
    "Resposta": "resposta",
    "Capacidade ≥ 43?": "cap_43",
    "≤ 4 500 € (5 noites)?": "preco_4500",
    "Estimativa custo (5 noites)": "custo_estimado",
    "Capacidade (n.º pessoas, confirmada)": "capacidade",
    "Última resposta (data)": "ultima_resposta",
    "Proposta tarifária (detalhe)": "proposta",
    "Unidades (detalhe – quartos/casas por tipologia)": "unidades",
    "N.º unidades consideradas": "unidades_n",
    "Observação unidades": "observacao",
    "Custo total (5 noites) – cenário base": "custo_total",
    "Resumo da resposta": "resumo",
    "Observações": "obs",
    "Notas do cálculo": "notas",
}

df = df.rename(columns=mapeamento)

# Limpeza e normalização
df["cap_43"] = df["cap_43"].map(to_bool)
df["preco_4500"] = df["preco_4500"].map(to_bool)
df["custo_estimado"] = df["custo_estimado"].map(to_money)
df["custo_total"] = df["custo_total"].map(to_money)
df["capacidade"] = df["capacidade"].map(to_int)
df["unidades_n"] = df["unidades_n"].map(to_int)
df["ultima_resposta"] = df["ultima_resposta"].map(to_date_iso)

# Apenas colunas válidas
cols = list(mapeamento.values())
df = df[[c for c in cols if c in df.columns]]

print("💾 A gravar na base...")
conn = sqlite3.connect(DB_PATH)
conn.execute(f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT, zona TEXT, morada TEXT, email TEXT, telefone TEXT, website TEXT,
    estado TEXT, resposta TEXT,
    cap_43 INTEGER, preco_4500 INTEGER,
    custo_estimado REAL, capacidade INTEGER, ultima_resposta TEXT,
    proposta TEXT, unidades TEXT, unidades_n INTEGER, observacao TEXT,
    custo_total REAL, resumo TEXT, obs TEXT, notas TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
""")
df.to_sql(TABLE, conn, if_exists="append", index=False)
conn.commit()

# Índices básicos para mobile
conn.execute("CREATE INDEX IF NOT EXISTS idx_quintas_estado ON quintas(estado)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_quintas_zona ON quintas(zona)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_quintas_capacidade ON quintas(capacidade)")
conn.commit()
conn.close()

print(f"✅ Importação concluída: {len(df)} linhas inseridas.")
