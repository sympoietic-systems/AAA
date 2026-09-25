import { ESLint } from "eslint"
import { readFile } from "node:fs/promises"
import path from "node:path"

// Legacy debt is explicit and scoped per file/rule. All unlisted violations fail.
const baseline = JSON.parse(await readFile(new URL("../eslint-debt.json", import.meta.url), "utf8"))
const results = await new ESLint({ cache: false }).lintFiles(["."])
const actual = {}
const regressions = []
let errors = 0
let warnings = 0
for (const result of results) {
  errors += result.errorCount
  warnings += result.warningCount
  const file = path.relative(process.cwd(), result.filePath).replaceAll("\\", "/")
  for (const message of result.messages) {
    const key = `${file}|${message.ruleId ?? "parse"}|${message.severity}`
    actual[key] = (actual[key] ?? 0) + 1
    if (actual[key] > (baseline[key] ?? 0)) regressions.push(`${file}:${message.line} ${message.ruleId}: ${message.message}`)
  }
}
const stale = Object.keys(baseline).filter(key => (actual[key] ?? 0) < baseline[key])
if (regressions.length) {
  console.error(regressions.join("\n\n"))
  process.exitCode = 1
}
if (stale.length) {
  console.error("Reduce resolved entries in eslint-debt.json before merging:\n" + stale.join("\n"))
  process.exitCode = 1
}
console.log(`ESLint: ${errors} legacy errors, ${warnings} legacy warnings; ${regressions.length} regressions. Run npm run lint:all for full diagnostics.`)
