#!/usr/bin/env python3
"""Gera a estrutura de um projeto de agente a partir de assets/templates/.

Uso:
    python3 scaffold.py <nome> --lang python|typescript [--channel cli|telegram] [--dest DIR]

Exemplos:
    python3 scaffold.py suporte-bot --lang python --channel telegram
    python3 scaffold.py doc-writer --lang typescript --channel cli --dest ~/projetos

O nome deve ser kebab-case (ex.: meu-agente). Os templates usam o nome
literal "example-agent"; este script substitui todas as variantes de casing
(example-agent, example_agent, ExampleAgent) pelo nome escolhido.

Convenções dos templates que este script aplica:
- Arquivos exclusivos do canal Telegram: python/telegram_bot.py e
  typescript/src/telegram.ts — só entram com --channel telegram.
- Marcadores de linha em QUALQUER arquivo de texto do template: uma linha
  terminada em um ou mais marcadores "# [tag]" / "// [tag]", com tag em
  {telegram, cli, python, typescript, template}, é mantida (sem os
  marcadores) quando TODAS as tags estão ativas — o canal e a linguagem
  escolhidos — e removida quando alguma não está. Ex.: "# [telegram]" em
  .env.example/requirements.txt/README; "# [python] # [telegram]" nas linhas
  de ExecStart/script de infra/ (linguagem E canal). A tag "template" nunca
  está ativa: marca linhas que existem só no template (notas de autoria).
- typescript/telegram.deps: manifesto (um nome de dependência por linha) das
  dependências do package.json que pertencem ao canal Telegram; removidas do
  package.json com --channel cli, junto com o script "telegram". O manifesto
  nunca é copiado para a saída.
- infra/ é sempre copiada, com o unit do systemd renomeado para <nome>.service.
"""

import argparse
import json
import re
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"
MARKER_RE = re.compile(r"\s*(?:#|//)\s*\[(telegram|cli|python|typescript|template)\]\s*$")
TELEGRAM_ONLY_FILES = {
    "python": ["telegram_bot.py"],
    "typescript": ["src/telegram.ts"],
}
TELEGRAM_DEPS_MANIFEST = "telegram.deps"
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def name_variants(kebab: str) -> dict:
    snake = kebab.replace("-", "_")
    pascal = "".join(part.capitalize() for part in kebab.split("-"))
    return {"example-agent": kebab, "example_agent": snake, "ExampleAgent": pascal}


def substitute(text: str, variants: dict) -> str:
    for token, value in variants.items():
        text = text.replace(token, value)
    return text


def process_line_markers(text: str, active_tags: set) -> str:
    """Mantém (sem os marcadores) linhas cujas tags estão TODAS ativas."""
    lines = []
    for line in text.splitlines():
        tags = []
        match = MARKER_RE.search(line)
        while match:
            tags.append(match.group(1))
            line = line[: match.start()].rstrip()
            match = MARKER_RE.search(line)
        if tags and not all(tag in active_tags for tag in tags):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def strip_telegram_entries(package_json_text: str, dep_names: list) -> str:
    """Remove do package.json as dependências e o script do canal Telegram."""
    data = json.loads(package_json_text)
    for section in ("dependencies", "devDependencies"):
        for dep in dep_names:
            data.get(section, {}).pop(dep, None)
    data.get("scripts", {}).pop("telegram", None)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def copy_tree(src: Path, dest: Path, variants: dict, active_tags: set, skip_rel: set, telegram_deps: list) -> list:
    written = []
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        if rel in skip_rel:
            continue
        target = dest / Path(substitute(rel, variants))
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            target.write_bytes(path.read_bytes())  # binário: copia como está
            written.append(target)
            continue
        text = substitute(text, variants)
        text = process_line_markers(text, active_tags)
        if path.name == "package.json" and "telegram" not in active_tags:
            text = strip_telegram_entries(text, telegram_deps)
        target.write_text(text, encoding="utf-8")
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera a estrutura de um projeto de agente (Claude Agent SDK).")
    parser.add_argument("name", help="nome do agente em kebab-case (ex.: suporte-bot)")
    parser.add_argument("--lang", required=True, choices=["python", "typescript"], help="linguagem do projeto")
    parser.add_argument("--channel", default="cli", choices=["cli", "telegram"], help="canal de entrada (default: cli)")
    parser.add_argument("--dest", default=".", help="diretório onde criar o projeto (default: diretório atual)")
    args = parser.parse_args()

    if not NAME_RE.match(args.name):
        print(f"erro: nome '{args.name}' inválido — use kebab-case (minúsculas, números, hífens; ex.: meu-agente)")
        return 1

    lang_dir = TEMPLATES_DIR / args.lang
    infra_dir = TEMPLATES_DIR / "infra"
    if not lang_dir.is_dir():
        print(f"erro: templates não encontrados em {lang_dir} — a skill agent-builder está instalada corretamente?")
        return 1

    dest = Path(args.dest).expanduser().resolve() / args.name
    if dest.exists():
        print(f"erro: {dest} já existe — escolha outro nome ou remova o diretório antes.")
        return 1

    variants = name_variants(args.name)
    active_tags = {args.channel, args.lang}

    # Arquivos que ficam de fora conforme o canal + manifesto de deps do Telegram
    skip_rel = {TELEGRAM_DEPS_MANIFEST}
    if args.channel != "telegram":
        skip_rel.update(TELEGRAM_ONLY_FILES.get(args.lang, []))
    manifest = lang_dir / TELEGRAM_DEPS_MANIFEST
    telegram_deps = []
    if manifest.is_file():
        telegram_deps = [line.strip() for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]

    written = copy_tree(lang_dir, dest, variants, active_tags, skip_rel, telegram_deps)
    written += copy_tree(infra_dir, dest / "infra", variants, active_tags, set(), [])

    print(f"Projeto criado em {dest} ({args.lang}, canal {args.channel}):")
    for path in written:
        print(f"  {path.relative_to(dest)}")
    print()
    print("Próximos passos:")
    print(f"  1. cd {dest}")
    print("  2. cp .env.example .env  # e preencha as variáveis")
    if args.lang == "python":
        print("  3. python3 -m venv .venv && .venv/bin/pip install -r requirements.txt  # requer Python >= 3.10")
        print("  4. .venv/bin/python agent.py" + ("  # ou telegram_bot.py para o bot" if args.channel == "telegram" else ""))
    else:
        print("  3. npm install  # requer Node >= 20.12")
        print("  4. npm run dev" + ("  # ou npm run telegram para o bot" if args.channel == "telegram" else ""))
    print("  Leia o README.md do projeto para detalhes; deploy 24/7: infra/ + references/10-deploy-e-producao.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
