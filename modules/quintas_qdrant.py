#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
modules/quintas_qdrant.py
=========================
Módulo para usar as quintas diretamente do Qdrant Cloud
Collection: quintas_info (35 pontos)
"""

import os
from typing import List, Dict, Optional
from qdrant_client import QdrantClient, models


COLLECTION_NAME = "quintas_info"


class QuintasQdrant:
    """Gestor de quintas usando Qdrant Cloud"""

    def __init__(self):
        self.client = self._get_client()
        self._cache = None

    def _get_client(self) -> QdrantClient:
        """Conecta ao Qdrant Cloud"""
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_url or not qdrant_key:
            try:
                import streamlit as st
                qdrant_url = st.secrets.get("QDRANT_URL")
                qdrant_key = st.secrets.get("QDRANT_API_KEY")
            except Exception:
                pass

        if qdrant_url and qdrant_key:
            return QdrantClient(url=qdrant_url, api_key=qdrant_key)
        else:
            raise ValueError("❌ Credenciais do Qdrant não configuradas!")

    def _get_all_quintas(self) -> List[Dict]:
        """Busca todas as quintas do Qdrant (com cache)"""
        if self._cache is not None:
            return self._cache

        quintas = []
        offset = None

        try:
            while True:
                resultados, offset = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=100,
                    offset=offset
                )

                if not resultados:
                    break

                for ponto in resultados:
                    quinta = ponto.payload
                    quinta["_id"] = ponto.id
                    quintas.append(quinta)

                if offset is None:
                    break

            self._cache = quintas
            print(f"✅ {len(quintas)} quintas carregadas do Qdrant")
            return quintas

        except Exception as e:
            print(f"❌ Erro ao buscar quintas: {e}")
            return []

    def contar(self) -> int:
        return len(self._get_all_quintas())

    def listar_todas(self, limite: int = None) -> List[Dict]:
        quintas = self._get_all_quintas()
        return quintas[:limite] if limite else quintas

    def buscar_por_nome(self, nome: str) -> Optional[Dict]:
        """Busca quinta por nome (aproximado)"""
        nome_lower = nome.lower().strip()
        quintas = self._get_all_quintas()

        for q in quintas:
            if q.get("nome", "").lower() == nome_lower:
                return q

        for q in quintas:
            if nome_lower in q.get("nome", "").lower():
                return q

        palavras = nome_lower.split()
        if len(palavras) > 1:
            for q in quintas:
                nome_q = q.get("nome", "").lower()
                if all(p in nome_q for p in palavras):
                    return q

        return None

    def buscar_por_zona(self, zona: str) -> List[Dict]:
        zona_lower = zona.lower().strip()
        return [
            q for q in self._get_all_quintas()
            if zona_lower in q.get("zona", "").lower()
        ]

    def contar_com_resposta(self) -> int:
        return len([q for q in self._get_all_quintas() if q.get("resposta")])

    def contar_sem_resposta(self) -> int:
        return len([q for q in self._get_all_quintas() if not q.get("resposta")])

    def listar_com_resposta(self) -> List[Dict]:
        return [q for q in self._get_all_quintas() if q.get("resposta")]

    def buscar_por_caracteristica(self, caracteristica: str) -> List[Dict]:
        c_lower = caracteristica.lower()
        resultados = []
        for q in self._get_all_quintas():
            texto = " ".join(
                str(q.get(k, "")).lower()
                for k in ["comodidades", "observacoes", "resposta", "resumo_resposta"]
            )
            if c_lower in texto:
                resultados.append(q)
        return resultados

    def executar_query_simulada(self, query: str) -> List[Dict]:
        q_lower = query.lower()
        quintas = self._get_all_quintas()

        if "count(*)" in q_lower:
            if "resposta is not null" in q_lower:
                return [{"total": len([q for q in quintas if q.get("resposta")])}]
            if "resposta is null" in q_lower:
                return [{"total": len([q for q in quintas if not q.get("resposta")])}]
            return [{"total": len(quintas)}]

        if "limit" in q_lower:
            import re
            m = re.search(r"limit\s+(\d+)", q_lower)
            if m:
                return quintas[: int(m.group(1))]

        if "where" in q_lower and "nome" in q_lower:
            import re
            m = re.search(r"nome\s+like\s+'%([^']+)%'", q_lower)
            if m:
                quinta = self.buscar_por_nome(m.group(1))
                return [quinta] if quinta else []

        if "where" in q_lower and "zona" in q_lower:
            import re
            m = re.search(r"zona\s+like\s+'%([^']+)%'", q_lower)
            if m:
                return self.buscar_por_zona(m.group(1))

        return quintas

    def get_estatisticas(self) -> Dict:
        quintas = self._get_all_quintas()
        total = len(quintas)
        com_resposta = len([q for q in quintas if q.get("resposta")])
        sem_resposta = total - com_resposta

        zonas = {}
        estados = {}

        for q in quintas:
            zonas[q.get("zona", "Desconhecida")] = zonas.get(q.get("zona", "Desconhecida"), 0) + 1
            estados[q.get("estado", "Desconhecido")] = estados.get(q.get("estado", "Desconhecido"), 0) + 1

        return {
            "total": total,
            "com_resposta": com_resposta,
            "sem_resposta": sem_resposta,
            "zonas": zonas,
            "estados": estados,
            "fonte": "Qdrant (quintas_info)",
        }


# Instância global e wrappers
_manager = None

def get_manager() -> QuintasQdrant:
    global _manager
    if _manager is None:
        _manager = QuintasQdrant()
    return _manager

def executar_query(query: str) -> List[Dict]:
    return get_manager().executar_query_simulada(query)

def listar_quintas(limite: int = None) -> List[Dict]:
    return get_manager().listar_todas(limite)

def buscar_quinta(nome: str) -> Optional[Dict]:
    return get_manager().buscar_por_nome(nome)

def contar_quintas() -> int:
    return get_manager().contar()

def get_estatisticas() -> Dict:
    return get_manager().get_estatisticas()

def executar_sql(query: str) -> List[Dict]:
    return executar_query(query)


def buscar_quinta_por_nome(nome: str):
    """Busca quinta específica por nome (aproximado)"""
    return buscar_quinta(nome)


def procurar_quinta_por_nome(nome: str):
    """Alias para manter compatibilidade com código anterior"""
    return buscar_quinta_por_nome(nome)
