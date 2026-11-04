#!/usr/bin/env node
// User-level PreToolUse hook (Bash and PowerShell tools): refuses a Python invocation that reads its script from stdin.
// On this Windows machine Python 3.14's REPL cannot get a console, loops on "OSError: [WinError 123]" and burns CPU
// forever, which froze sessions and sub-agents. Refused: `python -`, `python3 -`, `py -`, bare `python` (stdin or REPL),
// a heredoc / here-string / pipe / `<` redirect feeding an interpreter that has no script, `-m` or `-c`, and a `-c`
// whose code spans several lines. Allowed: `python script.py`, `python -m mod`, `python -c "one line"`, `--version`.
// Exit 2 + stderr = refusal (shown to the model). Fails open on input it cannot parse.
// Install: bash install.sh (copies it to ~/.claude/hooks/); register it from hooks/user-settings.snippet.json.
'use strict';

const REASON =
  'Blocked: Python reading its script from stdin hangs on this machine (Python 3.14 REPL loops on WinError 123). ' +
  'Use the Edit or Write tool, or write a .py/.js file and run it with a timeout (e.g. `timeout 60 python script.py`).';
const REASON_MULTILINE_C =
  'Blocked: `python -c` with code spanning several lines. ' +
  'Use the Edit or Write tool, or write a .py/.js file and run it with a timeout (e.g. `timeout 60 python script.py`).';

const INTERPRETER = /^(python(\d+(\.\d+)*t?)?|pythonw|py)$/;
const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh']);
const POWERSHELLS = new Set(['powershell', 'pwsh']);
const LEADING_KEYWORDS = new Set(['{', '!', 'then', 'do', 'else', 'elif', 'if', 'while', 'until']);
const MAX_DEPTH = 3;

function baseName(word) {
  return word.split(/[\\/]/).pop().toLowerCase().replace(/\.exe$/, '');
}

// Splits a command line into simple commands (arrays of {text, nl}); nl = the word holds a newline inside quotes.
// Heredoc bodies and redirection targets are dropped; quotes keep a word whole; `#` comments are skipped.
function splitCommands(cmd) {
  const segments = [];
  let tokens = [];
  let cur = null;
  let dropNextWord = false;
  const heredocs = [];
  const n = cmd.length;
  let i = 0;

  const word = () => (cur = cur || { text: '', nl: false });
  const endWord = () => {
    if (!cur) return;
    if (dropNextWord) dropNextWord = false;
    else tokens.push(cur);
    cur = null;
  };
  const endCommand = () => {
    endWord();
    if (tokens.length) segments.push(tokens);
    tokens = [];
  };
  const append = (text) => {
    const w = word();
    w.text += text;
    if (text.includes('\n')) w.nl = true;
  };
  const skipHeredocBodies = () => {
    while (heredocs.length) {
      const { tag, indented } = heredocs.shift();
      while (i < n) {
        let eol = cmd.indexOf('\n', i);
        if (eol < 0) eol = n;
        let line = cmd.slice(i, eol).replace(/\r$/, '');
        i = Math.min(eol + 1, n);
        if (indented) line = line.replace(/^\t+/, '');
        if (line === tag) break;
      }
    }
  };

  while (i < n) {
    const c = cmd[i];

    // PowerShell here-string @' ... '@ or @" ... "@
    if (!cur && c === '@' && (cmd[i + 1] === "'" || cmd[i + 1] === '"') && /^[ \t]*\r?\n/.test(cmd.slice(i + 2))) {
      const closing = new RegExp('\\r?\\n' + cmd[i + 1] + '@');
      const m = closing.exec(cmd.slice(i + 2));
      i = m ? i + 2 + m.index + m[0].length : n;
      append('<here-string>\n');
      continue;
    }
    if (c === "'") {
      const j = cmd.indexOf("'", i + 1);
      const stop = j < 0 ? n : j;
      word();
      append(cmd.slice(i + 1, stop));
      i = stop + 1;
      continue;
    }
    if (c === '"') {
      let j = i + 1;
      let text = '';
      while (j < n && cmd[j] !== '"') {
        if ((cmd[j] === '\\' || cmd[j] === '`') && j + 1 < n) { text += cmd[j] + cmd[j + 1]; j += 2; continue; }
        text += cmd[j++];
      }
      word();
      append(text);
      i = j + 1;
      continue;
    }
    if (c === '\\' && cmd[i + 1] === '\n') { i += 2; continue; }
    if (c === '\\' && cmd[i + 1] === '\r' && cmd[i + 2] === '\n') { i += 3; continue; }
    if (c === '`' && (cmd[i + 1] === '\n' || cmd[i + 1] === '\r')) { i += cmd[i + 1] === '\r' ? 3 : 2; continue; }
    if (c === '#' && !cur) {
      while (i < n && cmd[i] !== '\n') i++;
      continue;
    }
    if (c === '\n') {
      endCommand();
      i++;
      skipHeredocBodies();
      continue;
    }
    if (c === '<' && cmd[i + 1] === '<' && cmd[i + 2] !== '<') {
      endWord();
      i += 2;
      let indented = false;
      if (cmd[i] === '-') { indented = true; i++; }
      while (cmd[i] === ' ' || cmd[i] === '\t') i++;
      let tag = '';
      const quote = cmd[i] === "'" || cmd[i] === '"' ? cmd[i++] : '';
      while (i < n && (quote ? cmd[i] !== quote : !/[\s;|&()<>]/.test(cmd[i]))) tag += cmd[i++];
      if (quote) i++;
      heredocs.push({ tag, indented });
      continue;
    }
    if (c === '<') {
      endWord();
      i += cmd[i + 1] === '<' ? 3 : 1;
      dropNextWord = true;
      continue;
    }
    if (c === '>' || (c === '&' && cmd[i + 1] === '>')) {
      if (cur && /^\d$/.test(cur.text)) cur = null;
      else endWord();
      i += c === '&' ? 2 : 1;
      if (cmd[i] === '>') i++;
      if (cmd[i] === '&') {
        i++;
        while (/[0-9-]/.test(cmd[i] || '')) i++;
      } else {
        dropNextWord = true;
      }
      continue;
    }
    if (c === ';' || c === '|' || c === '&' || c === '(' || c === ')' || c === '`') {
      endCommand();
      i++;
      continue;
    }
    if (c === ' ' || c === '\t' || c === '\r') {
      endWord();
      i++;
      continue;
    }
    append(c);
    i++;
  }
  endCommand();
  return segments;
}

