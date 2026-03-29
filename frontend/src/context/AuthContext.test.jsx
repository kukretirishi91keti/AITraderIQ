import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';

const mockLogin = vi.fn();
const mockRegister = vi.fn();
const mockLogout = vi.fn();
const mockGetUser = vi.fn(() => null);
const mockIsAuthenticated = vi.fn(() => false);
const mockGetToken = vi.fn(() => null);

vi.mock('../services/auth', () => ({
  getUser: (...args) => mockGetUser(...args),
  isAuthenticated: (...args) => mockIsAuthenticated(...args),
  getToken: (...args) => mockGetToken(...args),
  login: (...args) => mockLogin(...args),
  register: (...args) => mockRegister(...args),
  logout: (...args) => mockLogout(...args),
}));

function TestConsumer() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="logged-in">{String(auth.isLoggedIn)}</span>
      <span data-testid="user">{auth.user ? auth.user.username : 'none'}</span>
      <button data-testid="login-btn" onClick={() => auth.login('testuser', 'pass')}>
        Login
      </button>
      <button data-testid="logout-btn" onClick={() => auth.logout()}>
        Logout
      </button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetUser.mockReturnValue(null);
    mockIsAuthenticated.mockReturnValue(false);
    mockGetToken.mockReturnValue(null);
  });

  it('initial state not logged in', () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('logged-in').textContent).toBe('false');
    expect(screen.getByTestId('user').textContent).toBe('none');
  });

  it('login updates state', async () => {
    mockLogin.mockResolvedValueOnce({
      access_token: 'tok',
      user: { id: 1, username: 'testuser' },
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await act(async () => {
      screen.getByTestId('login-btn').click();
    });

    expect(screen.getByTestId('logged-in').textContent).toBe('true');
    expect(screen.getByTestId('user').textContent).toBe('testuser');
  });

  it('logout clears state', async () => {
    // Start logged in
    mockGetUser.mockReturnValue({ id: 1, username: 'testuser' });
    mockIsAuthenticated.mockReturnValue(true);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('logged-in').textContent).toBe('true');

    await act(async () => {
      screen.getByTestId('logout-btn').click();
    });

    expect(screen.getByTestId('logged-in').textContent).toBe('false');
    expect(screen.getByTestId('user').textContent).toBe('none');
  });

  it('persists from localStorage', () => {
    mockGetUser.mockReturnValue({ id: 1, username: 'stored' });
    mockIsAuthenticated.mockReturnValue(true);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByTestId('logged-in').textContent).toBe('true');
    expect(screen.getByTestId('user').textContent).toBe('stored');
  });

  it('useAuth throws outside provider', () => {
    // Suppress console.error from React for the expected error
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => render(<TestConsumer />)).toThrow('useAuth must be used within AuthProvider');

    spy.mockRestore();
  });
});
