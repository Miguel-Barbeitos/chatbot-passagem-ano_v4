#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH_MELHORAR_CONTEXTO.py
Melhora o context-aware para perguntas tipo "e da 7" ou "da segunda"
"""

print("🔧 MELHORANDO CONTEXT-AWARE...")
print("="*60)

# Lê app.py
with open("app.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

# Adiciona lógica para números ordinais
codigo_adicional = '''
    # ✅ CONTEXTO: Números e ordinais (1ª, 2ª, 3ª, etc.)
    referencias_numero = {
        "1": 0, "primeira": 0, "1a": 0, "1ª": 0,
        "2": 1, "segunda": 1, "2a": 1, "2ª": 1,
        "3": 2, "terceira": 2, "3a": 2, "3ª": 2,
        "4": 3, "quarta": 3, "4a": 3, "4ª": 3,
        "5": 4, "quinta": 4, "5a": 4, "5ª": 4,
        "6": 5, "sexta": 5, "6a": 5, "6ª": 5,
        "7": 6, "setima": 6, "sétima": 6, "7a": 6, "7ª": 6,
        "8": 7, "oitava": 7, "8a": 7, "8ª": 7,
        "9": 8, "nona": 8, "9a": 8, "9ª": 8,
        "10": 9, "decima": 9, "décima": 9, "10a": 9, "10ª": 9,
    }
    
    # Verifica se última resposta tinha lista de quintas
    if "ultima_lista_quintas" in st.session_state and st.session_state.ultima_lista_quintas:
        # Verifica se pergunta é sobre número/ordinal
        for ref, idx in referencias_numero.items():
            # Patterns: "e da 7", "da 7", "7", "setima", etc.
            patterns = [
                f"e da {ref}",
                f"da {ref}",
                f"^{ref}$",
                f"e {ref}",
            ]
            
            if any(re.search(p, pergunta_l) for p in patterns):
                if idx < len(st.session_state.ultima_lista_quintas):
                    quinta_nome = st.session_state.ultima_lista_quintas[idx]
                    print(f"🎯 Contexto: {ref} → {quinta_nome}")
                    
                    # Se pede info específica
                    if any(t in pergunta_l for t in ["website", "site", "link", "morada", "email", "telefone"]):
                        tipo_info = "website" if "website" in pergunta_l or "site" in pergunta_l or "link" in pergunta_l else \
                                   "morada" if "morada" in pergunta_l else \
                                   "email" if "email" in pergunta_l else \
                                   "telefone" if "telefone" in pergunta_l else "info"
                        
                        pergunta = f"{tipo_info} da {quinta_nome}"
                        pergunta_l = normalizar(pergunta)
                        print(f"🔄 Reformulado: '{pergunta}'")
                        break
'''

# Encontra onde adicionar (após definição de gerar_resposta)
if "def gerar_resposta(pergunta: str, perfil_completo: dict):" in conteudo:
    # Adiciona após a normalização da pergunta
    conteudo = conteudo.replace(
        'pergunta_l = normalizar(pergunta)',
        'pergunta_l = normalizar(pergunta)\n' + codigo_adicional
    )
    
    print("✅ Context-aware melhorado em app.py")
else:
    print("⚠️ Não consegui encontrar local para adicionar código")

# Guarda
with open("app.py", "w", encoding="utf-8") as f:
    f.write(conteudo)

print("\n✨ Adiciona também tracking de listas:")
print("   Quando lista quintas, guarda em st.session_state.ultima_lista_quintas")
print("\n" + "="*60)