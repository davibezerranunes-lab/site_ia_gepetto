
import os
import re
import json
import hmac
import base64
import hashlib
import secrets
from pathlib import Path
from datetime import datetime
from html import escape
from io import BytesIO

import streamlit as st
from groq import Groq
from streamlit_cookies_manager import EncryptedCookieManager


# =====================================================
# CONFIGURAÇÃO
# =====================================================

st.set_page_config(
    page_title="Gepetto AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

PASTA = Path("dados_usuarios")
PASTA.mkdir(exist_ok=True)
ARQUIVO = PASTA / "usuarios.json"

cookies = EncryptedCookieManager(
    prefix="gepetto_ai/",
    password=os.environ.get(
        "COOKIES_PASSWORD",
        "troque-esta-senha-por-uma-chave-secreta",
    ),
)

if not cookies.ready():
    st.stop()


# =====================================================
# DESIGN
# =====================================================

st.markdown("""
<style>
.stApp {
    background: #080f1d;
    color: #f4f7ff;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0d192c,#0a1425);
    border-right: 1px solid #203451;
}
[data-testid="stHeader"] {
    background: #080f1d;
}
h1,h2,h3,h4,p,label {
    color: #f4f7ff;
}
.gepetto-logo {
    font-size: 27px;
    font-weight: 800;
    color: white;
}
.gepetto-sub {
    font-size: 14px;
    color: #a8bddf;
    line-height: 1.5;
}
.linha {
    border: 0;
    border-top: 1px solid #203451;
    margin: 20px 0;
}
.titulo-chat {
    font-size: 26px;
    font-weight: 750;
    padding: 8px 0 18px;
    border-bottom: 1px solid #203451;
    margin-bottom: 22px;
}
.mensagem-usuario {
    background: linear-gradient(135deg,#1677ff,#0861e8);
    color: white;
    padding: 13px 17px;
    border-radius: 15px 15px 5px 15px;
    margin: 12px 0 22px auto;
    max-width: 85%;
    width: fit-content;
    overflow-wrap: anywhere;
    line-height: 1.65;
}
.mensagem-ia {
    background: linear-gradient(135deg,#172842,#142239);
    border: 1px solid #203451;
    color: #e3edff;
    padding: 16px 18px;
    border-radius: 17px 17px 17px 5px;
    margin: 8px 0 24px;
    max-width: 95%;
    overflow-wrap: anywhere;
    line-height: 1.75;
}
.mensagem-ia p,.mensagem-ia li {
    color: #e3edff;
}
.stButton > button {
    border-radius: 11px;
    border: 1px solid #29466e;
    background: #14243d;
    color: #e8f0ff;
    min-height: 40px;
}
.stButton > button:hover {
    border-color: #1677ff;
    background: #1b3153;
    color: white;
}
.stButton > button[kind="primary"] {
    background: #1677ff;
    border-color: #1677ff;
    color: white;
}
[data-testid="stChatInput"],
[data-testid="stTextInput"] input {
    background: #111f34;
    color: white;
}
.rodape {
    color: #91a9d0;
    font-size: 13px;
    line-height: 1.6;
}
.vazio {
    text-align: center;
    padding: 45px 10px;
    color: #a8bddf;
}
@media(max-width:700px) {
    .titulo-chat {font-size:22px;}
    .mensagem-usuario {max-width:95%;}
    .mensagem-ia {max-width:100%;padding:13px;}
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# USUÁRIOS E SENHAS
# =====================================================

def carregar_usuarios():
    if not ARQUIVO.exists():
        return {}
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def salvar_usuarios(usuarios):
    temporario = ARQUIVO.with_suffix(".tmp")
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=2)
    temporario.replace(ARQUIVO)


def gerar_hash(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    resultado = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(salt),
        200_000,
    )
    return salt, resultado.hex()


def verificar_senha(senha, salt, hash_salvo):
    _, calculado = gerar_hash(senha, salt)
    return hmac.compare_digest(calculado, hash_salvo)


def criar_conta(usuario, senha):
    usuarios = carregar_usuarios()
    usuario = usuario.strip().lower()

    if len(usuario) < 3:
        return False, "O usuário precisa ter pelo menos 3 caracteres."

    if not re.fullmatch(r"[a-zA-Z0-9_.-]+", usuario):
        return False, "Use letras, números, ponto, hífen ou underline."

    if usuario in usuarios:
        return False, "Esse usuário já existe."

    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."

    salt, hash_senha = gerar_hash(senha)

    usuarios[usuario] = {
        "senha_salt": salt,
        "senha_hash": hash_senha,
        "chats": {"Nova conversa": []},
        "chat_atual": "Nova conversa",
    }
    salvar_usuarios(usuarios)
    return True, "Conta criada! Agora entre nela."


def entrar(usuario, senha):
    conta = carregar_usuarios().get(usuario.strip().lower())
    if not conta:
        return False
    return verificar_senha(
        senha,
        conta.get("senha_salt", ""),
        conta.get("senha_hash", ""),
    )


def salvar_conta(usuario, conta):
    usuarios = carregar_usuarios()
    if usuario in usuarios:
        usuarios[usuario] = conta
        salvar_usuarios(usuarios)


# =====================================================
# CONVERSAS
# =====================================================

def gerar_nome_chat(texto):
    texto = re.sub(r"\s+", " ", texto).strip()
    palavras = texto.split()

    if not palavras:
        return "Nova conversa"

    nome = " ".join(palavras[:7])
    if len(palavras) > 7:
        nome += "..."

    if len(nome) > 48:
        nome = nome[:45].rstrip() + "..."

    return nome


def nome_disponivel(chats, base):
    nome = base
    numero = 2
    while nome in chats:
        nome = f"{base} ({numero})"
        numero += 1
    return nome


def novo_chat(conta):
    nome = nome_disponivel(conta["chats"], "Nova conversa")
    conta["chats"][nome] = []
    conta["chat_atual"] = nome


def renomear_primeira_mensagem(conta, nome_antigo, texto):
    chats = conta["chats"]

    if chats.get(nome_antigo):
        return nome_antigo

    nome_novo = nome_disponivel(chats, gerar_nome_chat(texto))
    chats[nome_novo] = chats.pop(nome_antigo)
    conta["chat_atual"] = nome_novo
    return nome_novo


# =====================================================
# AUTENTICAÇÃO
# =====================================================

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = cookies.get("usuario", "")

if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = False

if "confirmar_exclusao_conta" not in st.session_state:
    st.session_state.confirmar_exclusao_conta = False

if not st.session_state.usuario_logado:
    _, centro, _ = st.columns([1, 1.4, 1])

    with centro:
        st.markdown("""
        <div style="text-align:center;padding:35px 0 20px">
            <div style="font-size:58px">🤖</div>
            <div class="gepetto-logo" style="font-size:36px">
                Gepetto AI
            </div>
            <div class="gepetto-sub">
                Uma inteligência artificial da Família Bezerra
            </div>
        </div>
        """, unsafe_allow_html=True)

        escolha = st.radio(
            "Acesso",
            ["Entrar", "Criar conta"],
            horizontal=True,
        )

        with st.form("autenticacao"):
            usuario = st.text_input("Nome de usuário")
            senha = st.text_input("Senha", type="password")
            confirmar = ""

            if escolha == "Criar conta":
                confirmar = st.text_input(
                    "Confirmar senha",
                    type="password",
                )

            enviado = st.form_submit_button(
                "Entrar" if escolha == "Entrar" else "Criar minha conta",
                type="primary",
                use_container_width=True,
            )

        if enviado:
            usuario = usuario.strip().lower()

            if not usuario or not senha:
                st.error("Preencha o usuário e a senha.")

            elif escolha == "Criar conta":
                if senha != confirmar:
                    st.error("As senhas não são iguais.")
                else:
                    sucesso, mensagem = criar_conta(usuario, senha)
                    if sucesso:
                        st.success(mensagem)
                    else:
                        st.error(mensagem)

            elif entrar(usuario, senha):
                st.session_state.usuario_logado = usuario
                cookies["usuario"] = usuario
                cookies.save()
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

        st.markdown(
            '<div class="rodape" style="text-align:center">'
            'Gepetto AI • Uma inteligência artificial da Família Bezerra'
            '</div>',
            unsafe_allow_html=True,
        )

    st.stop()


# =====================================================
# CARREGAR CONTA
# =====================================================

usuarios = carregar_usuarios()
usuario_atual = st.session_state.usuario_logado

if usuario_atual not in usuarios:
    st.session_state.usuario_logado = ""
    cookies["usuario"] = ""
    cookies.save()
    st.rerun()

conta = usuarios[usuario_atual]

if not isinstance(conta.get("chats"), dict):
    conta["chats"] = {}

if not conta["chats"]:
    novo_chat(conta)

if conta.get("chat_atual") not in conta["chats"]:
    conta["chat_atual"] = next(iter(conta["chats"]))

salvar_conta(usuario_atual, conta)


# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px">
        <div style="font-size:43px">🤖</div>
        <div>
            <div class="gepetto-logo">Gepetto AI</div>
            <div class="gepetto-sub">
                Uma inteligência artificial da Família Bezerra
            </div>
        </div>
    </div>
    <hr class="linha">
    """, unsafe_allow_html=True)

    st.markdown("### 💬 Conversas")
    st.caption(f"Conta: {usuario_atual}")

    if st.button("＋ Nova conversa", type="primary",
                 use_container_width=True):
        novo_chat(conta)
        salvar_conta(usuario_atual, conta)
        st.session_state.confirmar_exclusao = False
        st.rerun()

    nomes = list(conta["chats"].keys())
    atual = conta["chat_atual"]

    if atual in nomes:
        nomes.remove(atual)
        nomes.insert(0, atual)

    for i, nome in enumerate(nomes):
        col1, col2 = st.columns([5, 1])

        with col1:
            if st.button(
                ("🔵 " if nome == atual else "💬 ") + nome,
                key=f"chat_{i}_{nome}",
                use_container_width=True,
                type="primary" if nome == atual else "secondary",
            ):
                conta["chat_atual"] = nome
                salvar_conta(usuario_atual, conta)
                st.session_state.confirmar_exclusao = False
                st.rerun()

        with col2:
            if st.button("🗑️", key=f"lixeira_{i}_{nome}"):
                st.session_state.chat_para_excluir = nome
                st.session_state.confirmar_exclusao = True

    if st.session_state.confirmar_exclusao:
        nome = st.session_state.get("chat_para_excluir", "")

        if nome in conta["chats"]:
            st.warning(f"Excluir '{nome}'?")

            c1, c2 = st.columns(2)

            with c1:
                if st.button("Sim, excluir", type="primary"):
                    del conta["chats"][nome]

                    if conta["chat_atual"] == nome:
                        if conta["chats"]:
                            conta["chat_atual"] = next(iter(conta["chats"]))
                        else:
                            novo_chat(conta)

                    salvar_conta(usuario_atual, conta)
                    st.session_state.confirmar_exclusao = False
                    st.rerun()

            with c2:
                if st.button("Cancelar"):
                    st.session_state.confirmar_exclusao = False
                    st.rerun()

    st.markdown('<hr class="linha">', unsafe_allow_html=True)

    if st.button("↪️ Sair da conta", use_container_width=True):
        st.session_state.usuario_logado = ""
        cookies["usuario"] = ""
        cookies.save()
        st.rerun()

    if st.button("🗑️ Excluir minha conta", use_container_width=True):
        st.session_state.confirmar_exclusao_conta = True

    if st.session_state.confirmar_exclusao_conta:
        st.warning("Isso apagará sua conta e suas conversas.")

        if st.button("Confirmar exclusão da conta", type="primary"):
            usuarios = carregar_usuarios()
            usuarios.pop(usuario_atual, None)
            salvar_usuarios(usuarios)
            st.session_state.usuario_logado = ""
            st.session_state.confirmar_exclusao_conta = False
            cookies["usuario"] = ""
            cookies.save()
            st.rerun()

    st.markdown("""
    <hr class="linha">
    <div class="rodape">
        Gepetto AI • Uma inteligência artificial da Família Bezerra
    </div>
    """, unsafe_allow_html=True)


# =====================================================
# HISTÓRICO E IMAGENS
# =====================================================

nome_chat = conta["chat_atual"]
mensagens = conta["chats"][nome_chat]

st.markdown(
    f'<div class="titulo-chat">{escape(nome_chat)}</div>',
    unsafe_allow_html=True,
)

if not mensagens:
    st.markdown("""
    <div class="vazio">
        <div style="font-size:54px">🤖</div>
        <h2>Olá! Como posso ajudar?</h2>
        <p>Envie uma mensagem ou uma foto para começarmos!</p>
    </div>
    """, unsafe_allow_html=True)


def mostrar_mensagem(mensagem):
    papel = mensagem.get("role")
    texto = mensagem.get("content", "")

    if papel == "user":
        st.markdown(
            f'<div class="mensagem-usuario">{escape(texto)}</div>',
            unsafe_allow_html=True,
        )

        imagem = mensagem.get("image")
        if imagem:
            try:
                dados = base64.b64decode(imagem.split(",", 1)[1])
                st.image(dados, caption="Imagem enviada", width=350)
            except Exception:
                st.caption("Não foi possível exibir esta imagem.")

    elif papel == "assistant":
        with st.container():
            st.markdown("🤖")
            st.markdown(texto)


for mensagem in mensagens:
    mostrar_mensagem(mensagem)


# =====================================================
# UPLOAD DE FOTOS
# =====================================================

st.markdown("#### 📎 Adicionar uma foto")

foto = st.file_uploader(
    "Escolha uma imagem da galeria ou tire uma foto",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=False,
    help="Tamanho máximo recomendado: 8 MB.",
    key="upload_foto",
)

imagem_data_url = None

if foto is not None:
    bytes_foto = foto.getvalue()

    if len(bytes_foto) > 8 * 1024 * 1024:
        st.error("A imagem ultrapassa 8 MB. Escolha uma foto menor.")
    else:
        try:
            from PIL import Image

            imagem = Image.open(BytesIO(bytes_foto))
            imagem.verify()

            formato = imagem.format
            mime = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }.get(formato)

            if not mime:
                st.error("Formato de imagem não suportado.")
            else:
                imagem_data_url = (
                    f"data:{mime};base64,"
                    + base64.b64encode(bytes_foto).decode("utf-8")
                )
                st.image(bytes_foto, caption="Prévia da foto", width=300)

        except Exception:
            st.error("Esse arquivo não parece ser uma imagem válida.")
            imagem_data_url = None


