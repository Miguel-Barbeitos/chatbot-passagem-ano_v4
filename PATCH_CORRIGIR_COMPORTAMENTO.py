#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH_DEFINITIVO.py
===================
Corrige TODOS os problemas identificados:
1. "Já há sítio/quinta?" → Responder sobre Monte da Galega
2. "Quem vai?" → Mostrar lista completa de confirmados
3. "X vai?" → Verificar confirmações corretamente
"""

import os
import shutil
from datetime import datetime
import re

print("🔧 APLICANDO PATCH DEFINITIVO...")
print("="*70)

# =====================================================
# BACKUP
# =====================================================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f"backup_{timestamp}"
os.makedirs(backup_dir, exist_ok=True)

shutil.copy2("app.py", f"{backup_dir}/app.py")
print(f"✅ Backup: {backup_dir}/app.py")

# =====================================================
# LER APP.PY
# =====================================================
with open("app.py", "r", encoding="utf-8") as f:
    linhas = f.readlines()

# =====================================================
# ENCONTRAR FUNÇÃO gerar_resposta
# =====================================================
inicio_funcao = None
for i, linha in enumerate(linhas):
    if "def gerar_resposta(pergunta: str, perfil_completo: dict):" in linha:
        inicio_funcao = i
        break

if inicio_funcao is None:
    print("❌ Função gerar_resposta não encontrada!")
    exit(1)

print(f"✅ Função encontrada na linha {inicio_funcao}")

# =====================================================
# PREPARAR CÓDIGO DE FIXES
# =====================================================
codigo_fixes = '''    
    # ================================================================
    # 🔧 FIXES DEFINITIVOS - Prioridade sobre detecção normal
    # ================================================================
    
    import re
    import unicodedata
    from modules.confirmacoes import get_confirmados
    
    def normalizar_texto(texto):
        """Remove acentos e normaliza"""
        texto = unicodedata.normalize('NFKD', texto)
        texto = ''.join(c for c in texto if not unicodedata.combining(c))
        return texto.lower().strip()
    
    # ----------------------------------------------------------------
    # FIX 1: "Já há quinta/sítio?" → Monte da Galega
    # ----------------------------------------------------------------
    if re.search(r'\\b(ja\\s+ha|temos|existe)\\s+(quinta|sitio|sítio|local|lugar)', pergunta_l, re.IGNORECASE):
        resposta_texto = f"""🏡 **Sim!** 
        
Temos o **Monte da Galega** pré-reservado como plano B, mas ainda estamos a avaliar outras opções para garantir que escolhemos o melhor local para a festa! 🎉

