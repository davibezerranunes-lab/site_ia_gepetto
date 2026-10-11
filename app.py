
import hmac
import hashlib
import secrets

import streamlit as st
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg.errors import UniqueViolation

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

COOKIE_NOME = "gepetto_usuario"
ITERACOES_PBKDF2 = 200_000
MODELO = "openai/gpt-oss-20b"


# =========================
# CONEXÃO COM SUPABASE
# =========================

def conectar_db():
    return psycopg.connect(
        st.secrets["DATABASE_URL"],
        row_factory=dict_row,
        connect_timeout=15,
    )


# =========================
# COOKIES
# =========================

try:
    cookies = EncryptedCookieManager(
        prefix="gepetto/",
        password=st.secrets["COOKIES_PASSWORD"],
    )

    if not cookies.ready():
        st.stop()

except Exception:
    st.error(
        "Não foi possível inicializar os cookies. "
        "Confira COOKIES_PASSWORD e as dependências."
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
# VALIDAR E ORGANIZAR CHATS
# =========================

def normalizar_chats(chats):
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

    return chats_validos


# =========================
# CARREGAR E SALVAR CONTAS
# =========================

def carregar_dados(usuario):
    usuario = usuario.strip()

    if not usuario:
        return None

    with conectar_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT usuario, senha_salt, senha_hash,
                       chats, chat_atual
                FROM public.gepetto_usuarios
                WHERE LOWER(usuario) = LOWER(%s)
                LIMIT 1
                """,
                (usuario,),
            )
            dados = cursor.fetchone()

    if not dados:
        return None

    dados = dict(dados)
    dados["chats"] = normalizar_chats(dados.get("chats"))

    chat_atual = dados.get("chat_atual")

    if (
        not isinstance(chat_atual, str)
        or chat_atual not in dados["chats"]
    ):
        chat_atual = next(iter(dados["chats"]))

    dados["chat_atual"] = chat_atual

    return dados


def salvar_dados(usuario, dados):
    try:
        chats = normalizar_chats(dados.get("chats"))
        chat_atual = dados.get("chat_atual")

        if chat_atual not in chats:
            chat_atual = next(iter(chats))

        with conectar_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.gepetto_usuarios
                    SET chats = %s,
                        chat_atual = %s
                    WHERE LOWER(usuario) = LOWER(%s)
                    """,
                    (
                        Jsonb(chats),
                        chat_atual,
                        usuario.strip(),
                    ),
                )

                atualizado = cursor.rowcount > 0

        return atualizado

    except Exception:
        return False


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
        salt = str(dados["senha_salt"])
        hash_salvo = str(dados["senha_hash"])

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

    salt, senha_hash = gerar_senha(senha)

    try:
        with conectar_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO public.gepetto_usuarios
                        (usuario, senha_salt, senha_hash,
                         chats, chat_atual)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        usuario,
                        salt,
                        senha_hash,
                        Jsonb({"Conversa 1": []}),
                        "Conversa 1",
                    ),
                )

        return True, "Conta criada com sucesso!"

    except UniqueViolation:
        return False, "Esse usuário já existe."

    except Exception:
        return False, (
            "Não foi possível criar a conta no banco. "
            "Confira DATABASE_URL nos Secrets."
        )


# =========================
# SESSÃO E EXCLUSÃO
# =========================

def encerrar_sessao():
    cookies[COOKIE_NOME] = ""
    cookies.save()

    st.session_state.usuario = ""
    st.session_state.confirmar_exclusao = False


