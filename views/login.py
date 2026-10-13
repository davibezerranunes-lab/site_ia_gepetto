import streamlit as st
from gepetto_core import *  # noqa: F401,F403 — helpers shared by the existing auth flow

inicializar_runtime()

st.title("🤖 Gepetto AI")
st.caption("Seu assistente de inteligência artificial")

if st.session_state.get("usuario"):
    st.switch_page("views/chat.py")

# Depois do OAuth, contas vinculadas entram direto. Se for um Google novo,
# o usuário precisa escolher usuário e senha próprios do Gepetto antes de entrar.
if not st.session_state.usuario and autenticar_google_se_configurado():
    try:
        if st.user.is_logged_in:
            email_google = str(st.user.email or "").strip().casefold()
            nome_google = str(getattr(st.user, "name", "") or "").strip()
            if not email_valido(email_google):
                st.error("O Google não retornou um e-mail válido.")
                st.stop()

            usuario_vinculado = encontrar_usuario_por_google_email(email_google)
            if usuario_vinculado:
                dados_google = carregar_dados(usuario_vinculado)
                if dados_google and dados_google.get("bloqueado", False):
                    st.error("Esta conta está bloqueada. Entre em contato com o ADM.")
                    st.stop()
                if dados_google and dados_google.get("senha_hash") and (
                    dados_google.get("salt") or dados_google.get("senha_salt")
                ):
                    if gerar_sessao(usuario_vinculado):
                        st.rerun()
                    st.error("Não foi possível abrir sua conta. Tente novamente.")
                    st.stop()

                # Conta Google criada pelo fluxo antigo, sem senha própria: pedir
                # usuário/senha para completar a configuração sem perder o histórico.
                st.session_state.google_flow_mode = "legacy"
                st.session_state.google_flow_email = email_google
                st.session_state.google_flow_name = nome_google
                st.session_state.google_flow_existing_user = usuario_vinculado
            else:
                usuario_por_email = encontrar_usuario_por_email(email_google)
                if usuario_por_email:
                    dados_existente = carregar_dados(usuario_por_email)
                    if dados_existente and dados_existente.get("bloqueado", False):
                        st.error("Esta conta está bloqueada. Entre em contato com o ADM.")
                        st.stop()
                    if dados_existente and dados_existente.get("senha_hash"):
                        # Para vincular Google a uma conta local já existente, pedir
                        # confirmação da senha atual em vez de assumir que é a mesma pessoa.
                        st.session_state.google_flow_mode = "link"
                        st.session_state.google_flow_email = email_google
                        st.session_state.google_flow_name = nome_google
                        st.session_state.google_flow_existing_user = usuario_por_email
                    else:
                        st.session_state.google_flow_mode = "legacy"
                        st.session_state.google_flow_email = email_google
                        st.session_state.google_flow_name = nome_google
                        st.session_state.google_flow_existing_user = usuario_por_email
                else:
                    st.session_state.google_flow_mode = "new"
                    st.session_state.google_flow_email = email_google
                    st.session_state.google_flow_name = nome_google
                    st.session_state.google_flow_existing_user = ""
    except Exception:
        st.error("Não foi possível concluir o login com Google. Tente novamente.")

