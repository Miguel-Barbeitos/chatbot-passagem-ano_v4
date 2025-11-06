# -*- coding: utf-8 -*-
"""
App principal do Chatbot de Passagem de Ano 🎉
Integra confirmações, quintas e respostas gerais via LLM.
"""

import streamlit as st
import re
from datetime import datetime

# Importações principais
from llm_groq import gerar_resposta_llm
from modules.organizacao import responder_pergunta_organizacao
from modules.confirmacoes import (
    confirmar_pessoa,
    confirmar_familia_completa,
    get_confirmados,
    get_estatisticas,
    verificar_confirmacao_pessoa,
)
from modules.perfis_manager import (
    listar_todos_perfis,
    buscar_perfil,
    listar_familia,
)

# ==============================
# CONFIGURAÇÃO DA APP
# ==============================

st.set_page_config(page_title="Chatbot Passagem de Ano", layout="centered")
st.title("🎉 Chatbot Passagem de Ano")

# ==============================
# SECÇÃO: IDENTIDADE DO UTILIZADOR
# ==============================

st.markdown("### 👤 Escolhe quem és")

perfis_lista = listar_todos_perfis()
nomes = sorted(set(p["nome"] for p in perfis_lista if p.get("nome")))

nome_sel = st.selectbox(
    "Quem és tu?",
    nomes,
    index=0,
    help="Escolhe o teu nome para o chatbot saber quem está a falar."
)

st.info(
    f"Olá, **{nome_sel}** 👋! Exemplos: *eu vou*, *nós vamos*, "
    "*vai a família?*, *quem vai?*, *já temos quinta?*, *e a Isabel, posso levar?*"
)

# ==============================
# SECÇÃO: CHAT PRINCIPAL
# ==============================

st.markdown("---")
st.markdown("### 💬 Fala comigo!")

pergunta = st.text_input(
    "Escreve a tua pergunta:",
    placeholder="Ex: Já temos quinta? ou O João Paulo vai?"
)
botao = st.button("Enviar")


# ======================================================
# HELPERS
# ======================================================

PALAVRAS_IGNORADAS_NOME = {
    "o", "a", "os", "as", "de", "da", "do", "dos", "das",
    "vai", "vem", "foi", "irá", "comparece", "confirmou",
    "família", "familia", "nós", "nos", "todos", "toda",
    "eu", "vou", "vamos", "levar", "trazer"
}

def _limpar_artigos(txt: str) -> str:
    return re.sub(r"^(?:o|a|os|as|de|da|do|dos|das)\s+", "", txt.strip(), flags=re.I)

def extrair_nome(pergunta: str) -> str | None:
    """Extrai nome próprio, ignorando palavras funcionais."""
    tokens = [
        w.capitalize()
        for w in re.findall(r"[A-Za-zÀ-ÿ]+", pergunta)
        if w.lower() not in PALAVRAS_IGNORADAS_NOME
    ]
    if not tokens:
        return None
    nome = " ".join(tokens[:2]) if len(tokens) >= 2 else tokens[0]
    return _limpar_artigos(nome)

def intencao_familia_confirmar(p: str) -> bool:
    p = p.lower()
    return (
        ("nós" in p or "nos" in p or "família" in p or "familia" in p or "todos" in p)
        and any(v in p for v in ["vamos", "confirmo", "marca", "marcar", "regista", "registar"])
    )

def pergunta_sobre_familia_ir(p: str) -> bool:
    p = p.lower()
    return (
        ("família" in p or "familia" in p)
        and any(v in p for v in ["vai", "vão", "quem", "está", "esta", "confirmado", "confirmados"])
        and not intencao_familia_confirmar(p)
    )

def intencao_posso_levar(p: str) -> bool:
    p = p.lower()
    return any(k in p for k in ["posso levar", "posso trazer", "levo", "trago"])

# -----------------------------
# Parser semântico de relações
# -----------------------------

_REL_FILHOS = r"(?:filh[oa]s?)"
_REL_CONJ = r"(?:c[ôo]njuge|marido|esposa|namorad[oa])"

def _normalizar_relacao(palavra: str) -> str:
    palavra = palavra.lower()
    if re.search(_REL_FILHOS, palavra, re.I):
        return "filhos"
    if re.search(_REL_CONJ, palavra, re.I):
        return "conjuge"
    return ""

