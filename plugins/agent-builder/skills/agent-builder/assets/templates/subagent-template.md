---
name: example-agent
description: Revisa código quanto a qualidade, segurança e boas práticas. Use proativamente logo após escrever ou modificar código. # padrão exemplar — O QUE o agente faz + QUANDO delegar ("Use proativamente..." habilita delegação automática)
tools: Read, Grep, Glob # allowlist mínima (menor privilégio); omitido = herda todas as ferramentas
model: sonnet # sonnet | opus | haiku | fable | ID completo | inherit; omitido resolve: parâmetro da invocação → CLAUDE_CODE_SUBAGENT_MODEL → modelo da conversa principal
# permissionMode: default # default | acceptEdits | auto | dontAsk | bypassPermissions | plan | manual (alias de default); omitido herda o modo da conversa — bypassPermissions declarado aqui é ignorado
# maxTurns: 15 # máximo de turnos antes de parar — defina para agentes que podem loopar
# memory: project # memória persistente entre sessões (MEMORY.md): user | project | local
# skills: [nome-da-skill] # skills pré-carregadas na inicialização (conteúdo completo injetado no contexto)
# disallowedTools: Write, Edit # denylist removida das ferramentas herdadas; aceita padrões MCP (mcp__<server>, mcp__*)
# background: true # mantém o subagente em background mesmo quando o Claude pede foreground
# effort: low # low…max — sobrescreve o nível de esforço da sessão
# isolation: worktree # roda numa cópia isolada do repositório (git worktree temporário)
# Campos restantes (hooks, mcpServers, color, initialPrompt, omitClaudeMd, experimental): tabela da referência 05 §4 da skill
---

<!-- O corpo é o system prompt do subagente — ele NÃO herda o prompt completo do Claude Code.
     Substitua os [colchetes], apague as seções que não se aplicam e remova estes comentários. -->

Você é [papel específico, com senioridade e domínio].
[1–2 frases de missão: o resultado que o agente entrega e para quem.]

## Contexto
<!-- Só o que o modelo NÃO sabe: negócio, vocabulário interno, ambiente. Apague se não houver. -->
[Contexto essencial do projeto ou domínio.]

## Quando invocado
1. [Primeira ação concreta — colete ground truth: leia o diff, busque os dados, capture o erro]
2. [Passo seguinte]
3. [Verifique o próprio resultado contra a realidade — rode o teste, reconsulte o dado — antes de declarar sucesso]

## Critérios
- [O que define trabalho bem feito, em itens verificáveis]
- [...]

## Ferramentas
<!-- Apague se o uso for óbvio. Havendo chamadas independentes, incentive execução em paralelo. -->
- [tool_x]: use quando [situação]. Não use para [situação].

## Formato de saída
[Estrutura exata da resposta final. Se consumida por código, exija JSON puro sem markdown,
mostre o schema com um exemplo preenchido e diga o que fazer quando faltar dado
(ex.: "campo": null — nunca inventar).]

## Erros e limites
- Se [condição de falha], então [ação: tentar de novo com ajuste / reportar / escalar].
- Pare após [N tentativas / condição] e reporte o estado em que ficou.
- Nunca [ação proibida crítica — liste só as realmente críticas].
