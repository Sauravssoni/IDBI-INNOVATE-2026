# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: release-gate.spec.ts >> Vyapar Pulse Release Gate >> Policy page renders only implemented rules
- Location: e2e/release-gate.spec.ts:137:7

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: false
Received: true
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - alert [ref=e2]
  - generic [ref=e3]:
    - banner [ref=e4]:
      - link "Vyapar Pulse IDBI INNOVATE 2026" [ref=e6] [cursor=pointer]:
        - /url: /
        - img [ref=e8]
        - generic [ref=e11]:
          - generic [ref=e12]: Vyapar Pulse
          - generic [ref=e13]: IDBI INNOVATE 2026
      - generic [ref=e15]:
        - img [ref=e16]
        - 'textbox "Search business ID, legal name, GSTIN or case #..." [ref=e19]'
        - generic [ref=e20]: ⌘K
      - generic [ref=e21]:
        - generic [ref=e24]: Assessment Service
        - generic [ref=e25]:
          - img [ref=e26]
          - generic [ref=e28]: Risk Admin
          - generic [ref=e29]: (Risk Admin)
        - button "Sign out of Vyapar Pulse" [ref=e30] [cursor=pointer]:
          - img [ref=e31]
    - generic [ref=e34]:
      - complementary [ref=e35]:
        - generic [ref=e36]:
          - generic [ref=e37]: Navigation & Workflows
          - link "Dashboard" [ref=e38] [cursor=pointer]:
            - /url: /
            - generic [ref=e39]:
              - img [ref=e40]
              - generic [ref=e45]: Dashboard
          - link "Case Inventory" [ref=e46] [cursor=pointer]:
            - /url: /cases
            - generic [ref=e47]:
              - img [ref=e48]
              - generic [ref=e50]: Case Inventory
          - link "Policy & Risk Engine AI" [active] [ref=e51] [cursor=pointer]:
            - /url: /policy
            - generic [ref=e52]:
              - img [ref=e53]
              - generic [ref=e55]: Policy & Risk Engine
            - generic [ref=e56]: AI
          - link "Audit Log & CAS Trail" [ref=e57] [cursor=pointer]:
            - /url: /audit
            - generic [ref=e58]:
              - img [ref=e59]
              - generic [ref=e63]: Audit Log & CAS Trail
        - generic [ref=e64]:
          - generic [ref=e65]:
            - img [ref=e66]
            - generic [ref=e69]: Governance & Access
          - paragraph [ref=e70]: Role-Scoped Access enforced. Tamper-evident prototype audit chain.
      - main [ref=e71]:
        - generic [ref=e73]:
          - generic [ref=e74]:
            - generic [ref=e75]:
              - img [ref=e76]
              - generic [ref=e79]: CAS v1.1.3 • DETERMINISTIC POLICY ENGINE
            - heading "Credit Policy & Risk Rules Engine" [level=1] [ref=e80]:
              - img [ref=e81]
              - generic [ref=e83]: Credit Policy & Risk Rules Engine
            - paragraph [ref=e84]: Configurable decision parameters, debt-service thresholds, and automated fraud flags.
          - generic [ref=e85]:
            - generic [ref=e86]:
              - generic [ref=e87]:
                - generic [ref=e88]: DSCR Thresholds
                - img [ref=e89]
              - generic [ref=e90]: ≥ 1.15x
              - paragraph [ref=e91]: Minimum Debt Service Coverage Ratio required for deterministic evidence-linked recommendation and human-reviewed sanction decision.
            - generic [ref=e92]:
              - generic [ref=e93]:
                - generic [ref=e94]: Circular Trading Guard
                - img [ref=e95]
              - generic [ref=e98]: Active (0 Tol)
              - paragraph [ref=e99]: Real-time graph analysis across GST vendor/customer networks to block shell loops.
            - generic [ref=e100]:
              - generic [ref=e101]:
                - generic [ref=e102]: Gearing Cap
                - img [ref=e103]
              - generic [ref=e105]: ≤ 3.00x
              - paragraph [ref=e106]: Maximum Total Debt / Equity ratio permitted without mandatory Sanction Authority escalation.
          - generic [ref=e107]:
            - img [ref=e108]
            - heading "Built for IDBI Innovate 2026 Policy Matrix Active" [level=3] [ref=e111]
            - paragraph [ref=e112]: Illustrative prototype policy thresholds for AI-assisted credit assessment. Hackathon prototype—not an official IDBI Bank production system.
        - generic [ref=e113]:
          - generic [ref=e114]: Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system
          - generic [ref=e115]: Illustrative prototype policy thresholds • Tamper-evident prototype audit chain
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('Vyapar Pulse Release Gate', () => {
  4   |   let hasErrors = false;
  5   | 
  6   |   test.beforeEach(async ({ page }) => {
  7   |     page.on('pageerror', exception => {
  8   |       console.error(`Uncaught exception: "${exception}"`);
  9   |       hasErrors = true;
  10  |     });
  11  |     
  12  |     page.on('console', msg => {
  13  |       if (msg.type() === 'error') {
  14  |         console.error(`Console error: "${msg.text()}"`);
  15  |         hasErrors = true;
  16  |       }
  17  |     });
  18  | 
  19  |     page.on('response', response => {
  20  |       if (response.status() >= 400) {
  21  |         // Allow intentional 401s on initial load, or 403s for sys admin
  22  |         const url = response.url();
  23  |         if (!url.includes('/api/auth/me') && !url.includes('favicon.ico') && response.status() !== 403 && response.status() !== 404) {
  24  |           console.error(`Failed network call: ${response.status()} ${url}`);
  25  |           hasErrors = true;
  26  |         }
  27  |       }
  28  |     });
  29  |   });
  30  | 
  31  |   test.afterEach(async () => {
> 32  |     expect(hasErrors).toBe(false);
      |                       ^ Error: expect(received).toBe(expected) // Object.is equality
  33  |   });
  34  | 
  35  |   test('Shakti guided flow reaches all stages and captures screenshots', async ({ page }) => {
  36  |     await page.goto('/demo');
  37  |     await page.waitForLoadState('networkidle');
  38  |     await page.click('button:has-text("Start 3-Minute Credit Journey")');
  39  |     await expect(page).toHaveURL(/\/demo/);
  40  |     
  41  |     await expect(page.locator('text=Inspect Evidence Coverage')).toBeVisible({ timeout: 10000 });
  42  |     await page.screenshot({ path: '../docs/assets/screenshots/02-shakti-request.png' });
  43  |     
  44  |     await page.click('button:has-text("Inspect Evidence Coverage")');
  45  |     await expect(page.locator('text=Proceed to Reconciliation')).toBeVisible();
  46  |     await page.screenshot({ path: '../docs/assets/screenshots/03-evidence-coverage.png' });
  47  |     
  48  |     await page.click('button:has-text("Proceed to Reconciliation")');
  49  |     await expect(page.locator('text=Run Assessment Engine')).toBeVisible();
  50  |     
  51  |     await page.click('button:has-text("Run Assessment Engine")');
  52  |     await expect(page.locator('text=MSME Credit Twin')).toBeVisible({ timeout: 15000 });
  53  |     await page.screenshot({ path: '../docs/assets/screenshots/04-credit-twin.png' });
  54  |     
  55  |     // Assertions for Shakti outcome
  56  |     await expect(page.locator('text=DSCR')).toBeVisible();
  57  |     await expect(page.locator('text=1.85')).toBeVisible(); // DSCR 1.85
  58  |     await expect(page.locator('text=CONDITIONAL_OFFER').or(page.locator('text=Conditional Offer'))).toBeVisible();
  59  |     await expect(page.locator('text=35.69').or(page.locator('text=3,569,000'))).toBeVisible(); // supportable amount approximately ₹35.69 lakh
  60  |     
  61  |     await expect(page.locator('text=Proceed to Recommendation')).toBeVisible();
  62  |     await page.click('button:has-text("Proceed to Recommendation")');
  63  |     
  64  |     // Analyst alternative-structure recommendation
  65  |     await page.fill('textarea[placeholder*="rationale"]', 'Recommend alternative structure of 35L');
  66  |     await page.click('button:has-text("Submit Recommendation")');
  67  |     await expect(page.locator('text=Sanction Review')).toBeVisible();
  68  |     await page.screenshot({ path: '../docs/assets/screenshots/05-analyst-recommendation.png' });
  69  | 
  70  |     // SA transition verifies /api/auth/me and lands on stage 6
  71  |     await page.click('button:has-text("Simulate Sanctioning Authority Login")');
  72  |     await expect(page.locator('text=Sanction Review')).toBeVisible(); // Stage 6
  73  |     await expect(page.locator('text=Approve Application')).toBeVisible();
  74  |     await page.screenshot({ path: '../docs/assets/screenshots/06-sanction-review.png' });
  75  | 
  76  |     // manual SA alternative-structure approval
  77  |     await page.click('button:has-text("Approve Application")');
  78  |     await expect(page.locator('text=SANCTIONED').or(page.locator('text=Sanctioned'))).toBeVisible();
  79  |   });
  80  | 
  81  |   test('NavPrerna evidence-request/defer path', async ({ page }) => {
  82  |     await page.goto('/demo');
  83  |     await page.click('button:has-text("Credit Analyst")');
  84  |     const row = page.locator('table tbody tr').filter({ hasText: 'Navprerna' }).first();
  85  |     await row.locator('a', { hasText: 'Open' }).click();
  86  |     
  87  |     const runEngine = page.locator('button:has-text("Run Assessment Engine")');
  88  |     if (await runEngine.isVisible()) {
  89  |       await runEngine.click();
  90  |     }
  91  |     
  92  |     await expect(page.locator('text=DEFER').or(page.locator('text=Defer'))).toBeVisible({ timeout: 15000 });
  93  |   });
  94  | 
  95  |   test('Aarohan decline/decline-after-review path', async ({ page }) => {
  96  |     await page.goto('/demo');
  97  |     await page.click('button:has-text("Credit Analyst")');
  98  |     const row = page.locator('table tbody tr').filter({ hasText: 'Aarohan' }).first();
  99  |     await row.locator('a', { hasText: 'Open' }).click();
  100 |     
  101 |     const runEngine = page.locator('button:has-text("Run Assessment Engine")');
  102 |     if (await runEngine.isVisible()) {
  103 |       await runEngine.click();
  104 |     }
  105 |     
  106 |     await expect(page.locator('text=DECLINE').or(page.locator('text=Decline'))).toBeVisible({ timeout: 15000 });
  107 |   });
  108 | 
  109 |   test('Rangrez frozen expected path', async ({ page }) => {
  110 |     await page.goto('/demo');
  111 |     await page.click('button:has-text("Credit Analyst")');
  112 |     const row = page.locator('table tbody tr').filter({ hasText: 'Rangrez' }).first();
  113 |     await row.locator('a', { hasText: 'Open' }).click();
  114 |     
  115 |     await expect(page.locator('text=DECLINED').or(page.locator('text=Declined')).or(page.locator('text=FROZEN'))).toBeVisible();
  116 |   });
  117 | 
  118 |   test('Assessment History does not crash', async ({ page }) => {
  119 |     await page.goto('/demo');
  120 |     await page.click('button:has-text("Credit Analyst")');
  121 |     const row = page.locator('table tbody tr').first();
  122 |     await row.locator('a', { hasText: 'Open' }).click();
  123 |     await page.click('button:has-text("Assessment History")');
  124 |     await expect(page.locator('text=Event Hash')).toBeVisible();
  125 |   });
  126 | 
  127 |   test('Auditor trace renders timestamps and hashes', async ({ page }) => {
  128 |     await page.goto('/demo');
  129 |     await page.click('button:has-text("Auditor")');
  130 |     await page.click('a[href="/audit"]');
  131 |     await expect(page.locator('text=Audit Log & CAS Trail')).toBeVisible();
  132 |     await expect(page.locator('text=202')).toBeVisible(); // Part of a timestamp
```