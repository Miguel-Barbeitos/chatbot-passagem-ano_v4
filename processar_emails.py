"""
Processador de Emails EML → Qdrant
Lê ficheiros .eml de uma pasta e atualiza informações das quintas
"""

import os
import re
import email
import sqlite3
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path

from qdrant_client import QdrantClient, models

# Configuração
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMAILS_DIR = os.path.join(BASE_DIR, "data", "emails_quintas")
PROCESSADOS_DIR = os.path.join(BASE_DIR, "data", "emails_quintas", "processados")
DB_PATH = os.path.join(BASE_DIR, "data", "quintas.db")
COLLECTION_QUINTAS = "quintas_info"

# Criar pastas se não existirem
os.makedirs(EMAILS_DIR, exist_ok=True)
os.makedirs(PROCESSADOS_DIR, exist_ok=True)

# =====================================================
# 📧 LER EMAILS EML
# =====================================================

def ler_email_eml(filepath):
    """Lê um ficheiro .eml e extrai informações"""
    
    try:
        with open(filepath, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)
        
        # Headers
        subject = msg['subject'] or ''
        from_email = msg['from'] or ''
        to_email = msg['to'] or ''
        date = msg['date'] or ''
        
        # Extrai email limpo do remetente
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_email)
        email_clean = email_match.group(0).lower() if email_match else from_email.lower()
        
        # Body
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                # Ignora attachments
                if 'attachment' in content_disposition:
                    continue
                
                # Pega texto
                if content_type == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
                elif content_type == 'text/html' and not body:
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'from_email': email_clean,
            'from_name': from_email,
            'to_email': to_email,
            'subject': subject,
            'date': date,
            'body': body
        }
    
    except Exception as e:
        print(f"❌ Erro ao ler {filepath}: {e}")
        return None

# =====================================================
# 🔍 EXTRAIR INFORMAÇÕES DO EMAIL
# =====================================================

def extrair_info_quinta(email_data):
    """Extrai informações relevantes sobre a quinta do email"""
    
    body = email_data['body']
    body_lower = body.lower()
    
    info = {
        'tem_disponibilidade': None,
        'capacidade': None,
        'preco': None,
        'tem_piscina': None,
        'permite_animais': None,
        'observacoes': []
    }
    
    # ===== DISPONIBILIDADE =====
    disponivel_termos = [
        'sim, temos disponibilidade',
        'disponível',
        'disponivel',
        'temos vaga',
        'sim temos',
        'confirmamos disponibilidade',
        'podemos receber',
        'livre para essa data',
        'está disponível',
        'esta disponivel'
    ]
    
    indisponivel_termos = [
        'não temos',
        'nao temos',
        'indisponível',
        'indisponivel',
        'lotado',
        'já reservado',
        'ja reservado',
        'sem disponibilidade',
        'completo',
        'não conseguimos',
        'nao conseguimos'
    ]
    
    if any(termo in body_lower for termo in disponivel_termos):
        info['tem_disponibilidade'] = True
        info['observacoes'].append("Disponibilidade confirmada por email")
    elif any(termo in body_lower for termo in indisponivel_termos):
        info['tem_disponibilidade'] = False
        info['observacoes'].append("Sem disponibilidade")
    
    # ===== CAPACIDADE =====
    # Procura padrões como "40 pessoas", "capacidade de 43", etc
    capacidade_patterns = [
        r'(\d+)\s*pessoas',
        r'capacidade\s+(?:de|para)?\s*(\d+)',
        r'(?:até|máximo de)\s*(\d+)\s*pessoas',
        r'alojamento\s+(?:de|para)?\s*(\d+)'
    ]
    
    for pattern in capacidade_patterns:
        match = re.search(pattern, body_lower)
        if match:
            cap = int(match.group(1))
            if 10 <= cap <= 200:  # Validação básica
                info['capacidade'] = cap
                info['observacoes'].append(f"Capacidade: {cap} pessoas")
                break
    
    # ===== PREÇO =====
    # Procura padrões de preço
    preco_patterns = [
        r'(?:€|euros?)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|euros?)',
        r'(?:valor|preço|custo|orçamento).*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
        r'(?:proposta|total).*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)'
    ]
    
    precos_encontrados = []
    for pattern in preco_patterns:
        matches = re.finditer(pattern, body, re.IGNORECASE)
        for match in matches:
            try:
                preco_str = match.group(1).replace('.', '').replace(',', '.')
                preco = float(preco_str)
                if 500 <= preco <= 50000:  # Validação básica
                    precos_encontrados.append(preco)
            except:
                continue
    
    if precos_encontrados:
        # Pega o maior (provavelmente o preço total)
        info['preco'] = max(precos_encontrados)
        info['observacoes'].append(f"Preço: €{info['preco']:.2f}")
    
    # ===== CARACTERÍSTICAS =====
    if 'piscina' in body_lower:
        info['tem_piscina'] = True
        info['observacoes'].append("Tem piscina")
    
    if any(termo in body_lower for termo in ['cães aceites', 'animais permitidos', 'aceita animais', 'pet friendly']):
        info['permite_animais'] = True
        info['observacoes'].append("Permite animais")
    elif any(termo in body_lower for termo in ['não aceita animais', 'nao aceita animais', 'sem animais']):
        info['permite_animais'] = False
        info['observacoes'].append("Não permite animais")
    
    return info

