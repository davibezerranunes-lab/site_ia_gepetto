
import streamlit as st
import json
import os
import hashlib
import secrets
import uuid
from datetime import datetime
from groq import Groq
from streamlit_cookies_manager import EncryptedCookieManager

# ==================================================
# CONFIGURAÇÃO
# ==================================================

st.set_page_config(
    page_title="Gepetto AI",
    page_icon="🤖",
    layout="centered"
)

PASTA_DADOS = "dados_usuarios"
COOKIE_NOME = "gepetto_token"
MODELO = "openai/gpt-oss-20b"

os.makedirs(PASTA_DADOS, exist_ok=True)

# ==================================================
# COOKIES CRIPTOGRAFADOS
# Configure GROQ_API_KEY e COOKIES_PASSWORD
# em Settings > Secrets no Streamlit Cloud.
# ==================================================

try:
    cookies = EncryptedCookieManager(
        prefix="gepetto-ai/",
        password=st.secrets["COOKIES_PASSWORD"]
    )
except Exception:
    st.error(
        "Configure COOKIES_PASSWORD nos Secrets "
        "do Streamlit Cloud."
    )
    st.stop()

if not cookies.ready():
    st.info("Carregando sessão...")
    st.stop()

# ==================================================
# API GROQ
# ==================================================

try:
    cliente_groq = Groq(
        api_key=st.secrets["GROQ_API_KEY"]
    )
except Exception:
    st.error(
        "Configure GROQ_API_KEY nos Secrets "
        "do Streamlit Cloud."
    )
    st.stop()

# ==================================================
# FUNÇÕES DE USUÁRIOS
# ==================================================

def caminho_usuario(usuario):
    nome_seguro = hashlib.sha256(
        usuario.lower().encode("utf-8")
    ).hexdigest()

    return os.path.join(
        PASTA_DADOS,
        nome_seguro + ".json"
    )


def hash_senha(senha, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    resultado = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()

    return salt, resultado


def criar_hash_token(token):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def carregar_dados(usuario):
    caminho = caminho_usuario(usuario)

    if not os.path.exists(caminho):
        return None

    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (json.JSONDecodeError, OSError):
        return None

    # Compatibilidade com contas antigas que tinham
    # apenas um histórico de conversa.
    if "chats" not in dados:
        historico_antigo = dados.pop("historico", [])

        dados["chats"] = [{
            "id": str(uuid.uuid4()),
            "titulo": "Conversa antiga",
            "criado": datetime.now().isoformat(),
            "historico": historico_antigo
        }]

    if not dados["chats"]:
        dados["chats"] = [{
            "id": str(uuid.uuid4()),
            "titulo": "Novo chat",
            "criado": datetime.now().isoformat(),
            "historico": []
        }]

    return dados


def salvar_dados(usuario, dados):
    caminho = caminho_usuario(usuario)
    temporario = caminho + ".tmp"

    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporario, caminho)


def criar_conta(usuario, senha):
    usuario = usuario.strip().lower()

    if not usuario or not senha:
        return False, "Preencha o usuário e a senha."

    if len(usuario) < 3:
        return False, "O usuário precisa ter pelo menos 3 caracteres."

    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."

    if os.path.exists(caminho_usuario(usuario)):
        return False, "Esse usuário já existe."

    salt, senha_hash = hash_senha(senha)

    dados = {
        "senha_salt": salt,
        "senha_hash": senha_hash,
        "token_hash": "",
        "chats": [{
            "id": str(uuid.uuid4()),
            "titulo": "Novo chat",
            "criado": datetime.now().isoformat(),
            "historico": []
        }]
    }

    salvar_dados(usuario, dados)
    return True, "Conta criada com sucesso!"


def verificar_senha(usuario, senha):
    dados = carregar_dados(usuario)

    if not dados:
        return False

    salt = dados.get("senha_salt")
    senha_salva = dados.get("senha_hash")

    if salt and senha_salva:
        _, tentativa = hash_senha(senha, salt)
        return secrets.compare_digest(
            tentativa,
            senha_salva
        )

    # Compatibilidade com contas de versões anteriores
    salt_antigo = dados.get("salt")
    hash_antigo = dados.get("senha")

    if salt_antigo and hash_antigo:
        _, tentativa = hash_senha(senha, salt_antigo)
        return secrets.compare_digest(
            tentativa,
            hash_antigo
        )

    return False


