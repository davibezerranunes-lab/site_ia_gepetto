
import os
import re
import json
import time
import hmac
import hashlib
import secrets
import uuid
from datetime import datetime

import streamlit as st
from groq import Groq
from streamlit_cookies_manager import EncryptedCookieManager

# ==================================================
# CONFIGURAÇÃO
# ==================================================
st.set_page_config(
    page_title="Gepeto AI",
    page_icon="🤖",
    layout="wide"
)

PASTA_DADOS = "dados_usuarios"
COOKIE_NOME = "gepetto_auth"
os.makedirs(PASTA_DADOS, exist_ok=True)

INSTRUCOES_SISTEMA = {
    "role": "system",
    "content": (
        "Você é o GEPETTO, uma inteligência artificial "
        "acolhedora e ajudadora. Responda sempre em português "
        "do Brasil. Seja amigável, prestativo e preciso. "
        "Quando a resposta for longa, RESUMA."
    )
}

# ==================================================
# COOKIES
# ==================================================
try:
    senha_cookies = str(st.secrets["COOKIES_PASSWORD"])

    cookies = EncryptedCookieManager(
        prefix="gepetto-ai/",
        password=senha_cookies
    )
except Exception:
    st.error(
        "Configure COOKIES_PASSWORD em "
        "Settings > Secrets no Streamlit Cloud."
    )
    st.stop()

if not cookies.ready():
    st.info("Carregando sua sessão...")
    st.stop()

# ==================================================
# GROQ
# ==================================================
@st.cache_resource
def get_groq_client(api_key):
    return Groq(api_key=api_key)


def obter_cliente():
    try:
        chave = str(st.secrets["GROQ_API_KEY"]).strip()
        return get_groq_client(chave) if chave else None
    except Exception:
        return None


client = obter_cliente()

# ==================================================
# CONTAS E ARQUIVOS
# ==================================================
def obter_nome_arquivo(apelido):
    nome = re.sub(
        r"[^a-zA-Z0-9_-]",
        "",
        apelido.strip().lower()
    )
    if not nome:
        raise ValueError("Apelido inválido.")
    return os.path.join(PASTA_DADOS, f"historico_{nome}.json")


def gerar_hash_senha(senha):
    salt = os.urandom(16)
    derivacao = hashlib.pbkdf2_hmac(
        "sha256", senha.encode(), salt, 200000
    )
    return salt.hex() + ":" + derivacao.hex()


def verificar_senha(senha, salva):
    if ":" not in salva:
        return hmac.compare_digest(senha, salva)
    try:
        salt_hex, hash_salvo = salva.split(":", 1)
        derivacao = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode(),
            bytes.fromhex(salt_hex),
            200000
        ).hex()
        return hmac.compare_digest(derivacao, hash_salvo)
    except (ValueError, TypeError):
        return False


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def novo_chat():
    return {
        "id": uuid.uuid4().hex,
        "titulo": "Novo chat",
        "criado": datetime.now().isoformat(timespec="seconds"),
        "historico": [INSTRUCOES_SISTEMA.copy()]
    }


def carregar_dados(arquivo):
    if not os.path.exists(arquivo):
        return None
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            dados = json.load(f)

        # Migra automaticamente contas do formato antigo.
        if "chats" not in dados:
            historico_antigo = dados.pop("historico", [])
            if historico_antigo:
                titulo = "Conversa antiga"
                for m in historico_antigo:
                    if m.get("role") == "user":
                        titulo = m.get("content", titulo)[:35]
                        break
                dados["chats"] = [{
                    "id": uuid.uuid4().hex,
                    "titulo": titulo,
                    "criado": datetime.now().isoformat(timespec="seconds"),
                    "historico": historico_antigo
                }]
            else:
                dados["chats"] = [novo_chat()]

        if not dados["chats"]:
            dados["chats"] = [novo_chat()]

        return dados
    except (json.JSONDecodeError, OSError):
        return None


