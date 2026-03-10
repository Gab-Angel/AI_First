---
description: Instruções para auxiliar na criação de commits Git semânticos e padronizados. Ative sempre que o usuário pedir ajuda com commits, mensagens de commit, git add, git log ou qualquer fluxo de versionamento.
applyTo: "**"
---

# 📦 Guia de Commits Semânticos com Copilot

## 🎯 O que esse arquivo faz

Este arquivo instrui o GitHub Copilot a **auxiliar na criação de commits Git padronizados**, seguindo o padrão **Conventional Commits**. O agente não executa os comandos diretamente — ele gera os comandos prontos para você copiar e colar no terminal.

A comunicação entre agente e usuário é feita **em português (pt-BR)**. Os commits, por sua vez, são **sempre escritos em inglês**.

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

## 📐 Como o agente analisa e gera os commits

Quando você pedir ajuda para commitar, o agente irá:

1. **Analisar as alterações** com base no contexto do arquivo aberto, diff visível ou descrição que você fornecer.
2. **Identificar o tipo** de alteração realizada (veja tabela abaixo).
3. **Definir o escopo** com base no módulo, pasta ou funcionalidade afetada (quando aplicável).
4. **Redigir a mensagem** em inglês, no imperativo, curta e objetiva.
5. **Gerar o bloco de comandos** pronto para ser colado no terminal.

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

O agente irá responder em **português**, entender o contexto e gerar o **bloco de comandos em inglês** pronto para uso no terminal..