def criar_sessao(usuario):
    dados = carregar_dados(usuario)

    if not dados:
        return

    token = secrets.token_urlsafe(32)
    dados["token_hash"] = criar_hash_token(token)
    salvar_dados(usuario, dados)

    cookies[COOKIE_NOME] = usuario + "|" + token
    cookies.save()

    st.session_state.usuario = usuario
    st.session_state.autenticado = True
    st.session_state.chat_id = dados["chats"][0]["id"]


def recuperar_sessao():
    valor = cookies.get(COOKIE_NOME)

    if not valor or "|" not in valor:
        return False

    usuario, token = valor.split("|", 1)
    dados = carregar_dados(usuario)

    if not dados:
        return False

    token_salvo = dados.get("token_hash", "")
    token_atual = criar_hash_token(token)

    if not token_salvo or not secrets.compare_digest(
        token_salvo,
        token_atual
    ):
        return False

    st.session_state.usuario = usuario
    st.session_state.autenticado = True

    if "chat_id" not in st.session_state:
        st.session_state.chat_id = dados["chats"][0]["id"]

    return True


def encerrar_sessao():
    usuario = st.session_state.get("usuario")

    if usuario:
        dados = carregar_dados(usuario)

        if dados:
            dados["token_hash"] = ""
            salvar_dados(usuario, dados)

    cookies[COOKIE_NOME] = ""
    cookies.save()

    for chave in list(st.session_state.keys()):
        del st.session_state[chave]

    st.rerun()


# ==================================================
# FUNÇÕES DE CHAT
# ==================================================

def chat_atual(dados):
    chat_id = st.session_state.get("chat_id")

    for chat in dados["chats"]:
        if chat["id"] == chat_id:
            return chat

    dados["chats"].insert(0, {
        "id": str(uuid.uuid4()),
        "titulo": "Novo chat",
        "criado": datetime.now().isoformat(),
        "historico": []
    })

    st.session_state.chat_id = dados["chats"][0]["id"]
    return dados["chats"][0]


def criar_chat(usuario):
    dados = carregar_dados(usuario)

    novo_chat = {
        "id": str(uuid.uuid4()),
        "titulo": "Novo chat",
        "criado": datetime.now().isoformat(),
        "historico": []
    }

    dados["chats"].insert(0, novo_chat)
    salvar_dados(usuario, dados)

    st.session_state.chat_id = novo_chat["id"]
    st.rerun()


def excluir_chat(usuario, chat_id):
    dados = carregar_dados(usuario)

    dados["chats"] = [
        chat for chat in dados["chats"]
        if chat["id"] != chat_id
    ]

    if not dados["chats"]:
        dados["chats"].append({
            "id": str(uuid.uuid4()),
            "titulo": "Novo chat",
            "criado": datetime.now().isoformat(),
            "historico": []
        })

    salvar_dados(usuario, dados)
    st.session_state.chat_id = dados["chats"][0]["id"]
    st.rerun()


def atualizar_titulo(chat, mensagem):
    if chat["titulo"] == "Novo chat":
        titulo = mensagem.strip().replace("\n", " ")

        if len(titulo) > 30:
            titulo = titulo[:27] + "..."

        if titulo:
            chat["titulo"] = titulo


# ==================================================
# IDENTIDADE VISUAL
# ==================================================

