// Kit-only helper: turns the agent files of web-team-agents into the JSON that `claude --agents` takes, so a run
// measures the agents of the repository it records (agents_sha) instead of whatever ~/.claude/agents holds, and can
// hide the user's own settings (--setting-sources project,local) while the agents keep their frontmatter hooks.
// Usage: node agents2json.mjs <agents-dir> <out.json>
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import YAML from 'yaml';

const [dir, out] = process.argv.slice(2);
if (!dir || !out) {
  console.error('usage: node agents2json.mjs <agents-dir> <out.json>');
  process.exit(2);
}
const agents = {};
for (const file of readdirSync(dir).filter((f) => f.endsWith('.md')).sort()) {
  const text = readFileSync(join(dir, file), 'utf8');
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) throw new Error(`${file}: no frontmatter`);
  const { name, tools, ...fields } = YAML.parse(match[1]);
  agents[name] = {
    ...fields,
    // "Agent(a, b), Read" keeps the commas inside Agent(...) together
    ...(tools !== undefined && { tools: String(tools).split(/,(?![^(]*\))/).map((t) => t.trim()).filter(Boolean) }),
    prompt: text.slice(match[0].length),
  };
}
writeFileSync(out, JSON.stringify(agents, null, 1));
console.log(`${Object.keys(agents).length} agents -> ${out}`);
