import os
import time
import json
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# Carrega as variáveis de ambiente
load_dotenv()

# Configuração da página Web
st.set_page_config(page_title="Gepeto AI", page_icon="🤖", layout="centered")

# Inicializa o cliente Groq
@st.cache_resource
def get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

client = get_groq_client()

# Função para criar o nome do arquivo baseado no apelido do usuário
def obter_nome_arquivo(apelido):
    nome_limpo = "".join(apelido.split()).lower()
    return f"historico_{nome_limpo}.json"

# Função para salvar a senha e a conversa no computador
def salvar_dados_usuario(nome_arquivo, senha, historico):
    dados = {
        "senha": senha,
        "historico": historico
    }
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# Função para carregar os dados existentes
def carregar_dados_usuario(nome_arquivo):
    if os.path.exists(nome_arquivo):
        with open(nome_arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

instrucoes_sistema = {
    "role": "system",
    "content": (
        "Você é o GEPETTO, uma inteligencia artificial acolhedora e ajudadora de pessoas. "
        "Responda sempre em Portugues do Brasil. "
        "Você deve ser amigável, prestativo e fornecer informações precisas. "
        "Quando for falar coisas que vao levar muitas linhas RESUMA."
    )
}

# Título do site
st.title("🤖 GEPETTO - Assistente Virtual")
st.write("---")

# --- ESTADO DA SESSÃO ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.historico = []
    st.session_state.nome_arquivo = ""
    st.session_state.apelido = ""

# --- TELA DE LOGIN / CADASTRO ---
if not st.session_state.autenticado:
    conhece = st.radio("Você já me conhece?", ("Selecione uma opção", "Sim", "Não"))
    
    if conhece == "Sim":
        apelido_input = st.text_input("Digite seu apelido:").strip()
        # Campo de senha mascarado (com asteriscos)
        senha_input = st.text_input("Digite sua senha:", type="password").strip()
        
        if st.button("Entrar"):
            if apelido_input and senha_input:
                arq = obter_nome_arquivo(apelido_input)
                dados_salvos = carregar_dados_usuario(arq)
                
                # Se o usuário existir e a senha estiver correta
                if dados_salvos and dados_salvos.get("senha") == senha_input:
                    st.session_state.historico = dados_salvos["historico"]
                    st.session_state.nome_arquivo = arq
                    st.session_state.apelido = apelido_input
                    st.session_state.autenticado = True
                    st.success("Login realizado com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
                elif dados_salvos and dados_salvos.get("senha") != senha_input:
                    st.error("Senha incorreta! Tente novamente.")
                else:
                    st.error(f"Apelido '{apelido_input}' não encontrado! Mude para 'Não' caso queira criá-lo.")
            else:
                st.warning("Por favor, preencha o apelido e a senha.")
                
    elif conhece == "Não":
        apelido_input = st.text_input("Escolha um apelido:").strip()
        # Pede para criar uma senha para a nova conta
        senha_input = st.text_input("Crie uma senha de acesso:", type="password").strip()
        
        if st.button("Criar Conta e Conversar"):
            if apelido_input and senha_input:
                arq = obter_nome_arquivo(apelido_input)
                
                # Impede criar por cima de um apelido que já existe
                if os.path.exists(arq):
                    st.error("Esse apelido já está em uso! Escolha outro ou faça Login.")
                else:
                    st.session_state.historico = [instrucoes_sistema]
                    st.session_state.nome_arquivo = arq
                    st.session_state.apelido = apelido_input
                    st.session_state.autenticado = True
                    
                    # Salva os dados estruturados com a senha nova
                    salvar_dados_usuario(arq, senha_input, st.session_state.historico)
                    st.success("Conta criada com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.warning("Por favor, preencha o apelido e crie uma senha.")

# --- TELA DO CHAT ---
else:
    st.subheader(f"Conversando com {st.session_state.apelido}")
    
    # Barra lateral
    with st.sidebar:
        st.write(f"Usuário: **{st.session_state.apelido}**")
        if st.button("Sair da Conta"):
            st.session_state.autenticado = False
            st.rerun()
            
        st.write("---")
        if st.button("🚨 DELETAR HISTÓRICO PERMANENTEMENTE"):
            if os.path.exists(st.session_state.nome_arquivo):
                os.remove(st.session_state.nome_arquivo)
                st.toast("Sua conta e memórias foram apagadas!")
                time.sleep(1)
            st.session_state.autenticado = False
            st.rerun()

    # Exibe as mensagens antigas
    for msg in st.session_state.historico:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(msg["content"])

    # Entrada de mensagens
    if pergunta := st.chat_input("Diga algo para o Gepeto..."):
        with st.chat_message("user"):
            st.write(pergunta)
            
        st.session_state.historico.append({"role": "user", "content": pergunta})
        
        try:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Gepeto está pensando..."):
                    resposta = client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=st.session_state.historico
                    )
                    texto = resposta.choices[0].message.content
                    st.write(texto)
            
            st.session_state.historico.append({"role": "assistant", "content": texto})
            
            # Precisamos recuperar a senha atual para salvá-la de volta junto com o novo histórico
            dados_atuais = carregar_dados_usuario(st.session_state.nome_arquivo)
            senha_atual = dados_atuais["senha"] if dados_atuais else ""
            
            salvar_dados_usuario(st.session_state.nome_arquivo, senha_atual, st.session_state.historico)
            
        except Exception as e:
            st.error(f"Erro ao falar com o Gepeto: {e}")
