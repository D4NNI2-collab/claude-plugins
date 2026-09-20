# example-agent

Agente construído com o [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview):
o loop agêntico do Claude Code como biblioteca, com uma ferramenta de negócio
de exemplo (`orders_lookup`) registrada num servidor MCP in-process.

## Como rodar

Requisito: Python >= 3.10 (exigência do `claude-agent-sdk`).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencha as variáveis
```

```bash
.venv/bin/python agent.py "cadê meu pedido ORD-0001?"
.venv/bin/python agent.py    # modo interativo
.venv/bin/python telegram_bot.py    # bot do Telegram em polling # [telegram]
```

## Onde customizar

- **Comportamento**: `DEFAULT_SYSTEM_PROMPT` em `agent.py` — mantenha a estrutura
  (papel específico, passos numerados, formato de saída, condições de parada).
- **Ferramentas**: `tools.py` — troque `orders_lookup` pelas consultas do seu
  negócio e registre cada nova tool em `ALLOWED_TOOLS`.

## Custo estimado

Ordem de grandeza: com um modelo intermediário (Sonnet), uma execução simples
(1–2 chamadas de ferramenta) fica na faixa de US$ 0,01–0,10. Depende fortemente
do modelo escolhido, do tamanho do prompt e do número de turnos (`MAX_TURNS`).

## Deploy 24/7

Rode como serviço na VPS usando os arquivos de `infra/` deste projeto (systemd
ou PM2, com restart automático e limites de memória) — detalhes na referência
`references/10-deploy-e-producao.md` da skill agent-builder.