# =====================================================
# 🔗 LIGAR EMAIL À QUINTA
# =====================================================

def get_emails_quintas():
    """Busca emails das quintas na BD"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT nome, email FROM quintas WHERE email IS NOT NULL AND email != ''")
    quintas = cursor.fetchall()
    conn.close()
    
    return {q['email'].lower(): q['nome'] for q in quintas}

def sugerir_quintas(email_data, emails_quintas):
    """Sugere quintas possíveis baseado em similaridade"""
    
    sugestoes = []
    
    # Get todos os nomes de quintas
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nome, email, zona FROM quintas")
    quintas = cursor.fetchall()
    conn.close()
    
    email_from = email_data['from_email']
    dominio = email_from.split('@')[1] if '@' in email_from else ''
    filename = email_data['filename'].lower()
    texto = f"{email_data['subject']} {email_data['body']}".lower()
    
    for nome, email_bd, zona in quintas:
        score = 0
        motivos = []
        
        # Domínio similar
        if email_bd and dominio:
            dominio_bd = email_bd.split('@')[1] if '@' in email_bd else ''
            if dominio == dominio_bd:
                score += 10
                motivos.append("domínio igual")
            elif dominio in dominio_bd or dominio_bd in dominio:
                score += 5
                motivos.append("domínio similar")
        
        # Nome no ficheiro
        palavras_nome = [p for p in nome.lower().split() if len(p) >= 4]
        if palavras_nome:
            matches = sum(1 for p in palavras_nome if p in filename)
            if matches == len(palavras_nome):
                score += 8
                motivos.append("nome completo no ficheiro")
            elif matches > 0:
                score += matches * 2
                motivos.append(f"{matches} palavras no ficheiro")
        
        # Nome no texto
        if nome.lower() in texto:
            score += 6
            motivos.append("nome no email")
        elif palavras_nome and any(p in texto for p in palavras_nome):
            score += 3
            motivos.append("palavras no email")
        
        # Zona no texto
        if zona and zona.lower() in texto:
            score += 2
            motivos.append(f"zona {zona}")
        
        if score > 0:
            sugestoes.append((nome, ", ".join(motivos), score))
    
    # Ordena por score
    sugestoes.sort(key=lambda x: x[2], reverse=True)
    
    # Retorna top 3
    return [(nome, motivo) for nome, motivo, score in sugestoes[:3]]

def identificar_quinta(email_data, emails_quintas):
    """Identifica a quinta correspondente ao email"""
    
    email_from = email_data['from_email']
    filename = email_data['filename']
    
    # ===== 1. EXTRAI EMAIL DO NOME DO FICHEIRO =====
    # Procura padrão: nome_email@dominio.com.eml
    email_no_filename = re.search(r'_([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]{2,})\.eml$', filename)
    if email_no_filename:
        email_extraido = email_no_filename.group(1).lower()
        print(f"   📧 Email no ficheiro: {email_extraido}")
        
        # Busca direta por este email
        if email_extraido in emails_quintas:
            print(f"   ✅ Quinta identificada pelo nome do ficheiro!")
            return emails_quintas[email_extraido]
        
        # Busca por domínio
        dominio = email_extraido.split('@')[1] if '@' in email_extraido else ''
        if dominio:
            for email_quinta, nome_quinta in emails_quintas.items():
                if dominio in email_quinta:
                    print(f"   ✅ Quinta identificada pelo domínio no ficheiro!")
                    return nome_quinta
    
    # ===== 2. BUSCA DIRETA POR EMAIL DO REMETENTE =====
    if email_from in emails_quintas:
        print(f"   ✅ Quinta identificada pelo email remetente!")
        return emails_quintas[email_from]
    
    # ===== 3. BUSCA POR DOMÍNIO SIMILAR =====
    dominio = email_from.split('@')[1] if '@' in email_from else ''
    for email_quinta, nome_quinta in emails_quintas.items():
        if dominio and dominio in email_quinta:
            print(f"   ✅ Quinta identificada pelo domínio!")
            return nome_quinta
    
    # ===== 4. BUSCA PELO ASSUNTO OU CORPO =====
    texto_completo = f"{email_data['subject']} {email_data['body']}".lower()
    
    # Get todos os nomes de quintas da BD
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM quintas")
    quintas = cursor.fetchall()
    conn.close()
    
    for (nome,) in quintas:
        # Busca nome completo
        if nome.lower() in texto_completo:
            print(f"   ✅ Quinta identificada pelo nome no texto!")
            return nome
        
        # Busca por palavras-chave do nome (mínimo 4 letras)
        palavras = [p for p in nome.split() if len(p) >= 4]
        if palavras and all(p.lower() in texto_completo for p in palavras):
            print(f"   ✅ Quinta identificada por palavras-chave!")
            return nome
    
    # ===== 5. BUSCA NO NOME DO FICHEIRO (PALAVRAS) =====
    # Tenta encontrar o nome da quinta no nome do ficheiro
    filename_lower = filename.lower()
    for (nome,) in quintas:
        palavras = [p for p in nome.split() if len(p) >= 4]
        if palavras and all(p.lower() in filename_lower for p in palavras):
            print(f"   ✅ Quinta identificada pelo nome no ficheiro!")
            return nome
    
    return None

# =====================================================
# 💾 ATUALIZAR BD
# =====================================================

def inicializar_qdrant():
    """Inicializa conexão ao Qdrant"""
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_url and qdrant_key:
        return QdrantClient(url=qdrant_url, api_key=qdrant_key)
    
    try:
        # Tenta reutilizar conexão existente
        from modules.perfis_manager import client
        return client
    except:
        return QdrantClient(path=os.path.join(BASE_DIR, "qdrant_data"))

def atualizar_quinta(quinta_nome, info, email_data):
    """Atualiza quinta no SQLite e Qdrant"""
    
    # 1. Atualizar SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if info['tem_disponibilidade'] is not None:
        estado = 'Disponível' if info['tem_disponibilidade'] else 'Indisponível'
        updates.append("estado = ?")
        params.append(estado)
        
        updates.append("resposta = ?")
        params.append('Sim' if info['tem_disponibilidade'] else 'Não')
    
    if info['capacidade']:
        updates.append("capacidade_confirmada = ?")
        params.append(info['capacidade'])
    
    if info['preco']:
        updates.append("custo_total = ?")
        params.append(info['preco'])
    
    # Resumo
    resumo_partes = [f"Email processado: {email_data['filename']}"]
    if info['observacoes']:
        resumo_partes.extend(info['observacoes'])
    resumo = " | ".join(resumo_partes)
    
    updates.append("resumo_resposta = ?")
    params.append(resumo)
    
    updates.append("ultima_resposta = ?")
    params.append(datetime.now().strftime('%Y-%m-%d'))
    
    if updates:
        params.append(quinta_nome)
        sql = f"UPDATE quintas SET {', '.join(updates)} WHERE nome = ?"
        cursor.execute(sql, params)
        conn.commit()
        print(f"  ✅ SQLite atualizado")
    
    conn.close()
    
    # 2. Atualizar Qdrant
    try:
        client = inicializar_qdrant()
        
        # Busca o ponto da quinta
        resultados = client.scroll(
            collection_name=COLLECTION_QUINTAS,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="nome",
                        match=models.MatchValue(value=quinta_nome)
                    )
                ]
            ),
            limit=1
        )
        
        if resultados[0]:
            ponto = resultados[0][0]
            
            # Atualiza payload
            payload_novo = ponto.payload.copy()
            
            if info['tem_disponibilidade'] is not None:
                payload_novo['estado'] = 'Disponível' if info['tem_disponibilidade'] else 'Indisponível'
                payload_novo['resposta'] = 'Sim' if info['tem_disponibilidade'] else 'Não'
            
            if info['capacidade']:
                payload_novo['capacidade_confirmada'] = info['capacidade']
            
            if info['preco']:
                payload_novo['custo_total'] = info['preco']
            
            payload_novo['resumo_resposta'] = resumo
            payload_novo['ultima_resposta'] = datetime.now().strftime('%Y-%m-%d')
            
            # Atualiza no Qdrant
            client.upsert(
                collection_name=COLLECTION_QUINTAS,
                points=[
                    models.PointStruct(
                        id=ponto.id,
                        vector=ponto.vector,
                        payload=payload_novo
                    )
                ]
            )
            
            print(f"  ✅ Qdrant atualizado")
        else:
            print(f"  ⚠️  Quinta não encontrada no Qdrant")
        
    except Exception as e:
        print(f"  ⚠️  Erro ao atualizar Qdrant: {e}")

# =====================================================
# 🔄 PROCESSAR PASTA DE EMAILS
# =====================================================

def processar_emails_pasta():
    """Processa todos os emails .eml da pasta"""
    
    print("=" * 60)
    print("📧 PROCESSAR EMAILS DAS QUINTAS")
    print("=" * 60)
    print()
    print(f"📂 Pasta: {EMAILS_DIR}")
    print()
    
    # Lista ficheiros .eml
    eml_files = list(Path(EMAILS_DIR).glob("*.eml"))
    
    if not eml_files:
        print("❌ Nenhum ficheiro .eml encontrado!")
        print()
        print("💡 Instruções:")
        print(f"   1. Coloca os emails (.eml) na pasta: {EMAILS_DIR}")
        print("   2. Executa novamente este script")
        print()
        return
    
    print(f"📬 Encontrados {len(eml_files)} emails")
    print()
    
    # Get mapa email → quinta
    emails_quintas = get_emails_quintas()
    print(f"🏡 {len(emails_quintas)} quintas com email na BD")
    print()
    
    # Processar cada email
    print("-" * 60)
    print("📨 A processar emails...")
    print("-" * 60)
    print()
    
    processados = 0
    atualizados = 0
    nao_identificados = []
    erros = []
    
    for eml_file in eml_files:
        try:
            print(f"📧 {eml_file.name}")
            
            # Lê email
            email_data = ler_email_eml(eml_file)
            
            if not email_data:
                erros.append(eml_file.name)
                continue
            
            print(f"   De: {email_data['from_name'][:50]}")
            print(f"   Assunto: {email_data['subject'][:50]}")
            
            # Identifica quinta
            quinta_nome = identificar_quinta(email_data, emails_quintas)
            
            if not quinta_nome:
                print(f"   ⚠️  Quinta não identificada")
                
                # Tenta sugerir quintas baseado no email/filename
                sugestoes = sugerir_quintas(email_data, emails_quintas)
                if sugestoes:
                    print(f"   💡 Sugestões:")
                    for i, (nome, motivo) in enumerate(sugestoes[:3], 1):
                        print(f"      {i}. {nome} ({motivo})")
                    print(f"   💡 Para processar, adiciona email na BD ou renomeia ficheiro:")
                    print(f"      mv '{eml_file.name}' 'resposta_{sugestoes[0][0].lower().replace(' ', '_')}_{email_data['from_email']}.eml'")
                
                nao_identificados.append({
                    'filename': eml_file.name,
                    'email': email_data['from_email'],
                    'sugestoes': sugestoes
                })
                print()
                continue
            
            print(f"   🏡 Quinta: {quinta_nome}")
            
            # Extrai informações
            info = extrair_info_quinta(email_data)
            
            # Mostra info extraída
            if info['tem_disponibilidade'] is not None:
                status = "✅ Disponível" if info['tem_disponibilidade'] else "❌ Indisponível"
                print(f"   {status}")
            
            if info['capacidade']:
                print(f"   👥 Capacidade: {info['capacidade']} pessoas")
            
            if info['preco']:
                print(f"   💰 Preço: €{info['preco']:.2f}")
            
            if info['tem_piscina']:
                print(f"   🏊 Tem piscina")
            
            if info['permite_animais'] is not None:
                animal_status = "✅ Sim" if info['permite_animais'] else "❌ Não"
                print(f"   🐕 Animais: {animal_status}")
            
            # Atualiza BD
            atualizar_quinta(quinta_nome, info, email_data)
            atualizados += 1
            
            # Move para pasta processados
            destino = os.path.join(PROCESSADOS_DIR, eml_file.name)
            eml_file.rename(destino)
            print(f"   📁 Movido para: processados/")
            
            processados += 1
            print()
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            erros.append(eml_file.name)
            print()
    
    # Resumo
    print("=" * 60)
    print("📊 RESUMO:")
    print("=" * 60)
    print(f"✅ Emails processados: {processados}")
    print(f"✅ Quintas atualizadas: {atualizados}")
    
    if nao_identificados:
        print(f"\n⚠️  Não identificados: {len(nao_identificados)}")
        print()
        for item in nao_identificados[:5]:
            print(f"📧 {item['filename']}")
            print(f"   Email: {item['email']}")
            if item['sugestoes']:
                print(f"   Sugestões:")
                for nome, motivo in item['sugestoes']:
                    print(f"      • {nome} ({motivo})")
            print()
        
        if len(nao_identificados) > 5:
            print(f"   ... e mais {len(nao_identificados) - 5}")
        
        print("\n💡 COMO RESOLVER:")
        print("=" * 60)
        print("\n1️⃣  ADICIONA EMAIL NA BD (recomendado):")
        print("   ```sql")
        for item in nao_identificados[:3]:
            if item['sugestoes']:
                quinta = item['sugestoes'][0][0]
                email = item['email']
                print(f"   UPDATE quintas SET email = '{email}' WHERE nome = '{quinta}';")
        print("   ```")
        
        print("\n2️⃣  RENOMEIA FICHEIRO:")
        print("   Adiciona _email@dominio.eml no final:")
        for item in nao_identificados[:3]:
            if item['sugestoes']:
                quinta = item['sugestoes'][0][0].lower().replace(' ', '_')
                email = item['email']
                print(f"   → resposta_{quinta}_{email}.eml")
        print()
    
    if erros:
        print(f"\n❌ Erros: {len(erros)}")
        for nome in erros[:5]:
            print(f"   • {nome}")
    
    print("=" * 60)
    print()
    
    if nao_identificados:
        print("💡 Para emails não identificados:")
        print("   1. Verifica se a quinta tem email na BD")
        print("   2. Ou adiciona manualmente o nome da quinta no assunto do email")
        print()

# =====================================================
# 🎯 EXECUÇÃO DIRETA
# =====================================================

if __name__ == "__main__":
    processar_emails_pasta()