def excluir_conta(usuario):
    try:
        with conectar_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM public.gepetto_usuarios
                    WHERE LOWER(usuario) = LOWER(%s)
                    """,
                    (usuario.strip(),),
                )

        encerrar_sessao()
        st.rerun()

    except Exception:
        st.error("Não foi possível excluir a conta. Tente novamente.")


if "usuario" not in st.session_state:
    st.session_state.usuario = cookies.get(COOKIE_NOME, "")

if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = False


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

        with st.form("form_login"):
            login_usuario = st.text_input(
                "Usuário",
                max_chars=30,
            )

            login_senha = st.text_input(
                "Senha",
                type="password",
            )

            enviar_login = st.form_submit_button(
                "Entrar",
                use_container_width=True,
            )

        if enviar_login:
            usuario_digitado = login_usuario.strip()

            try:
                dados_login = carregar_dados(usuario_digitado)

                if dados_login and verificar_senha(
                    dados_login,
                    login_senha,
                ):
                    nome = dados_login["usuario"]

                    st.session_state.usuario = nome
                    cookies[COOKIE_NOME] = nome
                    cookies.save()
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

            except Exception:
                st.error(
                    "Não foi possível acessar o banco de dados. "
                    "Confira DATABASE_URL nos Secrets."
                )

    with aba_cadastro:
        st.subheader("Criar sua conta")

        with st.form("form_cadastro"):
            novo_usuario = st.text_input(
                "Escolha um usuário",
                max_chars=30,
            )

            nova_senha = st.text_input(
                "Escolha uma senha",
                type="password",
            )

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
                try:
                    sucesso, mensagem = criar_conta(
                        novo_usuario,
                        nova_senha,
                    )

                    if sucesso:
                        st.success(mensagem)
                        st.info("Agora entre na aba Entrar.")
                    else:
                        st.error(mensagem)

                except Exception:
                    st.error(
                        "Não foi possível conectar ao banco. "
                        "Confira DATABASE_URL nos Secrets."
                    )

    st.stop()


# =========================
# CARREGAR CONTA LOGADA
# =========================

usuario = st.session_state.usuario

try:
    dados = carregar_dados(usuario)
except Exception:
    st.error(
        "Não foi possível conectar ao banco de dados. "
        "Confira DATABASE_URL nos Secrets do Streamlit."
    )
    st.stop()

if dados is None:
    encerrar_sessao()
    st.warning(
        "A conta não foi encontrada no banco. "
        "Entre novamente."
    )
    st.rerun()

usuario = dados["usuario"]

if not salvar_dados(usuario, dados):
    st.warning("Não foi possível salvar as alterações no banco.")


# =========================
# BARRA LATERAL
# =========================

with st.sidebar:
    st.title("💬 Conversas")
    st.caption(f"Conta: {usuario}")

    nomes_chats = list(dados["chats"].keys())

    conversa_selecionada = st.selectbox(
        "Escolha uma conversa",
        nomes_chats,
        index=nomes_chats.index(dados["chat_atual"]),
    )

    if conversa_selecionada != dados["chat_atual"]:
        dados["chat_atual"] = conversa_selecionada

        if not salvar_dados(usuario, dados):
            st.error("Não foi possível salvar a conversa.")

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

        if salvar_dados(usuario, dados):
            st.rerun()
        else:
            st.error("Não foi possível criar a conversa.")

    st.divider()

    if st.button(
        "🚪 Sair da conta",
        use_container_width=True,
    ):
        encerrar_sessao()
        st.rerun()

    st.divider()

    if st.button(
        "🗑️ Excluir minha conta",
        use_container_width=True,
    ):
        st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        st.warning(
            "Isso apagará a conta e todas as conversas salvas. "
            "Essa ação não pode ser desfeita."
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
# HISTÓRICO
# =========================

st.subheader(dados["chat_atual"])

mensagens = dados["chats"][dados["chat_atual"]]

for mensagem in mensagens:
    with st.chat_message(mensagem["role"]):
        st.markdown(mensagem["content"])


# =========================
# ENVIAR MENSAGEM
# =========================

pergunta = st.chat_input("Converse com o Gepetto...")

if pergunta:
    mensagens.append({
        "role": "user",
        "content": pergunta,
    })

    if not salvar_dados(usuario, dados):
        st.error("Não foi possível salvar sua mensagem no banco.")

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
                st.error(
                    "A resposta foi gerada, mas não foi possível "
                    "salvá-la no histórico."
                )

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
