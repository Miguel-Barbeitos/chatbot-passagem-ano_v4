#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH_SEGURO.py
===============
Adiciona funções auxiliares ANTES da função gerar_resposta
Mais seguro - não mexe na indentação existente
"""

import os
import shutil
from datetime import datetime

print("🔧 APLICANDO PATCH SEGURO...")
print("="*70)

# =====================================================
# BACKUP
# =====================================================
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"app.py.backup_{timestamp}"

shutil.copy2("app.py", backup_file)
print(f"✅ Backup: {backup_file}")

# =====================================================
# LER APP.PY
# =====================================================
with open("app.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

# =====================================================
# CÓDIGO NOVO: Funções auxiliares ANTES de gerar_resposta
# =====================================================
funcoes_auxiliares = '''
# ================================================================
# 🔧 FUNÇÕES AUXILIARES - Detecção prioritária de perguntas
# ================================================================

def verificar_pergunta_quinta_reservada(pergunta: str) -> tuple[bool, str]:
    """Verifica se pergunta é sobre ter quinta reservada"""
    import re
    
    padrao = r'\\b(ja\\s+ha|temos|existe)\\s+(quinta|sitio|sítio|local|lugar)'
    if re.search(padrao, pergunta.lower(), re.IGNORECASE):
        resposta = """🏡 **Sim!** 

Temos o **Monte da Galega** pré-reservado como plano B, mas ainda estamos a avaliar outras opções para garantir que escolhemos o melhor local para a festa! 🎉

