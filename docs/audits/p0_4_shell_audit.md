# P0-4 Unified Shell Audit

Home preservation: `git diff --stat HEAD -- ui/index.html ui/home.js` produced no output. Baseline hashes remain `ui/index.html` `53bf82d252b50007de325fe2ffec0aa92f908650bad854ab84fdd834c00c1869` and `ui/home.js` `8f7c7e0221c2fb52cdea627cae3682308f88d9a58b07453e46f55ba4f22ac947`. `data/demo_replay.json` sha256 before and after P0-4: `93c05c662de4cc17cd1be5885f4d30465249649c2198d32cab00a8e7d160a745`.

Page disposition:

- `ui/index.html`: untouched home page; stays direct URL home.
- `ui/app.html`: new SPA shell entry.
- `ui/replays.html`: redirect stub to `app.html#/replays`.
- `ui/replay.html`: redirect stub to `app.html#/replays/:id`, preserving `?seed=`.
- `ui/garage.html`: redirect stub to `app.html#/garage`.
- `ui/reports.html`: redirect stub to `app.html#/reports`.
- `ui/arena.html`: redirect stub to `app.html#/arena`.

Render-function placement:

- Left rail: `left_rail.js` owns nav, identities, sessions, draft backend status.
- Center: `left_rail.js` updates route copy; `renderGallery` still fills the Film Room gallery.
- Right drawer: reused `renderHeader`, `renderReplayHero`, `renderPlayFeed`, `feedCard`, `renderInspectorTabs`, `renderInspectorPanel`, `renderOutcome`, `renderResources`, `renderGraphCards`, `renderBall`, `selectPlay`, `scrollFeedCard`, and `annotateReplay`.
- Shared utilities: `fetchReplayById`, `loadReplayIndex`, graph labels, motion helpers, and compare tray remain in `app.js`.

Tier-vocab findings removed or gated: `garage.html` visible tier selector became a redirect; `app.js` visible strings for `Tier 0`, `Tier 1`, `Tier 2`, and old phase copy were replaced with launch-safe local policy language; `empty_states.js` no longer says `Tier 0`; `gallery.js` no longer renders tier chips; topbar now routes Home to `index.html` and shell surfaces to `app.html`. The remaining `remote_endpoint` reference is inside legacy debug-gated code and not rendered by the launch shell.

Draft source of truth: `left_rail.js` loads `/v1/drafts` on shell load and writes backend/offline status into the Workbench route. The old localStorage draft helpers are not part of the default shell path; localStorage remains only a legacy/debug tab cache until P0-5 adds live draft editing.

Assistant seam choice: prompt textarea and Send are disabled with `Coming online - P0-5`. Clickable canonical prompt cards dispatch `coachbench:assistant:request`; Film Room and play-feed tweak actions dispatch the same event.

Manual smoke commands:

```bash
python -m uvicorn arena.api.app:app --host 127.0.0.1 --port 8766
python -m http.server 8765
```

Open `http://localhost:8765/ui/index.html` to confirm home is unchanged, `http://localhost:8765/ui/app.html` for the shell, and the five redirect stubs to confirm they land on `app.html#/<route>`. With the backend stopped, reload `app.html` and confirm offline left-rail states plus static Watch Film cards still render.

Automated verification run: targeted UI suite passed; `python -m pytest` passed `262 passed, 2 skipped`; static smoke on port `8790` confirmed `app.html` and the five redirect stubs served expected shell markup.
