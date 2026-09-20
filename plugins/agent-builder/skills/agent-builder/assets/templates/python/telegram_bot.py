"""Canal Telegram do example-agent (polling, para protótipo e uso interno).

Adaptador fino: recebe a mensagem, chama run_agent() de agent.py e responde.
Extensões de produção (não implementadas aqui de propósito):
- webhook HTTPS + resposta 200 imediata + fila — referência 10 da skill agent-builder, §3
- contexto/histórico por chat_id e comando /reset — referência 03 da skill
- autorização: em produção, vincule chat_id ao cliente antes de expor dados de
  pedido (qualquer pessoa pode falar com um bot público) — referência 08 da skill
"""

import logging
import os
import sys

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from agent import ensure_env, run_agent

logger = logging.getLogger("example_agent.telegram")


def _require_token() -> str:
    """Falha imediatamente no boot se o token do bot não estiver definido."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print(
            "erro: a variável de ambiente TELEGRAM_BOT_TOKEN não está definida.\n"
            "Crie um bot com o @BotFather no Telegram e coloque o token no .env.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return token


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata cada mensagem de texto como uma rodada isolada do agente.

    Sem histórico de propósito: para contexto por chat_id (e /reset), ver
    references/03 e 10 da skill agent-builder.
    """
    if update.message is None or not update.message.text:
        return
    chat_id = update.effective_chat.id if update.effective_chat else "?"
    logger.info("mensagem recebida (chat_id=%s)", chat_id)
    try:
        answer = await run_agent(update.message.text)
    except Exception:
        # Degradação graciosa: o bot responde em vez de silenciar.
        logger.exception("falha ao executar o agente (chat_id=%s)", chat_id)
        answer = "Estou instável agora; tente novamente em alguns instantes."
    # Telegram limita mensagens a 4096 caracteres.
    await update.message.reply_text(answer[:4096])


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    ensure_env()  # valida ANTHROPIC_API_KEY antes de aceitar mensagens
    token = _require_token()
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Polling: zero infra, um consumidor por token. Em produção, migre para
    # webhook + fila (references/10-deploy-e-producao.md §3).
    logger.info("bot no ar (polling); Ctrl+C para parar")
    app.run_polling()


if __name__ == "__main__":
    main()
