#!/usr/bin/env node
/**
 * Gera os SVGs de estatísticas e de radar de linguagens usados no README
 * do perfil, com dados públicos vindos da GitHub GraphQL API.
 *
 * Variáveis de ambiente esperadas:
 *   GITHUB_TOKEN  - token de acesso (o próprio GITHUB_TOKEN do Actions serve)
 *   GITHUB_USER   - usuário do GitHub cujo perfil será medido
 *
 * Saída:
 *   assets/stats-card.svg
 *   assets/radar-langs.svg
 */

import { writeFile, mkdir } from "node:fs/promises";

const TOKEN = process.env.GITHUB_TOKEN;
const USERNAME = process.env.GITHUB_USER || "JuanRodrigues-Dev";

if (!TOKEN) {
  console.error("Erro: variável de ambiente GITHUB_TOKEN não definida.");
  process.exit(1);
}

const QUERY = `
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: { field: SIZE, direction: DESC }) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
  }
}`;

async function fetchGithubData() {
  const res = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: QUERY, variables: { login: USERNAME } }),
  });

  if (!res.ok) {
    throw new Error(`GitHub API respondeu ${res.status}: ${await res.text()}`);
  }

  const json = await res.json();
  if (json.errors) {
    throw new Error(`Erro na GraphQL API: ${JSON.stringify(json.errors)}`);
  }
  return json.data.user;
}

function aggregateLanguages(repos) {
  const totals = new Map();
  for (const repo of repos) {
    for (const edge of repo.languages.edges) {
      const key = edge.node.name;
      const prev = totals.get(key) || { size: 0, color: edge.node.color || "#a9bef3" };
      prev.size += edge.size;
      totals.set(key, prev);
    }
  }
  return [...totals.entries()]
    .map(([name, v]) => ({ name, ...v }))
    .sort((a, b) => b.size - a.size);
}

// ---------------- Tema visual (SVG) ----------------

const THEME = {
  bg: "#0d1117",
  card: "#161b22",
  border: "#30363d",
  text: "#c9d1d9",
  subtext: "#8b949e",
  accent: "#a9bef3",
  grid: "#30363d",
  font: "'JetBrains Mono', 'Fira Code', monospace",
};

function escapeXml(value) {
  return String(value).replace(/[<>&'"]/g, (c) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
  })[c]);
}

// ---------------- Card de estatísticas ----------------

function statsCardSvg(stats) {
  const rows = [
    ["⭐ Total de estrelas", stats.stars],
    ["📦 Repositórios públicos", stats.repos],
    ["💾 Commits (último ano)", stats.commits],
    ["🔀 Pull requests", stats.prs],
    ["🐛 Issues abertas", stats.issues],
    ["👥 Seguidores", stats.followers],
  ];

  const width = 420;
  const rowHeight = 34;
  const headerHeight = 62;
  const height = headerHeight + rows.length * rowHeight + 20;

  const rowsSvg = rows
    .map(([label, value], i) => {
      const y = headerHeight + 24 + i * rowHeight;
      return `
    <text x="28" y="${y}" fill="${THEME.text}" font-size="14" font-family="${THEME.font}">${escapeXml(label)}</text>
    <text x="${width - 28}" y="${y}" fill="${THEME.accent}" font-size="14" font-family="${THEME.font}" text-anchor="end" font-weight="700">${escapeXml(value)}</text>`;
    })
    .join("");

  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Estatísticas do GitHub">
  <rect x="0.5" y="0.5" rx="12" width="${width - 1}" height="${height - 1}" fill="${THEME.card}" stroke="${THEME.border}"/>
  <text x="28" y="38" fill="${THEME.text}" font-size="18" font-family="${THEME.font}" font-weight="700">${escapeXml(stats.name)} · estatísticas</text>
  <line x1="28" y1="50" x2="${width - 28}" y2="50" stroke="${THEME.border}"/>
  ${rowsSvg}
</svg>`;
}

// ---------------- Radar de linguagens ----------------

function radarLangsSvg(languages) {
  const top = languages.slice(0, 6);
  const total = top.reduce((sum, l) => sum + l.size, 0) || 1;
  const maxShare = Math.max(...top.map((l) => l.size / total));
  const n = Math.max(top.length, 3);

  const width = 580;
  const height = 440;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = 130;

  function angleOf(i) {
    return (Math.PI * 2 * i) / n - Math.PI / 2;
  }

  function point(i, fraction) {
    const angle = angleOf(i);
    const r = radius * fraction;
    return [centerX + r * Math.cos(angle), centerY + r * Math.sin(angle)];
  }

  function anchorFor(i) {
    const cos = Math.cos(angleOf(i));
    if (cos > 0.15) return "start";
    if (cos < -0.15) return "end";
    return "middle";
  }

  const rings = [0.25, 0.5, 0.75, 1]
    .map((f) => {
      const pts = top.map((_, i) => point(i, f).join(",")).join(" ");
      return `<polygon points="${pts}" fill="none" stroke="${THEME.grid}" stroke-width="1"/>`;
    })
    .join("\n  ");

  const spokes = top
    .map((_, i) => {
      const [x, y] = point(i, 1);
      return `<line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" stroke="${THEME.grid}" stroke-width="1"/>`;
    })
    .join("\n  ");

  const dataPts = top
    .map((l, i) => point(i, l.size / total / maxShare).join(","))
    .join(" ");

  const labels = top
    .map((l, i) => {
      const [x, y] = point(i, 1.35);
      const pct = ((l.size / total) * 100).toFixed(1);
      return `<text x="${x}" y="${y}" fill="${THEME.text}" font-size="13" font-family="${THEME.font}" text-anchor="${anchorFor(i)}">${escapeXml(l.name)} ${pct}%</text>`;
    })
    .join("\n  ");

  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Radar de linguagens mais usadas">
  <rect width="${width}" height="${height}" fill="${THEME.bg}"/>
  ${rings}
  ${spokes}
  <polygon points="${dataPts}" fill="${THEME.accent}" fill-opacity="0.35" stroke="${THEME.accent}" stroke-width="2"/>
  ${labels}
</svg>`;
}

// ---------------- Execução ----------------

async function main() {
  const user = await fetchGithubData();
  const repos = user.repositories.nodes;
  const stars = repos.reduce((sum, r) => sum + r.stargazerCount, 0);
  const languages = aggregateLanguages(repos);

  const stats = {
    name: user.name || USERNAME,
    stars,
    repos: user.repositories.totalCount,
    commits: user.contributionsCollection.totalCommitContributions,
    prs: user.contributionsCollection.totalPullRequestContributions,
    issues: user.contributionsCollection.totalIssueContributions,
    followers: user.followers.totalCount,
  };

  await mkdir("assets", { recursive: true });
  await writeFile("assets/stats-card.svg", statsCardSvg(stats));
  await writeFile("assets/radar-langs.svg", radarLangsSvg(languages));

  console.log("SVGs gerados com sucesso.");
  console.log(stats);
  console.log(languages.slice(0, 6));
}

main().catch((err) => {
  console.error("Falha ao gerar métricas:", err);
  process.exit(1);
});
