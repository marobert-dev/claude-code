// Usage: node yaml2json.mjs <file.yaml>  -> JSON on stdout (exit 2 when the YAML does not parse).
import { readFileSync } from 'node:fs';
import { parse } from 'yaml';

try {
  process.stdout.write(JSON.stringify(parse(readFileSync(process.argv[2], 'utf8'))));
} catch (error) {
  process.stderr.write(`yaml2json: ${error.message}\n`);
  process.exit(2);
}
