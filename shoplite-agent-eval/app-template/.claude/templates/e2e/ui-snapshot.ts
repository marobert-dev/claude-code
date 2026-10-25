// Screenshot hook for story e2e tests; story-validator copies it once to tests/e2e/shared/ui-snapshot.ts.
// It does nothing in normal runs, so it never slows or fails the regression suite. ui-reviewer and doc-writer run a
// story's tests with `--output=test-results/ui-review/<story-id>` (or UI_SHOTS_DIR set) to capture every screen those
// tests reach, at phone and desktop width, in the test's language, together with what a script can establish on its
// own (horizontal overflow; accessibility violations when @axe-core/playwright is installed) in findings.jsonl.
// The --output form keeps the command a plain `npx playwright test …`, which permission allow-lists match.
import type { Page, TestInfo } from '@playwright/test';
import { appendFileSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

const WIDTHS = [360, 1280];
const HEIGHT = 800;
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
// Held in a variable so a project without @axe-core/playwright still type-checks and runs.
const AXE_MODULE = '@axe-core/playwright';

type AxeViolation = { id: string; impact?: string | null; help: string; nodes: { target: unknown[] }[] };
type AxeBuilderClass = new (options: { page: Page }) => {
  withTags(tags: string[]): { analyze(): Promise<{ violations: AxeViolation[] }> };
};

function captureDir(testInfo: TestInfo): string | undefined {
  if (process.env.UI_SHOTS_DIR) return resolve(process.env.UI_SHOTS_DIR);
  const runOutput = testInfo.project.outputDir;
  return /[\\/]ui-review[\\/][^\\/]+$/.test(runOutput) ? runOutput : undefined;
}

export async function uiSnapshot(page: Page, testInfo: TestInfo, screen: string): Promise<void> {
  const out = captureDir(testInfo);
  if (!out) return;
  mkdirSync(out, { recursive: true });
  const lang = (await page.evaluate(() => document.documentElement.lang)) || 'xx';
  const name = `${screen}-${lang}`.replace(/[^\w.-]+/g, '-');
  const original = page.viewportSize();
  try {
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: HEIGHT });
      await page.evaluate(async () => {
        await document.fonts?.ready;
      });
      const overflowPx = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      const file = join(out, `${name}-${width}.png`);
      await page.screenshot({ path: file, animations: 'disabled' });
      record(out, { screen, lang, width, file, overflowPx: Math.max(0, overflowPx), test: testInfo.title });
    }
    const axe = await axeViolations(page);
    if (axe) record(out, { screen, lang, axe });
  } catch (error) {
    record(out, { screen, lang, error: String(error) });
  } finally {
    if (original) await page.setViewportSize(original);
  }
}

async function axeViolations(page: Page) {
  let AxeBuilder: AxeBuilderClass;
  try {
    AxeBuilder = ((await import(AXE_MODULE)) as { default: AxeBuilderClass }).default;
  } catch {
    return undefined;
  }
  const { violations } = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
  return violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    help: v.help,
    targets: v.nodes.slice(0, 3).map((n) => n.target.join(' ')),
  }));
}

function record(dir: string, entry: Record<string, unknown>) {
  appendFileSync(join(dir, 'findings.jsonl'), `${JSON.stringify(entry)}\n`);
}