if not st.session_state.usuario and st.session_state.get("google_flow_mode"):
    modo_google = st.session_state.get("google_flow_mode", "new")
    email_google_pendente = str(st.session_state.get("google_flow_email", "")).strip().casefold()
    usuario_google_existente = str(st.session_state.get("google_flow_existing_user", "")).strip()

    st.subheader("🔐 Finalize sua conta do Gepetto")
    st.caption(f"Conta Google verificada: {email_google_pendente}")

    if modo_google == "link":
        st.write("Já existe uma conta do Gepetto com esse e-mail. Digite a senha atual do Gepetto para vincular o Google e manter seu usuário, senha e conversas.")
        with st.form("form_vincular_google_conta_existente"):
            st.text_input("Usuário do Gepetto", value=usuario_google_existente, disabled=True)
            senha_atual_vinculo = st.text_input("Senha atual do Gepetto", type="password")
            enviar_vinculo = st.form_submit_button("Vincular Google", use_container_width=True)
        if enviar_vinculo:
            sucesso, mensagem = vincular_google_a_conta_existente(
                usuario_google_existente, senha_atual_vinculo, email_google_pendente
            )
            if sucesso:
                st.success(mensagem)
                st.rerun()
            else:
                st.error(mensagem)

    elif modo_google == "legacy":
        st.write("Esta conta Google já existia no Gepetto, mas ainda não tem uma senha própria. Defina seu usuário e sua senha do Gepetto para continuar.")
        with st.form("form_completar_conta_google_antiga"):
            usuario_novo_google = st.text_input(
                "Escolha seu usuário",
                value=usuario_google_existente,
                max_chars=30,
            )
            senha_nova_google = st.text_input("Crie uma senha do Gepetto", type="password")
            confirmar_senha_google = st.text_input("Confirme a senha", type="password")
            enviar_conta_google_antiga = st.form_submit_button("Salvar usuário e senha", use_container_width=True)
        if enviar_conta_google_antiga:
            if senha_nova_google != confirmar_senha_google:
                st.error("As senhas não são iguais.")
            else:
                sucesso, mensagem = finalizar_cadastro_google(
                    usuario_novo_google,
                    senha_nova_google,
                    email_google_pendente,
                    usuario_existente=usuario_google_existente,
                )
                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)

    else:
        st.write("Crie sua conta vinculada ao Google. Você ainda terá um usuário e uma senha próprios do Gepetto.")
        with st.form("form_nova_conta_google"):
            sugestao_usuario = st.session_state.get("google_flow_name", "")
            sugestao_usuario = "".join(c if (c.isalnum() or c in "_-") else "_" for c in sugestao_usuario).strip("_-")[:30]
            if len(sugestao_usuario) < 3:
                sugestao_usuario = email_google_pendente.split("@", 1)[0]
                sugestao_usuario = "".join(c if (c.isalnum() or c in "_-") else "_" for c in sugestao_usuario).strip("_-")[:30]
            novo_usuario_google = st.text_input("Escolha um usuário", value=sugestao_usuario, max_chars=30)
            nova_senha_google = st.text_input("Crie uma senha do Gepetto", type="password")
            confirmar_nova_senha_google = st.text_input("Confirme a senha", type="password")
            enviar_nova_conta_google = st.form_submit_button("Criar conta com Google", use_container_width=True)
        if enviar_nova_conta_google:
            if nova_senha_google != confirmar_nova_senha_google:
                st.error("As senhas não são iguais.")
            else:
                sucesso, mensagem = finalizar_cadastro_google(
                    novo_usuario_google,
                    nova_senha_google,
                    email_google_pendente,
                )
                if sucesso:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.error(mensagem)

    st.stop()

