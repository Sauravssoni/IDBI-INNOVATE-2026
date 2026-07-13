import { request } from '@playwright/test';

async function run() {
  const ctx = await request.newContext();
  const apiUrl = 'http://localhost:3005';
  
  console.log('Logging in...');
  const loginRes = await ctx.post(`${apiUrl}/api/auth/demo/session`, {
    data: { role: 'CREDIT_ANALYST' }
  });
  console.log('Login status:', loginRes.status());
  
  if (loginRes.ok()) {
    const cookies = loginRes.headersArray().filter(h => h.name.toLowerCase() === 'set-cookie');
    let allCookies = [];
    let csrfToken = '';
    for (const cookie of cookies) {
      allCookies.push(cookie.value.split(';')[0]);
      if (cookie.value.includes('vyapar_csrf_token=')) {
        csrfToken = cookie.value.split(';')[0].replace('vyapar_csrf_token=', '');
      }
    }
    
    console.log('Sending reset...');
    const resetRes = await ctx.post(`${apiUrl}/api/demo/reset`, {
      headers: {
        'X-CSRF-Token': csrfToken,
        'X-Demo-Reset-Token': 'secret',
        'Cookie': allCookies.join('; ')
      }
    });
    console.log('Reset status:', resetRes.status());
    console.log('Reset text:', await resetRes.text());
  }
}

run().catch(console.error);
