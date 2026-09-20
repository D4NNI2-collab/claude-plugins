// Adaptador de canal: Telegram via grammy, em long polling.
// Polling: zero infra, ideal para protótipo e bots internos (um consumidor
// por token). Extensões de produção — referência 10 da skill agent-builder, §3:
// - webhook + fila: HTTPS público (Caddy), validar secret_token, responder
//   200 rápido e processar o update em background;
// - uma sessão/contexto por chat_id (histórico curto + notas persistentes),
//   com comando /reset — referência 03 da skill, §6;
// - autorização: vincule chat_id ao cliente antes de expor dados de pedido
//   (qualquer pessoa pode falar com um bot público) — referência 08 da skill.

import { Bot } from "grammy";
import { ensureEnv, runAgent } from "./agent.js";

// Validação no boot, antes de aceitar a primeira mensagem.
ensureEnv(); // ANTHROPIC_API_KEY (e carrega o .env)
const token = process.env.TELEGRAM_BOT_TOKEN;
if (!token) {
  console.error(
    "erro: TELEGRAM_BOT_TOKEN não definida. Crie o bot com o @BotFather e preencha o .env."
  );
  process.exit(1);
}

const bot = new Bot(token);

bot.on("message:text", async (ctx) => {
  const chatId = ctx.chat.id;
  console.error(`[telegram] mensagem recebida do chat ${chatId}`);
  try {
    // Cada mensagem vira uma execução independente do agente; para manter
    // contexto entre mensagens, carregue histórico por chat_id aqui.
    const answer = await runAgent(ctx.message.text);
    await ctx.reply(answer);
  } catch (error) {
    // Degradação graciosa: o cliente recebe um aviso, não silêncio.
    console.error(
      `[telegram] erro no chat ${chatId}:`,
      error instanceof Error ? error.message : error
    );
    await ctx.reply("Estou instável neste momento — tente de novo em instantes.");
  }
});

console.error("[telegram] bot iniciado em long polling; Ctrl+C para parar.");
void bot.start();
