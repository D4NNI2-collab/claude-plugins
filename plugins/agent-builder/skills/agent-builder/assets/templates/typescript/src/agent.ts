// example-agent — núcleo do agente (Claude Agent SDK).
// Canais de entrada (CLI aqui embaixo, Telegram em telegram.ts) chamam
// runAgent(); a lógica do agente vive num lugar só.

import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { query } from "@anthropic-ai/claude-agent-sdk";
import { toolsServer } from "./tools.js";

// Teto de tempo por mensagem — protege o canal de travar se a API demorar
// (referência 10 da skill agent-builder, §5-6).
const REQUEST_TIMEOUT_MS = 120_000;

let envReady = false;

/**
 * Carrega o .env da raiz do projeto (um nível acima de src/ e de dist/,
 * então funciona em dev e no build, independente do cwd) e valida as
 * variáveis obrigatórias. Chamada no boot de cada canal e em runAgent() —
 * e não no import, para que testes importem o módulo sem credenciais.
 * Sob systemd as variáveis já vêm do EnvironmentFile= (ver infra/).
 * Requer Node >= 20.12 (loadEnvFile).
 */
export function ensureEnv(): void {
  if (envReady) return;
  const envPath = fileURLToPath(new URL("../.env", import.meta.url));
  if (existsSync(envPath)) {
    process.loadEnvFile(envPath);
  }
  // Falhar agora, com mensagem clara, é melhor do que descobrir a falta
  // da chave na primeira mensagem de um cliente.
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error(
      "erro: ANTHROPIC_API_KEY não definida. Copie .env.example para .env e preencha a chave."
    );
    process.exit(1);
  }
  envReady = true;
}

// System prompt seguindo a referência 04 da skill agent-builder:
// papel específico, passos numerados, formato de saída e condições de parada.
// Adapte ao seu negócio — este é o principal ponto de customização.
const DEFAULT_SYSTEM_PROMPT = `Você é o atendente virtual de uma loja, especializado em consultas de pedidos.
Sua missão: responder clientes com dados corretos, em mensagens curtas.

Quando receber uma mensagem:
1. Identifique o que o cliente quer; se faltar o número do pedido, peça-o antes de qualquer consulta.
2. Consulte a ferramenta de pedidos — nunca afirme status, valor ou prazo de memória.
3. Responda em português, direto ao ponto.

Formato de saída: texto simples, sem markdown, no máximo 4 frases.

Erros e limites:
- Pedido não encontrado: informe o cliente e peça para conferir o número (formato ORD-NNNN).
- Fora do escopo (troca, reembolso, reclamação): diga que vai encaminhar a um atendente humano e encerre.
- Nunca invente dados de pedido nem prometa prazos que a ferramenta não retornou.`;

/**
 * Executa uma rodada completa do agente para uma mensagem de usuário e
 * retorna o texto final. Lança Error se o loop terminar sem resposta
 * (ex.: estourou maxTurns) — o canal decide como degradar graciosamente.
 */
export async function runAgent(userMessage: string): Promise<string> {
  ensureEnv();
  // Teto de tempo: aborta o loop se a mensagem demorar demais.
  const abortController = new AbortController();
  const timer = setTimeout(() => abortController.abort(), REQUEST_TIMEOUT_MS);
  try {
    for await (const message of query({
      prompt: userMessage,
      options: {
        systemPrompt: DEFAULT_SYSTEM_PROMPT,
        // O servidor in-process de tools.ts; a chave vira o prefixo dos nomes
        // das tools: mcp__example_agent__<tool>.
        mcpServers: { example_agent: toolsServer },
        // Pré-aprova só as tools do negócio (nome completo namespaced).
        allowedTools: ["mcp__example_agent__orders_lookup"],
        // Limite duro por mensagem: proteção de custo e de loop infinito.
        maxTurns: 10,
        abortController,
        // Isola o agente de settings/CLAUDE.md da máquina — comportamento
        // reprodutível em produção (referência 06 da skill agent-builder, §3).
        settingSources: [],
      },
    })) {
      if (message.type === "assistant") {
        // Log das chamadas de tool no stderr — observabilidade mínima.
        for (const block of message.message.content) {
          if (block.type === "tool_use") {
            console.error(`[agente] tool chamada: ${block.name}`);
          }
        }
      } else if (message.type === "result") {
        if (message.subtype === "success") {
          return message.result;
        }
        throw new Error(
          `o agente terminou sem resposta (${message.subtype}) — considere aumentar maxTurns ou revisar o prompt`
        );
      }
    }
    throw new Error("o stream terminou sem mensagem de resultado");
  } finally {
    clearTimeout(timer);
  }
}

// CLI mínima quando executado diretamente (npm run dev -- "sua pergunta").
const isMain =
  process.argv[1] !== undefined &&
  import.meta.url === pathToFileURL(process.argv[1]).href;

if (isMain) {
  const userMessage =
    process.argv.slice(2).join(" ").trim() ||
    "Qual o status do pedido ORD-1001?";
  try {
    console.error(`[agente] pergunta: ${userMessage}`);
    console.log(await runAgent(userMessage));
  } catch (error) {
    console.error(
      "erro ao executar o agente:",
      error instanceof Error ? error.message : error
    );
    process.exit(1);
  }
}
