import { request } from '@playwright/test';

async function run() {
  const ctx = await request.newContext();
  const backendUrl = 'http://127.0.0.1:8000';
  
  console.log('Sending reset directly to backend...');
  const resetRes = await ctx.post(`${backendUrl}/api/demo/reset`, {
    headers: {
      'X-Demo-Reset-Token': 'secret'
    }
  });
  console.log('Reset status:', resetRes.status());
  console.log('Reset text:', await resetRes.text());
}

run().catch(console.error);
