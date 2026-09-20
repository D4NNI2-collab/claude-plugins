# Engenharia de contexto para agentes

> Fonte primária: "Effective context engineering for AI agents" (Anthropic Engineering, set/2025). Prompt engineering é escrever boas instruções; **context engineering é curar TODO o estado que entra no modelo a cada inferência** — system prompt, ferramentas, MCP, dados externos, histórico. Em agentes de longa duração, isso decide o desempenho.

## 1. O princípio central

Contexto é um recurso **finito com retornos decrescentes**. Existe "context rot": quanto mais tokens na janela, menor a precisão do modelo em recuperar e relacionar informação (consequência da atenção n² do transformer e da distribuição do treino). O modelo tem um **orçamento de atenção** — cada token gasto reduz o que sobra.

**Meta prática: o menor conjunto possível de tokens de alto sinal que maximiza a probabilidade do resultado desejado.** Minimal não significa curto — significa sem desperdício. O agente precisa de informação suficiente, mas nada além.

## 2. System prompt na "altitude certa"

Dois modos de falha opostos:
- **Baixo demais**: lógica if/else frágil hardcoded no prompt para forçar comportamento exato → quebradiço, caro de manter.
- **Alto demais**: orientação vaga ("seja útil e cuidadoso") que assume contexto compartilhado que o modelo não tem.

O ponto ótimo: **específico o bastante para guiar, flexível o bastante para dar heurísticas fortes** (não regras rígidas). Método: comece com um prompt mínimo no melhor modelo disponível, rode nos seus casos, e adicione instruções e exemplos APENAS para os modos de falha observados.

Estruture em seções delimitadas (tags XML como `<instrucoes>`, `<contexto>`, ou headers Markdown `## Ferramentas`, `## Formato de saída`). Ver template em `04-prompts-de-sistema-para-agentes.md`.

## 3. Exemplos (few-shot)

Continuam fortemente recomendados — para o LLM, exemplos são "as imagens que valem mil palavras". Mas **não** empilhe uma lista de edge cases tentando cobrir toda regra possível. Cure um conjunto pequeno de exemplos **diversos e canônicos** que retratem o comportamento esperado.

## 4. Ferramentas enxutas

O modo de falha mais comum observado pela Anthropic: conjuntos de tools inchados que cobrem funcionalidade demais ou criam ambiguidade sobre qual usar. Ferramentas devem ser autocontidas, robustas a erro e claríssimas no propósito (ver `02-design-de-ferramentas.md`). Um conjunto mínimo viável de tools também facilita manter o contexto limpo em interações longas.

## 5. Recuperação "just-in-time" (a estratégia dos agentes modernos)

Em vez de pré-processar todos os dados relevantes antes da inferência (RAG clássico), agentes eficazes mantêm **identificadores leves** — caminhos de arquivo, queries salvas, links — e carregam o dado sob demanda com ferramentas. É como o Claude Code analisa bases de dados enormes: escreve queries direcionadas, usa `head`/`tail`, e nunca carrega o objeto inteiro no contexto.

Vantagens:
- Espelha a cognição humana (não decoramos o corpus; criamos sistemas de indexação: arquivos, inbox, bookmarks).
- Metadados guiam comportamento: `test_utils.py` dentro de `tests/` significa outra coisa que em `src/core/`. Hierarquia de pastas, convenções de nome e timestamps são sinais.
- Habilita **progressive disclosure**: o agente monta entendimento camada por camada, mantendo só o necessário na memória de trabalho.

Trade-off: exploração em runtime é mais lenta que dado pré-computado. **Estratégia híbrida** costuma vencer: um núcleo carregado up-front (como os arquivos CLAUDE.md do Claude Code) + navegação just-in-time (glob/grep) para o resto. Regra da Anthropic: "faça a coisa mais simples que funciona".

## 6. Tarefas de longo horizonte: 3 técnicas

Quando a tarefa excede a janela de contexto (migrações grandes, pesquisa extensa), use uma destas — a escolha depende da tarefa:

### 6.1 Compaction (compactação)
Resumir a conversa perto do limite e reiniciar a janela com o resumo. A arte está na seleção: preservar decisões de arquitetura, bugs não resolvidos e detalhes de implementação; descartar saídas de tool redundantes. Ajuste o prompt de compactação maximizando primeiro o *recall* (não perder nada crítico) e depois a *precision* (cortar o supérfluo). Forma mais segura e barata: **limpar resultados de tools antigos** — se a tool foi chamada lá atrás, o agente raramente precisa rever a saída crua.
- Melhor para: tarefas conversacionais com muita ida e volta.

### 6.2 Structured note-taking (memória agêntica)
O agente escreve notas persistentes FORA da janela (um `NOTES.md`, uma to-do list, arquivos de memória) e as relê depois. Custo mínimo, ganho enorme de coerência: o experimento "Claude joga Pokémon" mostra o agente mantendo contagens precisas por milhares de passos, mapas de regiões exploradas e estratégias de combate — e retomando sequências de horas após reset de contexto lendo as próprias notas.
- Melhor para: desenvolvimento iterativo com marcos claros. No Claude Code, o campo `memory` dos subagentes implementa exatamente isso (ver `05-subagentes-claude-code.md`).

### 6.3 Arquiteturas de subagentes
Em vez de um agente segurando todo o estado, subagentes especializados trabalham com janelas limpas. O agente líder coordena com um plano de alto nível; cada subagente explora profundamente (dezenas de milhares de tokens) mas **retorna só um resumo destilado de ~1–2 mil tokens**. Separação clara: contexto de busca isolado nos subagentes; o líder sintetiza. Mostrou melhora substancial sobre agentes únicos em pesquisa complexa.
- Melhor para: pesquisa e análise complexas onde exploração paralela compensa.

## 7. Regras operacionais para o agent-builder

Ao gerar um agente, aplique:
1. System prompt mínimo-mas-completo, em seções, na altitude certa.
2. 1–3 exemplos canônicos, não catálogo de edge cases.
3. Poucas tools, sem ambiguidade, com respostas token-eficientes.
4. Dados grandes: referências leves + carregamento just-in-time; nunca despejar tudo no prompt.
5. Se a tarefa é longa: escolher explicitamente compaction, note-taking ou subagentes — e implementar desde o início.
6. Reavaliar o contexto a cada iteração de teste: todo token precisa pagar o próprio aluguel.

## Fontes
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/engineering/multi-agent-research-system
