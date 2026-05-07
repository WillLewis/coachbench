(async () => {
  window.CBTopbar?.renderTopbar('replays');
  try {
    const manifest = await fetch('showcase_manifest.json').then(response => response.json());
    CBGallery.render('replayGallery', manifest);
  } catch {
    document.getElementById('replayGallery').innerHTML =
      '<p class="muted">Failed to load showcase manifest. Run <code>python scripts/run_showcase.py</code>.</p>';
  }
})();
