
import os
import re
import json
import time
import hmac
import hashlib
import secrets

import streamlit as st
from groq import Groq
from streamlit_cookies_manager import EncryptedCookieManager

# ==================================================
# CONFIGURAÇÃO
# ==================================================
st.set_page_config(
    page_title="Gepeto AI",
    page_icon="🤖",
    layout="centered"
)

PASTA_DADOS = "dados_usuarios"
COOKIE_NOME = "gepetto_auth"
DURACAO_COOKIE = 30 * 24 * 60 * 60

os.makedirs(PASTA_DADOS, exist_ok=True)

# ==================================================
# COOKIES CRIPTOGRAFADOS
# ==================================================
try:
    senha_cookies = str(st.secrets["COOKIES_PASSWORD"])

    if len(senha_cookies) < 32:
        st.error(
            "COOKIES_PASSWORD precisa ter pelo menos "
            "32 caracteres. Configure em Settings > Secrets."
        )
        st.stop()

    cookies = EncryptedCookieManager(
        prefix="gepetto-ai/",
        password=senha_cookies
    )

except Exception:
    st.error(
        "Configure COOKIES_PASSWORD em "
        "Streamlit Cloud > Settings > Secrets."
    )
    st.stop()

# Aguarda o navegador disponibilizar os cookies.
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
        if chave:
            return get_groq_client(chave)
    except Exception:
        pass
    return None


client = obter_cliente()

# ==================================================
# PERSONALIDADE DO GEPETTO
# ==================================================
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
# USUÁRIOS E ARQUIVOS
# ==================================================
def obter_nome_arquivo(apelido):
    nome_limpo = re.sub(
        r"[^a-zA-Z0-9_-]",
        "",
        apelido.strip().lower()
    )

    if not nome_limpo:
        raise ValueError("Apelido inválido.")

    return os.path.join(
        PASTA_DADOS,
        f"historico_{nome_limpo}.json"
    )


def gerar_hash_senha(senha):
    salt = os.urandom(16)

    derivacao = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        200000
    )

    return salt.hex() + ":" + derivacao.hex()


def verificar_senha(senha, senha_salva):
    # Compatibilidade com contas antigas.
    if ":" not in senha_salva:
        return hmac.compare_digest(senha, senha_salva)

    try:
        salt_hex, hash_salvo = senha_salva.split(":", 1)
        salt = bytes.fromhex(salt_hex)

        derivacao = hashlib.pbkdf2_hmac(
            "sha256",
            senha.encode("utf-8"),
            salt,
            200000
        ).hex()

        return hmac.compare_digest(derivacao, hash_salvo)

    except (ValueError, TypeError):
        return False


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def carregar_dados_usuario(arquivo):
    if not os.path.exists(arquivo):
        return None

    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def salvar_dados_usuario(
    arquivo,
    senha_salva,
    historico,
    token_hash=None
):
    dados_antigos = carregar_dados_usuario(arquivo) or {}

    if token_hash is None:
        token_hash = dados_antigos.get("token_hash", "")

    dados = {
        "senha": senha_salva,
        "historico": historico,
        "token_hash": token_hash
    }

    temporario = arquivo + ".tmp"

    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(
            dados,
            f,
            ensure_ascii=False,
            indent=4
        )

    os.replace(temporario, arquivo)


def criar_historico():
    return [INSTRUCOES_SISTEMA.copy()]


# ==================================================
# SESSÃO E AUTENTICAÇÃO
# ==================================================
def limpar_sessao():
    st.session_state.autenticado = False
    st.session_state.historico = []
    st.session_state.nome_arquivo = ""
    st.session_state.apelido = ""
    st.session_state.confirmar_exclusao = False


def autenticar_usuario(arquivo, apelido, dados):
    historico = dados.get("historico", criar_historico())

    if not historico:
        historico = criar_historico()

    st.session_state.autenticado = True
    st.session_state.historico = historico
    st.session_state.nome_arquivo = arquivo
    st.session_state.apelido = apelido


