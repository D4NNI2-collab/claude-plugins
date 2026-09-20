# Avaliação de agentes e skills

> Sem avaliação, toda otimização é chute. O método da Anthropic (usado nas próprias tools internas de Slack/Asana e no SWE-bench): construir avaliação realista cedo e iterar contra ela — inclusive deixando o Claude analisar transcrições e propor melhorias. A chave: comece com poucos casos e evolua; 5–10 tarefas reais já mudam o jogo.

## 1. Gerar tarefas de avaliação

- **Ancoradas no mundo real**: inspiradas em usos reais, sobre dados/serviços realistas. Evite sandboxes simplistas que não estressam o agente.
- **Multi-etapa e verificáveis**: tarefas fortes exigem várias chamadas de ferramenta (às vezes dezenas) e têm resultado checável.

Exemplos de tarefas FORTES (parafraseadas do guia da Anthropic):
- "Agende uma reunião com a Jane semana que vem sobre o projeto X, anexe as notas da última reunião de planejamento e reserve uma sala."
- "O cliente 9182 relatou cobrança triplicada numa única compra. Encontre os logs relevantes e determine se outros clientes foram afetados."
- "A cliente Sarah pediu cancelamento. Prepare uma oferta de retenção: por que está saindo, qual oferta seria mais convincente e quais fatores de risco."

Exemplos de tarefas FRACAS (um passo, resposta óbvia): "agende reunião com jane@x.com"; "busque `purchase_complete` nos logs"; "encontre o pedido 45892".

- Realismo textual: escreva como usuário escreve — com contexto pessoal, nomes de arquivos, abreviações, até erros de digitação. Varie comprimento e formalidade.

## 2. Verificadores (como saber se acertou)

- Espectro: comparação exata de string → checagens programáticas (arquivo existe? registro criado? teste passa?) → **LLM-como-juiz** com rubrica para saídas abertas.
- **Avalie o estado final, não o caminho**: existem múltiplas rotas válidas; não sobre-especifique quais tools deveriam ser chamadas (pode registrar as esperadas como sinal, sem reprovar rotas alternativas corretas).
- Verificadores não podem ser rígidos demais: não reprove por formatação, pontuação ou fraseado alternativo válido.
- Rubrica típica de juiz LLM: acurácia factual, completude, uso correto de fontes/ferramentas, atendimento ao formato pedido — cada critério com nota e evidência.

## 3. Métricas além da acurácia

Colete por execução: nº de chamadas de ferramenta, tokens totais, tempo total e por chamada, erros de tool. Leituras diagnósticas:
- Muitas chamadas redundantes → paginação/limites/consolidação de tools mal calibrados.
- Muitos erros de parâmetro → descrições e exemplos das tools insuficientes.
- Tokens explodindo → respostas de tool verbosas demais; ativar truncamento/filtros.

## 4. Analisar transcrições (onde mora o ouro)

- Leia o raciocínio E as chamadas cruas com resultados: comportamento importante nem sempre aparece no raciocínio declarado — **o que o agente omite costuma importar mais do que o que inclui** (LLMs nem sempre "dizem o que pensam").
- Procure: onde o agente hesita/confunde tools; loops improdutivos; passos desnecessários induzidos por instruções ruins (candidatos a REMOVER do prompt); trabalho repetido entre execuções (candidato a virar script/tool).
- **Deixe o Claude ajudar**: cole as transcrições no Claude Code e peça análise + refatoração de tools/prompt de uma vez — mantendo consistência entre implementação e descrição.

## 5. O loop (e como não se enganar)

1. Rodar o conjunto de avaliação (com o agente atual).
2. Revisão humana das saídas caso a caso + métricas quantitativas.
3. Melhorar generalizando: corrigir a causa nas tools/prompt, não colar um patch overfitado no exemplo que falhou.
4. Re-rodar TUDO (não só o caso corrigido) — regressões são comuns.
5. Repetir até estabilizar; então expandir o conjunto.

Proteções contra autoengano:
- **Held-out test set**: separe casos que NUNCA guiam mudanças (ex.: 60% treino / 40% teste) — foi o que revelou, na Anthropic, ganhos reais acima das implementações "expert" manuais.
- Rode cada caso mais de uma vez quando possível (agentes são não-determinísticos; olhe taxa, não um ponto).
- Comparação cega entre duas versões (A/B sem saber qual é qual, julgado por avaliador independente) quando "a nova versão é melhor?" precisa de resposta rigorosa.

## 6. Especificidades por tipo de artefato

- **Skill**: sempre compare COM skill vs SEM skill (baseline) nas mesmas tarefas — o ganho é a razão de existir. Além da qualidade, avalie o ACIONAMENTO: ~8–10 queries que devem ativar + ~8–10 quase-misses que não devem (ver `07-criacao-de-skills.md` §6).
- **Subagente**: teste a delegação automática (o Claude escolhe o subagente certo pela description?) e a qualidade do resumo retornado (útil e enxuto?).
- **Agente SDK/bot**: monte um conjunto de conversas reais anonimizadas; avalie resolução da tarefa, nº de turnos e custo por conversa; monitore contínuo em produção (amostrar transcrições semanalmente).

## 7. Checklist mínimo (o agent-builder entrega junto com cada agente)

- [ ] 3–5 tarefas de teste realistas escritas (multi-etapa, verificáveis)
- [ ] Critério de verificação por tarefa (programático ou rubrica de juiz)
- [ ] Primeira rodada executada, com transcrições salvas
- [ ] Métricas registradas (chamadas, tokens, tempo, erros)
- [ ] Melhorias aplicadas por generalização + re-execução completa
- [ ] Plano de expansão: quais casos adicionar quando o agente for a produção

## Fontes
- https://www.anthropic.com/engineering/writing-tools-for-agents (seção de evaluation)
- https://www.anthropic.com/engineering/multi-agent-research-system (avaliação de agentes de pesquisa, LLM-juiz)
- Skill oficial skill-creator (loop de teste com baseline e revisão humana)
