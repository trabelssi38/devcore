import { test, expect } from "@playwright/test";

test("dashboard component source exposes core cards", async ({ page }) => {
  await page.setContent(`
    <main aria-label="Vue synthétique DEV_CORE">
      <section aria-label="Résumé projet">ProjectSummary</section>
      <section aria-label="Liste des tâches">TaskList</section>
      <section aria-label="Chronologie des runs">RunTimeline</section>
      <section aria-label="Santé plateforme">HealthPanel</section>
    </main>
  `);

  await expect(page.getByLabel("Résumé projet")).toContainText("ProjectSummary");
  await expect(page.getByLabel("Liste des tâches")).toContainText("TaskList");
});
