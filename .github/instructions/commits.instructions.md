---
description: Instruções para auxiliar na criação de commits Git semânticos e padronizados. Ative sempre que o usuário pedir ajuda com commits, mensagens de commit, git add, git log ou qualquer fluxo de versionamento.
applyTo: "**"
---

# 📦 Guia de Commits Semânticos com Copilot

## 🎯 O que esse arquivo faz

Este arquivo instrui o GitHub Copilot a **auxiliar na criação de commits Git padronizados**, seguindo o padrão **Conventional Commits**. O agente não executa os comandos diretamente — ele gera os comandos prontos para você copiar e colar no terminal.

A comunicação entre agente e usuário é feita **em português (pt-BR)**. Os commits, por sua vez, são **sempre escritos em inglês**.

---

## ⚙️ Requisito: Agent Mode + MCP do GitKraken

> ⚠️ **Estas instruções só funcionam corretamente no Agent Mode do Copilot.**

Para que o agente consiga ver o estado real do repositório (arquivos modificados, branch atual, histórico de commits, PRs abertas), ele depende do **MCP Server do GitKraken**, embutido na extensão **GitLens**.

### Pré-requisitos
1. Extensão **GitLens** instalada e atualizada no VS Code
2. Copilot em modo **Agent** (selecionar no campo de texto do painel lateral)
3. MCP ativo — verificar em `⚙️ > MCP Server: GitKraken (bundled with GitLens)`

### Ferramentas MCP disponíveis para o agente

Com o MCP ativo, o agente tem acesso direto às seguintes informações **sem precisar que você cole nada**:

| Ferramenta MCP | O que fornece |
|----------------|---------------|
| `git_status` | Arquivos modificados, staged e untracked |
| `git_diff` | Conteúdo exato das alterações |
| `git_log` | Histórico de commits da branch atual |
| `git_branches` | Branch ativa e branches disponíveis |
| `git_show` | Detalhes de um commit específico |

> 💡 Quando o MCP estiver ativo, o agente **deve usar essas ferramentas diretamente** antes de sugerir qualquer commit, sem pedir que o usuário rode comandos manualmente.

---

## 🔍 Passo obrigatório antes de qualquer commit

> ⚠️ **O agente NUNCA deve sugerir um commit sem antes conhecer o estado real do repositório.**

### Se o MCP do GitKraken estiver ativo (Agent Mode)
O agente deve **usar as ferramentas MCP diretamente** para inspecionar o repositório:
1. Chamar `git_status` para listar o que foi modificado
2. Chamar `git_diff` nos arquivos relevantes para entender as alterações
3. Apresentar um resumo em português do que encontrou e propor o commit

### Se o MCP não estiver disponível (fallback)
O agente deve pedir que o usuário rode manualmente:

```bash
git status
git diff
```

E aguardar o output antes de sugerir qualquer coisa. Nunca assumir ou inferir o que está modificado sem ver o estado real do repositório.

Se o usuário não fornecer o output, o agente deve perguntar em português:
> _"Pode rodar `git status` e `git diff` no terminal e colar o resultado aqui? Assim consigo ver exatamente o que foi alterado antes de montar o commit."_

---

## 🛠️ Comandos que o agente pode gerar

O agente pode gerar os seguintes comandos Git para você executar:

```bash
# Verificar status dos arquivos modificados
git status

# Visualizar as alterações feitas
git diff

# Adicionar arquivos específicos ao stage
git add <arquivo>

# Adicionar todos os arquivos modificados ao stage
git add .

# Criar o commit com a mensagem formatada
git commit -m "<tipo>(<escopo opcional>): <mensagem em inglês>"

# Verificar histórico de commits
git log --oneline
```

---

## 🚫 Arquivos que NUNCA devem ser commitados

O agente deve identificar e **recusar** incluir qualquer um dos arquivos abaixo em comandos `git add`. Se detectado, deve avisar o usuário em português e removê-lo da lista.

**Arquivos de ambiente e segredos:**
- `.env`, `.env.local`, `.env.development`, `.env.production`, `.env.*`
- `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.cer`
- `*secret*`, `*password*`, `*token*` (em nomes de arquivo)
- `credentials.json`, `service-account.json`, `*.credentials`

**Dependências e build:**
- `node_modules/`, `vendor/`, `.venv/`, `__pycache__/`
- `dist/`, `build/`, `.next/`, `out/`
- `*.log`, `*.tmp`, `*.cache`

