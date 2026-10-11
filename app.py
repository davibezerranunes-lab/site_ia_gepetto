
import json
import hmac
import hashlib
import secrets
import re
from pathlib import Path

import streamlit as st

if not hasattr(st, "cache"):
    st.cache = st.cache_data

from groq import Groq
from streamlit_cookies_manager import EncryptedCookieManager


# =========================
# CONFIGURAÇÃO
# =========================

st.set_page_config(
    page_title="Gepetto AI",
    page_icon="🤖",
    layout="centered",
)

PASTA_DADOS = Path("dados_usuarios")
PASTA_DADOS.mkdir(parents=True, exist_ok=True)

COOKIE_NOME = "gepetto_usuario"
ITERACOES_PBKDF2 = 200_000
MODELO = "openai/gpt-oss-20b"


# =========================
# COOKIES
# =========================

try:
    cookies = EncryptedCookieManager(
        prefix="gepetto/",
        password=st.secrets["COOKIES_PASSWORD"],
    )

    if not cookies.ready():
        st.info("Carregando sua sessão...")
        st.stop()

except Exception:
    st.error(
        "Não foi possível inicializar os cookies. "
        "Confira COOKIES_PASSWORD nos Secrets."
    )
    st.stop()

# =========================
# GROQ
# =========================

try:
    cliente = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error(
        "Não foi possível configurar a IA. "
        "Confira GROQ_API_KEY nos Secrets."
    )
    st.stop()


# =========================
# ARQUIVOS E USUÁRIOS
# =========================

def caminho_usuario(usuario):
    identificador = hashlib.sha256(
        usuario.strip().lower().encode("utf-8")
    ).hexdigest()

    return PASTA_DADOS / f"{identificador}.json"


def carregar_dados(usuario):
    caminho = caminho_usuario(usuario)

    if not caminho.exists():
        return None

    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if not isinstance(dados, dict):
            return None

        dados["usuario"] = dados.get("usuario") or usuario.strip()

        chats = dados.get("chats")
        if not isinstance(chats, dict):
            chats = {}

        chats_validos = {}

        for nome, mensagens in chats.items():
            if not isinstance(nome, str):
                continue

            if not isinstance(mensagens, list):
                mensagens = []

            mensagens_validas = []

            for mensagem in mensagens:
                if not isinstance(mensagem, dict):
                    continue

                papel = mensagem.get("role")
                conteudo = mensagem.get("content")

                if papel not in ("user", "assistant"):
                    continue

                if not isinstance(conteudo, str):
                    continue

                mensagens_validas.append({
                    "role": papel,
                    "content": conteudo,
                })

            chats_validos[nome] = mensagens_validas

        if not chats_validos:
            chats_validos = {"Conversa 1": []}

        dados["chats"] = chats_validos

        chat_atual = dados.get("chat_atual")
        if (
            not isinstance(chat_atual, str)
            or chat_atual not in chats_validos
        ):
            chat_atual = next(iter(chats_validos))

        dados["chat_atual"] = chat_atual
        return dados

    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def salvar_dados(usuario, dados):
    caminho = caminho_usuario(usuario)
    temporario = caminho.with_suffix(".tmp")

    try:
        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump(
                dados,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        temporario.replace(caminho)
        return True

    except OSError:
        try:
            if temporario.exists():
                temporario.unlink()
        except OSError:
            pass

        return False


# =========================
# NOME AUTOMÁTICO DO CHAT
# =========================

def gerar_nome_chat(texto):
    texto = " ".join(texto.strip().split())

    # Remove pontuação apenas do final da frase.
    texto = texto.rstrip(" .,!?:;")

    if not texto:
        return "Nova conversa"

    palavras = texto.split()
    nome = " ".join(palavras[:6])

    if len(palavras) > 6:
        nome += "..."

    return nome[:50]


def nome_chat_disponivel(chats, nome, chat_original=None):
    nome_base = nome[:50]
    nome_final = nome_base
    contador = 2

    while nome_final in chats and nome_final != chat_original:
        sufixo = f" ({contador})"
        nome_final = nome_base[:50 - len(sufixo)] + sufixo
        contador += 1

    return nome_final


# =========================
# SENHAS
# =========================

def gerar_senha(senha):
    salt = secrets.token_hex(16)

    senha_hash = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        ITERACOES_PBKDF2,
    ).hex()

    return salt, senha_hash


