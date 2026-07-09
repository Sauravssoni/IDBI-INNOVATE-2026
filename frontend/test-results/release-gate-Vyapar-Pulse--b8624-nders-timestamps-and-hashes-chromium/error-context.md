# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: release-gate.spec.ts >> Vyapar Pulse Release Gate >> Auditor trace renders timestamps and hashes
- Location: e2e/release-gate.spec.ts:127:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=Audit Log & CAS Trail')
Expected: visible
Error: strict mode violation: locator('text=Audit Log & CAS Trail') resolved to 2 elements:
    1) <span>Audit Log & CAS Trail</span> aka getByRole('link', { name: 'Audit Log & CAS Trail' })
    2) <span>Audit Log & CAS Trail</span> aka getByRole('heading').getByText('Audit Log & CAS Trail')

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=Audit Log & CAS Trail')

```

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
          - generic [ref=e29]: Auditor
          - generic [ref=e30]: (AUDITOR)
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
          - link "Audit Log & CAS Trail" [active] [ref=e52] [cursor=pointer]:
            - /url: /audit
            - generic [ref=e53]:
              - img [ref=e54]
              - generic [ref=e58]: Audit Log & CAS Trail
        - generic [ref=e59]:
          - generic [ref=e60]:
            - img [ref=e61]
            - generic [ref=e64]: Governance & Access
          - paragraph [ref=e65]: Role-Scoped Access enforced. Tamper-evident prototype audit chain.
      - main [ref=e66]:
        - generic [ref=e68]:
          - generic [ref=e69]:
            - generic [ref=e70]:
              - generic [ref=e71]:
                - img [ref=e72]
                - generic [ref=e75]: TAMPER-EVIDENT AUDIT CHAIN • BUILT FOR IDBI INNOVATE 2026
              - heading "Audit Log & CAS Trail" [level=1] [ref=e76]:
                - img [ref=e77]
                - generic [ref=e81]: Audit Log & CAS Trail
              - paragraph [ref=e82]: Sequential audit trail of credit evaluations, BOLA authorization checks, and sanction decisions.
            - button "Refresh Ledger" [ref=e83] [cursor=pointer]:
              - img [ref=e84]
              - generic [ref=e89]: Refresh Ledger
          - table [ref=e92]:
            - rowgroup [ref=e93]:
              - row "Event Ref & Timestamp Actor / Role Action Executed Target Resource Tamper-Evident Audit Hash" [ref=e94]:
                - columnheader "Event Ref & Timestamp" [ref=e95]
                - columnheader "Actor / Role" [ref=e96]
                - columnheader "Action Executed" [ref=e97]
                - columnheader "Target Resource" [ref=e98]
                - columnheader "Tamper-Evident Audit Hash" [ref=e99]
            - rowgroup [ref=e100]:
              - row "97e25df6-596f-4de6-bde5-1392473c4ac2 9/7/2026, 11:41:54 am 97716d42-7d4d-4fe3-aac4-2856b46d34ee evaluate Case fc9be520-44de-4fea-a585-9c4a592e423d d4fe034f7c6f97df...f16a2499" [ref=e101]:
                - cell "97e25df6-596f-4de6-bde5-1392473c4ac2 9/7/2026, 11:41:54 am" [ref=e102]:
                  - generic [ref=e103]: 97e25df6-596f-4de6-bde5-1392473c4ac2
                  - generic [ref=e104]: 9/7/2026, 11:41:54 am
                - cell "97716d42-7d4d-4fe3-aac4-2856b46d34ee" [ref=e105]
                - cell "evaluate" [ref=e106]
                - cell "Case fc9be520-44de-4fea-a585-9c4a592e423d" [ref=e107]
                - cell "d4fe034f7c6f97df...f16a2499" [ref=e108]
              - row "c2c20ff3-efe1-473a-8206-c555da6401e2 9/7/2026, 11:41:41 am 97716d42-7d4d-4fe3-aac4-2856b46d34ee evaluate Case 968b5c8a-f3f8-472c-aa98-95c7ce2169c6 74a0c65d755c92f0...9a2b2eb4" [ref=e109]:
                - cell "c2c20ff3-efe1-473a-8206-c555da6401e2 9/7/2026, 11:41:41 am" [ref=e110]:
                  - generic [ref=e111]: c2c20ff3-efe1-473a-8206-c555da6401e2
                  - generic [ref=e112]: 9/7/2026, 11:41:41 am
                - cell "97716d42-7d4d-4fe3-aac4-2856b46d34ee" [ref=e113]
                - cell "evaluate" [ref=e114]
                - cell "Case 968b5c8a-f3f8-472c-aa98-95c7ce2169c6" [ref=e115]
                - cell "74a0c65d755c92f0...9a2b2eb4" [ref=e116]
              - row "dacf8764-0ffb-4c5d-b358-5bf7a0bf94dc 9/7/2026, 11:41:41 am 97716d42-7d4d-4fe3-aac4-2856b46d34ee analyst_recommendation Case ecb0249a-e619-4755-bad3-15fa83b8ba3d 82e0ccce6da9ffbd...54c29b9a" [ref=e117]:
                - cell "dacf8764-0ffb-4c5d-b358-5bf7a0bf94dc 9/7/2026, 11:41:41 am" [ref=e118]:
                  - generic [ref=e119]: dacf8764-0ffb-4c5d-b358-5bf7a0bf94dc
                  - generic [ref=e120]: 9/7/2026, 11:41:41 am
                - cell "97716d42-7d4d-4fe3-aac4-2856b46d34ee" [ref=e121]
                - cell "analyst_recommendation" [ref=e122]
                - cell "Case ecb0249a-e619-4755-bad3-15fa83b8ba3d" [ref=e123]
                - cell "82e0ccce6da9ffbd...54c29b9a" [ref=e124]
              - row "40adc043-461a-4171-be77-1216484ef02e 9/7/2026, 11:41:41 am 97716d42-7d4d-4fe3-aac4-2856b46d34ee evaluate Case ecb0249a-e619-4755-bad3-15fa83b8ba3d 5aeb18310716cfd9...4e9b9490" [ref=e125]:
                - cell "40adc043-461a-4171-be77-1216484ef02e 9/7/2026, 11:41:41 am" [ref=e126]:
                  - generic [ref=e127]: 40adc043-461a-4171-be77-1216484ef02e
                  - generic [ref=e128]: 9/7/2026, 11:41:41 am
                - cell "97716d42-7d4d-4fe3-aac4-2856b46d34ee" [ref=e129]
                - cell "evaluate" [ref=e130]
                - cell "Case ecb0249a-e619-4755-bad3-15fa83b8ba3d" [ref=e131]
                - cell "5aeb18310716cfd9...4e9b9490" [ref=e132]
              - row "a049ddd9-7044-4a0e-8946-5ff1b4477844 9/7/2026, 11:41:41 am 97716d42-7d4d-4fe3-aac4-2856b46d34ee evaluate Case 5b2a2dde-c996-4abf-b136-21a63d15a20f 27b9e46346f49620...c11d12c7" [ref=e133]:
                - cell "a049ddd9-7044-4a0e-8946-5ff1b4477844 9/7/2026, 11:41:41 am" [ref=e134]:
                  - generic [ref=e135]: a049ddd9-7044-4a0e-8946-5ff1b4477844
                  - generic [ref=e136]: 9/7/2026, 11:41:41 am
                - cell "97716d42-7d4d-4fe3-aac4-2856b46d34ee" [ref=e137]
                - cell "evaluate" [ref=e138]
                - cell "Case 5b2a2dde-c996-4abf-b136-21a63d15a20f" [ref=e139]
                - cell "27b9e46346f49620...c11d12c7" [ref=e140]
        - generic [ref=e141]:
          - generic [ref=e142]: Built for IDBI Innovate 2026 • Hackathon prototype—not an official IDBI Bank production system
          - generic [ref=e143]: Illustrative prototype policy thresholds • Tamper-evident prototype audit chain
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