import streamlit as st

st.set_page_config(
    page_title="Gepetto AI",
    page_icon="🤖",
    layout="centered",
)

# Importing the shared core restores the cookie-backed session and defines the common helpers.
import gepetto_core as core
core.inicializar_runtime()

usuario_atual = str(st.session_state.get("usuario", "")).strip()

if not usuario_atual:
    paginas = [
        st.Page("views/login.py", title="Entrar / Criar conta", icon="🔐", default=True),
    ]
else:
    paginas = [
        st.Page("views/chat.py", title="Conversas", icon="💬", default=True),
    ]
    if core.eh_admin(usuario_atual):
        paginas.append(
            st.Page("views/admin.py", title="Painel de ADM", icon="🛡️"),
        )

pagina_atual = st.navigation(paginas, position="sidebar", expanded=True)
pagina_atual.run()
