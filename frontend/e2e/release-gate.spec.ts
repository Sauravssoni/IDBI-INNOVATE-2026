import { test, expect } from '@playwright/test';

test.describe('Vyapar Pulse Release Gate', () => {
  let hasErrors = false;

  test.beforeAll(async ({ request }) => {
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
    const resetToken = process.env.DEMO_RESET_TOKEN || 'change-this-local-development-password';
    
    console.log(`Attempting demo reset directly via backend: ${backendUrl}/api/demo/reset`);
    console.log(`Using token: ${resetToken}`);
    
    let attempt = 0;
    let resetSuccess = false;

    while (attempt < 15 && !resetSuccess) {
      attempt++;
      try {
        const resetRes = await request.post(`${backendUrl}/api/demo/reset`, {
          headers: { 'X-Demo-Reset-Token': resetToken },
          timeout: 60000
        });

        if (resetRes.ok()) {
          console.log('Demo reset successful!');
          resetSuccess = true;
        } else {
          const errText = await resetRes.text();
          console.log(`Attempt ${attempt} - Reset failed: Status ${resetRes.status()}: ${errText}`);
          await new Promise(r => setTimeout(r, 2000));
        }
      } catch (e: any) {
        console.log(`Attempt ${attempt} - Request exception: ${e.message}`);
        await new Promise(r => setTimeout(r, 2000));
      }
    }

    if (!resetSuccess) {
      throw new Error(`Failed to reset demo environment.`);
    }
  });

  test.beforeEach(async ({ page }) => {
    page.on('pageerror', exception => {
      console.error(`Uncaught exception: "${exception}"`);
      hasErrors = true;
    });
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        const text = msg.text();
        if (!text.includes('401') && !text.includes('GSI_LOGGER') && !text.includes("Provider's accounts list is empty")) {
          console.error(`Console error: "${text}"`);
          hasErrors = true;
        }
      }
    });

    page.on('response', response => {
      if (response.status() >= 400 && response.status() !== 401 && response.status() !== 429 && response.status() !== 404) {
        const url = response.url();
        if (!url.includes('/api/auth/me') && !url.includes('favicon.ico')) {
          console.error(`Failed network call: ${response.status()} ${url}`);
          hasErrors = true;
        }
      }
    });
  });

  test.afterEach(async () => {
    expect(hasErrors).toBe(false);
  });

  test('Shakti guided flow reaches all stages and captures screenshots', async ({ page, context }) => {
    // 1. Analyst Phase
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    await expect(page).toHaveURL(/\//);
    await page.click('text=Shakti');
    await expect(page.locator('text=Inspect Evidence Coverage')).toBeVisible({ timeout: 10000 });
    await page.click('button:has-text("Inspect Evidence Coverage")');
    await page.click('button:has-text("Proceed to Reconciliation")');
    await page.click("button:has-text(\"Run Assessment Engine\")");
    await expect(page.locator("text=Computed Credit Twin")).toBeVisible({ timeout: 15000 });
    
    await expect(page.locator('text=System Recommendation')).toBeVisible();
    await page.click('button:has-text("Prepare Recommendation")');
    await page.click('button:has-text("Submit Recommendation")');
    await expect(page.locator('text=Recommendation Submitted')).toBeVisible();

    // 2. SA Phase & Seal
    await page.click('button:has-text("Continue as Sanctioning Authority")');
    await expect(page.locator('text=Sanctioning Authority Gate')).toBeVisible(); 
    
    // Check seal is not possible yet
    await expect(page.locator('button:has-text("Seal Package")')).not.toBeVisible();

    // Human terminal decision
    await page.click('button:has-text("Approve Alternative Structure")');
    await expect(page.locator('text=SANCTION APPROVED').or(page.locator('text=SANCTIONED'))).toBeVisible();

    // Now seal the package
    await expect(page.locator('text=PACKAGE NOT SEALED')).toBeVisible();
    await page.click('button:has-text("Seal Package")');
    await expect(page.locator('text=PACKAGE SEALED — NOT VERIFIED')).toBeVisible({ timeout: 15000 });
    
    // Verify Package Signature
    await page.click('button:has-text("Verify Package Signature")');
    await expect(page.locator('text=PACKAGE HASH VERIFIED')).toBeVisible({ timeout: 15000 });
    
    // Independent Replay
    await page.click('button:has-text("Execute Full Engine Replay")');
    await expect(page.locator('text=REPLAY MATCHED')).toBeVisible({ timeout: 30000 });
  });

  test('NavPrerna evidence-request/defer path', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').filter({ hasText: 'Navprerna' }).first();
    await row.getByRole('link').click();
    
    const runEngine = page.locator('button:has-text("Run Assessment Engine")');
    if (await runEngine.isVisible()) {
      await runEngine.click();
    }
    await expect(page.locator('text=Additional Evidence Required').or(page.locator('text=EVIDENCE_REQUEST'))).toBeVisible({ timeout: 15000 });
  });

  test('Nirmaan decline/decline-after-review path', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').filter({ hasText: 'Nirmaan' }).first();
    await row.getByRole('link').click();
    
    const runEngine = page.locator('button:has-text("Run Assessment Engine")');
    if (await runEngine.isVisible()) {
      await runEngine.click();
    }
    await expect(page.locator('text=Decline Recommended').or(page.locator('text=DECLINE')).first()).toBeVisible({ timeout: 15000 });
  });

  test('Rangrez frozen expected path', async ({ page }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    const row = page.locator('table tbody tr').filter({ hasText: 'Rangrez' }).first();
    await row.getByRole('link').click();
    
    await expect(page.locator('text=Decision Pending').or(page.locator('text=FROZEN')).first()).toBeVisible();
  });

  test('Offline mode functionality', async ({ page, context }) => {
    await page.goto('/login');
    await page.click('button:has-text("Credit Analyst")');
    await expect(page).toHaveURL(/\//);

    // Go offline
    await context.setOffline(true);
    
    // Navigate to Shakti offline
    await page.click('text=Shakti');
    await expect(page.locator('text=Inspect Evidence Coverage')).toBeVisible({ timeout: 10000 });
    
    // Write actions should be disabled offline
    await expect(page.locator('button:has-text("Inspect Evidence Coverage")')).toBeDisabled();
    await expect(page.locator('text=You are currently working offline')).toBeVisible();

    // Reconnect
    await context.setOffline(false);
    
    // Write actions enabled again
    await expect(page.locator('button:has-text("Inspect Evidence Coverage")')).toBeEnabled();
  });

});
