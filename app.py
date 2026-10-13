"""Ponto de entrada e roteador do Gepetto AI.

As rotas são registradas em todas as execuções, inclusive antes de a sessão
ser restaurada pelos cookies. Cada página inicializa e valida sua própria
sessão antes de mostrar conteúdo protegido.
"""

import streamlit as st

st.set_page_config(
    page_title="Gepetto AI",
    page_icon="🤖",
    layout="centered",
)

import gepetto_core as core  # noqa: E402

usuario_atual = str(st.session_state.get("usuario", "")).strip()
usuario_admin = bool(usuario_atual and core.eh_admin(usuario_atual))

# IMPORTANTE: mantenha todas as páginas registradas. Isso permite que URLs
# como /chat e /adm sejam reconhecidas mesmo em uma sessão recém-iniciada.
# As páginas ocultas continuam protegidas por verificações dentro dos próprios
# módulos (views/chat.py e views/admin.py).
paginas = [
    st.Page(
        "views/home.py",
        title="Início",
        icon="🤖",
        default=True,
    ),
    st.Page(
        "views/login.py",
        title="Entrar / Criar conta",
        icon="🔐",
        url_path="login",
        visibility="hidden" if usuario_atual else "visible",
    ),
    st.Page(
        "views/chat.py",
        title="Conversas",
        icon="💬",
        url_path="chat",
        visibility="visible" if usuario_atual else "hidden",
    ),
    st.Page(
        "views/admin.py",
        title="Painel de ADM",
        icon="🛡️",
        url_path="adm",
        visibility="visible" if usuario_admin else "hidden",
    ),
]

pagina_atual = st.navigation(paginas, position="sidebar", expanded=True)
pagina_atual.run()
