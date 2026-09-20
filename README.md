# d4nni2-plugins

Marketplace de plugins do Claude Code. Por enquanto, um plugin:

## agent-builder

Skill que cria agentes de IA e skills de ponta a ponta seguindo as práticas de engenharia da Anthropic — subagentes do Claude Code, agentes standalone com o Claude Agent SDK (Python/TypeScript), bots de Telegram/WhatsApp e deploy 24/7. Inclui 10 referências técnicas (validadas contra a doc oficial em 2026-09-19), templates de projeto prontos e um scaffold (`scaffold.py`).

### Instalar

Dentro de uma sessão do Claude Code:

```
/plugin marketplace add D4NNI2-collab/claude-plugins
/plugin install agent-builder@d4nni2-plugins
```

Ou pelo terminal:

```bash
claude plugin marketplace add D4NNI2-collab/claude-plugins
claude plugin install agent-builder@d4nni2-plugins
```

Depois de instalar, basta pedir naturalmente — "cria um bot de telegram que responde meus clientes", "quero um subagente que roda os testes" — que a skill aciona sozinha.

### Atualizar

```bash
claude plugin update agent-builder
```

### Manutenção (para quem mantém este repo)

As referências 05 (subagentes) e 06 (Agent SDK) envelhecem rápido: revalide-as contra https://code.claude.com/docs/llms.txt a cada ~2 meses e atualize a data no topo de cada arquivo. As demais referências são princípios estáveis.

### Estrutura

```
.claude-plugin/marketplace.json      ← catálogo do marketplace
plugins/agent-builder/
├── .claude-plugin/plugin.json       ← manifest do plugin
└── skills/agent-builder/            ← a skill (SKILL.md + references + templates + scaffold)
```