def interpretar_relacao(pergunta: str):
    """
    Tenta perceber perguntas como:
    - 'A Isabel vai levar as filhas?'
    - 'O Tiago leva o filho?'
    - 'Quem são os acompanhantes da Isabel?'
    Retorna dict {nome, tipo_relacao, modo} ou None.
    """
    p = pergunta.strip()

    # 1) Acompanhantes de X (lista de conjuge + filhos)
    m = re.search(r"(?i)quem\s+s[aã]o\s+os\s+acompanhantes\s+da?\s+([A-Za-zÀ-ÿ ]+)", p)
    if m:
        nome = _limpar_artigos(m.group(1))
        return {"nome": nome, "tipo_relacao": "acompanhantes", "modo": "listar"}

    # 2) [Nome] vai/leva/traz [o/os/a/as] (filho/filha/filhos/filhas|cônjuge...)
    m = re.search(
        rf"(?i)\b([A-Za-zÀ-ÿ ]+?)\s+(?:vai\s+levar|leva|traz|vai\s+trazer)\s+(?:o|os|a|as)?\s*({_REL_FILHOS}|{_REL_CONJ})\b",
        p
    )
    if m:
        nome = _limpar_artigos(m.group(1))
        rel = _normalizar_relacao(m.group(2))
        if rel:
            return {"nome": nome, "tipo_relacao": rel, "modo": "confirmacao"}

    # 3) 'Os/As filhos/filhas de [Nome] vão?' (variação)
    m = re.search(
        rf"(?i)\b(?:o|os|a|as)?\s*({_REL_FILHOS})\s+de\s+([A-Za-zÀ-ÿ ]+?)\s+(?:v[aã]o|v[ãa]o\s+ir|v[ãa]o\s+estar)\b",
        p
    )
    if m:
        rel = _normalizar_relacao(m.group(1))
        nome = _limpar_artigos(m.group(2))
        if rel:
            return {"nome": nome, "tipo_relacao": rel, "modo": "confirmacao"}

    return None


# ======================================================
# FUNÇÃO PRINCIPAL DE RESPOSTA
# ======================================================

