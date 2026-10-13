import streamlit as st
from gepetto_core import *  # noqa: F401,F403 — shared authorization and admin panel

inicializar_runtime()

usuario_admin = str(st.session_state.get("usuario", "")).strip()
if not usuario_admin:
    st.switch_page("views/login.py")
    st.stop()

# Segurança em profundidade: esconder a página na navegação não substitui autorização.
if not eh_admin(usuario_admin):
    st.error("Acesso negado. Esta página é exclusiva da conta administrativa.")
    st.stop()

# Revalidar os dados da conta antes de renderizar a área privilegiada.
dados_admin = carregar_dados(usuario_admin)
if not dados_admin or dados_admin.get("bloqueado", False):
    encerrar_sessao()
    st.error("A sessão administrativa não está mais válida. Entre novamente.")
    st.stop()

st.title("🤖 Gepetto AI")
st.caption("Área administrativa protegida")
mostrar_painel_admin(usuario_admin)
