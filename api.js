window.ZenAPI = (() => {
  const API_BASE = window.ZEN_API_BASE || (window.location.port === '8000' ? 'http://127.0.0.1:5000/api' : '/api');
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
    forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
    resetPassword: (token, password) => request('/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, password }) }),
    listJournals: () => request('/journals'),
    createJournal: (journal) => request('/journals', { method: 'POST', body: JSON.stringify(journal) }),
    updateJournal: (id, journal) => request(`/journals/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(journal) }),
    deleteJournal: (id) => request(`/journals/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    socialFeed: () => request('/social/feed'),
    socialUsers: () => request('/social/users'),
    toggleFollow: (username) => request(`/social/follow/${encodeURIComponent(username)}`, { method: 'POST' }),
    toggleLike: (postId) => request(`/social/posts/${encodeURIComponent(postId)}/like`, { method: 'POST' }),
    listComments: (postId) => request(`/social/posts/${encodeURIComponent(postId)}/comments`),
    createComment: (postId, text) => request(`/social/posts/${encodeURIComponent(postId)}/comments`, { method: 'POST', body: JSON.stringify({ text }) }),
    logout: () => request('/auth/logout', { method: 'POST' }),
    me: () => request('/auth/me'),
  };
})();
