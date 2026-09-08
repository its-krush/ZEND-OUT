document.documentElement.style.visibility = 'hidden';
window.ZenAuthReady = (async () => {
  if (!window.ZenAPI) throw new Error('API client unavailable');
  try {
    const profile = await ZenAPI.me();
    window.ZenAuthenticatedUser = profile;
    document.documentElement.style.visibility = 'visible';
    return profile;
  } catch (_) {
    window.location.replace('index.html');
    throw _;
  }
})();
