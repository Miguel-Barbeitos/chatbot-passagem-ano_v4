# -*- coding: utf-8 -*-
"""
Script de testes automáticos do Chatbot 🎭
Executa uma série de perguntas e guarda as respostas num ficheiro.
"""

import csv
import time
from app import gerar_resposta  # Importa a função principal
from modules.perfis_manager import listar_todos_perfis

# ------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------
UTILIZADOR_PADRAO = "Barbeitos"   # nome de teste (não é usado agora)
FICHEIRO_PERGUNTAS = "teste_chatbot_perguntas.csv"
FICHEIRO_RESULTADOS = "resultados_testes.csv"


# ------------------------------------------------------
# LER PERGUNTAS
# ------------------------------------------------------
def ler_perguntas_csv(caminho):
    perguntas = []
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # ignora cabeçalho
            for linha in reader:
                if not linha:
                    continue
                perguntas.append(linha[0].strip())
        return perguntas
    except FileNotFoundError:
        print(f"❌ Ficheiro {caminho} não encontrado.")
        return []


# ------------------------------------------------------
# EXECUTAR TESTES
# ------------------------------------------------------
def testar_chatbot():
    perguntas = ler_perguntas_csv(FICHEIRO_PERGUNTAS)
    if not perguntas:
        print("⚠️ Nenhuma pergunta para testar.")
        return

    print(f"🚀 A iniciar testes com {len(perguntas)} perguntas...\n")

    resultados = []
    for i, p in enumerate(perguntas, start=1):
        print(f"[{i}/{len(perguntas)}] 🧠 Pergunta: {p}")
        try:
            # ✅ Corrigido — agora só passa 1 argumento
            resposta = gerar_resposta(p)
        except Exception as e:
            resposta = f"❌ Erro: {e}"
        resultados.append({"pergunta": p, "resposta": resposta})
        print(f"🤖 Resposta: {resposta}\n")
        time.sleep(0.3)

    # Grava resultados
    with open(FICHEIRO_RESULTADOS, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["pergunta", "resposta"])
        writer.writeheader()
        writer.writerows(resultados)

    print(f"\n✅ Testes concluídos! Resultados gravados em {FICHEIRO_RESULTADOS}")


# ------------------------------------------------------
# EXECUTAR
# ------------------------------------------------------
if __name__ == "__main__":
    testar_chatbot()
