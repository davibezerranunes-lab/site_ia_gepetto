# Gepetto AI — versão multipáginas

## Estrutura

- `app.py`: entrada principal do Streamlit; monta a navegação com `st.navigation` e `st.Page`.
- `gepetto_core.py`: funções compartilhadas, autenticação, sessão, uploads, persistência e painel administrativo.
- `views/login.py`: login, cadastro, recuperação de senha e fluxo Google.
- `views/chat.py`: conversas, histórico, anexos, streaming e exportação.
- `views/admin.py`: painel administrativo com verificação de autorização no servidor.

## Publicação no Streamlit Community Cloud

1. Extraia o ZIP e envie todos os arquivos e pastas para o repositório GitHub usado pelo app.
2. Configure o app para executar `app.py` como arquivo principal.
3. Preserve os Secrets já configurados no Streamlit Cloud. Em especial, não remova nem compartilhe `GROQ_API_KEY`, `COOKIE_PASSWORD` e as credenciais de e-mail/OAuth já utilizadas pelo app.
4. O Streamlit instalará as dependências listadas em `requirements.txt` na próxima implantação.

O ZIP não inclui dados de usuários, tokens, arquivos enviados nem um arquivo local de Secrets.
