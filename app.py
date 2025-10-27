# ─────────────────────────────────────────────────────────────────────────────


# =====================================================
# 🎨 Layout geral (chat à esquerda, utilidades à direita)
# =====================================================
col_chat, col_side = st.columns([3, 1])


with col_side:
# Sidebar compacta com confirmados e ações
confirmados = get_confirmacoes()
mostrar_sidebar(confirmados)


# Utilidades (limpar, exportar histórico, atualizar confirmados JSON)
botoes_utilidade()


with col_chat:
# Saudação + histórico + input
mostrar_saudacao(nome)
mostrar_chat_historico()


# Input adaptável (text_area)
prompt = input_mensagem()


if prompt:
# Intenção (para badge/indicador visual)
intencao = identificar_intencao(prompt)
indicador_intencao_ui(intencao)


with st.spinner("💭 A pensar..."):
resposta = gerar_resposta(prompt, perfil)


# Render das mensagens
with st.chat_message("user"):
st.markdown(f"**{nome}:** {prompt}")
with st.chat_message("assistant"):
st.markdown(f"**Assistente:** {resposta}")


# Guardar no histórico (com hora)
ts = datetime.now().strftime('%H:%M')
if "historico" not in st.session_state:
st.session_state.historico = []
st.session_state.historico.append({"role": "user", "content": f"**{nome} ({ts}):** {prompt}"})
st.session_state.historico.append({"role": "assistant", "content": f"**Assistente ({ts}):** {resposta}"})