Já contactámos **35 quintas**. Queres saber mais sobre elas?"""
        return True, resposta
    
    return False, ""


def verificar_pergunta_quem_vai(pergunta: str) -> tuple[bool, str]:
    """Verifica se pergunta é 'quem vai?'"""
    import re
    from modules.confirmacoes import get_confirmados
    
    if re.search(r'^(quem\\s+vai|quem\\s+confirmou|lista.*confirmad)', pergunta.lower(), re.IGNORECASE):
        confirmados_data = get_confirmados()
        confirmados = confirmados_data.get('confirmados', [])
        total = len(confirmados)
        
        if total == 0:
            resposta = "Ainda ninguém confirmou. 😔\\n\\nSê o primeiro! Diz 'confirmo' ou 'vou'!"
        else:
            resposta = f"**Confirmados ({total}):**\\n\\n"
            
            por_familia = confirmados_data.get('por_familia', {})
            
            if por_familia:
                for fam_id, membros in por_familia.items():
                    resposta += f"• {', '.join(membros)}\\n"
            else:
                for nome in confirmados:
                    resposta += f"• {nome}\\n"
            
            resposta += f"\\n🎉 Total: **{total} pessoas**"
        
        return True, resposta
    
    return False, ""


def verificar_pergunta_pessoa_vai(pergunta: str) -> tuple[bool, str]:
    """Verifica se pergunta é 'X vai?'"""
    import re
    import unicodedata
    from modules.confirmacoes import get_confirmados
    
    match = re.search(r'\\b(?:o|a)?\\s*([\\w\\sáéíóúâêôãõç]+?)\\s+vai\\??\\s*$', pergunta.lower(), re.IGNORECASE)
    
    if match:
        nome_busca = match.group(1).strip()
        
        # Ignora palavras comuns
        if nome_busca.lower() not in ['eu', 'tu', 'ele', 'ela', 'voce', 'você']:
            confirmados_data = get_confirmados()
            confirmados = confirmados_data.get('confirmados', [])
            
            # Normaliza para comparação
            def norm(s):
                s = unicodedata.normalize('NFKD', s)
                s = ''.join(c for c in s if not unicodedata.combining(c))
                return s.lower().strip()
            
            nome_norm = norm(nome_busca)
            
            # Procura confirmado
            nome_encontrado = None
            for confirmado in confirmados:
                if norm(confirmado) == nome_norm:
                    nome_encontrado = confirmado
                    break
            
            if nome_encontrado:
                resposta = f"✅ **Sim!** {nome_encontrado} já confirmou presença! 🎉"
            else:
                resposta = f"❌ **Ainda não.** {nome_busca.title()} ainda não confirmou.\\n\\nAjuda a lembrar! 😊"
            
            return True, resposta
    
    return False, ""


def verificar_pergunta_info_quinta(pergunta: str) -> tuple[bool, str]:
    """Verifica se pergunta é sobre info específica de quinta por posição"""
    import re
    
    match = re.search(
        r'(website|site|morada|endereco|endereço|email|telefone|contacto)\\s+da?\\s+(primeira?|segunda?|terceira?|quarta?|quinta?|sexta?|setima?|sétima?|oitava?|nona?|decima?|décima?|\\d+a?)',
        pergunta.lower(),
        re.IGNORECASE
    )
    
    if match:
        tipo_info = match.group(1).lower()
        posicao = match.group(2).lower().rstrip('aª')
        
        mapa_pos = {
            "primeira": 0, "primeiro": 0, "1": 0,
            "segunda": 1, "segundo": 1, "2": 1,
            "terceira": 2, "terceiro": 2, "3": 2,
            "quarta": 3, "quarto": 3, "4": 3,
            "quinta": 4, "quinto": 4, "5": 4,
            "sexta": 5, "sexto": 5, "6": 5,
            "setima": 6, "sétima": 6, "setimo": 6, "7": 6,
            "oitava": 7, "oitavo": 7, "8": 7,
            "nona": 8, "nono": 8, "9": 8,
            "decima": 9, "décima": 9, "decimo": 9, "10": 9,
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
                    
                    resposta = f"**{nome_quinta}** ({zona})\\n\\n{icones.get(campo, '')} {valor}"
                else:
                    resposta = f"A **{nome_quinta}** não tem {campo} registado. 😕"
                
                return True, resposta
    
    return False, ""

'''

# =====================================================
# ENCONTRAR ONDE INSERIR (antes de def gerar_resposta)
# =====================================================
import re

# Procura def gerar_resposta
match = re.search(r'\ndef gerar_resposta\(', conteudo)

if not match:
    print("❌ Função gerar_resposta não encontrada!")
    exit(1)

posicao_insercao = match.start()

# Insere as funções auxiliares ANTES
novo_conteudo = (
    conteudo[:posicao_insercao] + 
    "\n" + funcoes_auxiliares + "\n" + 
    conteudo[posicao_insercao:]
)

# =====================================================
# MODIFICAR INÍCIO DE gerar_resposta para USAR as funções
# =====================================================
codigo_uso = '''def gerar_resposta(pergunta: str, perfil_completo: dict):
    """Gera resposta com detecção prioritária"""
    
    # ================================================================
    # 🎯 VERIFICAÇÕES PRIORITÁRIAS (antes de tudo)
    # ================================================================
    
    # 1. Já há quinta?
    detectado, resposta = verificar_pergunta_quinta_reservada(pergunta)
    if detectado:
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})
        return resposta
    
    # 2. Quem vai?
    detectado, resposta = verificar_pergunta_quem_vai(pergunta)
    if detectado:
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})
        return resposta
    
    # 3. X vai?
    detectado, resposta = verificar_pergunta_pessoa_vai(pergunta)
    if detectado:
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})
        return resposta
    
    # 4. Website/info da primeira
    detectado, resposta = verificar_pergunta_info_quinta(pergunta)
    if detectado:
        st.session_state.mensagens.append({"role": "assistant", "content": resposta})
        return resposta
    
    # ================================================================
    # Continua com fluxo normal...
    # ================================================================
    '''

# Substitui apenas a linha de definição
novo_conteudo = re.sub(
    r'def gerar_resposta\(pergunta: str, perfil_completo: dict\):',
    codigo_uso,
    novo_conteudo,
    count=1
)

# =====================================================
# GUARDAR
# =====================================================
with open("app.py", "w", encoding="utf-8") as f:
    f.write(novo_conteudo)

print("\n" + "="*70)
print("✅ PATCH SEGURO APLICADO!")
print("="*70)
print("\n📝 O QUE FOI FEITO:")
print("  ✅ Funções auxiliares adicionadas")
print("  ✅ Verificações prioritárias no início de gerar_resposta")
print("  ✅ Não mexeu na estrutura existente")
print()
print("🧪 TESTA:")
print("  streamlit run app.py")
print()
print(f"💾 Backup: {backup_file}")
print("="*70)