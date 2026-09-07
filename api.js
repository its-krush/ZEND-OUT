window.ZenAPI = (() => {
  const API_BASE = window.ZEN_API_BASE || '/api';
  let csrfToken;
  async function getCsrfToken() {
    if (csrfToken) return csrfToken;
    const response = await fetch(`${API_BASE}/csrf-token`, { credentials: 'include' });
    csrfToken = (await response.json()).csrf_token;
    return csrfToken;
  }
  async function request(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRFToken'] = await getCsrfToken();
    const response = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',
      headers,
      ...options,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || 'request_failed');
    return body;
  }
  return {
    login: (identifier, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ identifier, password }) }),
    register: (username, email, password) => request('/auth/register', { method: 'POST', body: JSON.stringify({ username, email, password }) }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    me: () => request('/auth/me'),
  };
})();
