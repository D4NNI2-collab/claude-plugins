# Deploy e produção — agentes rodando 24/7

> Guia operacional para colocar agentes standalone no ar (foco: VPS Ubuntu com PM2/systemd, bots de Telegram/WhatsApp, controle de custo). Engenharia padrão + práticas específicas de agentes.

## 1. Configuração e segredos

- Todo parâmetro em variáveis de ambiente: `ANTHROPIC_API_KEY`, tokens de bot, URLs de banco, flags de comportamento. Arquivo `.env` local (no `.gitignore`) + `.env.example` versionado.
- **Valide no boot**: o processo deve falhar imediatamente com mensagem clara se faltar variável obrigatória — não descobrir em runtime na primeira mensagem de cliente.
- Separe ambientes: `.env.dev` com chaves/bots de teste; nunca apontar o agente de desenvolvimento para dados de produção.

## 2. Rodando na VPS

### systemd (nativo, recomendado para serviços únicos)
```ini
# /etc/systemd/system/meu-agente.service
[Unit]
Description=Agente <nome>
After=network-online.target

[Service]
Type=simple
User=agente            # usuário SEM privilégios, dedicado
WorkingDirectory=/opt/meu-agente
EnvironmentFile=/opt/meu-agente/.env
ExecStart=/usr/bin/python3 -m app.main   # ou /usr/bin/node dist/main.js
Restart=on-failure
RestartSec=5
# Limites de proteção da VPS:
MemoryMax=1G
CPUQuota=80%

[Install]
WantedBy=multi-user.target
```
Comandos: `systemctl enable --now meu-agente`, logs com `journalctl -u meu-agente -f`.

### PM2 (prático para vários serviços Node/Python na mesma VPS)
```js
// ecosystem.config.cjs — use a extensão .cjs se o projeto for ESM
// ("type": "module" no package.json), senão o PM2 não lê o module.exports
module.exports = {
  apps: [{
    name: "meu-agente",
    script: "dist/main.js",          // ou script: "app/main.py", interpreter: "python3"
    // Atenção: o PM2 NÃO tem env_file — carregue o .env no boot do próprio app,
    // ou defina as variáveis no bloco env: {...} abaixo.
    cwd: __dirname,
    max_memory_restart: "800M",
    restart_delay: 5000,
    max_restarts: 10,
    time: true,                        // timestamps nos logs
  }]
}
```
Comandos: `pm2 start ecosystem.config.js`, `pm2 logs meu-agente`, `pm2 save && pm2 startup` (sobrevive a reboot).

Regra: um processo por agente; usuário de sistema dedicado sem sudo; firewall liberando só o necessário (ufw); HTTPS via reverse proxy (Caddy/Nginx) quando houver webhook.

## 3. Canais de entrada

### Telegram
- **Polling**: zero infra, ideal para protótipo e agentes internos. Limitação: um consumidor por token.
- **Webhook**: produção. Exige HTTPS público (Caddy resolve certificado sozinho). Valide o `secret_token` do webhook; responda o HTTP 200 RÁPIDO e processe o update em segundo plano (fila) — o Telegram reenvia updates não confirmados.
- Uma sessão/contexto por `chat_id`; comando `/reset` para o usuário limpar o contexto.

### WhatsApp
- Caminho oficial: WhatsApp Business Platform (Cloud API) — exige aprovação de templates para mensagens ativas; janela de 24h para respostas livres. Alternativa: provedores (Twilio, Z-API etc.) — avalie custo e termos.
- Mesmo padrão: webhook → 200 imediato → fila → worker.

### Padrão geral de processamento
```
update → validar assinatura → enfileirar → worker:
  carrega contexto do usuário (histórico curto + notas persistentes)
  → chama o agente (com max_turns e timeout)
  → envia resposta → persiste transcrição
```
Fila: em memória basta para volume baixo; Redis/BullMQ quando precisar de retry, concorrência controlada e sobrevivência a restart. Debounce de mensagens em rajada (usuário manda 4 mensagens seguidas → processar como uma).

## 4. Observabilidade

- **Logging estruturado (JSON)**: timestamp, `chat_id`/`task_id` (ID de correlação), etapa, tool chamada, tokens, latência, erro. Sem PII e sem segredos.
- **Transcrições completas persistidas** (banco ou arquivos por sessão): são seu material de debug E de avaliação contínua (`09-avaliacao-de-agentes.md`).
- Alertas mínimos: processo caiu (systemd/PM2 notificando), taxa de erro acima do normal, custo diário acima do teto. Um webhook para seu próprio Telegram já resolve o MVP de alerta.
- Métricas por dia: conversas, mensagens, tokens/custo, taxa de erro, latência p50/p95.

## 5. Controle de custo

1. **Modelo por etapa**: routing barato (Haiku classifica/filtra; modelo maior só quando necessário) — o padrão de maior alavancagem.
2. **Contexto enxuto**: histórico limitado por janela deslizante + notas persistentes em vez de conversa infinita; respostas de tool truncadas/filtradas (`02` e `03`).
3. **Prompt caching**: mantenha o system prompt e definições de tools estáveis no início do contexto para aproveitar cache entre chamadas.
4. **Limites duros**: `max_turns` por mensagem; teto de tokens por conversa; teto de custo diário com desligamento gracioso + alerta.
5. **Medir**: custo por conversa é métrica de produto. Registre tokens de entrada/saída por chamada e some por sessão.

## 6. Confiabilidade

- **Retry com backoff exponencial + jitter** para 429/5xx da API; respeitar `retry-after`.
- **Idempotência** em ações de efeito (criar pedido, enviar cobrança): chave de idempotência por operação; nunca reexecutar cegamente após timeout.
- **Dead-letter**: mensagem que falhou N vezes sai da fila para revisão humana, com alerta.
- **Degradação graciosa**: se a API de LLM está fora, o bot responde "estou instável, já volto" em vez de silêncio.
- **Backups**: transcrições, notas de memória e banco em backup diário; teste de restore.

## 7. Checklist de produção

- [ ] `.env` validado no boot; segredos fora do git; usuário sem privilégios
- [ ] Processo sob systemd/PM2 com restart, limites de memória e boot automático
- [ ] Webhook com HTTPS + validação de assinatura; 200 rápido + fila
- [ ] Logs estruturados + transcrições persistidas + alerta de queda/erro/custo
- [ ] `max_turns`, timeouts, retry/backoff, idempotência, dead-letter
- [ ] Teto de custo diário e métrica de custo por conversa
- [ ] Rodou 1 semana em modo piloto (grupo restrito) antes de abrir geral

## Fontes
- Padrões operacionais consolidados (systemd/PM2/Telegram Bot API/WhatsApp Cloud API — conferir docs oficiais de cada um na geração)
- https://www.anthropic.com/engineering/building-effective-agents (custo/latência e sandbox)
- https://platform.claude.com/docs (rate limits, prompt caching, context management)
