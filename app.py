import os
import re
import json
import time
import hashlib
import hmac
import streamlit as st
from groq import Groq

# ==================================================
# CONFIGURAÇÃO DO SITE
# ==================================================
st.set_page_config(
    page_title="Gepeto AI",
    page_icon="🤖",
    layout="centered"
)

# ==================================================
# API DA GROQ
# Configure GROQ_API_KEY em Settings > Secrets
# do Streamlit Cloud. Não coloque a chave no GitHub.
# ==================================================
@st.cache_resource
def get_groq_client(api_key):
    return Groq(api_key=api_key)


def obter_cliente():
    try:
        chave = st.secrets["GROQ_API_KEY"]
        if not chave or not str(chave).strip():
            return None
        return get_groq_client(str(chave).strip())
    except Exception:
        return None


client = obter_cliente()

# ==================================================
# ARMAZENAMENTO LOCAL
# ATENÇÃO: arquivos locais no Streamlit Cloud não
# garantem persistência permanente entre reinícios.
# ==================================================
PASTA_DADOS = "dados_usuarios"
os.makedirs(PASTA_DADOS, exist_ok=True)

# ==================================================
# INSTRUÇÕES DO GEPETTO
# ==================================================
INSTRUCOES_SISTEMA = {
    "role": "system",
    "content": (
        "Você é o GEPETTO, uma inteligência artificial "
        "acolhedora e ajudadora de pessoas. "
        "Responda sempre em português do Brasil. "
        "Seja amigável, prestativo e forneça informações "
        "precisas. Quando a resposta for longa, RESUMA."
    )
}

# ==================================================
# FUNÇÕES DE USUÁRIO
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
    # Compatibilidade com contas antigas que guardavam
    # a senha em texto puro.
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


def carregar_dados_usuario(nome_arquivo):
    if not os.path.exists(nome_arquivo):
        return None

    try:
        with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return None


def salvar_dados_usuario(nome_arquivo, senha_salva, historico):
    dados = {
        "senha": senha_salva,
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
    st.session_state.confirmar_exclusao = False

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

        apelido_input = st.text_input("Digite seu apelido:").strip()
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
                        # Atualiza contas antigas para senha com hash.
                        senha_salva = dados.get("senha", "")
                        if ":" not in senha_salva:
                            dados["senha"] = gerar_hash_senha(senha_input)
                            salvar_dados_usuario(
                                arquivo,
                                dados["senha"],
                                dados.get("historico", criar_historico())
                            )

                        historico = dados.get(
                            "historico",
                            criar_historico()
                        )

                        if not historico:
                            historico = criar_historico()

                        st.session_state.historico = historico
                        st.session_state.nome_arquivo = arquivo
                        st.session_state.apelido = apelido_input
                        st.session_state.autenticado = True

                        st.success("Login realizado com sucesso!")
                        time.sleep(0.3)
                        st.rerun()

                    else:
                        st.error("Senha incorreta!")

                except Exception as erro:
                    st.error(f"Erro ao entrar: {erro}")

    elif conhece == "Não":

        apelido_input = st.text_input("Escolha um apelido:").strip()
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
                        senha_hash = gerar_hash_senha(senha_input)

                        salvar_dados_usuario(
                            arquivo,
                            senha_hash,
                            historico
                        )

                        st.session_state.historico = historico
                        st.session_state.nome_arquivo = arquivo
                        st.session_state.apelido = apelido_input
                        st.session_state.autenticado = True

                        st.success("Conta criada com sucesso!")
                        time.sleep(0.3)
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
            st.session_state.autenticado = False
            st.session_state.historico = []
            st.session_state.nome_arquivo = ""
            st.session_state.apelido = ""
            st.session_state.confirmar_exclusao = False
            st.rerun()

        st.write("---")

        if st.button(
            "🗑️ Deletar conta e histórico",
            use_container_width=True
        ):
            st.session_state.confirmar_exclusao = True

        if st.session_state.confirmar_exclusao:

            st.warning("Tem certeza? Essa ação não pode ser desfeita.")

            if st.button("Confirmar exclusão"):
                arquivo = st.session_state.nome_arquivo

                if os.path.exists(arquivo):
                    os.remove(arquivo)

                st.session_state.autenticado = False
                st.session_state.historico = []
                st.session_state.nome_arquivo = ""
                st.session_state.apelido = ""
                st.session_state.confirmar_exclusao = False
                st.rerun()

            if st.button("Cancelar"):
                st.session_state.confirmar_exclusao = False
                st.rerun()

    # Mostra o histórico
    for mensagem in st.session_state.historico:
        if mensagem["role"] == "user":
            with st.chat_message("user"):
                st.write(mensagem["content"])

        elif mensagem["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(mensagem["content"])

    # Entrada de mensagens
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
                # Retira a pergunta que falhou da sessão.
                if (
                    st.session_state.historico
                    and st.session_state.historico[-1]["role"] == "user"
                    and st.session_state.historico[-1]["content"] == pergunta
                ):
                    st.session_state.historico.pop()

                st.error(f"Erro ao falar com o Gepetto: {erro}")
