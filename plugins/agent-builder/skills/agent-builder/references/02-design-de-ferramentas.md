# Design de ferramentas (tools) para agentes

> Fonte primária: "Writing effective tools for agents — with agents" (Anthropic Engineering, set/2025) + apêndice 2 de "Building Effective Agents". Ferramentas são o fator nº 1 de desempenho de um agente — na construção do agente de SWE-bench, a Anthropic gastou mais tempo otimizando ferramentas do que o prompt geral.

## 1. Mudança de paradigma

Software tradicional é um contrato entre sistemas determinísticos: `getWeather("NYC")` sempre executa igual. **Ferramenta de agente é um contrato entre um sistema determinístico e um agente não-determinístico**: diante da mesma pergunta, o agente pode chamar a ferramenta, responder de memória, pedir esclarecimento — ou alucinar o uso. Portanto: não escreva tools como escreveria uma API para outro dev. Escreva para um colaborador inteligente que só sabe o que está na descrição.

## 2. Escolher QUAIS ferramentas construir (e quais não)

- **Menos ferramentas, mais impacto.** Erro comum: criar um wrapper 1:1 para cada endpoint da API existente. Agentes têm contexto limitado; memória de computador é barata, atenção de LLM não é.
- **Consolide fluxos frequentes em uma ferramenta.** Uma tool pode fazer várias operações por baixo dos panos:
  - Em vez de `list_users` + `list_events` + `create_event` → `schedule_event` (acha horário e agenda).
  - Em vez de `read_logs` (despeja tudo) → `search_logs` (retorna só linhas relevantes + contexto ao redor).
  - Em vez de `get_customer_by_id` + `list_transactions` + `list_notes` → `get_customer_context` (compila tudo que importa de uma vez).
- **Cada ferramenta com propósito claro e distinto.** Se um engenheiro humano não sabe dizer qual tool usar numa situação, o agente também não saberá. Ferramentas sobrepostas ou demais distraem o agente de estratégias eficientes.
- Ferramentas devem permitir que o agente subdivida a tarefa como um humano faria — e reduzir o contexto que saídas intermediárias consumiriam.

## 3. Namespacing (nomear com prefixos)

Com dezenas de servidores MCP e centenas de tools, nomes ambíguos confundem. Agrupe por serviço e recurso: `asana_search`, `jira_search`; `asana_projects_search`, `asana_users_search`. A escolha entre prefixo e sufixo tem efeito mensurável nas avaliações — teste com o seu caso.

## 4. Retornar contexto SIGNIFICATIVO

- Priorize sinal alto: `name`, `file_type`, `image_url` informam a próxima ação; `uuid`, `mime_type`, `256px_image_url` raramente informam.
- **Linguagem natural > identificadores crípticos.** Resolver UUIDs arbitrários para nomes interpretáveis (ou IDs 0-indexados) melhora significativamente a precisão e reduz alucinação em tarefas de recuperação.
- Quando IDs técnicos são necessários para encadear chamadas (`search_user(name='jane')` → `send_message(id=12345)`), exponha um parâmetro `response_format: "concise" | "detailed"`: concise só conteúdo; detailed inclui IDs. (No exemplo da Anthropic com Slack, "concise" usou ~1/3 dos tokens.)
- O formato da resposta (JSON, XML, Markdown) impacta desempenho e não há resposta universal — decida por avaliação.

## 5. Eficiência de tokens

- Implemente **paginação, seleção de intervalo, filtros e truncamento** com defaults sensatos em qualquer tool que possa retornar muito. (Referência: o Claude Code trunca respostas de tools em 25.000 tokens por padrão.)
- Ao truncar, **instrua o agente** na própria resposta: sugira buscas menores e direcionadas em vez de uma busca ampla.
- **Erros são prompts.** Uma mensagem de erro deve comunicar melhoria específica e acionável ("o parâmetro `date` deve estar no formato YYYY-MM-DD; você enviou '15/03'") — nunca códigos opacos ou stack traces. Erros bem escritos ensinam o agente a se corrigir sozinho.

## 6. Prompt-engineering das descrições e specs

É um dos métodos mais eficazes de melhoria — refinamentos precisos nas descrições de tools levaram o Claude ao estado da arte no SWE-bench Verified, reduzindo drasticamente a taxa de erro.

- Escreva a descrição como explicaria a ferramenta a um **novo membro do time**: torne explícito o contexto implícito (formatos de query especiais, terminologia de nicho, relações entre recursos).
- **Parâmetros sem ambiguidade**: `user_id` em vez de `user`; declare formato, unidades e exemplos; imponha com schema estrito.
- Inclua na descrição: exemplo de uso, edge cases, requisitos de formato de entrada e fronteiras claras com ferramentas parecidas.
- **Poka-yoke**: mude os argumentos para tornar o erro difícil. Caso real da Anthropic: o modelo errava com caminhos relativos depois de mudar de diretório; exigir **caminhos absolutos** eliminou o erro por completo.
- Formato de escrita para o modelo: dê espaço para "pensar" antes de se comprometer; mantenha o formato próximo do que ocorre naturalmente na internet; evite overhead (escapar strings em JSON, contar linhas de diff).

## 7. Processo de desenvolvimento (loop com avaliação)

1. **Protótipo rápido** — suba as tools num servidor MCP local ou direto no código; teste você mesmo para sentir as arestas. Dê ao Claude a doc das libs/APIs (arquivos `llms.txt` oficiais ajudam).
2. **Avaliação** — gere dezenas de tarefas realistas, cada uma com resposta/critério verificável (ver `09-avaliacao-de-agentes.md`). Evite sandboxes simplistas.
3. **Métricas além da acurácia**: nº de chamadas, tokens, tempo, erros de tool. Muitas chamadas redundantes → ajustar paginação/limites; muitos erros de parâmetro → melhorar descrições/exemplos.
4. **Analise transcrições** — leia raciocínio E chamadas cruas. O que o agente omite importa tanto quanto o que inclui.
5. **Deixe o agente otimizar as próprias ferramentas** — cole as transcrições no Claude Code e peça melhorias; mantenha um conjunto de teste held-out para não overfitar. Foi assim que a Anthropic superou implementações "expert" manuais.

## 8. Checklist ao gerar ferramentas para um agente novo

- [ ] Cada tool corresponde a um fluxo real de trabalho (não a um endpoint)?
- [ ] Zero sobreposição de propósito entre tools?
- [ ] Nomes com namespace consistente?
- [ ] Respostas com sinal alto, IDs traduzidos, `response_format` quando fizer sentido?
- [ ] Paginação/filtros/truncamento com defaults + instruções ao truncar?
- [ ] Erros acionáveis escritos como prompts?
- [ ] Descrições com exemplo, edge cases e fronteiras; parâmetros inequívocos (poka-yoke)?
- [ ] Plano de avaliação com tarefas realistas definido?

## Fontes
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://www.anthropic.com/engineering/building-effective-agents (Apêndice 2)
