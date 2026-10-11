
import os
import json
import hmac
import hashlib
import secrets
from pathlib import Path

import streamlit as st
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
PASTA_DADOS.mkdir(exist_ok=True)

COOKIE_NOME = "gepetto_usuario"

cookies = EncryptedCookieManager(
    prefix="gepetto/",
    password=st.secrets.get(
        "COOKIES_PASSWORD",
        "senha-temporaria-troque-esta-chave",
    ),
)

if not cookies.ready():
    st.stop()


# =========================
# GROQ
# =========================

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    cliente = Groq(api_key=GROQ_API_KEY)
except Exception:
    st.error(
        "Não foi possível configurar a IA. "
        "Confira a GROQ_API_KEY nos Secrets do Streamlit."
    )
    st.stop()

MODELO = "openai/gpt-oss-20b"


# =========================
# ARQUIVOS E USUÁRIOS
# =========================

def caminho_usuario(usuario):
    nome_seguro = hashlib.sha256(
        usuario.lower().encode("utf-8")
    ).hexdigest()
    return PASTA_DADOS / f"{nome_seguro}.json"


def carregar_dados(usuario):
    caminho = caminho_usuario(usuario)

    if not caminho.exists():
        return None

    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if not isinstance(dados, dict):
            return None

        # Compatibilidade com formatos anteriores.
        if "chats" not in dados:
            dados["chats"] = {
                "Conversa 1": []
            }

        if not isinstance(dados["chats"], dict):
            dados["chats"] = {
                "Conversa 1": []
            }

        if "chat_atual" not in dados:
            dados["chat_atual"] = next(
                iter(dados["chats"]),
                "Conversa 1",
            )

        if dados["chat_atual"] not in dados["chats"]:
            dados["chats"][dados["chat_atual"]] = []

        return dados

    except (OSError, json.JSONDecodeError):
        return None


def salvar_dados(usuario, dados):
    caminho = caminho_usuario(usuario)
    temporario = caminho.with_suffix(".tmp")

    with temporario.open("w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2,
        )

    temporario.replace(caminho)


def gerar_senha(senha):
    salt = secrets.token_hex(16)
    senha_hash = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()

    return salt, senha_hash


def verificar_senha(dados, senha):
    # Formato atual.
    if "senha_salt" in dados and "senha_hash" in dados:
        tentativa = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            dados["senha_salt"].encode("utf-8"),
            200_000,
        ).hex()

        return hmac.compare_digest(
            tentativa,
            dados["senha_hash"],
        )

    # Compatibilidade com formato antigo: salt e senha.
    if "salt" in dados and "senha" in dados:
        tentativa = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            str(dados["salt"]).encode("utf-8"),
            200_000,
        ).hex()

        return hmac.compare_digest(
            tentativa,
            str(dados["senha"]),
        )

    return False


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
        "chats": {
            "Conversa 1": []
        },
        "chat_atual": "Conversa 1",
    }

    salvar_dados(usuario, dados)
    return True, "Conta criada com sucesso!"


def excluir_conta(usuario):
    caminho = caminho_usuario(usuario)

    try:
        if caminho.exists():
            caminho.unlink()

        # Apaga o cookie de login.
        cookies[COOKIE_NOME] = ""
        cookies.save()

        # Limpa o estado da sessão.
        for chave in list(st.session_state.keys()):
            del st.session_state[chave]

        st.rerun()

    except OSError:
        st.error(
            "Não foi possível excluir os dados da conta. "
            "Tente novamente."
        )


# =========================
# ESTADO DA SESSÃO
# =========================

if "usuario" not in st.session_state:
    st.session_state.usuario = cookies.get(COOKIE_NOME, "")

if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = False

if "mensagens_temporarias" not in st.session_state:
    st.session_state.mensagens_temporarias = []


# =========================
# CABEÇALHO
# =========================

st.title("🤖 Gepetto AI")
st.caption("Uma inteligência artificial da Família Bezerra")


# =========================
# LOGIN E CADASTRO
# =========================