def salvar_dados(arquivo, dados):
    temporario = arquivo + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(temporario, arquivo)


def criar_conta(arquivo, senha):
    dados = {
        "senha": gerar_hash_senha(senha),
        "token_hash": "",
        "chats": [novo_chat()]
    }
    salvar_dados(arquivo, dados)
    return dados


# ==================================================
# LOGIN PERSISTENTE
# ==================================================
def entrar_sessao(arquivo, apelido, dados):
    st.session_state.autenticado = True
    st.session_state.apelido = apelido
    st.session_state.nome_arquivo = arquivo
    st.session_state.chat_id = dados["chats"][0]["id"]


def restaurar_login():
    try:
        token = cookies.get(COOKIE_NOME)
        if not token:
            return

        procurado = hash_token(token)

        for nome in os.listdir(PASTA_DADOS):
            if not nome.startswith("historico_") or not nome.endswith(".json"):
                continue

            arquivo = os.path.join(PASTA_DADOS, nome)
            dados = carregar_dados(arquivo)
            if not dados:
                continue

            salvo = dados.get("token_hash", "")
            if salvo and hmac.compare_digest(str(salvo), procurado):
                apelido = nome[len("historico_"):-len(".json")]
                entrar_sessao(arquivo, apelido, dados)
                return
    except Exception:
        pass


def criar_login(arquivo, apelido, dados):
    token = secrets.token_urlsafe(32)
    dados["token_hash"] = hash_token(token)
    salvar_dados(arquivo, dados)

    cookies[COOKIE_NOME] = token
    cookies.save()

    entrar_sessao(arquivo, apelido, dados)


def sair():
    arquivo = st.session_state.get("nome_arquivo", "")
    dados = carregar_dados(arquivo) if arquivo else None

    if dados:
        dados["token_hash"] = ""
        salvar_dados(arquivo, dados)

    try:
        if COOKIE_NOME in cookies:
            del cookies[COOKIE_NOME]
        cookies.save()
    except Exception:
        pass

    for chave in (
        "autenticado", "apelido", "nome_arquivo", "chat_id"
    ):
        st.session_state.pop(chave, None)


# ==================================================
# ESTADO
# ==================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    restaurar_login()

# ==================================================
# FUNÇÕES DE CONVERSA
# ==================================================
def dados_atuais():
    return carregar_dados(st.session_state.nome_arquivo)


def salvar_conversas(dados):
    salvar_dados(st.session_state.nome_arquivo, dados)


def chat_atual(dados):
    chat_id = st.session_state.get("chat_id")
    for chat in dados["chats"]:
        if chat["id"] == chat_id:
            return chat
    st.session_state.chat_id = dados["chats"][0]["id"]
    return dados["chats"][0]


def criar_novo_chat():
    dados = dados_atuais()
    chat = novo_chat()
    dados["chats"].insert(0, chat)
    salvar_conversas(dados)
    st.session_state.chat_id = chat["id"]


# ==================================================
# TELA DE LOGIN E CADASTRO
# ==================================================
st.title("🤖 GEPETTO")
st.caption("Seu assistente virtual pessoal")

