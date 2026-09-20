"""Núcleo do example-agent (Claude Agent SDK).

Ponto único da lógica do agente: qualquer canal (CLI abaixo, Telegram em
telegram_bot.py) chama run_agent() e recebe o texto final da resposta.
Customize o comportamento em DEFAULT_SYSTEM_PROMPT e as ferramentas em tools.py.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from tools import ALLOWED_TOOLS, SERVER_NAME, server

logger = logging.getLogger("example_agent")

# Limite duro de iterações por execução — proteção contra loop e custo.
MAX_TURNS = 10
# Teto de tempo (segundos) por mensagem — protege o canal de travar se a API
# demorar (referência 10 da skill agent-builder, §5-6).
REQUEST_TIMEOUT_S = 120


def _load_env_file() -> None:
    """Carrega o .env ao lado deste arquivo, sem sobrescrever o ambiente.

    Loader mínimo para dispensar dependência extra; em produção prefira
    variáveis já exportadas ou o EnvironmentFile= do systemd (ver infra/).
    """
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _validate_env() -> None:
    """Falha imediatamente no boot se faltar variável obrigatória."""
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        print(
            "erro: a variável de ambiente ANTHROPIC_API_KEY não está definida.\n"
            "Copie .env.example para .env e preencha a chave "
            "(https://platform.claude.com), ou exporte-a no ambiente.",
            file=sys.stderr,
        )
        raise SystemExit(1)


_env_ready = False


def ensure_env() -> None:
    """Carrega o .env e valida as variáveis obrigatórias (idempotente).

    Chamada no boot de cada canal e em run_agent() — e não no import,
    para que testes e tooling importem o módulo sem precisar de credenciais.
    """
    global _env_ready
    if _env_ready:
        return
    _load_env_file()
    _validate_env()
    _env_ready = True

# System prompt padrão — troque pelo do SEU agente mantendo a estrutura:
# papel específico, passos numerados, formato de saída, condições de parada.
DEFAULT_SYSTEM_PROMPT = """\
Você é um atendente sênior de suporte a pedidos. Sua missão é responder \
clientes sobre o andamento de pedidos com precisão, sempre a partir dos \
dados reais do sistema.

Quando invocado:
1. Identifique o ID do pedido na mensagem (formato ORD-NNNN); se não houver, peça-o.
2. Consulte o pedido com a ferramenta orders_lookup — nunca responda de memória.
3. Responda usando somente o que a ferramenta retornou.

Formato de saída:
- Resposta curta em pt-BR, citando ID, status e total quando relevante.

Erros e limites:
- Pedido inexistente: informe o cliente e peça para confirmar o ID.
- Se a ferramenta falhar 2 vezes seguidas, pare e oriente a tentar mais tarde.
- Nunca invente dados de pedido.
"""


async def run_agent(user_message: str) -> str:
    """Executa uma rodada completa do agente e retorna o texto final."""
    ensure_env()
    options = ClaudeAgentOptions(
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        mcp_servers={SERVER_NAME: server},
        allowed_tools=ALLOWED_TOOLS,
        max_turns=MAX_TURNS,
        # Isola o agente de settings/CLAUDE.md da máquina — comportamento
        # reprodutível em produção (referência 06 da skill agent-builder, §3).
        # Remova para carregar a configuração .claude/ local do projeto.
        setting_sources=[],
    )
    final_text = ""
    fallback: list[str] = []

    async def _consume() -> None:
        nonlocal final_text
        async for message in query(prompt=user_message, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        # Log curto por chamada de ferramenta — observabilidade mínima.
                        logger.info("tool call: %s %s", block.name, block.input)
                    elif isinstance(block, TextBlock):
                        fallback.append(block.text)
            elif isinstance(message, ResultMessage):
                if message.subtype == "success" and message.result:
                    final_text = message.result
                else:
                    logger.warning("execução terminou sem sucesso: %s", message.subtype)

    try:
        await asyncio.wait_for(_consume(), timeout=REQUEST_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning("execução excedeu %ss; devolvendo contingência", REQUEST_TIMEOUT_S)
    return (
        final_text
        or "\n".join(fallback).strip()
        or "Não consegui gerar uma resposta agora; tente reformular a pergunta."
    )


def main() -> None:
    """CLI de teste local: pergunta única via argumentos ou loop interativo."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    ensure_env()
    if len(sys.argv) > 1:
        print(asyncio.run(run_agent(" ".join(sys.argv[1:]))))
        return
    print("example-agent — modo interativo ('sair' ou Ctrl+C para encerrar)")
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not question:
            continue
        if question.lower() in {"sair", "exit", "quit"}:
            return
        print(asyncio.run(run_agent(question)))


if __name__ == "__main__":
    main()
