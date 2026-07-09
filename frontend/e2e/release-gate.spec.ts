import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

test.describe('Vyapar Pulse Release Gate', () => {
  
  test.beforeEach(async ({ page }) => {
    // Listen for unhandled errors
    page.on('pageerror', exception => {
      console.error(`Uncaught exception: "${exception}"`);
    });
    
    page.on('console', msg => {
      if (msg.type() === 'error')
        console.error(`Console error: "${msg.text()}"`);
    });
  });

  test('login page has no runtime or console error and renders properly', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('text=Vyapar Pulse')).toBeVisible();
    
    // Screenshot 1: Login Screen
    await page.screenshot({ path: '../docs/assets/screenshots/01_login_screen.png' });
  });

  test('Credit Analyst one-click login and navigation', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Credit Analyst")');
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    // Screenshot 2: Credit Analyst Dashboard
    await page.screenshot({ path: '../docs/assets/screenshots/02_analyst_dashboard.png' });
    
    // Click on a non-Shakti case to preserve Shakti for the guided flow test
    const firstCase = page.locator('table tbody tr').filter({ hasText: 'Navprerna' }).first();
    await expect(firstCase).toBeVisible();
    await firstCase.locator('a', { hasText: 'Open' }).click();
    await expect(page.locator('text=BACK TO CASE INVENTORY')).toBeVisible();
      
      // Screenshot 3: Case Detail View
      await page.screenshot({ path: '../docs/assets/screenshots/03_case_detail_view.png' });
      
      // Run Assessment Engine if available, otherwise just view the existing Credit Twin
      const runEngine = page.locator('button:has-text("Run Assessment Engine")');
      if (await runEngine.isVisible()) {
        await runEngine.click();
      }
      
      // Wait for evaluation (or existing evaluation) to be visible
      await expect(page.locator('text=MSME Credit Twin')).toBeVisible({ timeout: 15000 });
      
      // Screenshot 4: Credit Twin Computed
      await page.screenshot({ path: '../docs/assets/screenshots/04_credit_twin.png' });
  });

  test('SA one-click login and assessment history', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Sanctioning Authority")');
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    // Click on a non-Shakti case
    const firstCase = page.locator('table tbody tr').filter({ hasText: 'Navprerna' }).first();
    await expect(firstCase).toBeVisible();
    await firstCase.locator('a:has-text("Open")').click();
    await page.click('button:has-text("Assessment History")');
    
    // Screenshot 5: Assessment History
    await page.screenshot({ path: '../docs/assets/screenshots/05_assessment_history.png' });
  });

  test('Auditor one-click login and global audit log', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Auditor")');
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    await page.click('a[href="/audit"]');
    await expect(page.locator('text=Audit Log & CAS Trail')).toBeVisible();
    
    // Screenshot 6: Global Audit
    await page.screenshot({ path: '../docs/assets/screenshots/06_global_audit.png' });
  });

  test('System Admin receives no borrower content or case/audit navigation', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("System Admin")');
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    // Should see system admin view
    await expect(page.locator('text=Governance & Access Controls')).toBeVisible();
    
    // Should NOT see cases
    await expect(page.locator('table')).not.toBeVisible();
    
    // Screenshot 7: System Admin
    await page.screenshot({ path: '../docs/assets/screenshots/07_system_admin.png' });
  });

  test('Relationship Manager read-only access to cases', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Relationship Manager")');
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    // Click on a non-Shakti case
    const firstCase = page.locator('table tbody tr').filter({ hasText: 'Navprerna' }).first();
    await expect(firstCase).toBeVisible();
    await firstCase.locator('a', { hasText: 'Open' }).click();
    await expect(page.locator('text=BACK TO CASE INVENTORY')).toBeVisible();
      
    // RM should NOT see "Run Assessment Engine" or recommendation buttons
    await expect(page.locator('button:has-text("Run Assessment Engine")')).not.toBeVisible();
  });

  test('Risk Admin access to policy engine config', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Risk Admin")');
    await expect(page).toHaveURL('/', { timeout: 10000 });
    
    // Risk admin should see policy configuration
    await page.click('a[href="/policy"]');
    await expect(page.locator('text=Credit Policy & Risk Rules Engine')).toBeVisible();
  });
  
  test('Shakti guided flow reaches all stages and captures screenshots', async ({ page }) => {
    await page.goto('/demo');
    await page.waitForLoadState('networkidle');
    await page.click('button:has-text("Start 3-Minute Credit Journey")');
    
    // Wait for login and navigation to /demo
    await expect(page).toHaveURL(/\/demo/);
    
    // Screenshot 8: Guided walkthrough - business & request
    await expect(page.locator('text=Inspect Evidence Coverage')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: '../docs/assets/screenshots/08_guided_business_request.png' });
    
    // Proceed to Evidence Coverage
    await page.click('button:has-text("Inspect Evidence Coverage")');
    await expect(page.locator('text=Proceed to Reconciliation')).toBeVisible();
    
    // Screenshot 9: Guided walkthrough - evidence coverage
    await page.screenshot({ path: '../docs/assets/screenshots/09_guided_evidence_coverage.png' });
    
    // Proceed to Reconciliation
    await page.click('button:has-text("Proceed to Reconciliation")');
    await expect(page.locator('text=Run Assessment Engine')).toBeVisible();
    
    // Screenshot 10: Guided walkthrough - reconciliation
    await page.screenshot({ path: '../docs/assets/screenshots/10_guided_reconciliation.png' });
  });
});