**Sistema operacional e editor:**
- `.DS_Store`, `Thumbs.db`
- `.vscode/settings.json` (a menos que seja intencional para o projeto)
- `*.swp`, `*.swo`

> ⚠️ **Regra crítica:** se o usuário pedir `git add .` e houver arquivos sensíveis no diretório, o agente deve **listar os arquivos problemáticos**, avisar o risco e gerar o comando com os arquivos seguros de forma **explícita e individual**, nunca usando `git add .` nesses casos.

---

## 📐 Como o agente analisa e gera os commits

Quando você pedir ajuda para commitar, o agente irá:

1. **Verificar a segurança** — checar se há arquivos sensíveis ou proibidos no escopo antes de qualquer coisa.
2. **Confirmar o escopo com você** — perguntar em português quais arquivos ou funcionalidades devem entrar no commit, especialmente se houver múltiplas alterações não relacionadas.
3. **Analisar as alterações** com base no contexto do arquivo aberto, diff visível ou descrição que você fornecer.
4. **Identificar o tipo** de alteração realizada (veja tabela abaixo).
5. **Definir o escopo** com base no módulo, pasta ou funcionalidade afetada (quando aplicável).
6. **Redigir a mensagem** em inglês, no imperativo, curta e objetiva.
7. **Gerar o bloco de comandos** pronto para ser colado no terminal.

> 💡 **Comportamento esperado:** o agente nunca deve assumir que "tudo" deve ser commitado junto. Se houver arquivos de naturezas diferentes modificados (ex: um arquivo de instrução `.md` e um arquivo de código), ele deve sugerir commits separados e perguntar qual fazer primeiro.

---

## ✅ Estrutura do commit

```
<tipo>(<escopo>): <mensagem curta em inglês>

[corpo opcional — explica o "porquê", não o "o quê"]

[rodapé opcional — ex: BREAKING CHANGE, closes #123]
```

### Tipos aceitos

| Tipo       | Quando usar |
|------------|-------------|
| `feat`     | Nova funcionalidade |
| `fix`      | Correção de bug |
| `docs`     | Alterações em documentação |
| `style`    | Formatação, espaços, ponto e vírgula (sem mudança de lógica) |
| `refactor` | Refatoração sem adicionar feature ou corrigir bug |
| `perf`     | Melhoria de performance |
| `test`     | Adição ou ajuste de testes |
| `chore`    | Tarefas de manutenção, configs, dependências |
| `ci`       | Alterações em pipelines de CI/CD |
| `build`    | Mudanças no sistema de build ou dependências externas |
| `revert`   | Reversão de commit anterior |

---

## 📝 Regras de escrita da mensagem

- **Idioma:** sempre em inglês
- **Modo verbal:** imperativo ("add", "fix", "update", "remove" — não "added", "fixing")
- **Tamanho:** máximo de 72 caracteres na primeira linha
- **Capitalização:** primeira letra minúscula após o tipo
- **Sem ponto final** na linha de título
- **Escopo:** opcional, em letras minúsculas, representa o módulo/área afetada

---

## 💡 Exemplos de output gerado pelo agente

### Exemplo 1 — Nova funcionalidade
```bash
git add src/components/LoginForm.tsx
git commit -m "feat(auth): add login form with email and password validation"
```

### Exemplo 2 — Correção de bug
```bash
git add src/utils/formatDate.ts
git commit -m "fix(utils): correct date formatting for timezone offset"
```

### Exemplo 3 — Documentação
```bash
git add README.md
git commit -m "docs: update setup instructions for local environment"
```

### Exemplo 4 — Refatoração
```bash
git add .
git commit -m "refactor(api): simplify error handling in request interceptor"
```

### Exemplo 5 — Com corpo explicativo
```bash
git add src/services/paymentService.ts
git commit -m "feat(payment): integrate Stripe checkout session

Replace manual payment flow with Stripe-hosted checkout.
Simplifies PCI compliance and improves conversion rate."
```

### Exemplo 6 — Breaking change
```bash
git add .
git commit -m "feat(api)!: change authentication endpoint response format

BREAKING CHANGE: /auth/login now returns { token, user } instead of { jwt }"
```

---

## 🚀 Como pedir ajuda ao agente

Você pode dizer coisas como:

- _"Me ajuda a criar um commit para essas mudanças"_
- _"Gera o comando de commit para o que eu alterei nesse arquivo"_
- _"Faz um commit semântico para essa refatoração"_
- _"Quero commitar tudo, o que você sugere?"_

O agente irá responder em **português**, entender o contexto e gerar o **bloco de comandos em inglês** pronto para uso no terminal.