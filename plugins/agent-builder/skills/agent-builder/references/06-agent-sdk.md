# Claude Agent SDK — agentes standalone (Python e TypeScript)

> **Validado contra a documentação oficial em 2026-09-19** (12 páginas `agent-sdk/*`; 4 correções aplicadas nessa data). ⚠️ **A API do SDK evolui rápido.** Este arquivo dá o mapa mental e os padrões; antes de gerar código, SEMPRE valide assinaturas atuais em https://code.claude.com/docs/llms.txt → páginas `agent-sdk/*` (overview, quickstart, subagents, custom tools, sessions, permissions). Gere código refletindo a doc de hoje, não a memória de treino.

## 1. O que é e quando usar

O Agent SDK é **o Claude Code como biblioteca**: o mesmo loop de agente, ferramentas integradas (ler/editar arquivos, executar comandos, buscar na web) e gerenciamento de contexto (compactação automática, cache), programável em Python e TypeScript. Foi renomeado de "Claude Code SDK" no fim de 2025.

**Use o Agent SDK quando** o agente é um serviço/programa próprio: bot de Telegram/WhatsApp, worker 24/7 na VPS, automação de CI/CD, agente SRE, assistente jurídico/financeiro, agente de suporte. **Use a Messages API pura quando** você quer controle total do loop ou o padrão é um workflow simples (chaining/routing) — muitos padrões cabem em poucas linhas sem SDK. **Use subagentes do Claude Code quando** a tarefa vive dentro de uma sessão de desenvolvimento (ver `05-subagentes-claude-code.md`).

## 2. Instalação e autenticação

- **TypeScript**: `npm install @anthropic-ai/claude-agent-sdk` (Node 18+).
- **Python**: `pip install claude-agent-sdk` ou `uv add claude-agent-sdk` (Python 3.10+).
- Ambos os pacotes embutem o binário nativo do Claude Code — a maioria das instalações dispensa o CLI separado. Exceções: npm pulando optional dependencies (`npm ci --omit=optional`) e Python sem wheel para a plataforma (ex.: ARM64 Windows) — nesses casos instale o Claude Code nativo (em TS, aponte `pathToClaudeCodeExecutable` se preciso).
- Chave via variável de ambiente `ANTHROPIC_API_KEY` (nunca hardcoded — ver `10-deploy-e-producao.md`). Suporta provedores terceiros (Bedrock, Vertex).

## 3. Conceitos centrais

- **`query()`**: ponto de entrada que cria o loop agêntico. Retorna um iterador assíncrono; você consome mensagens em stream enquanto o Claude pensa → chama ferramenta → observa → decide. 
- **`ClaudeAgentOptions`**: configuração do agente. Campos-chave (confirme nomes exatos na doc): `system_prompt`, `allowed_tools` (pré-aprova ferramentas, ex.: `["Read","Edit","Glob"]`), `permission_mode` (ex.: `acceptEdits` auto-aprova edições), `mcp_servers`, `agents` (subagentes programáticos), `max_turns`, `cwd`, `setting_sources` (omitido, carrega user/project/local como o CLI — CLAUDE.md, skills e settings do projeto já entram sem setar nada; passe `[]` para ISOLAR o agente em produção/CI/multi-tenant; exceção: com a opção `skills` definida, o default carrega só user e project).
- **Mensagens do stream**: raciocínio, chamadas de tool, resultados de tool e o resultado final — trate cada tipo (log, UI, persistência).

### Esqueleto mínimo (Python)
```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="Leia os arquivos deste diretório e resuma o projeto",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            system_prompt="Você é um analista técnico objetivo.",
            max_turns=15,
        ),
    ):
        print(message)  # em produção: tratar por tipo de mensagem

asyncio.run(main())
```

### Esqueleto mínimo (TypeScript)
```ts
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Leia os arquivos deste diretório e resuma o projeto",
  options: {
    allowedTools: ["Read", "Glob", "Grep"],
    systemPrompt: "Você é um analista técnico objetivo.",
    maxTurns: 15,
  },
})) {
  console.log(message);
}
```