def verificar_senha(dados, senha):
    try:
        if "senha_salt" in dados and "senha_hash" in dados:
            salt = str(dados["senha_salt"])
            hash_salvo = str(dados["senha_hash"])
        elif "salt" in dados and "senha" in dados:
            salt = str(dados["salt"])
            hash_salvo = str(dados["senha"])
        else:
            return False

        tentativa = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt.encode("utf-8"),
            ITERACOES_PBKDF2,
        ).hex()

        return hmac.compare_digest(tentativa, hash_salvo)

    except (TypeError, ValueError, KeyError):
        return False


# =========================
# CADASTRO
# =========================

def criar_conta(usuario, senha):
    usuario = usuario.strip()

    if len(usuario) < 3:
        return False, "O usuário precisa ter pelo menos 3 caracteres."

    if len(usuario) > 30:
        return False, "O usuário pode ter no máximo 30 caracteres."

    if not all(c.isalnum() or c in "_-" for c in usuario):
        return False, "Use apenas letras, números, _ ou - no usuário."

    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."

    if caminho_usuario(usuario).exists():
        return False, "Esse usuário já existe."

    salt, senha_hash = gerar_senha(senha)

    dados = {
        "usuario": usuario,
        "senha_salt": salt,
        "senha_hash": senha_hash,
        "chats": {},
        "chat_atual": "",
    }

    if not salvar_dados(usuario, dados):
        return False, "Não foi possível salvar a conta."

    return True, "Conta criada com sucesso!"


# =========================
# SESSÃO E EXCLUSÃO
# =========================

def encerrar_sessao():
    cookies[COOKIE_NOME] = ""
    cookies.save()

    st.session_state.usuario = ""
    st.session_state.confirmar_exclusao = False
    st.session_state.confirmar_exclusao_chat = False


def excluir_conta(usuario):
    caminho = caminho_usuario(usuario)

    try:
        if caminho.exists():
            caminho.unlink()

        encerrar_sessao()
        st.rerun()

    except OSError:
        st.error("Não foi possível excluir os dados da conta.")


def excluir_chat(usuario, dados, nome_chat):
    if nome_chat not in dados["chats"]:
        return False

    del dados["chats"][nome_chat]

    if dados["chats"]:
        dados["chat_atual"] = next(iter(dados["chats"]))
    else:
        dados["chat_atual"] = ""

    return salvar_dados(usuario, dados)


if "usuario" not in st.session_state:
    st.session_state.usuario = cookies.get(COOKIE_NOME, "")

if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = False

if "confirmar_exclusao_chat" not in st.session_state:
    st.session_state.confirmar_exclusao_chat = False


# =========================
# CABEÇALHO
# =========================

st.title("🤖 Gepetto AI")
st.caption("Uma inteligência artificial da Família Bezerra")


# =========================
# LOGIN E CADASTRO
# =========================

if not st.session_state.usuario:
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login:
        st.subheader("Entrar na sua conta")

        with st.form("form_login"):
            login_usuario = st.text_input("Usuário", max_chars=30)
            login_senha = st.text_input("Senha", type="password")

            enviar_login = st.form_submit_button(
                "Entrar",
                use_container_width=True,
            )

        if enviar_login:
            usuario_digitado = login_usuario.strip()
            dados_login = carregar_dados(usuario_digitado)

            if dados_login and verificar_senha(dados_login, login_senha):
                nome_autenticado = (
                    dados_login.get("usuario") or usuario_digitado
                )

                dados_login["usuario"] = nome_autenticado

                if salvar_dados(nome_autenticado, dados_login):
                    st.session_state.usuario = nome_autenticado
                    cookies[COOKIE_NOME] = nome_autenticado
                    cookies.save()
                    st.rerun()
                else:
                    st.error("Não foi possível atualizar os dados da conta.")
            else:
                st.error("Usuário ou senha incorretos.")

    with aba_cadastro:
        st.subheader("Criar sua conta")

        with st.form("form_cadastro"):
            novo_usuario = st.text_input(
                "Escolha um usuário",
                max_chars=30,
            )
            nova_senha = st.text_input("Escolha uma senha", type="password")
            confirmar_senha = st.text_input(
                "Confirme a senha",
                type="password",
            )

            enviar_cadastro = st.form_submit_button(
                "Criar conta",
                use_container_width=True,
            )

        if enviar_cadastro:
            if nova_senha != confirmar_senha:
                st.error("As senhas não são iguais.")
            else:
                sucesso, mensagem = criar_conta(
                    novo_usuario,
                    nova_senha,
                )

                if sucesso:
                    st.success(mensagem)
                    st.info("Agora entre na aba Entrar.")
                else:
                    st.error(mensagem)

    st.stop()


# =========================
# CARREGAR CONTA
# =========================