def gerar_resposta(pergunta: str):
    """Centraliza a lógica de decisão da resposta."""
    if not pergunta:
        return "😅 Podes repetir a pergunta?"

    pergunta_l = pergunta.lower().strip()

    # MULTI-INTENÇÕES: "eu vou, o Tiago vai?"
    partes = re.split(r"[,.!?]", pergunta)
    if len(partes) > 1:
        respostas = []
        for parte in partes:
            parte = parte.strip()
            if not parte:
                continue
            resposta_parcial = gerar_resposta(parte)
            if resposta_parcial:
                respostas.append(resposta_parcial)
        return "\n\n".join(respostas)

    # Contexto do utilizador atual
    perfil_util = buscar_perfil(nome_sel) or {}
    familia_id = perfil_util.get("familia_id")
    membros_familia = listar_familia(familia_id) if familia_id else []
    nomes_membros_familia = [m.get("nome") for m in membros_familia] if membros_familia else []

    # PRIORIDADE 1: Organização / Quintas
    resposta_org = responder_pergunta_organizacao(pergunta)
    if resposta_org:
        return resposta_org

    # PRIORIDADE 2A: Confirmar toda a família
    if intencao_familia_confirmar(pergunta_l):
        resultado = confirmar_familia_completa(nome_sel)
        return resultado["mensagem"]

    # PRIORIDADE 2B: Perguntas sobre FAMÍLIA (sem confirmar)
    if pergunta_sobre_familia_ir(pergunta_l):
        confirmados = set(get_confirmados())
        if not nomes_membros_familia:
            return f"🤔 {nome_sel}, não encontrei a tua família registada."

        ja_vao = [n for n in nomes_membros_familia if n in confirmados]
        por_confirmar = [n for n in nomes_membros_familia if n not in confirmados]

        if ja_vao and por_confirmar:
            return (
                "👨‍👩‍👧‍👦 Estado da tua família:\n"
                + "✅ Confirmados: " + ", ".join(sorted(set(ja_vao)))
                + "\n⏳ Por confirmar: " + ", ".join(sorted(set(por_confirmar)))
            )
        elif ja_vao:
            ja_vao_unicos = list(dict.fromkeys(ja_vao))
            return "🎉 Toda a tua família já está confirmada: " + ", ".join(ja_vao_unicos)
        else:
            return "🙃 Ainda ninguém da tua família confirmou."

    # PRIORIDADE 2C: 'Posso levar...'
    if intencao_posso_levar(pergunta_l):
        if "família" in pergunta_l or "familia" in pergunta_l:
            return f"Claro que sim, {nome_sel}! 🏡 A tua família faz parte da lista de convidados."
        possivel = extrair_nome(pergunta)
        if possivel and (possivel in nomes_membros_familia):
            return f"Sim, **{possivel}** é da tua família e está incluíd{ 'o' if possivel not in ['Isabel','Sandra','Filipa','Inês'] else 'a' }."
        return f"Desculpa, {nome_sel}, não tenho essa pessoa como tua família direta. Queres que verifique na lista?"

    # >>> NOVO BLOCO: PERGUNTAS DE RELAÇÃO (filhos/cônjuge/acompanhantes) <<<
    rel_info = interpretar_relacao(pergunta)
    if rel_info:
        nome_querido = rel_info["nome"]
        alvo = buscar_perfil(nome_querido)
        if not alvo:
            return f"🤔 Não encontrei ninguém chamado '{nome_querido}' na lista de convidados."

        relacoes = alvo.get("relacoes", {}) or {}
        confirmados = set(get_confirmados())

        # Acompanhantes = cônjuge + filhos
        if rel_info["tipo_relacao"] == "acompanhantes":
            acompanhantes = []
            if relacoes.get("conjuge"):
                acompanhantes.append(relacoes["conjuge"])
            if relacoes.get("filhos"):
                acompanhantes.extend(relacoes["filhos"])
            if not acompanhantes:
                return f"👀 Não tenho acompanhantes registados para {alvo.get('nome')}."
            conf = [n for n in acompanhantes if n in confirmados]
            nconf = [n for n in acompanhantes if n not in confirmados]
            msg = f"👥 Acompanhantes de {alvo.get('nome')}: " + ", ".join(acompanhantes)
            if conf:
                msg += "\n✅ Já confirmados: " + ", ".join(conf)
            if nconf:
                msg += "\n⏳ Por confirmar: " + ", ".join(nconf)
            return msg

        # Filhos ou Cônjuge
        if rel_info["tipo_relacao"] in {"filhos", "conjuge"}:
            pessoas = []
            etiqueta = "Filhos" if rel_info["tipo_relacao"] == "filhos" else "Cônjuge"
            if rel_info["tipo_relacao"] == "filhos":
                pessoas = relacoes.get("filhos", []) or []
            else:
                c = relacoes.get("conjuge")
                if c:
                    pessoas = [c]
            if not pessoas:
                return f"👀 Não tenho {etiqueta.lower()} registad{ 'o' if etiqueta=='Cônjuge' else 'os' } para {alvo.get('nome')}."
            conf = [n for n in pessoas if n in confirmados]
            nconf = [n for n in pessoas if n not in confirmados]
            base = f"👨‍👩‍👧 {etiqueta} de {alvo.get('nome')}: " + ", ".join(pessoas)
            if conf or nconf:
                if conf:
                    base += "\n✅ Já confirmados: " + ", ".join(conf)
                if nconf:
                    base += "\n⏳ Por confirmar: " + ", ".join(nconf)
            return base

    # PRIORIDADE 3: CONSULTAR CONFIRMAÇÕES (quem vai? / pessoa específica)
    tem_quinta = any(p in pergunta_l for p in ["quinta", "quintas", "reserva", "local", "evento", "sítio", "sitio"])

    if not tem_quinta and any(p in pergunta_l for p in ["vai", "vem", "comparece", "presente", "confirmou"]):
        # Caso genérico: "quem vai?"
        if pergunta_l.startswith("quem "):
            confirmados = get_confirmados()
            if confirmados:
                if len(confirmados) > 10:
                    return "🎉 Até agora confirmaram: " + ", ".join(confirmados[:10]) + f" ... e mais {len(confirmados) - 10}!"
                return "🎉 Confirmaram: " + ", ".join(confirmados)
            else:
                return "😅 Ainda ninguém confirmou presença."

        # Nome específico
        nome_mencionado = extrair_nome(pergunta)
        if not nome_mencionado:
            return "🤔 Podes repetir quem queres confirmar?"

        perfil = buscar_perfil(nome_mencionado)
        if perfil:
            if perfil.get("confirmado"):
                return f"✅ Sim! {perfil['nome']} já confirmou presença."
            else:
                return f"❌ {perfil['nome']} ainda não confirmou presença."
        else:
            return f"🤔 Não encontrei ninguém chamado '{nome_mencionado}' na lista de convidados."

    # PRIORIDADE 4: ESTATÍSTICAS
    if "quantos" in pergunta_l and any(p in pergunta_l for p in ["confirmados", "confirmou", "vão", "presentes"]):
        stats = get_estatisticas()
        return (
            f"📊 Confirmados: {stats.get('total_confirmados', 0)} pessoas\n"
            f"👨‍👩‍👧‍👦 Famílias completas: {stats.get('familias_completas', 0)}\n"
            f"👨‍👩‍👧 Famílias parciais: {stats.get('familias_parciais', 0)}\n"
            f"🕒 Última atualização: {stats.get('ultima_atualizacao', '—')}"
        )

    # PRIORIDADE 5: CONFIRMAÇÃO INDIVIDUAL
    if any(p in pergunta_l for p in ["confirmo", "vou", "conta comigo", "podes confirmar", "marca-me"]):
        resultado = confirmar_pessoa(nome_sel, confirmado_por=nome_sel)
        return resultado["mensagem"]

    # PRIORIDADE 6: FALLBACK — LLM
    perfil_selecionado = next((p for p in perfis_lista if p.get("nome") == nome_sel), {})
    resposta_llm = gerar_resposta_llm(pergunta, perfil_completo=perfil_selecionado)
    return resposta_llm


# ======================================================
# EXECUÇÃO DO CHAT
# ======================================================

if botao and pergunta:
    resposta = gerar_resposta(pergunta)
    st.markdown("---")
    st.markdown(f"**🤖 Resposta:**\n\n{resposta}")

# ==============================
# RODAPÉ
# ==============================

st.markdown("---")
st.caption(f"© {datetime.now().year} — Chatbot Passagem de Ano 🎆")