def criar_cookie_login(arquivo, apelido, dados):
    # Token imprevisível. O arquivo guarda somente seu hash.
    token = secrets.token_urlsafe(32)

    senha_salva = dados.get("senha", "")
    historico = dados.get("historico", criar_historico())

    salvar_dados_usuario(
        arquivo,
        senha_salva,
        historico,
        token_hash=hash_token(token)
    )

    cookies[COOKIE_NOME] = token
    cookies.save()

    autenticar_usuario(arquivo, apelido, dados)


def restaurar_login():
    try:
        token = cookies.get(COOKIE_NOME)

        if not token or not isinstance(token, str):
            return False

        token_procurado = hash_token(token)

        for nome in os.listdir(PASTA_DADOS):
            if (
                not nome.startswith("historico_")
                or not nome.endswith(".json")
            ):
                continue

            arquivo = os.path.join(PASTA_DADOS, nome)
            dados = carregar_dados_usuario(arquivo)

            if not dados:
                continue

            token_salvo = dados.get("token_hash", "")

            if (
                token_salvo
                and hmac.compare_digest(
                    str(token_salvo),
                    token_procurado
                )
            ):
                apelido = nome[
                    len("historico_"):-len(".json")
                ]

                autenticar_usuario(
                    arquivo,
                    apelido,
                    dados
                )

                return True

    except Exception:
        return False

    return False


# ==================================================
# INICIALIZAÇÃO
# ==================================================
if "autenticado" not in st.session_state:
    limpar_sessao()

# Só tenta restaurar se esta sessão ainda não entrou.
if not st.session_state.autenticado:
    restaurar_login()

# ==================================================
# CABEÇALHO
# ==================================================
st.title("🤖 GEPETTO - Assistente Virtual")
st.write("---")

# ==================================================
# LOGIN E CADASTRO
# ==================================================
if not st.session_state.autenticado:

    conhece = st.radio(
        "Você já me conhece?",
        ("Selecione uma opção", "Sim", "Não")
    )

    if conhece == "Sim":
        apelido_input = st.text_input(
            "Digite seu apelido:"
        ).strip()

        senha_input = st.text_input(
            "Digite sua senha:",
            type="password"
        )

        if st.button("Entrar", use_container_width=True):
            if not apelido_input or not senha_input:
                st.warning("Preencha o apelido e a senha.")

            else:
                try:
                    arquivo = obter_nome_arquivo(apelido_input)
                    dados = carregar_dados_usuario(arquivo)

                    if dados is None:
                        st.error(
                            "Conta não encontrada. Confira o apelido "
                            "ou selecione Não para criar uma conta."
                        )

                    elif verificar_senha(
                        senha_input,
                        str(dados.get("senha", ""))
                    ):
                        senha_salva = dados["senha"]

                        # Converte senhas antigas em texto puro.
                        if ":" not in senha_salva:
                            senha_salva = gerar_hash_senha(
                                senha_input
                            )

                        dados["senha"] = senha_salva

                        # Cria uma sessão persistente no navegador.
                        criar_cookie_login(
                            arquivo,
                            apelido_input,
                            dados
                        )

                        st.success("Login realizado!")
                        time.sleep(0.5)
                        st.rerun()

                    else:
                        st.error("Senha incorreta!")

                except Exception as erro:
                    st.error(f"Erro ao entrar: {erro}")

    elif conhece == "Não":
        apelido_input = st.text_input(
            "Escolha um apelido:"
        ).strip()

        senha_input = st.text_input(
            "Crie uma senha de acesso:",
            type="password"
        )

        confirmar_senha = st.text_input(
            "Confirme sua senha:",
            type="password"
        )

        if st.button(
            "Criar Conta e Conversar",
            use_container_width=True
        ):
            if not apelido_input or not senha_input:
                st.warning("Preencha o apelido e crie uma senha.")

            elif senha_input != confirmar_senha:
                st.error("As senhas não são iguais.")

            elif len(senha_input) < 4:
                st.warning(
                    "Use uma senha com pelo menos 4 caracteres."
                )

            else:
                try:
                    arquivo = obter_nome_arquivo(apelido_input)

                    if os.path.exists(arquivo):
                        st.error(
                            "Esse apelido já está em uso! "
                            "Escolha outro ou faça login."
                        )

                    else:
                        historico = criar_historico()
                        senha_hash = gerar_hash_senha(senha_input)

                        dados = {
                            "senha": senha_hash,
                            "historico": historico,
                            "token_hash": ""
                        }

                        salvar_dados_usuario(
                            arquivo,
                            senha_hash,
                            historico,
                            token_hash=""
                        )

                        criar_cookie_login(
                            arquivo,
                            apelido_input,
                            dados
                        )

                        st.success("Conta criada com sucesso!")
                        time.sleep(0.5)
                        st.rerun()

                except Exception as erro:
                    st.error(f"Erro ao criar conta: {erro}")