// Index of the first word after a wrapper such as `timeout 60` or `env -i FOO=1`.
function skipWrapper(name, tokens, from) {
  let k = from;
  const optionsWithValue = { timeout: new Set(['-k', '-s']), nice: new Set(['-n']), env: new Set(['-u', '-C', '-S']), stdbuf: new Set() }[name] || new Set();
  if (name === 'rtk') return tokens[k] && tokens[k].text === 'proxy' ? k + 1 : from - 1;
  while (k < tokens.length && tokens[k].text.startsWith('-') && tokens[k].text.length > 1) {
    k += optionsWithValue.has(tokens[k].text) ? 2 : 1;
  }
  if (name === 'timeout') k += 1;
  return k;
}
const WRAPPERS = new Set(['timeout', 'time', 'nohup', 'env', 'command', 'exec', 'sudo', 'nice', 'winpty', 'stdbuf', 'setsid', 'rtk']);

// null when the python call is fine, otherwise the refusal text.
function pythonProblem(name, args) {
  const isLauncher = name === 'py';
  for (let k = 0; k < args.length; k++) {
    const a = args[k].text;
    if (a === '-') return REASON;
    if (a.startsWith('--')) {
      if (a === '--version' || a === '--help' || a === '--list' || a === '--list-paths') return null;
      continue;
    }
    if (a[0] === '-' && a.length > 1) {
      if (isLauncher && /^-(\d+(\.\d+)?(-\d+)?|V:.+|0p?)$/.test(a)) {
        if (/^-0p?$/.test(a)) return null;
        continue;
      }
      for (let p = 1; p < a.length; p++) {
        const flag = a[p];
        const rest = a.slice(p + 1);
        if (flag === 'm' || flag === 'V' || flag === 'h' || flag === '?') return null;
        if (flag === 'c') {
          const code = rest ? { nl: false } : args[k + 1];
          return code && code.nl ? REASON_MULTILINE_C : null;
        }
        if (flag === 'W' || flag === 'X') {
          if (!rest) k++;
          break;
        }
      }
      continue;
    }
    return null;
  }
  return REASON;
}

function commandProblem(tokens, depth) {
  let i = 0;
  while (i < tokens.length) {
    const text = tokens[i].text;
    const name = baseName(text);
    if (LEADING_KEYWORDS.has(text) || /^[A-Za-z_][A-Za-z0-9_]*=/.test(text)) { i++; continue; }
    if (WRAPPERS.has(name)) {
      const next = skipWrapper(name, tokens, i + 1);
      if (next < i + 1) break;
      i = next;
      continue;
    }
    break;
  }
  if (i >= tokens.length) return null;
  const name = baseName(tokens[i].text);
  const args = tokens.slice(i + 1);

  if (INTERPRETER.test(name)) return pythonProblem(name, args);
  if (depth >= MAX_DEPTH) return null;

  if (SHELLS.has(name)) {
    const k = args.findIndex((a) => /^-[a-z]*c[a-z]*$/.test(a.text));
    if (k >= 0 && args[k + 1]) return textProblem(args[k + 1].text, depth + 1);
  } else if (POWERSHELLS.has(name)) {
    const k = args.findIndex((a) => /^-(c|command)$/i.test(a.text));
    if (k >= 0 && args[k + 1]) return textProblem(args.slice(k + 1).map((a) => a.text).join(' '), depth + 1);
  } else if (name === 'cmd') {
    const k = args.findIndex((a) => /^\/[ck]$/i.test(a.text));
    if (k >= 0 && args[k + 1]) return textProblem(args.slice(k + 1).map((a) => a.text).join(' '), depth + 1);
  }
  return null;
}

function textProblem(command, depth) {
  for (const tokens of splitCommands(command)) {
    const problem = commandProblem(tokens, depth);
    if (problem) return problem;
  }
  return null;
}

function main() {
  let input;
  try {
    input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
  } catch (e) {
    return 0;
  }
  const tool = input && input.tool_name;
  const command = input && input.tool_input && input.tool_input.command;
  if ((tool !== 'Bash' && tool !== 'PowerShell') || typeof command !== 'string') return 0;
  const problem = textProblem(command, 0);
  if (!problem) return 0;
  process.stderr.write(problem + '\n');
  return 2;
}

if (require.main === module) process.exit(main());
module.exports = { textProblem };