usuario = st.session_state.usuario
dados = carregar_dados(usuario)

if dados is None:
    encerrar_sessao()
    st.warning("Não foi possível localizar os dados dessa conta. Entre novamente.")
    st.rerun()

dados["usuario"] = dados.get("usuario") or usuario

if not salvar_dados(usuario, dados):
    st.warning("Não foi possível atualizar o arquivo da conta.")


# =========================
# BARRA LATERAL
# =========================

with st.sidebar:
    st.title("💬 Conversas")
    st.caption(f"Conta: {usuario}")

    nomes_chats = list(dados["chats"].keys())

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

    if nomes_chats:
        nomes_chats = list(dados["chats"].keys())

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

        if st.button("🗑️ Excluir conversa selecionada", use_container_width=True):
            st.session_state.confirmar_exclusao_chat = True

        if st.session_state.confirmar_exclusao_chat:
            st.warning(
                f"Excluir a conversa '{dados['chat_atual']}'? "
                "Essa ação não pode ser desfeita."
            )

            if st.button("SIM, EXCLUIR CONVERSA", use_container_width=True):
                nome_excluir = dados["chat_atual"]

                if excluir_chat(usuario, dados, nome_excluir):
                    st.session_state.confirmar_exclusao_chat = False
                    st.rerun()
                else:
                    st.error("Não foi possível excluir a conversa.")

            if st.button("Cancelar exclusão da conversa", use_container_width=True):
                st.session_state.confirmar_exclusao_chat = False
                st.rerun()
    else:
        st.info("Você ainda não tem conversas. Crie uma para começar.")

    st.divider()

    if st.button("🚪 Sair da conta", use_container_width=True):
        encerrar_sessao()
        st.rerun()

    st.divider()

    if st.button("🗑️ Excluir minha conta", use_container_width=True):
        st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        st.warning(
            "Isso apagará a conta e todo o histórico deste armazenamento."
        )

        if st.button(
            "SIM, EXCLUIR CONTA",
            use_container_width=True,
            type="primary",
        ):
            excluir_conta(usuario)

        if st.button("Cancelar exclusão da conta", use_container_width=True):
            st.session_state.confirmar_exclusao = False
            st.rerun()


# =========================
# HISTÓRICO
# =========================

chat_atual = dados["chat_atual"]

if chat_atual:
    st.subheader(chat_atual)
    mensagens = dados["chats"][chat_atual]

    for mensagem in mensagens:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
else:
    st.info("Clique em 'Nova conversa' para começar.")


# =========================
# ENVIAR MENSAGEM
# =========================

pergunta = st.chat_input("Converse com o Gepetto...")

if pergunta:
    if not dados["chat_atual"]:
        dados["chats"]["Nova conversa"] = []
        dados["chat_atual"] = "Nova conversa"

    chat_antigo = dados["chat_atual"]
    mensagens = dados["chats"][chat_antigo]

    # A primeira mensagem define o nome do chat.
    if not mensagens:
        nome_base = gerar_nome_chat(pergunta)
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
        "content": pergunta,
    })

    if not salvar_dados(usuario, dados):
        st.error("Não foi possível salvar sua mensagem.")

    st.rerun()


# A resposta é gerada na execução seguinte quando há uma mensagem
# de usuário ainda sem resposta do assistente.
if dados["chat_atual"]:
    mensagens = dados["chats"][dados["chat_atual"]]

    if mensagens and mensagens[-1]["role"] == "user":
        pergunta_pendente = mensagens[-1]["content"]

        with st.chat_message("assistant"):
            area_resposta = st.empty()

            try:
                resposta = cliente.chat.completions.create(
                    model=MODELO,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Você é Gepetto, uma IA prestativa, "
                                "clara e educada. Responda em português "
                                "quando o usuário escrever em português."
                            ),
                        },
                        *mensagens,
                    ],
                    temperature=0.7,
                    max_completion_tokens=2048,
                )

                texto = (
                    resposta.choices[0].message.content
                    or "Não consegui gerar uma resposta."
                )

                area_resposta.markdown(texto)

                mensagens.append({
                    "role": "assistant",
                    "content": texto,
                })

                if not salvar_dados(usuario, dados):
                    st.error("Não foi possível salvar a resposta no histórico.")

            except Exception:
                area_resposta.error(
                    "Não consegui falar com a IA. "
                    "Verifique a conexão e a configuração da Groq."
                )


# =========================
# RODAPÉ
# =========================

st.divider()
st.caption(
    "Gepetto AI • Uma inteligência artificial da Família Bezerra"
)
