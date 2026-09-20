# Subagentes do Claude Code — referência completa

> **Validado contra a documentação oficial em 2026-09-19** (páginas sub-agents, hooks e agent-teams; 7 correções aplicadas nessa data). ATENÇÃO: esta área muda rápido. Antes de gerar um subagente, confirme os campos atuais em https://code.claude.com/docs/en/sub-agents (índice geral: https://code.claude.com/docs/llms.txt).

## 1. O que são e quando usar

Subagentes são assistentes especializados que rodam **em janela de contexto própria**, com system prompt customizado, ferramentas específicas e permissões independentes. O Claude delega quando a tarefa bate com a `description` do subagente; ele trabalha isolado e retorna só o resultado.

**Use subagente quando**: a tarefa produz saída verbosa que você não quer no contexto principal (testes, logs, exploração); quer impor restrições de ferramentas/permissões; o trabalho é autocontido e cabe num resumo; quer rotear para modelo mais barato (Haiku).
**Use a conversa principal quando**: precisa de ida e volta frequente; fases compartilham muito contexto; mudança rápida; latência importa (subagente começa do zero).
**Use uma skill quando**: quer prompt/fluxo reutilizável rodando NO contexto da conversa principal, não isolado.

Fato importante: desde a v2.1.198, `/agents` **não abre mais assistente interativo** — o fluxo oficial é pedir ao Claude para escrever o arquivo ou editar `.claude/agents/` diretamente. É exatamente o papel do agent-builder.

## 2. Anatomia do arquivo

Arquivo Markdown com frontmatter YAML; **o corpo é o system prompt**. O subagente recebe SÓ esse prompt + detalhes básicos de ambiente — **não herda o system prompt completo do Claude Code**. Ele começa com contexto limpo: não vê o histórico da conversa nem os arquivos já lidos; recebe uma mensagem de tarefa que o Claude compõe, mais CLAUDE.md/status do git (os integrados Explore e Plan pulam isso).

```markdown
---
name: revisor-de-codigo
description: Revisa código quanto a qualidade e boas práticas. Use proativamente após escrever ou modificar código.
tools: Read, Glob, Grep
model: sonnet
---

Você é um revisor de código. Ao ser invocado, analise o código e dê
feedback específico e acionável sobre qualidade, segurança e boas práticas.
```

## 3. Onde salvar (escopo e prioridade)

| Local | Escopo | Prioridade |
|---|---|---|
| Managed settings (admin) | Organização | 1 (maior) |
| Flag CLI `--agents` (JSON) | Sessão atual | 2 |
| `.claude/agents/` | Projeto (versione no git p/ o time) | 3 |
| `~/.claude/agents/` | Todos os seus projetos | 4 |
| `agents/` de plugin | Onde o plugin está ativo | 5 |

- Diretórios são varridos **recursivamente** (pode organizar em subpastas); a identidade vem do `name` do frontmatter, não do caminho. Mantenha `name` único.
- Alterações em arquivos são detectadas em segundos, **sem reiniciar** — exceto na primeira criação do diretório `agents/` de um escopo (aí reinicie).
- Por segurança, subagentes vindos de **plugin** ignoram `hooks`, `mcpServers` e `permissionMode`.

## 4. Campos de frontmatter (tabela atual — só `name` e `description` são obrigatórios)