if not st.session_state.autenticado:
    modo = st.radio(
        "Bem-vindo!",
        ["Entrar", "Criar conta"],
        horizontal=True
    )

    apelido = st.text_input("Apelido").strip()
    senha = st.text_input("Senha", type="password")

    if modo == "Criar conta":
        confirmar = st.text_input("Confirme a senha", type="password")

        if st.button("Criar conta", use_container_width=True):
            if not apelido or not senha:
                st.warning("Preencha o apelido e a senha.")
            elif senha != confirmar:
                st.error("As senhas não coincidem.")
            elif len(senha) < 4:
                st.warning("Use pelo menos 4 caracteres.")
            else:
                try:
                    arquivo = obter_nome_arquivo(apelido)
                    if os.path.exists(arquivo):
                        st.error("Esse apelido já está em uso.")
                    else:
                        dados = criar_conta(arquivo, senha)
                        criar_login(arquivo, apelido, dados)
                        st.rerun()
                except Exception as erro:
                    st.error(f"Erro ao criar conta: {erro}")

    else:
        if st.button("Entrar", use_container_width=True):
            if not apelido or not senha:
                st.warning("Preencha o apelido e a senha.")
            else:
                try:
                    arquivo = obter_nome_arquivo(apelido)
                    dados = carregar_dados(arquivo)

                    if not dados:
                        st.error("Conta não encontrada.")
                    elif verificar_senha(senha, str(dados.get("senha", ""))):
                        # Atualiza contas antigas com senha em texto puro.
                        if ":" not in str(dados["senha"]):
                            dados["senha"] = gerar_hash_senha(senha)
                        criar_login(arquivo, apelido, dados)
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
                except Exception as erro:
                    st.error(f"Erro ao entrar: {erro}")

    st.stop()

# ==================================================
# INTERFACE PRINCIPAL
# ==================================================
dados = dados_atuais()

if not dados:
    st.error("Não foi possível carregar sua conta.")
    st.stop()

if not dados.get("chats"):
    dados["chats"] = [novo_chat()]
    salvar_conversas(dados)

with st.sidebar:
    st.title("💬 Seus chats")
    st.caption(f"Conta: {st.session_state.apelido}")

    if st.button("➕ Novo chat", use_container_width=True):
        criar_novo_chat()
        st.rerun()

    st.divider()

    for chat in dados["chats"]:
        titulo = chat.get("titulo", "Novo chat")
        if len(titulo) > 30:
            titulo = titulo[:30] + "…"

        selecionado = chat["id"] == st.session_state.chat_id

        if st.button(
            ("▶ " if selecionado else "　") + titulo,
            key="abrir_" + chat["id"],
            use_container_width=True
        ):
            st.session_state.chat_id = chat["id"]
            st.rerun()

    st.divider()

    if st.button("🗑️ Excluir conversa atual", use_container_width=True):
        if len(dados["chats"]) == 1:
            dados["chats"] = [novo_chat()]
        else:
            dados["chats"] = [
                c for c in dados["chats"]
                if c["id"] != st.session_state.chat_id
            ]

        st.session_state.chat_id = dados["chats"][0]["id"]
        salvar_conversas(dados)
        st.rerun()

    if st.button("🚪 Sair da conta", use_container_width=True):
        sair()
        st.rerun()

chat = chat_atual(dados)
historico = chat["historico"]

st.subheader(chat.get("titulo", "Novo chat"))

for mensagem in historico:
    if mensagem["role"] == "system":
        continue
    with st.chat_message(
        mensagem["role"],
        avatar="🤖" if mensagem["role"] == "assistant" else None
    ):
        st.markdown(mensagem["content"])

pergunta = st.chat_input("Mande uma mensagem para o Gepetto...")

if pergunta:
    if client is None:
        st.error(
            "Configure GROQ_API_KEY em Streamlit Cloud > Settings > Secrets."
        )
        st.stop()

    historico.append({"role": "user", "content": pergunta})

    if chat.get("titulo") == "Novo chat":
        chat["titulo"] = pergunta.strip().replace("\n", " ")[:35]
    salvar_conversas(dados)

    with st.chat_message("user"):
        st.markdown(pergunta)

    try:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Gepetto está pensando..."):
                resposta = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=historico,
                    temperature=0.7,
                    max_tokens=2048
                )
                texto = (
                    resposta.choices[0].message.content
                    or "Não consegui gerar uma resposta."
                )
                st.markdown(texto)

        historico.append({"role": "assistant", "content": texto})
        salvar_conversas(dados)

    except Exception as erro:
        # Mantém a pergunta no histórico para não perder o que foi enviado.
        salvar_conversas(dados)
        st.error(f"Erro ao falar com o Gepetto: {erro}")
