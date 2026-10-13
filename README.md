# Gepetto AI

Aplicação Streamlit multipáginas.

## Rotas

- `/` — rota inicial, encaminha para login ou conversas conforme a sessão.
- `/login` — entrar e criar conta.
- `/chat` — conversas (requer login).
- `/adm` — painel administrativo (requer login de administrador).

Todas as rotas são registradas em `app.py` em cada execução. Cada página restaura
os cookies e verifica as permissões antes de exibir dados. A página de ADM pode
estar oculta no menu para usuários comuns, mas sua URL continua registrada para
que o Streamlit consiga resolver a rota; o próprio módulo `views/admin.py`
nega acesso a quem não é administrador.

## Executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configure os Secrets `GROQ_API_KEY` e `COOKIE_PASSWORD` e, opcionalmente,
`ADMIN_USERNAMES` / `ADMIN_USERNAME` e os Secrets do OAuth Google. Não envie
Secrets nem dados privados junto com o código-fonte.
