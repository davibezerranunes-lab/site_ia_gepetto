
import os
import re
import time
import json
import streamlit as st
from groq import Groq

# ==================================================
# COLOQUE SUA API KEY DA GROQ AQUI
# ==================================================
GROQ_API_KEY = "SUA_CHAVE_AQUI"

# ==================================================
# CONFIGURAÇÃO DO SITE
# ==================================================
st.set_page_config(
    page_title="Gepeto AI",
    page_icon="🤖",
    layout="centered"
)

# ==================================================
# CLIENTE GROQ
# ==================================================
@st.cache_resource
def get_groq_client():
    if (
        not GROQ_API_KEY
        or GROQ_API_KEY == "COLE_SUA_API_KEY_AQUI"
    ):
        return None

    return Groq(api_key=GROQ_API_KEY)


try:
    client = get_groq_client()
except Exception:
    client = None


# ==================================================
# CONFIGURAÇÕES DO GEPETTO
# ==================================================
INSTRUCOES_SISTEMA = {
    "role": "system",
    "content": (
        "Você é o GEPETTO, uma inteligência artificial "
        "acolhedora e ajudadora de pessoas. "
        "Responda sempre em português do Brasil. "
        "Seja amigável, prestativo e forneça informações "
        "precisas. Quando for falar coisas que vão levar "
        "muitas linhas, RESUMA."
    )
}

PASTA_DADOS = "dados_usuarios"
os.makedirs(PASTA_DADOS, exist_ok=True)


# ==================================================
# FUNÇÕES DE USUÁRIO E HISTÓRICO
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


def carregar_dados_usuario(nome_arquivo):
    if not os.path.exists(nome_arquivo):
        return None

    try:
        with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return None


def salvar_dados_usuario(nome_arquivo, senha, historico):
    dados = {
        "senha": senha,
        "historico": historico
    }

    temporario = nome_arquivo + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    os.replace(temporario, nome_arquivo)


def criar_historico():
    return [INSTRUCOES_SISTEMA.copy()]


# ==================================================
# ESTADO DA SESSÃO
# ==================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.historico = []
    st.session_state.nome_arquivo = ""
    st.session_state.apelido = ""


# ==================================================
# TÍTULO
# ==================================================
st.title("🤖 GEPETTO - Assistente Virtual")
st.write("---")


# ==================================================
# TELA DE LOGIN E CADASTRO
# ==================================================
if not st.session_state.autenticado:

    conhece = st.radio(
        "Você já me conhece?",
        ("Selecione uma opção", "Sim", "Não")
    )

    # ---------------- LOGIN ----------------
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
                            "Conta não encontrada. "
                            "Confira o apelido ou crie uma conta."
                        )

                    elif dados.get("senha") != senha_input:
                        st.error("Senha incorreta!")

                    else:
                        st.session_state.historico = dados.get(
                            "historico",
                            criar_historico()
                        )

                        if not st.session_state.historico:
                            st.session_state.historico = criar_historico()

                        st.session_state.nome_arquivo = arquivo
                        st.session_state.apelido = apelido_input
                        st.session_state.autenticado = True

                        st.success("Login realizado com sucesso!")
                        time.sleep(0.5)
                        st.rerun()

                except Exception as erro:
                    st.error(f"Erro ao entrar: {erro}")

    # ---------------- CADASTRO ----------------
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
                st.warning("Use uma senha com pelo menos 4 caracteres.")

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

                        salvar_dados_usuario(
                            arquivo,
                            senha_input,
                            historico
                        )

                        st.session_state.historico = historico
                        st.session_state.nome_arquivo = arquivo
                        st.session_state.apelido = apelido_input
                        st.session_state.autenticado = True

                        st.success("Conta criada com sucesso!")
                        time.sleep(0.5)
                        st.rerun()

                except Exception as erro:
                    st.error(f"Erro ao criar conta: {erro}")


# ==================================================
# TELA DO CHAT
# ==================================================
else:

    st.subheader(
        f"Conversando com {st.session_state.apelido}"
    )

    # ---------------- BARRA LATERAL ----------------
    with st.sidebar:

        st.write(
            f"Usuário: **{st.session_state.apelido}**"
        )

        if st.button("Sair da Conta", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.historico = []
            st.session_state.nome_arquivo = ""
            st.session_state.apelido = ""
            st.rerun()

        st.write("---")

        if st.button(
            "🗑️ DELETAR CONTA E HISTÓRICO",
            use_container_width=True
        ):
            st.session_state.confirmar_exclusao = True

        if st.session_state.get("confirmar_exclusao", False):

            st.warning(
                "Tem certeza? Essa ação não pode ser desfeita."
            )

            if st.button("CONFIRMAR EXCLUSÃO"):
                arquivo = st.session_state.nome_arquivo

                if os.path.exists(arquivo):
                    os.remove(arquivo)

                st.session_state.autenticado = False
                st.session_state.historico = []
                st.session_state.nome_arquivo = ""
                st.session_state.apelido = ""
                st.session_state.confirmar_exclusao = False
                st.rerun()

            if st.button("Cancelar exclusão"):
                st.session_state.confirmar_exclusao = False
                st.rerun()

    # ---------------- HISTÓRICO ----------------
    for mensagem in st.session_state.historico:

        if mensagem["role"] == "user":
            with st.chat_message("user"):
                st.write(mensagem["content"])

        elif mensagem["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(mensagem["content"])

    # ---------------- ENTRADA DO CHAT ----------------
    pergunta = st.chat_input("Diga algo para o Gepeto...")

    if pergunta:

        if client is None:
            st.error(
                "API Key não configurada. "
                "Coloque sua chave válida da Groq na variável "
                "GROQ_API_KEY no começo do código."
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

                        texto = resposta.choices[0].message.content

                        if not texto:
                            texto = "Não consegui gerar uma resposta."

                        st.write(texto)

                st.session_state.historico.append({
                    "role": "assistant",
                    "content": texto
                })

                dados_atuais = carregar_dados_usuario(
                    st.session_state.nome_arquivo
                )

                senha_atual = (
                    dados_atuais.get("senha", "")
                    if dados_atuais
                    else ""
                )

                salvar_dados_usuario(
                    st.session_state.nome_arquivo,
                    senha_atual,
                    st.session_state.historico
                )

            except Exception as erro:

                # Remove a pergunta que falhou do histórico salvo
                if (
                    st.session_state.historico
                    and st.session_state.historico[-1]["role"] == "user"
                    and st.session_state.historico[-1]["content"] == pergunta
                ):
                    st.session_state.historico.pop()

                st.error(
                    f"Erro ao falar com o Gepetto: {erro}"
                )
