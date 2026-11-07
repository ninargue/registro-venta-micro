// PreToolUse hook del subagente adversarial-reviewer.
// - Write/Edit: solo dentro de docs/reviews/.
// - Bash: solo comandos de lectura (git log/diff/show, gh pr view/diff, gh issue view),
//   sin redirecciones ni encadenamientos que puedan escribir archivos.
// Sale con código 2 para bloquear; stderr llega al agente como motivo.
import path from "node:path";

const ALLOWED_DIR = path.join("docs", "reviews");
const BASH_ALLOWED = /^\s*(git\s+(log|diff|show)|gh\s+(pr\s+(view|diff)|issue\s+view))\b/;
const BASH_FORBIDDEN = /(>|\btee\b|\$\(|`|;|&&|\|\||\n)/;
// Tras un pipe solo se admiten filtros de lectura.
const PIPE_ALLOWED = /^\s*(head|tail|grep|wc|sort|uniq|cat)\b/;

function block(reason) {
  process.stderr.write(`Bloqueado por adversarial-reviewer-guard: ${reason}\n`);
  process.exit(2);
}

const chunks = [];
for await (const chunk of process.stdin) chunks.push(chunk);
const input = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
const tool = input.tool_name ?? "";
const toolInput = input.tool_input ?? {};

if (tool === "Write" || tool === "Edit") {
  const projectDir = process.env.CLAUDE_PROJECT_DIR ?? input.cwd ?? process.cwd();
  const allowed = path.resolve(projectDir, ALLOWED_DIR);
  const target = path.resolve(projectDir, toolInput.file_path ?? "");
  const norm = (p) => (process.platform === "win32" ? p.toLowerCase() : p);
  const rel = path.relative(norm(allowed), norm(target));
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) {
    block(`solo se puede escribir dentro de ${ALLOWED_DIR}/ (intentó: ${toolInput.file_path}).`);
  }
} else if (tool === "Bash") {
  const command = toolInput.command ?? "";
  const [first, ...piped] = command.split("|");
  const pipeOk = piped.every((seg) => PIPE_ALLOWED.test(seg));
  if (!BASH_ALLOWED.test(first) || BASH_FORBIDDEN.test(command) || !pipeOk) {
    block("Bash solo admite git log/diff/show, gh pr view/diff y gh issue view, sin redirecciones ni encadenamientos.");
  }
}

process.exit(0);
