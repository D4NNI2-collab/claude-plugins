# example-agent

Agente construído com o Claude Agent SDK (TypeScript), com padrão de produção: núcleo do agente separado dos canais de entrada e ferramentas de negócio como servidor MCP in-process.

## Rodar

Requisito: Node >= 20.12 (o boot usa `process.loadEnvFile`).

```bash
cp .env.example .env    # preencha as variáveis
npm install
npm run dev -- "Qual o status do pedido ORD-1001?"
npm run telegram        # bot do Telegram em long polling # [telegram]
```

Produção: `npm run build && npm start` — ou rode sob systemd/PM2 (ver Deploy).

## Customizar

- `src/agent.ts` — system prompt (`DEFAULT_SYSTEM_PROMPT`), `maxTurns` e opções do loop.
- `src/tools.ts` — troque a ferramenta de exemplo (`orders_lookup`) pelas tools do seu negócio; registre cada uma em `allowedTools` como `mcp__example_agent__<tool>`.
- `src/telegram.ts` — canal do Telegram; para produção, migre de polling para webhook + fila. # [telegram]

## Custo

Cada mensagem dispara um loop agêntico (várias chamadas ao modelo). Controle: `maxTurns` baixo, respostas de tool enxutas e teto de custo diário. Registre tokens por conversa — custo por conversa é métrica de produto.

## Deploy

O diretório `infra/` traz unit do systemd e `ecosystem.config.cjs` do PM2 prontos para VPS (`.cjs` porque este projeto é ESM). Guia completo (segredos, observabilidade, confiabilidade): `references/10-deploy-e-producao.md` da skill agent-builder.
