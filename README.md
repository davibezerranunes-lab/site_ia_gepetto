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

## Painel administrativo

O painel em `/adm` contém cinco seções: Estatísticas, Usuários, Solicitações, Arquivos e Prompts da IA. A seção é escolhida por um controle de seleção (em vez do componente `st.tabs`), para que a troca de área provoque uma renderização completa e funcione melhor em telas móveis.

A seção **Prompts da IA** permite editar os dois prompts que existem no código: o prompt padrão e o prompt administrativo. A configuração é salva em `dados_usuarios/prompts_ia.json` no armazenamento local da aplicação. Esse arquivo não contém segredos de acesso, mas o armazenamento local de uma hospedagem pode ser temporário; para persistência garantida entre reinicializações/redeploys, é necessário usar um banco de dados ou armazenamento persistente.