## 4. Ferramentas customizadas (o coração do agente de negócio)

O SDK permite registrar ferramentas próprias como um **servidor MCP in-process** (sem processo externo): em Python via decorator de tool + criação de servidor SDK; em TS via `createSdkMcpServer`/`tool` com schema (zod). Cada tool: nome namespaced, descrição rica, schema de entrada estrito, resposta token-eficiente e erros acionáveis — aplique integralmente `02-design-de-ferramentas.md`. Também é possível plugar servidores MCP externos (stdio/http) via `mcp_servers`.

Exemplos de tools típicas de negócio: `crm_buscar_cliente`, `pedidos_resumo_do_dia`, `telegram_enviar_mensagem`, `planilha_registrar_linha`.

## 5. Subagentes programáticos

Defina no parâmetro `agents` (nome → descrição, prompt, tools, model). O Claude delega com base na `description`; os exemplos oficiais incluem a ferramenta de spawn (`Agent`) em `allowed_tools`, mas chamadas a `Agent` não pedem aprovação mesmo sem listá-la. Subagentes PODEM gerar subagentes próprios — por padrão até 3 níveis abaixo do agente principal (limite a profundidade com a env `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, `1` desliga o aninhamento; concorrência via `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, padrão 20). Definições programáticas têm precedência sobre arquivos `.claude/agents/` de mesmo nome. Use para o padrão orquestrador-workers (`01-principios-de-agentes.md` §4.4).

## 6. Sessões, permissões e hooks

- **Sessões**: o SDK gerencia sessão e permite retomar conversas; para estado de longo prazo entre execuções, combine com note-taking em arquivos/banco (`03-engenharia-de-contexto.md` §6.2).
- **Permissões**: além de `permission_mode`, há callback de autorização por chamada de ferramenta (human-in-the-loop programático) — use para ações destrutivas/dinheiro.
- **Hooks**: pontos de intercepção (pré/pós ferramenta etc.) para validação, logging e políticas — mesmo espírito dos hooks de subagente.

## 7. Arquitetura de referência: bot 24/7 (Telegram → agente → resposta)

```
[Telegram] --webhook--> [servidor HTTP (FastAPI/Express)]
                              |  valida + enfileira update
                              v
                        [fila em memória/Redis]
                              |
                              v
                 [worker: monta contexto do usuário
                  (histórico curto + notas persistentes)]
                              |
                              v
                 [query() com system prompt + tools de negócio]
                              |
                    stream de mensagens → logs/transcrição
                              |
                              v
                 [resposta final → sendMessage no Telegram]
```

Decisões: webhook (produção, exige HTTPS) vs polling (protótipo, zero infra); uma conversa = uma sessão/contexto por chat_id; persistir transcrições para debug e avaliação; timeout + `max_turns` por mensagem; tratar 429/5xx com retry exponencial. Deploy e operação: `10-deploy-e-producao.md`.

## 8. Checklist de geração de um agente SDK

- [ ] Doc atual consultada; assinaturas confirmadas antes de escrever código
- [ ] Estrutura de projeto: `agent.(py|ts)`, `tools.(py|ts)`, `.env.example`, `README.md` com como rodar
- [ ] System prompt pelo template de `04-prompts-de-sistema-para-agentes.md`
- [ ] Tools seguindo `02-design-de-ferramentas.md` (consolidação, erros acionáveis, token-eficiência)
- [ ] `max_turns`, timeout e tratamento de erro de API implementados
- [ ] Permissões: nenhuma ação destrutiva sem gate (callback/confirmação)
- [ ] Logging estruturado das mensagens do stream
- [ ] Rodou localmente com um caso de teste real antes de entregar

## Fontes
- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/agent-sdk/quickstart
- https://code.claude.com/docs/en/agent-sdk/subagents
- https://www.anthropic.com/engineering/building-effective-agents (quando usar SDK vs API direta)