# ==================================================
# CHAT
# ==================================================
else:
    st.subheader(
        f"Conversando com {st.session_state.apelido}"
    )

    with st.sidebar:
        st.write(f"Usuário: **{st.session_state.apelido}**")

        if st.button("Sair da Conta", use_container_width=True):
            arquivo = st.session_state.nome_arquivo
            dados = carregar_dados_usuario(arquivo)

            # Invalida o token no servidor.
            if dados:
                salvar_dados_usuario(
                    arquivo,
                    dados.get("senha", ""),
                    dados.get("historico", criar_historico()),
                    token_hash=""
                )

            # Remove o cookie persistente.
            try:
                if COOKIE_NOME in cookies:
                    del cookies[COOKIE_NOME]
                cookies.save()
            except Exception:
                pass

            limpar_sessao()
            st.rerun()

        st.write("---")

        if st.button(
            "🗑️ Deletar conta e histórico",
            use_container_width=True
        ):
            st.session_state.confirmar_exclusao = True

        if st.session_state.confirmar_exclusao:
            st.warning(
                "Tem certeza? Essa ação não pode ser desfeita."
            )

            if st.button("Confirmar exclusão"):
                arquivo = st.session_state.nome_arquivo

                if os.path.exists(arquivo):
                    os.remove(arquivo)

                try:
                    if COOKIE_NOME in cookies:
                        del cookies[COOKIE_NOME]
                    cookies.save()
                except Exception:
                    pass

                limpar_sessao()
                st.rerun()

            if st.button("Cancelar"):
                st.session_state.confirmar_exclusao = False
                st.rerun()

    # Exibe o histórico.
    for mensagem in st.session_state.historico:
        if mensagem["role"] == "user":
            with st.chat_message("user"):
                st.write(mensagem["content"])

        elif mensagem["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(mensagem["content"])

    pergunta = st.chat_input("Diga algo para o Gepeto...")

    if pergunta:
        if client is None:
            st.error(
                "API Key não configurada. Acesse o Streamlit Cloud, "
                "abra Settings > Secrets e configure GROQ_API_KEY."
            )

        else:
            st.session_state.historico.append({
                "role": "user",
                "content": pergunta
            })

            with st.chat_message("user"):
                st.write(pergunta)

            try:
                with st.chat_message("assistant", avatar="🤖"):
                    with st.spinner("Gepetto está pensando..."):
                        resposta = client.chat.completions.create(
                            model="openai/gpt-oss-20b",
                            messages=st.session_state.historico,
                            temperature=0.7,
                            max_tokens=2048
                        )

                        texto = (
                            resposta.choices[0].message.content
                            or "Não consegui gerar uma resposta."
                        )

                        st.write(texto)

                st.session_state.historico.append({
                    "role": "assistant",
                    "content": texto
                })

                dados_atuais = carregar_dados_usuario(
                    st.session_state.nome_arquivo
                ) or {}

                salvar_dados_usuario(
                    st.session_state.nome_arquivo,
                    dados_atuais.get("senha", ""),
                    st.session_state.historico,
                    token_hash=dados_atuais.get("token_hash", "")
                )

            except Exception as erro:
                if (
                    st.session_state.historico
                    and st.session_state.historico[-1]["role"] == "user"
                    and st.session_state.historico[-1]["content"] == pergunta
                ):
                    st.session_state.historico.pop()

                st.error(f"Erro ao falar com o Gepetto: {erro}")
