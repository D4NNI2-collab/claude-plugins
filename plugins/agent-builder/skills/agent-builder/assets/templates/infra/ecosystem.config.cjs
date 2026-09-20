// Config do PM2 para um agente rodando 24/7 (ver references/10-deploy-e-producao.md).
// Extensão .cjs de propósito: em projeto ESM ("type": "module" no package.json),
// um .js seria lido como ESM e o PM2 não enxergaria o module.exports.
// Subir:               pm2 start infra/ecosystem.config.cjs
// Logs:                pm2 logs example-agent
// Sobreviver a reboot: pm2 save && pm2 startup
//
// Variáveis de ambiente: o PM2 NÃO carrega .env sozinho (não existe env_file).
// O próprio app carrega o .env do diretório do projeto no boot (agent.py/agent.ts);
// alternativa: definir as variáveis no bloco `env: {...}` abaixo.
// As linhas com "// [python]" / "// [typescript]" são resolvidas pelo scaffold. // [template]
module.exports = {
  apps: [
    {
      name: "example-agent",
      // Canal cli: agent.js/agent.py é uma CLI de teste — troque o script pelo seu serviço real // [cli]
      script: "dist/agent.js", // [typescript] // [cli]
      script: "dist/telegram.js", // [typescript] // [telegram]
      script: "agent.py", // [python] // [cli]
      script: "telegram_bot.py", // [python] // [telegram]
      interpreter: "./.venv/bin/python", // [python]
      // Garante que o app roda a partir do diretório do projeto:
      cwd: __dirname + "/..",
      max_memory_restart: "800M",
      restart_delay: 5000,
      max_restarts: 10,
      time: true, // timestamps nos logs
      // env: { NODE_ENV: "production" },
    },
  ],
};