if not st.session_state.usuario:
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login:
        st.subheader("Entrar na sua conta")

        with st.form("form_login"):
            login_usuario = st.text_input("Usuário", max_chars=30)
            login_senha = st.text_input("Senha", type="password")
            enviar_login = st.form_submit_button("Entrar", use_container_width=True)

        if enviar_login:
            usuario_digitado = login_usuario.strip()
            dados_login = carregar_dados(usuario_digitado)
            if (
                dados_login
                and not dados_login.get("bloqueado", False)
                and verificar_senha(dados_login, login_senha)
            ):
                nome_autenticado = dados_login.get("usuario") or usuario_digitado
                if gerar_sessao(nome_autenticado):
                    st.rerun()
                else:
                    st.error("Não foi possível salvar os dados da sessão.")
            elif dados_login and dados_login.get("bloqueado", False):
                st.error("Esta conta está bloqueada. Entre em contato com o ADM.")
            else:
                st.error("Usuário ou senha incorretos.")

        st.divider()
        if autenticar_google_se_configurado():
            if st.button("🔐 Continuar com Google", use_container_width=True, key="login_google"):
                st.login("google")
        else:
            st.caption("Configure as credenciais OAuth do Google nos Secrets do Streamlit para ativar o login Google.")

        with st.expander("Esqueci minha senha"):
            st.caption("Se a conta estiver vinculada ao Google, o Gepetto usa o e-mail Google para enviar o código de recuperação da senha do Gepetto.")
            st.caption("Contas criadas sem Google precisam ter um e-mail de recuperação cadastrado nas configurações da conta.")
            email_recuperacao = st.text_input("E-mail de recuperação", key="email_recuperacao_login")
            if st.button("Enviar código de recuperação", use_container_width=True, key="enviar_recuperacao_login"):
                if not email_valido(email_recuperacao):
                    st.error("Informe um e-mail válido.")
                else:
                    usuario_recuperacao = encontrar_usuario_por_email(email_recuperacao)
                    if not usuario_recuperacao:
                        st.error("Não encontramos uma conta vinculada a esse e-mail. Se você não cadastrou e-mail de recuperação, entre com Google se a conta estiver vinculada ou peça ajuda ao ADM.")
                    else:
                        try:
                            enviar_codigo_para_email(email_recuperacao)
                            st.session_state.recuperacao_usuario = usuario_recuperacao
                            st.success("Código enviado para o e-mail cadastrado. Ele expira em 10 minutos.")
                        except Exception:
                            st.error("Não foi possível enviar o código. Confira SMTP_EMAIL e SMTP_APP_PASSWORD nos Secrets.")

            if st.session_state.get("recuperacao_usuario"):
                with st.form("form_confirmar_recuperacao_login"):
                    codigo_recuperacao = st.text_input("Código recebido por e-mail", max_chars=6, type="password")
                    nova_senha_recuperada = st.text_input("Nova senha", type="password")
                    confirmar_senha_recuperada = st.text_input("Confirme a nova senha", type="password")
                    confirmar_recuperacao = st.form_submit_button("Verificar código e redefinir senha", use_container_width=True)
                if confirmar_recuperacao:
                    ok_codigo, msg_codigo = verificar_codigo_recuperacao(codigo_recuperacao, email_recuperacao)
                    if not ok_codigo:
                        st.error(msg_codigo)
                    elif nova_senha_recuperada != confirmar_senha_recuperada:
                        st.error("As senhas não são iguais.")
                    else:
                        ok_senha, msg_senha = atualizar_senha_usuario(st.session_state.recuperacao_usuario, nova_senha_recuperada)
                        (st.success if ok_senha else st.error)(msg_senha)
                        if ok_senha:
                            st.session_state.recuperacao_usuario = ""
                            st.session_state.recuperacao_codigo_verificado_ate = 0
                            st.info("Agora entre com sua nova senha do Gepetto.")

    with aba_cadastro:
        st.subheader("Criar uma conta")
        st.write("Escolha uma das opções: crie uma conta com Google (e depois defina usuário e senha do Gepetto) ou cadastre-se diretamente.")

        if autenticar_google_se_configurado():
            if st.button("➕ Criar conta com Google", use_container_width=True, key="criar_conta_google"):
                st.login("google")
        else:
            st.caption("O cadastro com Google só fica disponível depois de configurar o OAuth nos Secrets do Streamlit.")

        st.divider()
        st.subheader("Ou crie uma conta com usuário e senha")
        with st.form("form_cadastro"):
            novo_usuario = st.text_input("Escolha um usuário", max_chars=30)
            nova_senha = st.text_input("Escolha uma senha", type="password")
            confirmar_senha = st.text_input("Confirme a senha", type="password")
            enviar_cadastro = st.form_submit_button("Criar conta", use_container_width=True)

        if enviar_cadastro:
            if nova_senha != confirmar_senha:
                st.error("As senhas não são iguais.")
            else:
                sucesso, mensagem = criar_conta(novo_usuario, nova_senha)
                if sucesso:
                    st.success(mensagem)
                    st.info("Agora entre pela aba Entrar. Para recuperar a senha no futuro, adicione um e-mail em 'Meu e-mail de recuperação' depois de entrar.")
                else:
                    st.error(mensagem)

    st.stop()
