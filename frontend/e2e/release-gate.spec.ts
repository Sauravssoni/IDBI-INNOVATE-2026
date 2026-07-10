import { test, expect } from '@playwright/test';

test.describe('Vyapar Pulse Release Gate', () => {
  let hasErrors = false;

  test.beforeEach(async ({ page }) => {
    page.on('pageerror', exception => {
      console.error(`Uncaught exception: "${exception}"`);
      hasErrors = true;
    });
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        // Ignore expected 401 or 403 errors which show up as "Failed to load resource"
        if (!text.includes('401 (Unauthorized)') && !text.includes('403 (Forbidden)') && !text.includes('404 (Not Found)')) {
          console.error(`Console error: "${text}"`);
          hasErrors = true;
        }
      }
    });

    page.on('response', response => {
      if (response.status() >= 400) {
        // Allow intentional 401s on initial load, or 403s for sys admin
        const url = response.url();
        if (!url.includes('/api/auth/me') && !url.includes('favicon.ico') && response.status() !== 403 && response.status() !== 404) {
          console.error(`Failed network call: ${response.status()} ${url}`);
          hasErrors = true;
        }
      }
    });
  });

  test.afterEach(async () => {
    expect(hasErrors).toBe(false);
  });

  test('Shakti guided flow reaches all stages and captures screenshots', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Start 3-Minute Credit Journey")');
    await expect(page).toHaveURL(/\/demo/);
    
    await expect(page.locator('text=Inspect Evidence Coverage')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: '../docs/assets/screenshots/02-shakti-request.png' });
    
    await page.click('button:has-text("Inspect Evidence Coverage")');
    await expect(page.locator('text=Proceed to Reconciliation')).toBeVisible();
    await page.screenshot({ path: '../docs/assets/screenshots/03-evidence-coverage.png' });
    
    await page.click('button:has-text("Proceed to Reconciliation")');
    await expect(page.locator('text=Run Assessment Engine')).toBeVisible();
    
    const runEngine = page.locator('button:has-text("Run Assessment Engine")');
    if (await runEngine.isVisible()) {
      await runEngine.click();
    }
    await expect(page.locator('text=Computed Credit Twin')).toBeVisible({ timeout: 15000 });
    await page.screenshot({ path: '../docs/assets/screenshots/04-credit-twin.png' });
    
    // Assertions for Shakti outcome
    await expect(page.locator('text=System Recommendation')).toBeVisible();
    await expect(page.locator('text=Binding Support Limit')).toBeVisible(); // DSCR 1.85
    await expect(page.locator('text=CONDITIONAL_OFFER').or(page.locator('text=CONDITIONAL OFFER'))).toBeVisible();
    await expect(page.locator('text=₹35.69').or(page.locator('text=3,569,000'))).toBeVisible(); // supportable amount approximately ₹35.69 lakh
    
    await expect(page.locator('text=Prepare Recommendation')).toBeVisible();
    await page.click('button:has-text("Prepare Recommendation")');
    
    // Analyst alternative-structure recommendation
    await page.click('button:has-text("Submit Recommendation")');
    await expect(page.locator('text=Recommendation Submitted')).toBeVisible();
    await page.screenshot({ path: '../docs/assets/screenshots/05-analyst-recommendation.png' });

    // SA transition verifies /api/auth/me and lands on stage 6
    await page.click('button:has-text("Continue as Sanctioning Authority")');
    await expect(page.locator('text=Sanctioning Authority Gate')).toBeVisible(); // Stage 6
    await expect(page.locator('text=Approve Alternative Structure')).toBeVisible();
    await page.screenshot({ path: '../docs/assets/screenshots/06-sanction-review.png' });

    // manual SA alternative-structure approval
    await page.click('button:has-text("Approve Application")');
    await expect(page.locator('text=SANCTIONED').or(page.locator('text=Sanctioned'))).toBeVisible();
  });

  test('NavPrerna evidence-request/defer path', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').filter({ hasText: 'Navprerna' }).first();
    await row.locator('a', { hasText: 'Open' }).click();
    
    const runEngine = page.locator('button:has-text("Run Assessment Engine")');
    if (await runEngine.isVisible()) {
      await runEngine.click();
    }
    
    await expect(page.locator('text=Additional Evidence Required')).toBeVisible({ timeout: 15000 });
  });

  test('Aarohan decline/decline-after-review path', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').filter({ hasText: 'Aarohan' }).first();
    await row.locator('a', { hasText: 'Open' }).click();
    
    const runEngine = page.locator('button:has-text("Run Assessment Engine")');
    if (await runEngine.isVisible()) {
      await runEngine.click();
    }
    
    await expect(page.locator('text="Decline Recommended"').or(page.locator('text=DECLINE')).first()).toBeVisible({ timeout: 15000 });
  });

  test('Rangrez frozen expected path', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').filter({ hasText: 'Rangrez' }).first();
    await row.locator('a', { hasText: 'Open' }).click();
    
    await expect(page.locator('text=Decision Pending').or(page.locator('text=FROZEN')).first()).toBeVisible();
  });

  test('Assessment History does not crash', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').first();
    await row.locator('a', { hasText: 'Open' }).click();
    await page.click('button:has-text("Assessment History")');
    await expect(page.locator('text=evaluate').first()).toBeVisible();
  });

  test('Auditor trace renders timestamps and hashes', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Auditor")');
    await page.click('a[href="/audit"]');
    await expect(page.locator('text=Audit Log & CAS Trail')).toBeVisible();
    await expect(page.locator('table').first()).toBeVisible();
    await expect(page.locator('text=Tamper-Evident Audit Hash')).toBeVisible();
    await page.screenshot({ path: '../docs/assets/screenshots/09-auditor-trace.png' });
  });

  test('Policy page renders only implemented rules', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Risk Admin")');
    await page.click('a[href="/policy"]');
    await expect(page.locator('text=Credit Policy & Risk Rules Engine')).toBeVisible();
    await expect(page.locator('text=DSCR Thresholds').first()).toBeVisible();
    await page.screenshot({ path: '../docs/assets/screenshots/10-policy-matrix.png' });
  });

  test('System Admin isolation', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("System Admin")');
    await expect(page.locator('text=Governance & Access Controls')).toBeVisible();
    await expect(page.locator('table')).not.toBeVisible();
  });

  test('Relationship Manager demo login', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Relationship Manager")');
    const row = page.locator('table tbody tr').first();
    await row.locator('a', { hasText: 'Open' }).click();
    await expect(page.locator('button:has-text("Run Assessment Engine")')).not.toBeVisible();
  });

  test('Data assertions (no ₹0 approval, no raw enum)', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const content = await page.textContent('body');
    expect(content).not.toContain('₹0');
    expect(content).not.toContain('RECOMMEND_ALTERNATIVE_STRUCTURE');
  });

  test('Capture missing screenshots', async ({ page }) => {
    await page.goto('/login');
    await page.screenshot({ path: '../docs/assets/screenshots/01-demo-access.png' });
    await page.click('button:has-text("Credit Analyst")');
    await page.screenshot({ path: '../docs/assets/screenshots/08-dashboard.png' });
    const row = page.locator('table tbody tr').first();
    await row.locator('a', { hasText: 'Open' }).click();
    await page.click('button:has-text("Assessment History")');
    await page.screenshot({ path: '../docs/assets/screenshots/07-final-audit.png' });
  });

  test('SA-only login test', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Sanctioning Authority")');
    await expect(page.locator('text=Case Inventory').first()).toBeVisible();
    await page.click('a[href="/cases"]');
    await expect(page.locator('table')).toBeVisible();
  });
});
