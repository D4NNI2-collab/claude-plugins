"""Ferramentas de negócio do example-agent (servidor MCP in-process).

É AQUI que você pluga as ferramentas do SEU negócio: troque orders_lookup
por consultas reais (banco, API interna, planilha), mantendo o padrão —
descrição rica, schema estrito, resposta token-eficiente e erro acionável.
"""

from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

# Nome do servidor: vira o prefixo namespaced das ferramentas
# (mcp__<servidor>__<ferramenta>) usado em allowed_tools.
SERVER_NAME = "example_agent"

# Base local simulada — substitua pela consulta ao seu sistema real.
_ORDERS: dict[str, dict[str, Any]] = {
    "ORD-0001": {
        "customer": "Ana Souza",
        "status": "em transporte",
        "items": [{"qty": 2, "name": "Camiseta básica preta"}],
        "total": 119.80,
        "updated_at": "2026-09-18",
    },
    "ORD-0002": {
        "customer": "Bruno Lima",
        "status": "aguardando pagamento",
        "items": [{"qty": 1, "name": "Tênis de corrida 42"}],
        "total": 349.90,
        "updated_at": "2026-09-19",
    },
    "ORD-0003": {
        "customer": "Carla Menezes",
        "status": "entregue",
        "items": [
            {"qty": 1, "name": "Mochila 20L"},
            {"qty": 3, "name": "Meia esportiva"},
        ],
        "total": 287.50,
        "updated_at": "2026-09-15",
    },
}


@tool(
    "orders_lookup",
    "Busca UM pedido pelo ID exato e retorna cliente, status, itens, total e "
    "data da última atualização. Use quando o usuário perguntar sobre um pedido "
    "específico (ex.: 'cadê meu pedido ORD-0002?'). IDs têm o formato ORD-NNNN. "
    "Não serve para listar pedidos nem para buscar por nome de cliente.",
    {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "ID do pedido no formato ORD-NNNN (ex.: 'ORD-0001').",
                "pattern": "^ORD-[0-9]{4}$",
            },
        },
        "required": ["order_id"],
        "additionalProperties": False,
    },
)
async def orders_lookup(args: dict[str, Any]) -> dict[str, Any]:
    order_id = str(args["order_id"]).strip().upper()
    order = _ORDERS.get(order_id)
    if order is None:
        # Erro acionável, escrito como prompt: diz o formato e o próximo passo.
        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Pedido '{order_id}' não encontrado; IDs válidos têm "
                        "formato ORD-NNNN (ex.: ORD-0001). Confirme o número com "
                        "o cliente antes de tentar novamente."
                    ),
                }
            ],
            "is_error": True,
        }
    # Resposta token-eficiente: uma linha, só sinal alto.
    # Em produção, restrinja o que expõe: o chamador é quem conversa com o
    # bot, não necessariamente o dono do pedido (autorização por chat_id —
    # referência 08 da skill agent-builder).
    items = "; ".join(f"{item['qty']}x {item['name']}" for item in order["items"])
    total_brl = f"{order['total']:.2f}".replace(".", ",")
    text = (
        f"{order_id} | cliente: {order['customer']} | status: {order['status']} | "
        f"itens: {items} | total: R$ {total_brl} | "
        f"atualizado em: {order['updated_at']}"
    )
    return {"content": [{"type": "text", "text": text}]}


# Servidor MCP in-process: roda dentro do seu processo, sem binário externo.
server = create_sdk_mcp_server(name=SERVER_NAME, version="1.0.0", tools=[orders_lookup])

# Nomes namespaced pré-aprovados — registre aqui cada nova ferramenta.
ALLOWED_TOOLS = [f"mcp__{SERVER_NAME}__orders_lookup"]
