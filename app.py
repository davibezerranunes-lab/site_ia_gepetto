
import os
import json
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

import streamlit as st
from groq import Groq
from streamlit_cookies_manager import EncryptedCookieManager

# =========================
# CONFIGURAÇÃO
# =========================

st.set_page_config(
    page_title="Gepetto AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

PASTA_DADOS = Path("dados_usuarios")
ARQUIVO_USUARIOS = PASTA_DADOS / "usuarios.json"

PASTA_DADOS.mkdir(exist_ok=True)

# =========================
# COOKIES E API
# =========================

try:
    senha_cookies = st.secrets["COOKIES_PASSWORD"]
except Exception:
    senha_cookies = os.environ.get("COOKIES_PASSWORD", "")

if not senha_cookies:
    st.error(
        "Configure COOKIES_PASSWORD nos Secrets do Streamlit "
        "com uma senha longa e aleatória."
    )
    st.stop()

cookies = EncryptedCookieManager(
    prefix="gepetto/",
    password=senha_cookies
)

if not cookies.ready():
    st.stop()

try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    api_key = os.environ.get("GROQ_API_KEY", "")

if not api_key:
    st.error("Configure GROQ_API_KEY nos Secrets do Streamlit.")
    st.stop()

cliente = Groq(api_key=api_key)
MODELO = "openai/gpt-oss-20b"

# =========================
# ARQUIVOS DE USUÁRIOS
# =========================

def carregar_usuarios():
    if not ARQUIVO_USUARIOS.exists():
        return {}

    try:
        with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            return dados if isinstance(dados, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def salvar_usuarios(usuarios):
    arquivo_temporario = ARQUIVO_USUARIOS.with_suffix(".tmp")

    with open(arquivo_temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            usuarios,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    os.replace(arquivo_temporario, ARQUIVO_USUARIOS)


usuarios = carregar_usuarios()

# =========================
# SENHAS
# =========================

def criar_hash(senha, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    resultado = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()

    return salt, resultado


def verificar_senha(senha, salt, hash_salvo):
    _, hash_calculado = criar_hash(senha, salt)
    return secrets.compare_digest(hash_calculado, hash_salvo)


# =========================
# ESTILO VISUAL
# =========================

st.markdown("""
<style>
    .stApp {
        background: #0b1020;
        color: #f1f5f9;
    }

    [data-testid="stSidebar"] {
        background: #080d19;
        border-right: 1px solid #202b42;
    }

    .gepetto-logo {
        font-size: 30px;
        font-weight: 800;
        color: #7c9cff;
        letter-spacing: -1px;
        margin-bottom: 2px;
    }

    .gepetto-subtitle {
        color: #8793ad;
        font-size: 13px;
        margin-bottom: 24px;
    }

    .gepetto-card {
        background: #111a2d;
        border: 1px solid #263450;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 16px;
    }

    .gepetto-welcome {
        text-align: center;
        padding: 70px 10px 35px 10px;
    }

    .gepetto-welcome h1 {
        font-size: 38px;
        color: #f1f5f9;
    }

    .gepetto-welcome p {
        font-size: 16px;
        color: #94a3b8;
    }

    div[data-testid="stChatMessage"] {
        background: #111a2d;
        border: 1px solid #202d45;
        border-radius: 15px;
        padding: 12px;
        margin-bottom: 12px;
    }

    .stButton > button {
        border-radius: 10px;
        border: 1px solid #2c3b59;
        background: #14213a;
        color: #f1f5f9;
        min-height: 40px;
    }

    .stButton > button:hover {
        border-color: #7c9cff;
        color: #ffffff;
    }

    [data-testid="stChatInput"] {
        border-color: #344563;
    }

    footer {
        visibility: hidden;
    }

    #MainMenu {
        visibility: hidden;
    }

    .footer-gepetto {
        text-align: center;
        color: #71809b;
        font-size: 12px;
        padding: 22px 0 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# SESSÃO
# =========================

if "usuario" not in st.session_state:
    st.session_state.usuario = cookies.get("usuario", "")

if "modo_auth" not in st.session_state:
    st.session_state.modo_auth = "Entrar"

if "chat_atual" not in st.session_state:
    st.session_state.chat_atual = None

if "confirmar_exclusao_conta" not in st.session_state:
    st.session_state.confirmar_exclusao_conta = False


# =========================
# FUNÇÕES DE CONVERSA
# =========================

def criar_conversa(usuario):
    novo_id = secrets.token_hex(8)

    nova_conversa = {
        "titulo": "Nova conversa",
        "mensagens": [],
        "criada_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    usuarios[usuario]["chats"][novo_id] = nova_conversa
    salvar_usuarios(usuarios)

    st.session_state.chat_atual = novo_id
    return novo_id


def obter_conversa(usuario, chat_id):
    return usuarios[usuario]["chats"].get(chat_id)


def excluir_conversa(usuario, chat_id):
    usuarios[usuario]["chats"].pop(chat_id, None)
    salvar_usuarios(usuarios)

    if st.session_state.chat_atual == chat_id:
        st.session_state.chat_atual = None


def gerar_titulo(texto):
    texto = " ".join(texto.strip().split())

    if not texto:
        return "Nova conversa"

    if len(texto) > 32:
        return texto[:32].rstrip() + "..."

    return texto


def responder_groq(mensagens):
    historico = [
        {
            "role": "system",
            "content": (
                "Você é Gepetto AI, um assistente útil, amigável e direto. "
                "Responda em português quando o usuário escrever em português. "
                "Use respostas claras e evite textos desnecessariamente longos."
            )
        }
    ]

    for mensagem in mensagens:
        if mensagem.get("role") in ("user", "assistant"):
            conteudo = mensagem.get("content", "")
            if isinstance(conteudo, str) and conteudo.strip():
                historico.append({
                    "role": mensagem["role"],
                    "content": conteudo
                })

    resposta = cliente.chat.completions.create(
        model=MODELO,
        messages=historico,
        temperature=0.7,
        max_completion_tokens=2048
    )

    return resposta.choices[0].message.content or "Não consegui gerar uma resposta."


# =========================
# TELA DE LOGIN E CADASTRO
# =========================

def tela_autenticacao():
    st.markdown(
        '<div class="gepetto-logo">🤖 Gepetto AI</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="gepetto-subtitle">Sua inteligência artificial pessoal</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="gepetto-card">', unsafe_allow_html=True)
    st.subheader("Bem-vindo ao Gepetto")

    modo = st.radio(
        "Escolha uma opção",
        ["Entrar", "Criar conta"],
        horizontal=True,
        key="seletor_auth"
    )

    with st.form("formulario_auth"):
        nome_usuario = st.text_input(
            "Nome de usuário",
            max_chars=30
        ).strip().lower()

        senha = st.text_input(
            "Senha",
            type="password"
        )

        if modo == "Criar conta":
            confirmar_senha = st.text_input(
                "Confirmar senha",
                type="password"
            )
        else:
            confirmar_senha = senha

        enviado = st.form_submit_button(
            "Entrar" if modo == "Entrar" else "Criar conta",
            use_container_width=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if not enviado:
        return

    if not nome_usuario or not senha:
        st.error("Preencha o usuário e a senha.")
        return

    if len(nome_usuario) < 3:
        st.error("O nome de usuário precisa ter pelo menos 3 caracteres.")
        return

    if len(senha) < 6:
        st.error("A senha precisa ter pelo menos 6 caracteres.")
        return

    if modo == "Criar conta":
        if senha != confirmar_senha:
            st.error("As senhas não são iguais.")
            return

        if nome_usuario in usuarios:
            st.error("Esse nome de usuário já existe.")
            return

        salt, senha_hash = criar_hash(senha)

        usuarios[nome_usuario] = {
            "salt": salt,
            "senha_hash": senha_hash,
            "chats": {}
        }

        salvar_usuarios(usuarios)
        cookies["usuario"] = nome_usuario
        cookies.save()

        st.session_state.usuario = nome_usuario
        st.session_state.chat_atual = None
        st.rerun()

    else:
        dados = usuarios.get(nome_usuario)

        if not dados or not verificar_senha(
            senha,
            dados["salt"],
            dados["senha_hash"]
        ):
            st.error("Usuário ou senha incorretos.")
            return

        cookies["usuario"] = nome_usuario
        cookies.save()

        st.session_state.usuario = nome_usuario
        st.session_state.chat_atual = None
        st.rerun()


# =========================
# APLICATIVO PRINCIPAL
# =========================

def aplicativo():
    usuario = st.session_state.usuario

    if usuario not in usuarios:
        st.session_state.usuario = ""
        cookies["usuario"] = ""
        cookies.save()
        st.rerun()

    usuarios[usuario].setdefault("chats", {})

    with st.sidebar:
        st.markdown(
            '<div class="gepetto-logo">🤖 Gepetto</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="gepetto-subtitle">Inteligência artificial</div>',
            unsafe_allow_html=True
        )

        if st.button("＋ Nova conversa", use_container_width=True):
            criar_conversa(usuario)
            st.rerun()

        st.divider()
        st.caption("SUAS CONVERSAS")

        chats = usuarios[usuario]["chats"]

        if not chats:
            st.caption("Nenhuma conversa ainda.")

        for chat_id, conversa in reversed(list(chats.items())):
            col1, col2 = st.columns([5, 1])

            with col1:
                selecionado = st.session_state.chat_atual == chat_id

                if st.button(
                    ("● " if selecionado else "　") + conversa.get(
                        "titulo", "Nova conversa"
                    ),
                    key=f"abrir_{chat_id}",
                    use_container_width=True
                ):
                    st.session_state.chat_atual = chat_id
                    st.rerun()

            with col2:
                if st.button("×", key=f"excluir_{chat_id}"):
                    excluir_conversa(usuario, chat_id)
                    st.rerun()

        st.divider()
        st.caption(f"Conectado como **{usuario}**")

        if st.button("Sair da conta", use_container_width=True):
            st.session_state.usuario = ""
            st.session_state.chat_atual = None
            cookies["usuario"] = ""
            cookies.save()
            st.rerun()

        if st.button("Excluir minha conta", use_container_width=True):
            st.session_state.confirmar_exclusao_conta = True

        if st.session_state.confirmar_exclusao_conta:
            st.warning("Isso apagará a conta e as conversas salvas.")

            if st.button("Confirmar exclusão da conta", type="primary"):
                usuarios.pop(usuario, None)
                salvar_usuarios(usuarios)

                st.session_state.usuario = ""
                st.session_state.chat_atual = None
                st.session_state.confirmar_exclusao_conta = False

                cookies["usuario"] = ""
                cookies.save()
                st.rerun()

            if st.button("Cancelar exclusão"):
                st.session_state.confirmar_exclusao_conta = False
                st.rerun()

    # Seleciona ou cria a conversa
    chat_id = st.session_state.chat_atual

    if chat_id not in usuarios[usuario]["chats"]:
        chat_id = None

    if chat_id is None:
        if usuarios[usuario]["chats"]:
            chat_id = next(iter(usuarios[usuario]["chats"]))
            st.session_state.chat_atual = chat_id
        else:
            chat_id = criar_conversa(usuario)

    conversa = obter_conversa(usuario, chat_id)

    if conversa is None:
        st.error("Não foi possível abrir esta conversa.")
        return

    st.title(conversa.get("titulo", "Nova conversa"))
    st.caption("Converse com o Gepetto AI")

    mensagens = conversa.setdefault("mensagens", [])

    if not mensagens:
        st.markdown("""
        <div class="gepetto-welcome">
            <h1>Como posso ajudar?</h1>
            <p>Faça uma pergunta para começar uma conversa.</p>
        </div>
        """, unsafe_allow_html=True)

    for mensagem in mensagens:
        papel = mensagem.get("role", "assistant")
        conteudo = mensagem.get("content", "")

        with st.chat_message(papel):
            st.markdown(conteudo)

    pergunta = st.chat_input("Envie uma mensagem para o Gepetto...")

    if pergunta and pergunta.strip():
        pergunta = pergunta.strip()

        if not mensagens:
            conversa["titulo"] = gerar_titulo(pergunta)

        mensagens.append({
            "role": "user",
            "content": pergunta
        })

        salvar_usuarios(usuarios)

        with st.chat_message("user"):
            st.markdown(pergunta)

        with st.chat_message("assistant"):
            with st.spinner("Gepetto está pensando..."):
                try:
                    resposta = responder_groq(mensagens)

                    st.markdown(resposta)

                    mensagens.append({
                        "role": "assistant",
                        "content": resposta
                    })

                    salvar_usuarios(usuarios)

                except Exception as erro:
                    st.error(
                        "Não consegui conectar à IA. "
                        "Verifique a API Groq e tente novamente."
                    )
                    print(f"Erro da Groq: {erro}")

        st.rerun()

    st.markdown(
        '<div class="footer-gepetto">Uma inteligência artificial da Família Bezerra</div>',
        unsafe_allow_html=True
    )


# =========================
# INICIALIZAÇÃO
# =========================

if st.session_state.usuario:
    aplicativo()
else:
    tela_autenticacao()
