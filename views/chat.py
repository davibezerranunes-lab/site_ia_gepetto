import streamlit as st
from gepetto_core import *  # noqa: F401,F403 — shared account and chat helpers

inicializar_runtime()

if not st.session_state.get("usuario"):
    st.switch_page("views/login.py")
    st.stop()


# =========================================================
# CABEÇALHO
# =========================================================

# O menu fica fixo no canto superior direito, na posição marcada pelo usuário,
# mesmo quando a conversa é rolada para cima ou para baixo.
st.markdown("""
<style>
/* Área fixa maior que o botão: evita que o círculo seja recortado pelos wrappers do Streamlit. */
.st-key-gepetto_menu_fixo {
    position: fixed !important;
    top: 52px !important;
    right: 12px !important;
    z-index: 100000 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
    min-height: 52px !important;
    max-height: none !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    clip-path: none !important;
    contain: none !important;
    pointer-events: none !important;
}
.st-key-gepetto_menu_fixo > div {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 52px !important;
    height: 52px !important;
    min-width: 52px !important;
    min-height: 52px !important;
    max-height: none !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    overflow: visible !important;
    clip-path: none !important;
    pointer-events: auto !important;
}
.st-key-gepetto_menu_fixo [data-testid="stPopover"] {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 48px !important;
    height: 48px !important;
    min-width: 48px !important;
    min-height: 48px !important;
    max-height: none !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    clip-path: none !important;
    pointer-events: auto !important;
}

/* Botão igual à referência: círculo totalmente preto, três pontos brancos e SEM a setinha do popover. */
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button,
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"],
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"] {
    display: flex !important;
    flex: 0 0 44px !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
    width: 44px !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    min-height: 44px !important;
    max-height: 44px !important;
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
    border-radius: 50% !important;
    background: #000000 !important;
    background-color: #000000 !important;
    background-image: none !important;
    border: 0 !important;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.28) !important;
    color: #ffffff !important;
    font-size: 15px !important;
    font-weight: 800 !important;
    letter-spacing: 1px !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    opacity: 1 !important;
    outline: none !important;
    overflow: visible !important;
    clip-path: none !important;
    -webkit-appearance: none !important;
    appearance: none !important;
    transition: box-shadow 120ms ease, transform 120ms ease !important;
}
/* Streamlit acrescenta uma setinha ao botão de popover; escondê-la mantém só os três pontos. */
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button svg,
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"] svg,
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"] svg {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
}
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button > div,
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button [data-testid="stMarkdownContainer"],
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"] > div,
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"] > div {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: auto !important;
    height: auto !important;
    max-height: none !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    overflow: visible !important;
    clip-path: none !important;
}
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button:hover,
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button:focus,
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button:focus-visible,
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button:active,
.st-key-gepetto_menu_fixo [data-testid="stPopover"] > button[aria-expanded="true"],
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"]:hover,
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"]:focus,
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"]:focus-visible,
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"]:active,
.st-key-gepetto_menu_fixo [data-testid="stPopoverButton"][aria-expanded="true"],
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"]:hover,
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"]:focus,
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"]:focus-visible,
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"]:active,
.st-key-gepetto_menu_fixo button[aria-haspopup="dialog"][aria-expanded="true"] {
    background: #000000 !important;
    background-color: #000000 !important;
    background-image: none !important;
    color: #ffffff !important;
    border: 0 !important;
    opacity: 1 !important;
    box-shadow: 0 2px 7px rgba(0, 0, 0, 0.34) !important;
}
.st-key-gepetto_menu_fixo button:active {
    transform: scale(0.97) !important;
}
@media (max-width: 700px) {
    .st-key-gepetto_menu_fixo {
        top: 52px !important;
        right: 8px !important;
        width: 52px !important;
        height: 52px !important;
        min-width: 52px !important;
        min-height: 52px !important;
    }
    .st-key-gepetto_menu_fixo > div {
        width: 52px !important;
        height: 52px !important;
        min-width: 52px !important;
        min-height: 52px !important;
    }
    .st-key-gepetto_menu_fixo [data-testid="stPopover"] {
        width: 48px !important;
        height: 48px !important;
        min-width: 48px !important;
        min-height: 48px !important;
    }
    .st-key-gepetto_menu_fixo [data-testid="stPopover"] > button,
    .st-key-gepetto_menu_fixo [data-testid="stPopoverButton"],
    .st-key-gepetto_menu_fixo button[aria-haspopup="dialog"] {
        width: 44px !important;
        min-width: 44px !important;
        max-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        max-height: 44px !important;
        font-size: 15px !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 Gepetto AI")
st.caption("Seu assistente de inteligência artificial")

if st.session_state.get("usuario"):
    with st.container(key="gepetto_menu_fixo"):
        with st.popover("•••", help="Configurações da conta"):
            usuario_menu_atual = st.session_state.get("usuario", "")
            st.caption(f"Conta: {usuario_menu_atual}")
            if eh_admin(usuario_menu_atual):
                if st.button(
                    "🛡️ Abrir Painel de ADM",
                    key="menu_abrir_painel_admin",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state.painel_admin_autorizado = True
                    st.session_state.confirmar_exclusao_admin = ""
                    st.switch_page("views/admin.py")
                st.divider()
            renderizar_configuracoes_conta(usuario_menu_atual)



# =========================================================
# CARREGAR CONTA
# =========================================================

usuario = st.session_state.usuario
dados = carregar_dados(usuario)

if dados is None:
    st.error("Não foi possível localizar os dados dessa conta.")

    if encerrar_sessao():
        st.rerun()

    st.stop()

if dados.get("bloqueado", False) and not eh_admin(usuario):
    encerrar_sessao()
    st.error("Esta conta foi bloqueada pelo ADM.")
    st.stop()

dados["usuario"] = dados.get("usuario") or usuario

if not salvar_dados(usuario, dados):
    st.warning("Não foi possível atualizar os dados da conta.")


# =========================================================
# BARRA LATERAL — LAYOUT ANTIGO
# =========================================================

with st.sidebar:
    st.title("💬 Conversas")
    st.caption(f"Conta: {usuario}")

    if st.button("➕ Nova conversa", use_container_width=True):
        numero = 1
        nome = f"Conversa {numero}"

        while nome in dados["chats"]:
            numero += 1
            nome = f"Conversa {numero}"

        dados["chats"][nome] = []
        dados["chat_atual"] = nome

        st.session_state.confirmar_exclusao_chat = False

        if salvar_dados(usuario, dados):
            st.rerun()
        else:
            st.error("Não foi possível criar a conversa.")

    nomes_chats = list(dados["chats"].keys())

    if nomes_chats:
        if dados["chat_atual"] not in nomes_chats:
            dados["chat_atual"] = nomes_chats[0]

        conversa_selecionada = st.selectbox(
            "Escolha uma conversa",
            nomes_chats,
            index=nomes_chats.index(dados["chat_atual"]),
        )

        if conversa_selecionada != dados["chat_atual"]:
            dados["chat_atual"] = conversa_selecionada
            st.session_state.confirmar_exclusao_chat = False

            if not salvar_dados(usuario, dados):
                st.error("Não foi possível salvar a conversa.")

            st.rerun()

        if st.button(
            "🗑️ Excluir conversa selecionada",
            use_container_width=True,
        ):
            st.session_state.confirmar_exclusao_chat = True

        # Exportação da conversa selecionada em TXT e Markdown.
        mensagens_exportar = dados["chats"].get(dados["chat_atual"], [])
        historico_exportar = "\\n\\n".join(
            f"{str(m.get('role', 'mensagem')).upper()}: {m.get('content', '')}"
            for m in mensagens_exportar
        )
        nome_base_exportar = re.sub(r"[^A-Za-z0-9_-]+", "_", dados["chat_atual"]).strip("_") or "conversa"
        st.download_button(
            "📥 Exportar conversa (.txt)",
            data=historico_exportar,
            file_name=f"{nome_base_exportar}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.download_button(
            "📄 Exportar conversa (.md)",
            data=historico_exportar,
            file_name=f"{nome_base_exportar}.md",
            mime="text/markdown",
            use_container_width=True,
        )

        with st.expander("⚙️ Configurações da IA"):
            st.slider("Criatividade (Temperatura)", 0.0, 1.0, 0.6, step=0.1, key="gepetto_temperatura")
            st.slider("Tamanho máximo da resposta (tokens)", 256, 4096, 2048, step=256, key="gepetto_max_tokens")

        if st.session_state.confirmar_exclusao_chat:
            st.warning(
                f"Excluir a conversa '{dados['chat_atual']}'? "
                "Essa ação não pode ser desfeita."
            )

            if st.button(
                "SIM, EXCLUIR CONVERSA",
                use_container_width=True,
            ):
                nome_excluir = dados["chat_atual"]

                if excluir_chat(usuario, dados, nome_excluir):
                    st.session_state.confirmar_exclusao_chat = False
                    st.rerun()
                else:
                    st.error("Não foi possível excluir a conversa.")

            if st.button(
                "Cancelar exclusão da conversa",
                use_container_width=True,
            ):
                st.session_state.confirmar_exclusao_chat = False
                st.rerun()

    else:
        st.info("Você ainda não tem conversas. Crie uma para começar.")

    st.divider()

    if st.button("🗑️ Excluir minha conta", use_container_width=True):
        st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        if eh_admin(usuario):
            st.warning("A conta administrativa está protegida contra exclusão.")
            st.session_state.confirmar_exclusao = False
        else:
            st.warning(
                "Isso apagará a conta e todo o histórico "
                "deste armazenamento."
            )

            if st.button(
                "SIM, EXCLUIR CONTA",
                use_container_width=True,
                type="primary",
            ):
                excluir_conta(usuario)

            if st.button(
                "Cancelar exclusão da conta",
                use_container_width=True,
            ):
                st.session_state.confirmar_exclusao = False
                st.rerun()


# =========================================================
# HISTÓRICO
# =========================================================

chat_atual = dados["chat_atual"]

if chat_atual:
    st.subheader(chat_atual)
    mensagens = dados["chats"][chat_atual]

    for indice_mensagem, mensagem in enumerate(mensagens):
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
            anexos_mensagem = mensagem.get("attachments", [])
            if isinstance(anexos_mensagem, list) and anexos_mensagem:
                for indice_anexo, anexo in enumerate(anexos_mensagem):
                    caminho = caminho_anexo(usuario, anexo.get("saved_name"))
                    if not caminho or not caminho.is_file():
                        st.caption(f"📎 {anexo.get('name', 'Arquivo')} — arquivo não está mais disponível neste servidor.")
                        continue
                    if anexo.get("kind") == "image":
                        # Exibe miniatura compacta (máximo de 280 × 280 px), mantendo o arquivo original para download.
                        try:
                            from PIL import Image
                            with Image.open(caminho) as imagem_original:
                                miniatura = imagem_original.copy()
                                miniatura.thumbnail((280, 280))
                            st.image(miniatura, caption=anexo.get("name", "Imagem anexada"), width=280)
                        except Exception:
                            st.caption(f"📷 {anexo.get('name', 'Imagem anexada')} — não foi possível mostrar a miniatura.")
                        st.download_button(
                            "Baixar imagem",
                            data=caminho.read_bytes(),
                            file_name=anexo.get("name", "imagem.png"),
                            mime=anexo.get("mime", "image/png"),
                            key=f"download_img_{indice_mensagem}_{indice_anexo}_{anexo.get('saved_name', '')}",
                        )
                    else:
                        with st.expander(f"📎 {anexo.get('name', 'Arquivo anexado')}", expanded=False):
                            if anexo.get("text_content"):
                                st.caption("O texto deste arquivo foi enviado ao Gepetto para análise.")
                            st.download_button(
                                "Baixar arquivo",
                                data=caminho.read_bytes(),
                                file_name=anexo.get("name", "arquivo"),
                                mime=anexo.get("mime", "application/octet-stream"),
                                key=f"download_{indice_mensagem}_{indice_anexo}_{anexo.get('saved_name', '')}",
                            )
else:
    st.info("Clique em 'Nova conversa' para começar.")


# =========================================================
# RECEBER MENSAGEM
# =========================================================

st.markdown("""
<style>
/* Clipe discreto no campo de mensagem (somente botão de anexar). */
[data-testid="stChatInputFileUploadButton"],
[data-testid="stChatInputUploadButton"],
.stChatInput button[aria-label*="attach" i],
.stChatInput button[aria-label*="anexar" i] {
    color: rgba(255, 255, 255, 0.72) !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    opacity: 0.68;
    transition: opacity 120ms ease;
}
[data-testid="stChatInputFileUploadButton"] svg,
[data-testid="stChatInputUploadButton"] svg,
.stChatInput button[aria-label*="attach" i] svg,
.stChatInput button[aria-label*="anexar" i] svg {
    color: rgba(255, 255, 255, 0.78) !important;
    stroke: currentColor !important;
}
[data-testid="stChatInputFileUploadButton"]:hover,
[data-testid="stChatInputUploadButton"]:hover,
.stChatInput button[aria-label*="attach" i]:hover,
.stChatInput button[aria-label*="anexar" i]:hover {
    opacity: 1;
}
</style>
""", unsafe_allow_html=True)
st.caption("Limite diário por conta: 15 fotos e 5 arquivos por dia, com até 5 MB por arquivo. As cotas reiniciam à meia-noite (horário de Brasília).")

entrada_chat = st.chat_input(
    "Converse com o Gepetto...",
    accept_file="multiple",
    file_type=EXTENSOES_UPLOAD,
)

if entrada_chat:
    # Streamlit pode retornar str ou um objeto ChatInputValue semelhante a dict,
    # dependendo da versão e de accept_file. Leia os dois formatos explicitamente.
    if isinstance(entrada_chat, str):
        texto_original = entrada_chat
        arquivos_enviados = []
    else:
        try:
            texto_original = entrada_chat.get("text", "") or ""
        except (AttributeError, TypeError):
            texto_original = getattr(entrada_chat, "text", "") or ""
        try:
            arquivos_enviados = list(entrada_chat.get("files", []) or [])
        except (AttributeError, TypeError):
            arquivos_enviados = list(getattr(entrada_chat, "files", []) or [])
        texto_original = str(texto_original)

    texto = texto_original.strip()

    fotos_enviadas = [
        arquivo for arquivo in arquivos_enviados
        if Path(str(arquivo.name)).suffix.lower().lstrip(".") in EXTENSOES_IMAGEM
    ]
    documentos_enviados = [arquivo for arquivo in arquivos_enviados if arquivo not in fotos_enviadas]
    cota_upload = carregar_cota_upload(usuario)
    fotos_restantes = max(0, MAX_FOTOS_POR_DIA - cota_upload["fotos"])
    arquivos_restantes = max(0, MAX_ARQUIVOS_POR_DIA - cota_upload["arquivos"])
    if len(fotos_enviadas) > fotos_restantes:
        st.error(
            f"Você ainda pode enviar {fotos_restantes} foto(s) hoje. "
            f"O limite é {MAX_FOTOS_POR_DIA} fotos por dia; a cota reinicia amanhã à meia-noite (horário de Brasília)."
        )
        st.stop()
    if len(documentos_enviados) > arquivos_restantes:
        st.error(
            f"Você ainda pode enviar {arquivos_restantes} arquivo(s) hoje. "
            f"O limite é {MAX_ARQUIVOS_POR_DIA} arquivos por dia; a cota reinicia amanhã à meia-noite (horário de Brasília)."
        )
        st.stop()
    arquivos_grandes = [arquivo.name for arquivo in arquivos_enviados if getattr(arquivo, "size", 0) > TAMANHO_MAXIMO_ARQUIVO]
    if arquivos_grandes:
        st.error(f"Cada arquivo pode ter no máximo {TAMANHO_MAXIMO_ARQUIVO_MB} MB: " + ", ".join(arquivos_grandes[:3]))
        st.stop()
    if not texto and not arquivos_enviados:
        st.stop()
    if not texto:
        texto = "Analise os arquivos e as fotos anexados e me ajude com eles."

    anexos_nova_mensagem = []
    try:
        for arquivo_enviado in arquivos_enviados:
            anexos_nova_mensagem.append(salvar_anexo(usuario, arquivo_enviado))
    except ValueError as erro_upload:
        st.error(str(erro_upload))
        st.stop()
    except OSError:
        st.error("Não consegui salvar os anexos. Tente novamente.")
        st.stop()

    if arquivos_enviados:
        cota_upload["fotos"] += len(fotos_enviadas)
        cota_upload["arquivos"] += len(documentos_enviados)
        if not salvar_cota_upload(usuario, cota_upload):
            st.error("Não consegui registrar o limite diário de anexos. Tente novamente mais tarde.")
            st.stop()

    # -----------------------------------------------------
    # SOLICITAÇÕES DE PERMISSÃO PELO PAINEL DE ADM
    # -----------------------------------------------------

    if st.session_state.aguardando_codigo:
        # Compatibilidade com verificações de e-mail iniciadas antes desta versão.
        if texto.casefold() == "cancelar":
            cancelar_verificacao()
            st.info("Verificação cancelada. Você pode conversar normalmente.")
            st.rerun()
        if verificar_codigo(texto):
            comando = st.session_state.comando_pendente
            st.session_state.comando_pendente = None
            if not eh_admin(usuario):
                cancelar_verificacao()
                st.error("Acesso administrativo negado.")
                st.stop()
            if comando == "20456742":
                mostrar_codigo_fonte()
            elif comando == "20456742v2":
                mostrar_requirements()
            elif comando == "paineladm":
                st.session_state.painel_admin_autorizado = True
                st.rerun()
            st.stop()
        if st.session_state.aguardando_codigo:
            st.stop()
        st.rerun()

    if texto in ("20456742", "20456742v2"):
        if eh_admin(usuario):
            # A conta ADM autenticada pode acessar os arquivos diretamente, sem e-mail.
            if texto == "20456742":
                mostrar_codigo_fonte()
            else:
                mostrar_requirements()
            st.stop()

        if permissao_aprovada(usuario, texto):
            if texto == "20456742":
                mostrar_codigo_fonte()
            else:
                mostrar_requirements()
            st.stop()

        if criar_solicitacao_admin(usuario, texto):
            st.info("🔔 Sua solicitação foi enviada ao Painel de ADM. Aguarde a aprovação e envie o mesmo comando novamente.")
        else:
            st.error("Não foi possível registrar a solicitação. Tente novamente.")
        st.stop()

    if texto == "paineladm":
        if not eh_admin(usuario):
            st.error("O Painel de ADM é exclusivo da conta administrativa.")
            st.stop()
        st.session_state.painel_admin_autorizado = True
        st.switch_page("views/admin.py")

    # -----------------------------------------------------
    # MODO ADMIN: SOMENTE "2045 pergunta"
    # -----------------------------------------------------

    modo_admin_desta_resposta = texto.startswith("2045 ")

    if modo_admin_desta_resposta:
        pergunta_limpa = texto[5:].strip()

        if not pergunta_limpa:
            st.info("Digite uma pergunta depois de '2045 '.")
            st.stop()
    else:
        pergunta_limpa = texto

    # -----------------------------------------------------
    # PROTEÇÃO BÁSICA DE ENTRADA
    # -----------------------------------------------------

    if input_suspeito(pergunta_limpa):
        st.error(
            "Sua mensagem contém uma frase que pode tentar "
            "manipular as instruções da IA. Reformule a pergunta."
        )
        st.stop()

    # -----------------------------------------------------
    # SALVAR MENSAGEM
    # -----------------------------------------------------

    if not dados["chat_atual"]:
        nome_inicial = nome_chat_disponivel(
            dados["chats"],
            "Nova conversa",
        )
        dados["chats"][nome_inicial] = []
        dados["chat_atual"] = nome_inicial

    chat_antigo = dados["chat_atual"]
    mensagens = dados["chats"][chat_antigo]

    if not mensagens:
        nome_base = gerar_nome_chat(pergunta_limpa)

        nome_novo = nome_chat_disponivel(
            dados["chats"],
            nome_base,
            chat_original=chat_antigo,
        )

        dados["chats"][nome_novo] = mensagens

        if nome_novo != chat_antigo:
            del dados["chats"][chat_antigo]

        dados["chat_atual"] = nome_novo

    mensagens.append({
        "role": "user",
        "content": pergunta_limpa,
        **({"attachments": anexos_nova_mensagem} if anexos_nova_mensagem else {}),
    })

    st.session_state.resposta_modo_admin = (
        modo_admin_desta_resposta
    )

    if not salvar_dados(usuario, dados):
        st.error("Não foi possível salvar sua mensagem.")
        st.stop()

    st.rerun()


# =========================================================
# RESPOSTA DA IA
# =========================================================

if dados["chat_atual"]:
    mensagens = dados["chats"][dados["chat_atual"]]

    if mensagens and mensagens[-1]["role"] == "user":
        mensagem_usuario = mensagens[-1]
        modo_admin_desta_resposta = st.session_state.get(
            "resposta_modo_admin",
            False,
        )

        with st.chat_message("assistant"):
            area_resposta = st.empty()

            try:
                prompt = PROMPT_ADMIN if modo_admin_desta_resposta else PROMPT_PADRAO
                mensagens_api = [{"role": "system", "content": prompt}]

                # As fotos são analisadas em pequenos lotes para respeitar os limites do modelo visual.
                anexos_usuario = mensagem_usuario.get("attachments", [])
                if anexos_usuario and any(a.get("kind") == "image" for a in anexos_usuario):
                    try:
                        resumo_visual = analisar_imagens_anexadas(usuario, anexos_usuario)
                        if resumo_visual:
                            mensagem_usuario["attachment_summary"] = resumo_visual[:30000]
                            if not salvar_dados(usuario, dados):
                                st.warning("Não consegui guardar o resumo das fotos no histórico.")
                    except Exception:
                        mensagem_usuario["attachment_summary"] = "Não consegui analisar automaticamente uma ou mais fotos anexadas."

                for mensagem in mensagens[-12:]:
                    if mensagem.get("role") not in ("user", "assistant"):
                        continue
                    conteudo_texto = str(mensagem.get("content", ""))
                    anexos_mensagem = mensagem.get("attachments", [])
                    if isinstance(anexos_mensagem, list):
                        partes_documentos = []
                        for anexo in anexos_mensagem:
                            texto_arquivo = anexo.get("text_content", "")
                            if texto_arquivo:
                                partes_documentos.append(
                                    f"[Conteúdo extraído de {anexo.get('name', 'arquivo')}]\n{texto_arquivo}"
                                )
                        if partes_documentos:
                            conteudo_texto += "\n\n" + "\n\n".join(partes_documentos)
                    resumo_visual_salvo = mensagem.get("attachment_summary", "")
                    if resumo_visual_salvo:
                        conteudo_texto += "\n\n[Análise visual das fotos anexadas]\n" + resumo_visual_salvo
                    limite_contexto = 30000 if mensagem is mensagem_usuario else 4000
                    mensagens_api.append({
                        "role": mensagem["role"],
                        "content": conteudo_texto[:limite_contexto],
                    })

                temperatura = float(st.session_state.get("gepetto_temperatura", 0.6))
                max_tokens = int(st.session_state.get("gepetto_max_tokens", 2048))
                resposta_stream = obter_cliente_groq().chat.completions.create(
                    model=MODELO,
                    messages=mensagens_api,
                    temperature=temperatura,
                    max_completion_tokens=max_tokens,
                    stream=True,
                )

                def gerar_texto():
                    for chunk in resposta_stream:
                        if not chunk.choices:
                            continue
                        trecho = chunk.choices[0].delta.content
                        if trecho:
                            yield trecho

                texto_resposta = area_resposta.write_stream(gerar_texto())
                if not texto_resposta:
                    texto_resposta = "Não consegui gerar uma resposta."
                    area_resposta.markdown(texto_resposta)
                mensagens.append({"role": "assistant", "content": texto_resposta})
                if not salvar_dados(usuario, dados):
                    st.error("Não foi possível salvar a resposta no histórico.")

            except Exception:
                area_resposta.error(
                    "Não consegui responder agora. Confira a conexão e tente novamente."
                )
            finally:
                st.session_state.resposta_modo_admin = False


# =========================================================
# RODAPÉ
# =========================================================

st.divider()

st.caption(
    "Gepetto AI • Seu assistente de inteligência artificial"
)

