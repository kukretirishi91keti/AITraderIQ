import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getToken, getUser, isAuthenticated, login, logout, register, authFetch } from './auth';

globalThis.fetch = vi.fn();

describe('auth service', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('login stores token in localStorage', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'tok123', user: { id: 1 } }),
    });

    await login('testuser', 'pass123');
    expect(localStorage.getItem('traderai_token')).toBe('tok123');
  });

  it('login stores user in localStorage', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'tok123', user: { id: 1, username: 'testuser' } }),
    });

    await login('testuser', 'pass123');
    const user = getUser();
    expect(user).toEqual({ id: 1, username: 'testuser' });
  });

  it('logout clears localStorage', () => {
    localStorage.setItem('traderai_token', 'tok123');
    localStorage.setItem('traderai_user', JSON.stringify({ id: 1 }));

    logout();

    expect(getToken()).toBeNull();
    expect(getUser()).toBeNull();
  });

  it('isAuthenticated true when token exists', () => {
    localStorage.setItem('traderai_token', 'tok123');
    expect(isAuthenticated()).toBe(true);
  });

  it('isAuthenticated false when no token', () => {
    localStorage.clear();
    expect(isAuthenticated()).toBe(false);
  });

  it('authFetch adds Bearer header', async () => {
    localStorage.setItem('traderai_token', 'mytoken');
    fetch.mockResolvedValueOnce({ status: 200, ok: true, json: async () => ({}) });

    await authFetch('/test');

    expect(fetch).toHaveBeenCalledWith(
      '/test',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer mytoken',
        }),
      })
    );
  });

  it('authFetch auto-logout on 401', async () => {
    localStorage.setItem('traderai_token', 'expired');
    fetch.mockResolvedValueOnce({ status: 401, ok: false });

    await expect(authFetch('/test')).rejects.toThrow('Session expired');
    expect(getToken()).toBeNull();
  });

  it('register sends correct payload', async () => {
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ access_token: 'newtok', user: { id: 2, username: 'newuser' } }),
    });

    await register({ email: 'a@b.com', username: 'newuser', password: 'secret' });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/auth/register'),
      expect.objectContaining({
        method: 'POST',
        body: expect.any(String),
      })
    );

    const body = JSON.parse(fetch.mock.calls[0][1].body);
    expect(body.email).toBe('a@b.com');
    expect(body.username).toBe('newuser');
    expect(body.password).toBe('secret');
  });
});
