# Criação de skills — autoria de alto nível

> Base: docs oficiais de Agent Skills + guia "Skill authoring best practices" (platform.claude.com) + a skill oficial skill-creator da Anthropic. Use este arquivo quando o pedido for gerar uma SKILL (inclusive skills que acompanham um agente).

## 1. Anatomia e progressive disclosure

```
minha-skill/
├── SKILL.md            # obrigatório: frontmatter YAML + instruções
├── scripts/            # código executável (CLIs pequenos e determinísticos)
├── references/         # documentação carregada sob demanda
└── assets/             # templates, imagens, fontes usados NA SAÍDA (não entram no contexto)
```

Três níveis de carregamento — a razão de skills escalarem sem poluir contexto:

| Nível | Quando carrega | Custo |
|---|---|---|
| Metadata (name + description) | Sempre, no startup | ~100 tokens por skill |
| Corpo do SKILL.md | Quando a skill é acionada | Ideal < 500 linhas |
| references/scripts/assets | Sob demanda | Sem limite prático — arquivo não consome contexto até ser lido; script executado consome só a SAÍDA |

Consequências práticas: SKILL.md é um **roteador**, não uma enciclopédia; conhecimento pesado vai para `references/` com ponteiros claros de quando ler cada um; lógica determinística e repetitiva vira `scripts/` (mais barato e confiável que o modelo regenerar código toda vez); arquivos de referência com mais de ~300 linhas ganham sumário no topo.

**Organização por domínio**: quando a skill cobre variantes (ex.: subagente vs SDK Python vs SDK TS), um arquivo de referência por variante — o Claude lê só o relevante.

## 2. Frontmatter — regras formais

- `name`: máx. 64 caracteres; só minúsculas, números e hífens; sem tags XML; não pode conter as palavras reservadas "anthropic" ou "claude".
- `description`: obrigatória; máx. 1024 caracteres; sem tags XML; **em terceira pessoa**.

## 3. A description é o campo mais importante

É o ÚNICO conteúdo que o Claude vê antes de decidir carregar a skill — ela define o acionamento entre potencialmente dezenas de skills. Fórmula: **O QUE a skill faz + QUANDO usar + frases-gatilho que o usuário realmente diria**.

- O Claude tende a **subacionar** (undertrigger) skills; compense com descriptions "empurradas": liste explicitamente contextos e sinônimos ("use sempre que o usuário mencionar X, Y ou Z, mesmo sem pedir a skill pelo nome").
- Nuance: o Claude só consulta skills para tarefas que não resolve trivialmente sozinho — pedidos de um passo podem não acionar mesmo com description perfeita. Teste com tarefas substantivas.

Ruim: `Ajuda com processamento de documentos.`
Bom: `Extrai texto e tabelas de PDFs, preenche formulários e mescla documentos. Use sempre que o usuário mencionar PDF, formulário, extração de tabela ou anexar um arquivo .pdf — mesmo que não peça "processamento" explicitamente.`

## 4. Princípios de escrita do corpo

1. **Conciso é rei.** A janela de contexto é um bem público: sua skill divide espaço com system prompt, histórico, metadata das outras skills e o pedido em si. Cada token precisa se pagar.
2. **Assuma que o Claude já é muito inteligente.** Só adicione o contexto que ele NÃO tem: convenções internas, restrições do ambiente, formatos específicos, armadilhas conhecidas. Não explique o que é um PDF nem como programar.
3. **Graus de liberdade calibrados.** Tarefa aberta/criativa → instruções de alto nível e princípios (liberdade alta). Operação frágil/exata (ordem de passos crítica, formato binário) → passos numerados estritos com checklist (liberdade baixa).
4. **Explique o porquê, não grite MUSTs.** Modelos seguem melhor instruções cujo racional entendem; SEMPRE/NUNCA em caps lock e estruturas rígidas são sinal amarelo — prefira transmitir o entendimento da tarefa.
5. **Workflows com checklist** para tarefas multi-etapa: passos numerados que o modelo consegue acompanhar e verificar.
6. **Imperativo + exemplos.** Um padrão de exemplo (Entrada → Saída) vale mais que parágrafos de descrição. Formatos de saída: mostre o template exato.
7. **Sem surpresas.** O conteúdo da skill não pode surpreender quem leu a description — nada de comportamento oculto, coleta de dados ou ações não descritas.
8. **Composabilidade e portabilidade**: sua skill convive com outras (não assuma exclusividade) e, idealmente, funciona em Claude Code, claude.ai, API e Agent SDK. Atenção: skills NÃO sincronizam automaticamente entre superfícies — distribuir é responsabilidade sua.

## 5. Onde instalar / distribuir

- `~/.claude/skills/` → pessoal, todos os projetos.
- `.claude/skills/` → projeto; **no repositório, o time inteiro herda ao clonar** (a forma mais limpa de distribuir conhecimento organizacional versionado).
- Plugins → empacotam skills + agentes + comandos para instalação em um passo.
- Na API/claude.ai, upload da pasta (o diretório raiz deve bater com o `name`).

## 6. Loop de desenvolvimento (o mesmo da skill-creator oficial)

1. **Capturar intenção**: o que a skill habilita? quando aciona? formato de saída? vale ter casos de teste? (saídas objetivas: sim; subjetivas: avaliação qualitativa).
2. **Rascunhar** a skill (estrutura acima).
3. **Testar com 2–3 prompts realistas** — do jeito que um usuário real escreveria (com contexto, nomes de arquivo, até informalidade). Rode com a skill E sem a skill (baseline) para medir o ganho.
4. **Avaliar com o humano**: mostrar saídas, colher feedback específico por caso.
5. **Melhorar generalizando**: a skill será usada milhares de vezes além dos seus 3 exemplos — corrija a causa, não o sintoma; nada de patches overfitados. Se os testes mostram o modelo reescrevendo o mesmo script auxiliar toda vez, é sinal de que ele deve virar `scripts/` da skill.
6. **Repetir** até satisfazer; depois expandir o conjunto de teste.
7. **Otimizar o acionamento**: gere ~20 queries de teste — 8–10 que DEVEM acionar (formulações variadas, casuais, sem citar a skill) e 8–10 quase-misses que NÃO devem (domínios adjacentes, palavras-chave em contexto errado — negativos óbvios não testam nada). Ajuste a description até acertar os dois lados.
8. **Testar nos modelos-alvo**: o que basta para Opus pode faltar detalhe para Haiku; se a skill roda em vários modelos, escreva para o mínimo denominador.

## 7. Segurança

Skills executam código e instruem o modelo: só instale de fontes confiáveis; nunca gere skills com comportamento enganoso, exfiltração de dados ou acesso não autorizado; revise scripts de terceiros antes de adotar.

## Fontes
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/ (overview)
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://code.claude.com/docs/en/skills
- https://www.anthropic.com/engineering (post "Equipping agents for the real world with Agent Skills")