if not st.session_state.usuario:
    aba_login, aba_cadastro = st.tabs(
        ["Entrar", "Criar conta"]
    )

    with aba_login:
        st.subheader("Entrar na sua conta")

        login_usuario = st.text_input(
            "Usuário",
            key="login_usuario",
        )

        login_senha = st.text_input(
            "Senha",
            type="password",
            key="login_senha",
        )

        if st.button(
            "Entrar",
            use_container_width=True,
        ):
            dados = carregar_dados(login_usuario.strip())

            if dados and verificar_senha(dados, login_senha):
                st.session_state.usuario = dados["usuario"]
                cookies[COOKIE_NOME] = dados["usuario"]
                cookies.save()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with aba_cadastro:
        st.subheader("Criar sua conta")

        novo_usuario = st.text_input(
            "Escolha um usuário",
            key="novo_usuario",
        )

        nova_senha = st.text_input(
            "Escolha uma senha",
            type="password",
            key="nova_senha",
        )

        confirmar_senha = st.text_input(
            "Confirme a senha",
            type="password",
            key="confirmar_senha",
        )

        if st.button(
            "Criar conta",
            use_container_width=True,
        ):
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
    cookies[COOKIE_NOME] = ""
    cookies.save()
    st.session_state.usuario = ""
    st.rerun()

# Salva possíveis ajustes de formato.
salvar_dados(usuario, dados)


# =========================
# BARRA LATERAL
# =========================

with st.sidebar:
    st.title("💬 Conversas")
    st.caption(f"Conta: {usuario}")

    nomes_chats = list(dados["chats"].keys())

    if not nomes_chats:
        dados["chats"] = {"Conversa 1": []}
        dados["chat_atual"] = "Conversa 1"
        salvar_dados(usuario, dados)
        nomes_chats = ["Conversa 1"]

    if dados["chat_atual"] not in nomes_chats:
        dados["chat_atual"] = nomes_chats[0]

    conversa_selecionada = st.selectbox(
        "Escolha uma conversa",
        nomes_chats,
        index=nomes_chats.index(dados["chat_atual"]),
    )

    if conversa_selecionada != dados["chat_atual"]:
        dados["chat_atual"] = conversa_selecionada
        salvar_dados(usuario, dados)
        st.rerun()

    if st.button(
        "➕ Nova conversa",
        use_container_width=True,
    ):
        numero = 1
        while f"Conversa {numero}" in dados["chats"]:
            numero += 1

        nome = f"Conversa {numero}"
        dados["chats"][nome] = []
        dados["chat_atual"] = nome
        salvar_dados(usuario, dados)
        st.rerun()

    st.divider()

    if st.button(
        "🚪 Sair da conta",
        use_container_width=True,
    ):
        cookies[COOKIE_NOME] = ""
        cookies.save()
        st.session_state.usuario = ""
        st.session_state.confirmar_exclusao = False
        st.rerun()

    # BOTÃO PARA EXCLUIR A CONTA
    st.divider()

    if st.button(
        "🗑️ Excluir minha conta",
        use_container_width=True,
    ):
        st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        st.warning(
            "Isso apagará sua conta e o histórico de conversas "
            "salvos neste armazenamento. Essa ação não pode ser desfeita."
        )

        if st.button(
            "SIM, EXCLUIR CONTA",
            use_container_width=True,
            type="primary",
        ):
            excluir_conta(usuario)

        if st.button(
            "Cancelar exclusão",
            use_container_width=True,
        ):
            st.session_state.confirmar_exclusao = False
            st.rerun()


# =========================
# HISTÓRICO DA CONVERSA
# =========================

st.subheader(dados["chat_atual"])

mensagens = dados["chats"][dados["chat_atual"]]

for mensagem in mensagens:
    papel = mensagem.get("role", "assistant")
    conteudo = mensagem.get("content", "")

    if papel not in ("user", "assistant"):
        continue

    with st.chat_message(papel):
        st.markdown(conteudo)


# =========================
# ENVIAR MENSAGEM
# =========================

pergunta = st.chat_input("Converse com o Gepetto...")

if pergunta:
    mensagens.append({
        "role": "user",
        "content": pergunta,
    })
    salvar_dados(usuario, dados)

    with st.chat_message("user"):
        st.markdown(pergunta)

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

            texto = resposta.choices[0].message.content or (
                "Não consegui gerar uma resposta."
            )

            area_resposta.markdown(texto)

            mensagens.append({
                "role": "assistant",
                "content": texto,
            })
            salvar_dados(usuario, dados)

        except Exception as erro:
            area_resposta.error(
                "Não consegui falar com a IA. "
                "Verifique a conexão e a configuração da Groq."
            )
            st.caption(f"Detalhes técnicos: {erro}")


# =========================
# RODAPÉ
# =========================

st.divider()
st.caption("Gepetto AI • Uma inteligência artificial da Família Bezerra")