# =====================================================
# ENVIO E RESPOSTA DA IA
# =====================================================

pergunta = st.chat_input(
    "Converse com o Gepetto..."
)

if pergunta is not None:
    pergunta = pergunta.strip()

    if not pergunta and not imagem_data_url:
        st.warning("Escreva uma mensagem ou selecione uma foto.")

    elif foto is not None and len(foto.getvalue()) > 8 * 1024 * 1024:
        st.error("Escolha uma imagem de até 8 MB.")

    else:
        if not pergunta:
            pergunta = "Descreva esta imagem e diga o que você consegue identificar."

        nome_antigo = conta["chat_atual"]

        if not conta["chats"][nome_antigo]:
            renomear_primeira_mensagem(conta, nome_antigo, pergunta)

        nome_chat = conta["chat_atual"]
        mensagens = conta["chats"][nome_chat]

        nova_mensagem = {
            "role": "user",
            "content": pergunta,
        }

        if imagem_data_url:
            nova_mensagem["image"] = imagem_data_url

        mensagens.append(nova_mensagem)
        salvar_conta(usuario_atual, conta)

        chave_api = st.secrets.get(
            "GROQ_API_KEY",
            os.environ.get("GROQ_API_KEY", ""),
        )

        if not chave_api:
            st.error("Configure GROQ_API_KEY nos Secrets do Streamlit.")

        else:
            try:
                cliente = Groq(api_key=chave_api)
                tem_imagem = any(
                    item.get("image")
                    for item in mensagens
                    if item.get("role") == "user"
                )

                historico_api = []

                for item in mensagens:
                    if item.get("role") not in ("user", "assistant"):
                        continue

                    if item["role"] == "assistant":
                        historico_api.append({
                            "role": "assistant",
                            "content": item["content"],
                        })
                        continue

                    imagem_item = item.get("image")

                    if imagem_item:
                        historico_api.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": item["content"],
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": imagem_item,
                                    },
                                },
                            ],
                        })
                    else:
                        historico_api.append({
                            "role": "user",
                            "content": item["content"],
                        })

                modelo = (
                    "qwen/qwen3.6-27b"
                    if tem_imagem
                    else "openai/gpt-oss-20b"
                )

                with st.spinner("O Gepetto está pensando..."):
                    resposta = cliente.chat.completions.create(
                        model=modelo,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "Você é o Gepetto AI, uma IA amigável, "
                                    "útil e direta. Responda em português "
                                    "quando o usuário escrever em português. "
                                    "Quando receber imagens, analise o que "
                                    "estiver visível e seja honesto sobre "
                                    "detalhes que não conseguir identificar."
                                ),
                            },
                            *historico_api,
                        ],
                        temperature=0.7,
                        max_completion_tokens=2048,
                    )

                    texto_resposta = (
                        resposta.choices[0].message.content
                        or "Não consegui gerar uma resposta."
                    )

                mensagens.append({
                    "role": "assistant",
                    "content": texto_resposta,
                })
                salvar_conta(usuario_atual, conta)

                # Limpa o campo de upload para a próxima mensagem.
                st.rerun()

            except Exception as erro:
                st.error(
                    "Não consegui obter a resposta. Confira sua chave Groq "
                    "e tente novamente."
                )
                st.caption(f"Detalhe técnico: {erro}")
