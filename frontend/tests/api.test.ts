import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from '../lib/api';

describe('apiFetch', () => {
  const originalFetch = global.fetch;
  const originalLocation = window.location;

  beforeEach(() => {
    global.fetch = vi.fn();
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { pathname: '/cases', href: 'http://localhost:3000/cases' },
    });
    document.cookie = '';
    localStorage.clear();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    });
    vi.restoreAllMocks();
  });

  it('uses credentials: "include" and default localhost:8000 URL', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ success: true }),
    });

    await apiFetch('/api/test');

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/test',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.any(Object),
      })
    );
  });

  it('extracts CSRF cookie and injects X-CSRF-Token for mutation requests', async () => {
    document.cookie = 'vyapar_csrf_token=test_token_val; other=123';
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ updated: true }),
    });

    await apiFetch('/api/cases/1/evaluate', {
      method: 'POST',
      body: JSON.stringify({ version: 1 }),
    });

    const callArgs = (global.fetch as any).mock.calls[0];
    const headers = callArgs[1].headers as Record<string, string>;
    expect(headers['X-CSRF-Token']).toBe('test_token_val');
    expect(headers['Content-Type']).toBe('application/json');
  });

  it('does NOT inject X-CSRF-Token for GET requests', async () => {
    document.cookie = 'vyapar_csrf_token=test_token_val';
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ([]),
    });

    await apiFetch('/api/cases');

    const callArgs = (global.fetch as any).mock.calls[0];
    const headers = callArgs[1].headers as Record<string, string>;
    expect(headers['X-CSRF-Token']).toBeUndefined();
  });

  it('clears localStorage and redirects on 401 when not on login page', async () => {
    localStorage.setItem('vyapar_user', JSON.stringify({ id: '123', email: 'test@bank.com' }));
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Unauthorized' }),
    });

    const res = await apiFetch('/api/cases');

    expect(res.status).toBe(401);
    expect(localStorage.getItem('vyapar_user')).toBeNull();
    expect(window.location.href).toBe('/login');
  });

  it('handles structured FastAPI detail error objects (STALE_VERSION, IDEMPOTENCY_IN_PROGRESS)', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 409,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        detail: {
          code: 'IDEMPOTENCY_IN_PROGRESS',
          message: 'An identical request is currently being processed.',
          retryable: true,
          retry_after_seconds: 5,
        },
      }),
    });

    const res = await apiFetch('/api/cases/1/evaluate', { method: 'POST' });

    expect(res.status).toBe(409);
    expect(res.error).toBe('IDEMPOTENCY_IN_PROGRESS: An identical request is currently being processed.');
    expect(res.data).toEqual({
      code: 'IDEMPOTENCY_IN_PROGRESS',
      message: 'An identical request is currently being processed.',
      retryable: true,
      retry_after_seconds: 5,
    });
  });

  it('handles STALE_VERSION structured error', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 409,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        detail: {
          code: 'STALE_VERSION',
          message: 'Case version conflict. Refresh required.',
        },
      }),
    });

    const res = await apiFetch('/api/cases/1/evaluate', { method: 'POST' });

    expect(res.status).toBe(409);
    expect(res.error).toBe('STALE_VERSION: Case version conflict. Refresh required.');
  });
});
