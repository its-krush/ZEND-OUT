document.documentElement.style.visibility = 'hidden';
window.ZenAuthReady = (async () => {
  if (!window.ZenAPI) throw new Error('API client unavailable');
  try {
    const profile = await ZenAPI.me();
    window.ZenAuthenticatedUser = profile;
    const pageName = location.pathname.split('/').pop().replace('.html','') || 'dashboard';
    const startedAt = Date.now();
    let recorded = false;
    const recordTime = () => {
      if (recorded) return;
      recorded = true;
      const seconds = Math.round((Date.now() - startedAt) / 1000);
      if (seconds > 0) ZenAPI.recordScreenTime(pageName, seconds).catch(() => {});
    };
    window.addEventListener('pagehide', recordTime, { once: true });
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') recordTime(); }, { once: true });
    document.documentElement.style.visibility = 'visible';
    return profile;
  } catch (_) {
    window.location.replace('index.html');
    throw _;
  }
})();
