# Princípios e padrões de arquitetura de agentes

> Fonte primária: "Building Effective Agents" (Anthropic Engineering, dez/2024) + "Effective Context Engineering" (set/2025). Este arquivo define COMO DECIDIR a arquitetura antes de gerar qualquer código.

## 1. A distinção fundamental: workflow vs. agente

- **Workflow**: LLM e ferramentas orquestrados por caminhos de código pré-definidos. Você controla a sequência.
- **Agente**: o LLM dirige dinamicamente o próprio processo e uso de ferramentas, mantendo controle sobre como cumpre a tarefa. Definição prática que a Anthropic adota hoje: *um LLM usando ferramentas em loop, de forma autônoma*.

As implementações de maior sucesso na indústria não usam frameworks complexos — usam padrões simples e componíveis. Frameworks aceleram o início, mas criam camadas de abstração que escondem prompts e respostas e dificultam debug. Comece direto na API/SDK; se usar framework, entenda o que ele faz por baixo.

## 2. Regra de ouro: a solução mais simples que funciona

Ordem de escalada (só suba de nível quando o nível anterior comprovadamente não resolve):

1. **Uma chamada de LLM** otimizada (com retrieval e exemplos no contexto) — resolve a maioria dos casos.
2. **Workflow** — quando a tarefa tem etapas previsíveis e você quer consistência.
3. **Agente autônomo** — quando o número de passos é imprevisível e não dá para hardcodar o caminho.

Agentes trocam **latência e custo** por desempenho. Sempre pergunte: essa troca vale a pena aqui? Um script determinístico é mais barato, mais rápido e mais confiável quando a tarefa é mecânica. **Não crie um agente para o que um cron + script resolve.**

## 3. O bloco de construção: o LLM aumentado

Todo sistema agêntico parte de um LLM com três aumentos: **retrieval** (busca de informação), **ferramentas** (ações no mundo) e **memória** (estado persistente). Duas prioridades de implementação: adaptar esses aumentos ao caso de uso específico e dar ao LLM uma interface simples e bem documentada para cada um (ver `02-design-de-ferramentas.md`).

## 4. Os 5 padrões de workflow

### 4.1 Prompt chaining (encadeamento)
Decompõe a tarefa em sequência de passos; cada chamada processa a saída da anterior. Pode ter **gates** programáticos entre etapas para validar que está no trilho.
- **Quando usar**: tarefa decomponível em subtarefas fixas e limpas. Troca latência por acurácia (cada chamada fica mais fácil).
- **Exemplos**: gerar copy → traduzir; escrever outline → validar critérios → escrever documento final.

### 4.2 Routing (roteamento)
Classifica a entrada e direciona para um fluxo/prompt especializado. Separação de responsabilidades: otimizar para um tipo de entrada sem prejudicar os outros.
- **Quando usar**: categorias distintas de entrada, com classificação confiável.
- **Exemplos**: triagem de atendimento (dúvida geral / reembolso / técnico); rotear perguntas fáceis para Haiku e difíceis para Sonnet/Opus (otimiza custo e velocidade).

### 4.3 Parallelization (paralelização)
Duas variações:
- **Sectioning**: dividir em subtarefas independentes rodando em paralelo.
- **Voting**: rodar a mesma tarefa várias vezes para diversidade/confiança.
- **Quando usar**: velocidade (subtarefas independentes) ou confiança (múltiplas perspectivas). LLMs performam melhor quando cada consideração tem uma chamada focada.
- **Exemplos**: guardrail em paralelo com a resposta principal (um modelo responde, outro filtra conteúdo impróprio); revisão de código por vulnerabilidades com vários prompts votando.

### 4.4 Orchestrator-workers (orquestrador + trabalhadores)
Um LLM central decompõe a tarefa dinamicamente, delega para LLMs workers e sintetiza os resultados. Diferença da paralelização: as subtarefas **não são pré-definidas** — o orquestrador decide conforme a entrada.
- **Quando usar**: tarefas complexas onde você não consegue prever as subtarefas (ex.: quantos arquivos mudar num refactor; pesquisa em múltiplas fontes).
- **Regras práticas de orquestração** (lições dos sistemas multi-agente da Anthropic):
  - O orquestrador delega com **objetivo, formato de saída esperado, ferramentas permitidas e limites** explícitos — instruções vagas geram trabalho duplicado ou lacunas.
  - Workers exploram muito (dezenas de milhares de tokens) mas retornam **apenas um resumo destilado** (~1–2 mil tokens) — o contexto de busca fica isolado no worker.
  - Escale o esforço à complexidade: consulta simples = 1 agente e poucas chamadas; pesquisa ampla = vários workers com responsabilidades divididas.

### 4.5 Evaluator-optimizer (gerador + avaliador)
Uma chamada gera, outra avalia e dá feedback, em loop.
- **Quando usar**: existem critérios de avaliação claros E o refinamento iterativo agrega valor mensurável. Sinais de bom fit: feedback humano articulado melhora a resposta, e um LLM consegue dar esse feedback.
- **Exemplos**: tradução literária com nuances; pesquisa complexa onde o avaliador decide se precisa de mais buscas.

## 5. O agente autônomo

Estrutura: começa com um comando (ou conversa) do humano → planeja → opera em loop **percebendo → decidindo → agindo → observando**. Pontos críticos:

- **Ground truth a cada passo**: o agente precisa avaliar o próprio progresso com feedback real do ambiente (resultado de tool call, execução de código, testes). Nunca deixe o agente "achar" que deu certo — faça-o verificar.
- **Condições de parada**: máximo de iterações, timeout, orçamento. Sem isso, erros se acumulam e o custo explode.
- **Checkpoints humanos**: pause para feedback em marcos ou bloqueios; ações irreversíveis exigem aprovação (ver `08-guardrails-e-seguranca.md`).
- Implementação costuma ser simples: um loop `while` alternando chamada de LLM e execução de ferramenta. A sofisticação está nas ferramentas e no prompt, não no loop.
- **Onde agentes brilham**: problemas abertos com nº de passos imprevisível, ambiente confiável, e resultado verificável (código com testes, suporte com resolução mensurável).

## 6. Os 3 princípios de implementação (Anthropic)

1. **Simplicidade** no design do agente.
2. **Transparência**: mostrar explicitamente os passos de planejamento do agente.
3. **ACI (Agent-Computer Interface)**: investir em documentação e teste das ferramentas com o mesmo cuidado que se investe em UX para humanos.

## 7. Árvore de decisão rápida (usar na entrevista com o usuário)

| Situação | Arquitetura |
|---|---|
| Uma chamada bem promptada resolve | Prompt único (sem agente) |
| Tarefa mecânica e determinística | Script/cron (sem LLM no loop) |
| Etapas fixas e conhecidas | Workflow (chaining ± gates) |
| Tipos de entrada muito diferentes | Routing |
| Subtarefas independentes ou preciso de confiança | Parallelization |
| Subtarefas imprevisíveis, síntese central | Orchestrator-workers |
| Qualidade iterável com critério claro | Evaluator-optimizer |
| Passos imprevisíveis, ambiente confiável, resultado verificável | Agente autônomo |
| Delegação dentro do Claude Code | Subagente (ver `05-subagentes-claude-code.md`) |
| Serviço 24/7 / bot / integração externa | Agent SDK (ver `06-agent-sdk.md`) |

## Fontes
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://www.anthropic.com/engineering/multi-agent-research-system
