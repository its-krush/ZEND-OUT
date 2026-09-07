(async () => {
  if (!window.ZenAPI) return;
  try {
    const profile = await ZenAPI.me();
    window.ZenAuthenticatedUser = profile;
  } catch (_) {
    window.location.href = 'index.html';
  }
})();