Já contactámos **35 quintas**. Queres saber mais sobre elas?"""
        
        st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
        return resposta_texto
    
    # ----------------------------------------------------------------
    # FIX 2: "Quem vai?" → Lista completa de confirmados
    # ----------------------------------------------------------------
    if re.search(r'^(quem\\s+vai|quem\\s+confirmou|lista.*confirmad)', pergunta_l, re.IGNORECASE):
        confirmados_data = get_confirmados()
        confirmados = confirmados_data.get('confirmados', [])
        total = len(confirmados)
        
        if total == 0:
            resposta_texto = "Ainda ninguém confirmou. 😔\\n\\nSê o primeiro! Diz 'confirmo' ou 'vou'!"
        else:
            resposta_texto = f"**Confirmados ({total}):**\\n\\n"
            
            # Agrupa por família se possível
            por_familia = confirmados_data.get('por_familia', {})
            
            if por_familia:
                for fam_id, membros in por_familia.items():
                    resposta_texto += f"• {', '.join(membros)}\\n"
            else:
                for nome in confirmados:
                    resposta_texto += f"• {nome}\\n"
            
            resposta_texto += f"\\n🎉 Total: **{total} pessoas**"
        
        st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
        return resposta_texto
    
    # ----------------------------------------------------------------
    # FIX 3: "X vai?" ou "O X vai?" → Verificar confirmações
    # ----------------------------------------------------------------
    match_vai = re.search(r'\\b(?:o|a)?\\s*([\\w\\sáéíóúâêôãõç]+?)\\s+vai\\??\\s*$', pergunta_l, re.IGNORECASE)
    
    if match_vai:
        nome_busca = match_vai.group(1).strip()
        
        # Ignora palavras comuns
        if nome_busca.lower() not in ['eu', 'tu', 'ele', 'ela', 'voce', 'você']:
            print(f"🔍 Verificando se '{nome_busca}' vai...")
            
            confirmados_data = get_confirmados()
            confirmados = confirmados_data.get('confirmados', [])
            
            nome_norm = normalizar_texto(nome_busca)
            
            # Verifica se está confirmado
            nome_encontrado = None
            for confirmado in confirmados:
                if normalizar_texto(confirmado) == nome_norm:
                    nome_encontrado = confirmado
                    break
            
            if nome_encontrado:
                resposta_texto = f"✅ **Sim!** {nome_encontrado} já confirmou presença! 🎉"
                
                # Verifica família
                from modules.perfis_manager import PerfilsManager
                pm = PerfilsManager()
                perfil = pm.buscar_perfil(nome_encontrado)
                
                if perfil and perfil.get('familia_id'):
                    familia = pm.listar_familia(perfil['familia_id'])
                    familia_confirmada = [
                        p['nome'] for p in familia 
                        if p['nome'] in confirmados
                    ]
                    familia_pendente = [
                        p['nome'] for p in familia 
                        if p['nome'] not in confirmados and p['nome'] != nome_encontrado
                    ]
                    
                    if familia_confirmada:
                        resposta_texto += f"\\n\\n👨‍👩‍👧‍👦 Da família também vão: {', '.join(familia_confirmada)}"
                    
                    if familia_pendente:
                        resposta_texto += f"\\n\\n⏳ Ainda faltam confirmar: {', '.join(familia_pendente)}"
            else:
                resposta_texto = f"❌ **Ainda não.** {nome_busca.title()} ainda não confirmou.\\n\\nAjuda a lembrar! 😊"
            
            st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
            return resposta_texto
    
    # ----------------------------------------------------------------
    # FIX 4: "Website/info da primeira" → Resposta direta
    # ----------------------------------------------------------------
    match_info = re.search(
        r'(website|site|morada|endereco|endereço|email|telefone|contacto)\\s+da?\\s+(primeira?|segunda?|terceira?|\\d+a?)',
        pergunta_l,
        re.IGNORECASE
    )
    
    if match_info:
        tipo_info = match_info.group(1).lower()
        posicao = match_info.group(2).lower().rstrip('aª')
        
        mapa_pos = {
            "primeira": 0, "primeiro": 0, "1": 0,
            "segunda": 1, "segundo": 1, "2": 1,
            "terceira": 2, "terceiro": 2, "3": 2,
            "quarta": 3, "quarto": 3, "4": 3,
            "quinta": 4, "quinto": 4, "5": 4,
            "sexta": 5, "sexto": 5, "6": 5,
            "setima": 6, "sétima": 6, "7": 6,
            "oitava": 7, "oitavo": 7, "8": 7,
            "nona": 8, "nono": 8, "9": 8,
            "decima": 9, "décima": 9, "10": 9,
        }
        
        indice = mapa_pos.get(posicao)
        
        if indice is not None:
            from modules.quintas_qdrant import listar_quintas
            todas_quintas = listar_quintas()
            
            if indice < len(todas_quintas):
                quinta = todas_quintas[indice]
                nome_quinta = quinta.get('nome', 'N/A')
                zona = quinta.get('zona', 'N/A')
                
                campo_map = {
                    'website': 'website', 'site': 'website',
                    'morada': 'morada', 'endereco': 'morada', 'endereço': 'morada',
                    'email': 'email',
                    'telefone': 'telefone', 'contacto': 'telefone',
                }
                
                campo = campo_map.get(tipo_info, 'website')
                valor = quinta.get(campo, '')
                
                if valor and valor.strip():
                    icones = {
                        'website': '🌐',
                        'morada': '📍',
                        'email': '📧',
                        'telefone': '📞'
                    }
                    
                    resposta_texto = f"**{nome_quinta}** ({zona})\\n\\n{icones.get(campo, '')} {valor}"
                else:
                    resposta_texto = f"A **{nome_quinta}** não tem {campo} registado. 😕"
                
                st.session_state.mensagens.append({"role": "assistant", "content": resposta_texto})
                return resposta_texto
    
    # ================================================================
    # Continua com o fluxo normal...
    # ================================================================
    
'''

# =====================================================
# INSERIR CÓDIGO NO INÍCIO DA FUNÇÃO
# =====================================================

# Encontra onde começa o corpo da função (após a definição)
indice_insercao = inicio_funcao + 1

# Pula linhas vazias e docstrings
while indice_insercao < len(linhas):
    linha = linhas[indice_insercao].strip()
    if linha and not linha.startswith('"""') and not linha.startswith("'''"):
        break
    indice_insercao += 1

# Insere o código
linhas.insert(indice_insercao, codigo_fixes + "\n")

print(f"✅ Código inserido na linha {indice_insercao}")

# =====================================================
# GUARDAR
# =====================================================
with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(linhas)

print("\n" + "="*70)
print("✨ PATCH DEFINITIVO APLICADO!")
print("="*70)
print("\n✅ FIXES APLICADOS:")
print("  1. 'Já há quinta?' → Monte da Galega")
print("  2. 'Quem vai?' → Lista completa")
print("  3. 'O barbeitos vai?' → Verifica confirmações")
print("  4. 'Website da primeira' → Resposta direta")
print("\n🧪 TESTA AGORA:")
print("  streamlit run app.py")
print()
print("  Perguntas:")
print("  • 'Já há sítio?'")
print("  • 'Quem vai?'")
print("  • 'O barbeitos vai?'")
print("  • 'Website da primeira'")
print()
print(f"💾 Backup: {backup_dir}/app.py")
print("="*70)