| Campo | Função |
|---|---|
| `name` | Identificador único, minúsculas e hífens |
| `description` | Quando o Claude deve delegar (inclua "use proactively" para delegação proativa) |
| `tools` | Allowlist de ferramentas; omitido = herda todas. Se NENHUMA entrada resolver para uma ferramenta, o subagente falha ao iniciar com erro nomeando as entradas não resolvidas (v2.1.208+) |
| `disallowedTools` | Denylist, removida da lista herdada. Aceita padrões MCP: `mcp__<server>`, `mcp__*` |
| `model` | `sonnet` \| `opus` \| `haiku` \| `fable` \| ID completo \| `inherit` (= modelo da conversa principal). Omitido: resolve na ordem parâmetro da invocação → `CLAUDE_CODE_SUBAGENT_MODEL` → modelo da conversa principal |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan`, `manual` (alias de `default`). Omitido: herda o modo da conversa principal. `bypassPermissions` declarado no subagente é ignorado — mantém o modo da conversa (v2.1.267+) |
| `maxTurns` | Máximo de turnos antes de parar (condição de parada!) |
| `skills` | Skills pré-carregadas no contexto na inicialização (conteúdo completo injetado) |
| `mcpServers` | Servidores MCP para este subagente: referência por nome (compartilha conexão) ou definição inline (conecta/desconecta com o subagente) |
| `hooks` | Hooks de ciclo de vida escopados a este subagente (ex.: `PreToolUse` validando comandos) |
| `memory` | Memória persistente entre sessões: `user` \| `project` \| `local` |
| `background` | `true` = mantém em background mesmo quando o Claude pede foreground. Com fork mode ligado (padrão em sessão interativa), subagentes já rodam em background; desligado (modo `-p` e SDK), o Claude decide |
| `effort` | `low`…`max` — sobrescreve o nível de esforço da sessão |
| `isolation` | `worktree` = roda numa cópia isolada do repositório (git worktree temporário) |
| `color` | Cor de exibição na lista de tarefas |
| `initialPrompt` | Primeiro turno automático quando o agente roda como sessão principal (`--agent`) |
| `omitClaudeMd` | `true` = inicia o subagente sem os CLAUDE.md de usuário/projeto/local (política gerenciada ainda carrega); ignorado com `--agent` (v2.1.271+) |
| `experimental` | Mapa de opções experimentais, ex.: `cacheTtl: 5m` ou `1h` — TTL do cache de prompt do subagente (v2.1.248+) |

## 5. Decisões de design ao gerar um subagente

1. **Foco único**: um subagente excelente em UMA tarefa > um genérico. Description detalhada decide a delegação automática.
2. **Menor privilégio**: `tools` como allowlist explícita. Revisor = `Read, Grep, Glob` (sem Edit/Write); debugger precisa de `Edit`. Alternativa: `disallowedTools: Write, Edit` para herdar o resto.
3. **Modelo por custo**: exploração/rotina → `haiku`; padrão → `sonnet` ou `inherit`; raciocínio pesado → `opus`.
4. **Controle fino via hooks**: quando `tools` não basta (ex.: permitir Bash mas só SELECT no banco), use `PreToolUse` com script que lê o JSON no stdin e sai com código 2 para bloquear.
5. **Memória** para agentes recorrentes: `memory: project` (compartilhável via git) faz o subagente acumular padrões da base, decisões e aprendizados em `MEMORY.md` (as primeiras ~200 linhas/25KB entram no prompt). Inclua no corpo: "Atualize sua memória com padrões e decisões que descobrir".
6. **Aninhamento**: por padrão um subagente pode gerar subagentes próprios, até 3 níveis abaixo da conversa principal (ajustável via `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; `1` desliga o aninhamento). Para proibir num agente específico, use `tools` como allowlist sem `Agent` ou coloque `Agent` em `disallowedTools`. Como thread principal (`claude --agent x`), `Agent(worker, researcher)` restringe QUAIS tipos pode gerar.
7. **MCP escopado**: definir um servidor inline no subagente mantém as descrições de tools dele FORA do contexto da conversa principal — só o subagente as vê.

## 6. Invocação e operação

- **Automática**: pela `description`. **Explícita**: citar o nome no prompt, `@`-mencionar (`@agent-<nome>`), ou rodar a sessão inteira como o agente: `claude --agent revisor-de-codigo` (o prompt do agente SUBSTITUI o do Claude Code).
- **Background** por padrão; prompts de permissão aparecem na sessão principal nomeando o subagente. `Ctrl+B` manda tarefa para background; `/tasks` lista.
- **Retomar**: cada invocação cria instância nova, mas o Claude pode retomar um subagente existente (via `SendMessage` com o ID/nome) mantendo todo o histórico — útil para "continue aquela revisão e agora analise X".
- **Fork** (`/subtask <diretiva>` — atenção: o comando NÃO é mais `/fork`, que hoje copia a sessão inteira para uma background session): subagente que herda TODA a conversa atual (system prompt, pool exato de tools, modelo e histórico), roda em background e devolve só um resumo ao thread principal — ideal quando um subagente nomeado precisaria de contexto demais. Ocupa um slot do limite de subagentes concorrentes, mas nunca é bloqueado por ele.
- **Equipes de agentes**: para sessões paralelas que se comunicam entre si, existe o recurso separado de agent teams (as definições de subagente podem ser reaproveitadas como colegas de equipe).
- Desabilitar: `permissions.deny: ["Agent(nome)"]` em settings.

## 7. Padrões de uso comprovados

- **Isolar operações de alto volume**: "use um subagente para rodar a suíte de testes e reportar só as falhas com as mensagens de erro".
- **Pesquisa em paralelo**: vários subagentes investigando módulos independentes; o Claude sintetiza. Cuidado: muitos retornos detalhados também consomem contexto — peça resumos.
- **Encadear**: "use o revisor para achar problemas de performance, depois o otimizador para corrigi-los".

## 8. Checklist de geração (o agent-builder valida antes de entregar)

- [ ] `name` minúsculo-com-hífens, único; `description` diz O QUE + QUANDO (com "use proactively" se fizer sentido)
- [ ] `tools` mínimas para a função; escrita só se necessária
- [ ] `model` justificado por custo/complexidade
- [ ] Corpo segue o template de `04-prompts-de-sistema-para-agentes.md` (fluxo numerado, checklist, formato de saída, condições de parada)
- [ ] `maxTurns` definido para agentes que podem loopar
- [ ] Escopo certo (projeto vs usuário) e arquivo salvo no diretório correspondente
- [ ] Testado com uma invocação real logo após criar

## Fontes
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/agent-teams
- https://code.claude.com/docs/en/hooks
