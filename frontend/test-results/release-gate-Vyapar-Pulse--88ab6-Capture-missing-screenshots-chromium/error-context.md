# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: release-gate.spec.ts >> Vyapar Pulse Release Gate >> Capture missing screenshots
- Location: e2e/release-gate.spec.ts:169:7

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
          - generic [ref=e29]: Credit Analyst
          - generic [ref=e30]: (Credit Analyst)
        - button "Sign out of Vyapar Pulse" [ref=e31] [cursor=pointer]:
          - img [ref=e32]
    - generic [ref=e35]:
      - complementary [ref=e36]:
        - generic [ref=e37]:
          - generic [ref=e38]: Navigation & Workflows
          - link "Dashboard" [ref=e39] [cursor=pointer]:
            - /url: /
            - generic [ref=e40]:
              - img [ref=e41]
              - generic [ref=e46]: Dashboard
          - link "Case Inventory" [ref=e47] [cursor=pointer]:
            - /url: /cases
            - generic [ref=e48]:
              - img [ref=e49]
              - generic [ref=e51]: Case Inventory
          - link "Policy & Risk Engine AI" [ref=e52] [cursor=pointer]:
            - /url: /policy
            - generic [ref=e53]:
              - img [ref=e54]
              - generic [ref=e56]: Policy & Risk Engine
            - generic [ref=e57]: AI
        - generic [ref=e58]:
          - generic [ref=e59]:
            - img [ref=e60]
            - generic [ref=e63]: Governance & Access
          - paragraph [ref=e64]: Role-Scoped Access enforced. Tamper-evident prototype audit chain.
      - main [ref=e65]:
        - generic [ref=e67]:
          - generic [ref=e68]:
            - link "BACK TO CASE INVENTORY" [ref=e69] [cursor=pointer]:
              - /url: /cases
              - img [ref=e70]
              - generic [ref=e72]: BACK TO CASE INVENTORY
            - generic [ref=e73]:
              - img [ref=e74]
              - generic [ref=e77]: Hackathon prototype—not an official IDBI Bank production system
          - generic [ref=e80]:
            - img [ref=e82]
            - generic [ref=e86]:
              - generic [ref=e87]:
                - heading "Aarohan Infrastructure" [level=1] [ref=e88]
                - generic [ref=e89]: Assessment Completed
              - paragraph [ref=e90]:
                - generic [ref=e91]: "ID: 968b5c8a..."
                - text: •
          - generic [ref=e92]:
            - button "Overview" [ref=e93] [cursor=pointer]:
              - img [ref=e94]
              - generic [ref=e96]: Overview
            - button "Evidence Data" [ref=e97] [cursor=pointer]:
              - img [ref=e98]
              - generic [ref=e102]: Evidence Data
            - button "Reconciliation" [ref=e103] [cursor=pointer]:
              - img [ref=e104]
              - generic [ref=e108]: Reconciliation
            - button "Assessment History" [active] [ref=e109] [cursor=pointer]:
              - img [ref=e110]
              - generic [ref=e113]: Assessment History
          - generic [ref=e115]:
            - heading "Assessment History" [level=3] [ref=e116]:
              - img [ref=e117]
              - text: Assessment History
            - generic [ref=e121]:
              - img [ref=e123]
              - generic [ref=e126]:
                - generic [ref=e127]:
                  - generic [ref=e128]: evaluate
                  - generic [ref=e129]: 7/9/2026, 11:41:41 AM
                - generic [ref=e130]:
                  - generic [ref=e131]:
                    - img [ref=e132]
                    - generic [ref=e135]: 97716d42-7d4d-4fe3-aac4-2856b46d34ee
                    - generic [ref=e136]: SYSTEM
                  - generic [ref=e137]: "\"Automated Assessment\""
                  - generic [ref=e139]: "{ \"recommendation\": \"UNKNOWN\", \"binding_limit\": \"0\", \"dscr\": null, \"policy_version\": \"1.1\", \"calculation_version\": \"DSCR_SANDBOX_V1\" }"
        - generic [ref=e140]:
          - generic [ref=e141]: Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system
          - generic [ref=e142]: Illustrative prototype policy thresholds • Tamper-evident prototype audit chain
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