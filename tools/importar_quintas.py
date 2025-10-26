import pandas as pd
import sqlite3
import os
import hashlib

# =====================================================
# ⚙️ CONFIGURAÇÃO
# =====================================================
EXCEL_PATH = "data/locais_com_quintas_destacadas_ATUALIZADO_v2.xlsx"
DB_PATH = "data/quintas.db"
TABELA = "quintas"


# =====================================================
# 🧠 FUNÇÕES AUXILIARES
# =====================================================
def hash_registo(row):
    """Cria um hash único para detetar alterações."""
    texto = "|".join(str(v) for v in row.values)
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def limpar_valor(v):
    """Normaliza os valores (booleans, strings e NaN)."""
    if pd.isna(v):
        return None
    if isinstance(v, str):
        v = v.strip()
        if v.lower() in ["sim", "yes", "true"]:
            return True
        if v.lower() in ["não", "nao", "no", "false"]:
            return False
    return v


def criar_tabela(conn):
    """Cria a tabela 'quintas' se ainda não existir."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quintas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            zona TEXT,
            morada TEXT,
            email TEXT,
            telefone TEXT,
            website TEXT,
            estado TEXT,
            resposta TEXT,
            capacidade_43 BOOLEAN,
            custo_4500 BOOLEAN,
            estimativa_custo REAL,
            capacidade_confirmada INTEGER,
            ultima_resposta TEXT,
            proposta_tarifaria TEXT,
            unidades_detalhe TEXT,
            num_unidades INTEGER,
            observacao_unidades TEXT,
            custo_total REAL,
            resumo_resposta TEXT,
            observacoes TEXT,
            notas_calculo TEXT,
            hash_registo TEXT
        )
    """)
    conn.commit()


def carregar_existentes(conn):
    """Lê os registos existentes e devolve (nome → hash)."""
    query = f"SELECT nome, hash_registo FROM {TABELA}"
    try:
        df = pd.read_sql_query(query, conn)
        return dict(zip(df["nome"], df["hash_registo"]))
    except Exception:
        return {}


# =====================================================
# 📖 IMPORTAÇÃO DO EXCEL
# =====================================================
print("📖 A carregar ficheiro Excel...")
df = pd.read_excel(EXCEL_PATH)
print(f"✅ {len(df)} registos carregados.\n")

# Normalizar nomes de colunas
mapeamento = {
    "Nome": "nome",
    "Zona": "zona",
    "Morada": "morada",
    "Email": "email",
    "Telefone": "telefone",
    "Website": "website",
    "Estado": "estado",
    "Resposta": "resposta",
    "Capacidade ≥ 43?": "capacidade_43",
    "≤ 4 500 € (5 noites)?": "custo_4500",
    "Estimativa custo (5 noites)": "estimativa_custo",
    "Capacidade (n.º pessoas, confirmada)": "capacidade_confirmada",
    "Última resposta (data)": "ultima_resposta",
    "Proposta tarifária (detalhe)": "proposta_tarifaria",
    "Unidades (detalhe – quartos/casas por tipologia)": "unidades_detalhe",
    "N.º unidades consideradas": "num_unidades",
    "Observação unidades": "observacao_unidades",
    "Custo total (5 noites) – cenário base": "custo_total",
    "Resumo da resposta": "resumo_resposta",
    "Observações": "observacoes",
    "Notas do cálculo": "notas_calculo"
}

df = df.rename(columns=mapeamento)
df = df.applymap(limpar_valor)

# Adicionar hash de cada registo
df["hash_registo"] = df.apply(hash_registo, axis=1)

# =====================================================
# 💾 CONEXÃO E SINCRONIZAÇÃO
# =====================================================
os.makedirs("data", exist_ok=True)
conn = sqlite3.connect(DB_PATH)
criar_tabela(conn)

existentes = carregar_existentes(conn)
novos, atualizados = 0, 0

for _, row in df.iterrows():
    nome = row["nome"]
    hash_atual = row["hash_registo"]

    # Inserção nova
    if nome not in existentes:
        placeholders = ", ".join(["?"] * len(row))
        colunas = ", ".join(row.index)
        conn.execute(f"INSERT INTO {TABELA} ({colunas}) VALUES ({placeholders})", tuple(row))
        novos += 1

    # Atualização (se o hash for diferente)
    elif existentes[nome] != hash_atual:
        sets = ", ".join([f"{c}=?" for c in row.index])
        conn.execute(f"UPDATE {TABELA} SET {sets} WHERE nome=?", tuple(row) + (nome,))
        atualizados += 1

conn.commit()
conn.close()

print(f"✅ Sincronização concluída!")
print(f"🆕 Novos registos: {novos}")
print(f"🔁 Atualizados: {atualizados}")
print(f"📦 Total atual: {len(df)} registos.\n")