st.markdown(
    """
    <style>
    .gepetto-assinatura {
        text-align: center;
        color: #888888;
        font-size: 12px;
        margin-top: -14px;
        margin-bottom: 20px;
        letter-spacing: 0.2px;
    }

    .gepetto-rodape {
        text-align: center;
        color: #888888;
        font-size: 11px;
        margin-top: 24px;
        padding: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def mostrar_cabecalho():
    st.title("🤖 Gepetto AI")

    st.markdown(
        """
        <div class="gepetto-assinatura">
            Uma inteligência artificial da Família Bezerra
        </div>
        """,
        unsafe_allow_html=True
    )


# ==================================================
# LOGIN AUTOMÁTICO
# ==================================================

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    recuperar_sessao()


# ==================================================
# TELA DE LOGIN E CADASTRO
# ==================================================

if not st.session_state.autenticado:
    mostrar_cabecalho()

    aba_login, aba_cadastro = st.tabs([
        "Entrar",
        "Criar conta"
    ])

    with aba_login:
        st.subheader("Entrar na sua conta")

        usuario_login = st.text_input(
            "Usuário",
            key="usuario_login"
        )

        senha_login = st.text_input(
            "Senha",
            type="password",
            key="senha_login"
        )

        if st.button("Entrar", use_container_width=True):
            usuario = usuario_login.strip().lower()

            if verificar_senha(usuario, senha_login):
                criar_sessao(usuario)
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with aba_cadastro:
        st.subheader("Criar sua conta")

        usuario_novo = st.text_input(
            "Escolha um usuário",
            key="usuario_novo"
        )

        senha_nova = st.text_input(
            "Escolha uma senha",
            type="password",
            key="senha_nova"
        )

        confirmar_senha = st.text_input(
            "Confirme a senha",
            type="password",
            key="confirmar_senha"
        )

        if st.button("Cadastrar", use_container_width=True):
            if senha_nova != confirmar_senha:
                st.error("As senhas não são iguais.")
            else:
                sucesso, mensagem = criar_conta(
                    usuario_novo,
                    senha_nova
                )

                if sucesso:
                    st.success(mensagem)
                    st.info("Agora entre na sua conta pela aba Entrar.")
                else:
                    st.error(mensagem)

    st.markdown(
        """
        <div class="gepetto-rodape">
            Gepetto AI · Família Bezerra
        </div>
        """,
        unsafe_allow_html=True
    )

    st.stop()


# ==================================================
# INTERFACE PRINCIPAL
# ==================================================

usuario = st.session_state.usuario
dados = carregar_dados(usuario)

if not dados:
    encerrar_sessao()

chat = chat_atual(dados)

with st.sidebar:
    st.title("💬 Conversas")

    st.caption("Usuário: " + usuario)

    if st.button("➕ Novo chat", use_container_width=True):
        criar_chat(usuario)

    st.divider()

    # Lista de conversas
    for conversa in dados["chats"]:
        selecionado = (
            conversa["id"] == st.session_state.chat_id
        )

        texto_botao = (
            "● " if selecionado else ""
        ) + conversa["titulo"]

        if st.button(
            texto_botao,
            key="chat_" + conversa["id"],
            use_container_width=True
        ):
            st.session_state.chat_id = conversa["id"]
            st.rerun()

    st.divider()

    if st.button("🗑️ Excluir conversa atual", use_container_width=True):
        excluir_chat(usuario, st.session_state.chat_id)

    if st.button("🚪 Sair da conta", use_container_width=True):
        encerrar_sessao()


# Recarrega a conversa selecionada
dados = carregar_dados(usuario)
chat = chat_atual(dados)

mostrar_cabecalho()

# Mostra o título da conversa atual
st.caption("Conversa: " + chat["titulo"])

# Exibe o histórico
for mensagem in chat["historico"]:
    papel = mensagem.get("role", "assistant")

    if papel not in ("user", "assistant"):
        continue

    with st.chat_message(papel):
        st.markdown(mensagem.get("content", ""))


# ==================================================
# ENVIO DE MENSAGENS
# ==================================================

pergunta = st.chat_input("Converse com o Gepetto...")

if pergunta:
    atualizar_titulo(chat, pergunta)

    chat["historico"].append({
        "role": "user",
        "content": pergunta
    })

    salvar_dados(usuario, dados)

    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        area_resposta = st.empty()

        try:
            mensagens_api = [
                {
                    "role": "system",
                    "content": (
                        "Você é o Gepetto AI, uma inteligência artificial "
                        "da Família Bezerra. Seja útil, educado, natural "
                        "e claro. Responda em português quando o usuário "
                        "falar português. Adapte o tamanho da resposta "
                        "ao pedido do usuário."
                    )
                }
            ]

            for item in chat["historico"]:
                papel = item.get("role")
                conteudo = item.get("content", "")

                if papel in ("user", "assistant"):
                    mensagens_api.append({
                        "role": papel,
                        "content": conteudo
                    })

            resposta = cliente_groq.chat.completions.create(
                model=MODELO,
                messages=mensagens_api,
                temperature=0.7,
                max_tokens=2048
            )

            texto_resposta = (
                resposta.choices[0].message.content or
                "Não consegui gerar uma resposta."
            )

            area_resposta.markdown(texto_resposta)

            chat["historico"].append({
                "role": "assistant",
                "content": texto_resposta
            })

            salvar_dados(usuario, dados)

        except Exception as erro:
            area_resposta.error(
                "Não consegui responder. Verifique a conexão "
                "e a configuração da API Groq."
            )

            # Registra o erro no log do Streamlit, sem
            # exibir detalhes técnicos ou credenciais ao usuário.
            print("Erro na API Groq:", str(erro))


# ==================================================
# RODAPÉ DISCRETO
# ==================================================

st.markdown(
    """
    <div class="gepetto-rodape">
        Gepetto AI · Uma criação da Família Bezerra
    </div>
    """,
    unsafe_allow_html=True
)
