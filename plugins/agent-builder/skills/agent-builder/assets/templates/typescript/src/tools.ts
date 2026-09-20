// Ferramentas de negócio do agente — aqui entram as tools que conectam o
// agente aos seus sistemas (CRM, banco de dados, planilhas, APIs internas).
//
// Padrões desta camada (referência 02 da skill agent-builder):
// - poucas ferramentas, cada uma cobrindo um fluxo real de trabalho;
// - descrição rica: o modelo só sabe o que está escrito nela;
// - parâmetros inequívocos, impostos por schema estrito (zod);
// - resposta token-eficiente (sinal alto, nada de despejar objetos crus);
// - erros escritos como prompts acionáveis, que ensinam o agente a se corrigir.

import { tool, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

// Registro local simulado — substitua pela consulta real ao seu sistema
// (banco de dados, API do e-commerce, ERP). Mantém o template executável.
interface OrderRecord {
  customerName: string;
  status: string;
  items: string[];
  totalBRL: number;
  estimatedDelivery: string; // YYYY-MM-DD
}

const ORDERS: Record<string, OrderRecord> = {
  "ORD-1001": {
    customerName: "Maria Souza",
    status: "em transporte",
    items: ["Cadeira ergonômica", "Apoio de pés"],
    totalBRL: 1249.9,
    estimatedDelivery: "2026-09-24",
  },
  "ORD-1002": {
    customerName: "João Lima",
    status: "aguardando pagamento",
    items: ["Mesa dobrável"],
    totalBRL: 389.0,
    estimatedDelivery: "2026-09-30",
  },
};

const ordersLookup = tool(
  "orders_lookup",
  "Consulta um pedido pelo número e retorna cliente, status atual, itens, " +
    "valor total e previsão de entrega. Use sempre que o cliente perguntar " +
    "sobre um pedido específico — nunca responda dados de pedido de memória. " +
    "Exemplo de uso: order_id=\"ORD-1001\". Se o cliente não informou o " +
    "número do pedido, peça o número antes de chamar esta ferramenta.",
  {
    order_id: z
      .string()
      .regex(/^ORD-\d{4}$/, "formato esperado: ORD-NNNN (ex.: ORD-1001)")
      .describe("Número do pedido no formato ORD-NNNN, ex.: ORD-1001"),
  },
  async (args) => {
    const order = ORDERS[args.order_id];
    if (!order) {
      // Erro como prompt: diz o que houve e qual é a próxima ação útil.
      return {
        content: [
          {
            type: "text" as const,
            text:
              `Pedido ${args.order_id} não encontrado. Confirme o número com o ` +
              `cliente (formato ORD-NNNN, impresso no e-mail de confirmação) e ` +
              `tente de novo; se o cliente insistir que o número está certo, ` +
              `encaminhe para um atendente humano.`,
          },
        ],
        isError: true,
      };
    }

    // Resposta compacta, só sinal alto — nomes legíveis em vez de IDs crípticos.
    // Em produção, restrinja o que expõe: o chamador é quem conversa com o
    // bot, não necessariamente o dono do pedido (autorização por chat_id —
    // referência 08 da skill agent-builder).
    return {
      content: [
        {
          type: "text" as const,
          text:
            `Pedido ${args.order_id} — cliente: ${order.customerName}; ` +
            `status: ${order.status}; itens: ${order.items.join(", ")}; ` +
            `total: R$ ${order.totalBRL.toFixed(2).replace(".", ",")}; ` +
            `previsão de entrega: ${order.estimatedDelivery}.`,
        },
      ],
    };
  },
  // Somente leitura: permite ao modelo paralelizar com outras tools de leitura.
  { annotations: { readOnlyHint: true } }
);

// Servidor MCP in-process: roda dentro do próprio processo, sem infra extra.
// Adicione novas tools ao array `tools` e libere-as em allowedTools no agent.ts
// com o nome completo mcp__example_agent__<nome_da_tool>.
export const toolsServer = createSdkMcpServer({
  name: "example_agent",
  version: "1.0.0",
  tools: [ordersLookup],
});
