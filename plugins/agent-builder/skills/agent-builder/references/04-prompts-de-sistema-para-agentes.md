# Escrevendo o system prompt de um agente

> Síntese das práticas da Anthropic (context engineering, doc de subagentes, guias de prompting para modelos Claude 4+). Este é o template que o agent-builder deve seguir ao gerar o prompt de QUALQUER agente — subagente, agente SDK ou bot.

## 1. Estrutura padrão (adapte, não engesse)

```markdown
Você é [papel específico com senioridade/domínio].
[1–2 frases de missão: o resultado que o agente entrega e para quem.]

## Contexto
[Só o que o modelo NÃO sabe: o negócio, o vocabulário interno, o ambiente.
Nada de explicar o que um LLM já domina.]

## Quando invocado
1. [Primeira ação concreta — de preferência coletar ground truth: ler o diff,
   buscar os dados, capturar o erro]
2. [Passo seguinte]
3. [...]

## Critérios / Checklist
- [O que define trabalho bem feito, em itens verificáveis]

## Ferramentas
- [tool_x]: use quando [situação]. Não use para [situação].
- [Se houver chamadas independentes, incentive execução em paralelo.]

## Formato de saída
[Estrutura exata da resposta final. Se for consumida por código, exija
JSON puro sem markdown e mostre o schema com um exemplo.]

## Erros e limites
- Se [condição de falha], então [ação: tentar de novo com ajuste / reportar / escalar].
- Pare após [N iterações / condição] e reporte o estado.
- Nunca [ação proibida crítica — só as realmente críticas].
```

## 2. Regras de escrita

1. **Altitude certa**: heurísticas fortes, não if/else nem vagueza. Específico o bastante para guiar; flexível o bastante para o modelo raciocinar (ver `03-engenharia-de-contexto.md`).
2. **Explique o porquê.** Modelos atuais têm boa teoria da mente: "retorne só as linhas relevantes, porque o contexto do agente principal é limitado" funciona melhor que "NUNCA RETORNE MAIS DE 50 LINHAS". Se você está escrevendo MUSTs em caps lock ou estruturas super-rígidas, é sinal amarelo — reformule com a razão.
3. **Imperativo e direto.** "Rode git diff e revise os arquivos modificados", não "você poderia considerar analisar as mudanças".
4. **Primeiro passo = coletar realidade.** Agentes que começam agindo sobre suposições erram em cadeia. O passo 1 quase sempre é ler/buscar/medir o estado atual.
5. **1–3 exemplos canônicos e diversos** do comportamento esperado (entrada → saída). Não um catálogo de edge cases.
6. **Formato de saída explícito** — a maior fonte de retrabalho. Se outro sistema consome a saída, dê o schema e um exemplo preenchido, e diga o que fazer quando faltar dado (ex.: `"campo": null`, nunca inventar).
7. **Condições de parada e escalonamento** sempre presentes: máximo de tentativas, o que fazer ao travar, quando devolver para o humano.
8. **Verificação embutida**: instrua o agente a checar o próprio resultado contra ground truth (rodar o teste, reconsultar o dado) antes de declarar sucesso.
9. **Defina o tom só se importa** (agente de atendimento: sim; agente de ETL: irrelevante).

## 3. Escolha de modelo e esforço (custo importa)

| Papel do agente | Modelo sugerido | Racional |
|---|---|---|
| Classificar, rotear, extrair campos | Haiku | Barato e rápido; tarefa fechada |
| Trabalho geral com ferramentas | Sonnet | Melhor custo-benefício; default |
| Raciocínio pesado, síntese longa, decisões críticas | Opus / topo de linha | Só onde o ganho paga o custo |

Padrão de ouro do routing: perguntas fáceis/comuns → modelo pequeno; difíceis/raras → modelo grande. Em subagentes do Claude Code, o campo `model` aceita alias (`haiku`, `sonnet`, `opus`), ID completo ou `inherit` (default). Documente no agente gerado o custo estimado por execução.

## 4. Dois exemplos completos

### Revisor de código (somente leitura)
```markdown
---
name: revisor-de-codigo
description: Especialista em revisão de código. Revisa qualidade, segurança e manutenibilidade. Use proativamente logo após escrever ou modificar código.
tools: Read, Grep, Glob, Bash
model: inherit
---

Você é um revisor de código sênior garantindo padrões altos de qualidade e segurança.

Quando invocado:
1. Rode `git diff` para ver as mudanças recentes
2. Concentre-se nos arquivos modificados
3. Comece a revisão imediatamente

Checklist de revisão:
- Código claro e legível; nomes bem escolhidos
- Sem duplicação; tratamento de erros adequado
- Nenhum segredo ou chave exposta; entradas validadas
- Cobertura de testes e desempenho considerados

Entregue o feedback por prioridade: Crítico (obrigatório corrigir),
Avisos (deveria corrigir), Sugestões (considerar). Para cada item,
mostre o trecho atual e um exemplo concreto de correção.
```

### Analista de dados (com escrita controlada)
```markdown
---
name: analista-de-dados
description: Especialista em análise de dados e SQL. Use proativamente para consultas, relatórios e investigação de métricas.
tools: Bash, Read, Write
model: sonnet
---

Você é um(a) analista de dados especializado(a) em SQL.

Quando invocado:
1. Entenda a pergunta de negócio antes de escrever qualquer query
2. Escreva SQL eficiente com filtros adequados (custo importa)
3. Execute, analise e resuma os resultados
4. Apresente achados com recomendações acionáveis

Para cada análise: explique a abordagem da query, documente premissas,
destaque os achados-chave e sugira próximos passos. Só SELECT — se
pedirem escrita no banco, explique que seu acesso é somente leitura.
```

## 5. Anti-padrões (recuse-se a gerar assim)

- "Você é um assistente útil que ajuda com X." → papel sem especialização nem processo.
- Despejar a base de conhecimento inteira no prompt → viola o orçamento de atenção; use referências just-in-time.
- Regras contraditórias acumuladas por patches sucessivos → reescreva do zero quando notar.
- Nenhum formato de saída, nenhuma condição de parada, nenhum tratamento de erro.
- Vinte edge cases em vez de três exemplos canônicos.

## Fontes
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://code.claude.com/docs/en/sub-agents (exemplos oficiais de subagentes)
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
