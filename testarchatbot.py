#!/usr/bin/env python3
"""
Script de teste REAL - Copia perguntas para clipboard
"""

import json
import time
import sys

try:
    import pyperclip
    TEM_CLIPBOARD = True
except ImportError:
    TEM_CLIPBOARD = False
    print("⚠️  pyperclip não instalado. Instala com: pip install pyperclip")

def carregar_perguntas():
    """Carrega 76 perguntas"""
    with open('teste_perguntas_corrigido.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [item['pergunta'] for item in data]

def testar_interativo():
    """Modo interativo - copia perguntas uma a uma"""
    perguntas = carregar_perguntas()
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║           🧪 TESTE AUTOMÁTICO - MODO INTERATIVO                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    
    print(f"✅ {len(perguntas)} perguntas carregadas\n")
    print("📋 INSTRUÇÕES:\n")
    print("1. Abre o chatbot no browser")
    print("2. Coloca as janelas lado a lado")
    print("3. Pressiona ENTER para copiar cada pergunta")
    print("4. Cola no chatbot (Ctrl+V)")
    print("5. Valida a resposta")
    print("6. Volta aqui e pressiona ENTER para próxima\n")
    print("Para sair: Ctrl+C\n")
    print("="*70 + "\n")
    
    input("Pressiona ENTER para começar...")
    
    for i, pergunta in enumerate(perguntas, 1):
        print(f"\n📝 PERGUNTA {i}/{len(perguntas)}:")
        print(f"   {pergunta}")
        
        if TEM_CLIPBOARD:
            pyperclip.copy(pergunta)
            print("   ✅ Copiada para clipboard!")
        
        print("\n   Ações:")
        print("   - Cole no chatbot (Ctrl+V)")
        print("   - Valida resposta")
        print("   - [ENTER] próxima | [S] skip | [Q] quit")
        
        acao = input("\n   > ").lower()
        
        if acao == 'q':
            print("\n✅ Teste interrompido")
            print(f"   Testadas: {i-1}/{len(perguntas)}")
            break
        elif acao == 's':
            print("   ⏭️  Pergunta saltada")
            continue
    
    print("\n" + "="*70)
    print(f"\n🎉 Teste completo! {len(perguntas)} perguntas testadas")
    print("\nRelembra:")
    print("- Todas as perguntas de quintas devem funcionar")
    print("- Perguntas gerais (mundial, capital) devem dar respostas corretas")
    print("- Nenhuma pergunta geral deve responder com quintas")

def gerar_arquivo_teste():
    """Gera arquivo TXT com todas as perguntas numeradas"""
    perguntas = carregar_perguntas()
    
    with open('/mnt/user-data/outputs/76_PERGUNTAS_TESTE.txt', 'w', encoding='utf-8') as f:
        f.write("╔══════════════════════════════════════════════════════════════════╗\n")
        f.write("║              76 PERGUNTAS PARA TESTAR CHATBOT                    ║\n")
        f.write("╚══════════════════════════════════════════════════════════════════╝\n\n")
        
        categorias = {
            "ESTADO DA ORGANIZAÇÃO": [],
            "INFORMAÇÕES DAS QUINTAS": [],
            "CONFIRMAÇÕES DOS CONVIDADOS": [],
            "DETALHES DO EVENTO": [],
            "FORA DO CONTEXTO": []
        }
        
        for pergunta in perguntas:
            p = pergunta.lower()
            if any(x in p for x in ["quinta", "responderam", "disponível", "indisponível", "contactadas"]):
                if any(x in p for x in ["website", "km", "perto", "barata", "capacidade", "preço", "setúbal"]):
                    categorias["INFORMAÇÕES DAS QUINTAS"].append(pergunta)
                else:
                    categorias["ESTADO DA ORGANIZAÇÃO"].append(pergunta)
            elif any(x in p for x in ["convidados", "confirmou", "isabel", "joão", "família", "casais"]):
                categorias["CONFIRMAÇÕES DOS CONVIDADOS"].append(pergunta)
            elif any(x in p for x in ["evento", "tema", "cor", "check-in", "custar", "orçamento", "jantar", "dress", "brunch"]):
                categorias["DETALHES DO EVENTO"].append(pergunta)
            else:
                categorias["FORA DO CONTEXTO"].append(pergunta)
        
        contador = 1
        for cat, pergs in categorias.items():
            if len(pergs) == 0:
                continue
            f.write(f"\n{'='*70}\n")
            f.write(f"  {cat} ({len(pergs)} perguntas)\n")
            f.write(f"{'='*70}\n\n")
            for pergunta in pergs:
                f.write(f"{contador:2d}. {pergunta}\n")
                contador += 1
        
        f.write(f"\n{'='*70}\n")
        f.write(f"\nTOTAL: {len(perguntas)} perguntas\n")
    
    print("✅ Arquivo criado: 76_PERGUNTAS_TESTE.txt")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--gerar":
        gerar_arquivo_teste()
    else:
        if not TEM_CLIPBOARD:
            print("\nInstalando pyperclip...")
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "pyperclip"])
            print("✅ Instalado! Executa de novo.")
        else:
            testar_interativo()