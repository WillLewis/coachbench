(() => {
  const $ = id => document.getElementById(id);
  const escapeHtml = raw => String(raw ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const label = raw => String(raw || '').replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());
  const riskValues = ['low', 'medium', 'high'];
  const runPassValues = ['balanced_pass', 'pass_heavy', 'run_to_play_action'];
  const numericControls = new Set(['adaptation_speed', 'screen_trigger_confidence', 'explosive_shot_tolerance', 'disguise_sensitivity', 'pressure_frequency', 'counter_repeat_tolerance']);
  const enumOptions = {
    risk_tolerance: riskValues,
    run_pass_tendency: runPassValues,
  };
  const IDEAS = {
    garage: [
      'Build an offense that punishes pressure without throwing picks.',
      'Make my defense disguise more without burning the rush budget.',
      'We got baited by simulated pressure. What should I change?',
      'Build a run-first coordinator that unlocks play-action.',
      'Give me a safe red-zone defense that prevents explosives.',
    ],
    replays: [
      'Show me where my belief flipped before the touchdown.',
      'Why did the agent abandon the run on 2nd & 6?',
      'Compare this drive to seed 311 — what changed?',
      'Highlight every adaptation event with a belief delta over 0.15.',
    ],
  };
  let parameterGlossary = {};
  let identities = [];
  let currentProposal = null;
  let editIndex = null;

  async function fetchJson(path, options) {
    const response = await fetch(path, options);
    if (!response.ok) {
      const body = await response.text().catch(() => '');
      throw new Error(body || `${path} ${response.status}`);
    }
    return response.json();
  }

  async function loadParameterGlossary() {
    if (Object.keys(parameterGlossary).length) return parameterGlossary;
    parameterGlossary = await fetchJson('../agent_garage/parameter_glossary.json').catch(() => ({
      risk_tolerance: {},
      adaptation_speed: {},
      screen_trigger_confidence: {},
      explosive_shot_tolerance: {},
      run_pass_tendency: {},
      disguise_sensitivity: {},
      pressure_frequency: {},
      counter_repeat_tolerance: {},
    }));
    return parameterGlossary;
  }

  async function loadIdentities() {
    if (identities.length) return identities;
    const payload = await fetchJson('/v1/identities').catch(() => ({ identities: [] }));
    identities = payload.identities || [];
    return identities;
  }

  function activeDraft() {
    const state = window.CBState?.get?.() || {};
    return (state.garageDrafts || []).find(draft => draft.id === state.activeDraftId) || null;
  }

  function configFor(draft) {
    return draft?.config_json && typeof draft.config_json === 'object' ? draft.config_json : null;
  }

  function setComposerStatus(copy) {
    const status = $('assistantStatus');
    if (status) status.textContent = copy;
  }

  const setStatus = setComposerStatus;

  function clearRouteEmpty() {
    const dock = $('proposalDock');
    if (!dock) return;
    if (dock.dataset.routeEmpty) {
      dock.innerHTML = '';
      delete dock.dataset.routeEmpty;
    }
  }

  function assistantRow(inner, extraClass = '') {
    return `<div class="chat-row ${extraClass}">
      <span class="chat-avatar" aria-hidden="true">CB</span>
      ${inner}
    </div>`;
  }

  function ideaKey(routeName) {
    return routeName === 'replay-detail' ? 'replays' : routeName;
  }

  function sparkleIcon(klass) {
    return `<svg class="${klass}" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5l1.6 4.4 4.4 1.6-4.4 1.6L8 13.5l-1.6-4.4-4.4-1.6 4.4-1.6L8 1.5z" fill="currentColor"/></svg>`;
  }

  function promptButton(text, klass = 'suggested-prompt') {
    return `<button class="${klass}" type="button" data-canonical-prompt="${escapeHtml(text)}">${escapeHtml(text)}</button>`;
  }

  function setIdeasOpen(open, returnFocus = false) {
    const panel = $('suggestedPromptsPanel');
    const toggle = $('ideasToggle');
    const labelNode = toggle?.querySelector('.ideas-toggle__label');
    if (!panel || !toggle) return;
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (labelNode) labelNode.textContent = open ? 'Hide ideas' : 'More ideas';
    if (open) {
      panel.querySelector('.ideas-card')?.focus();
    } else if (returnFocus) {
      toggle.focus();
    }
  }

  function dispatchIdea(text) {
    window.dispatchEvent(new CustomEvent('coachbench:assistant:request', { detail: { type: 'canonical_prompt', text } }));
    setIdeasOpen(false, false);
    $('assistantPrompt')?.focus();
  }

  function bindIdeaButtons(root = document) {
    root.querySelectorAll('[data-canonical-prompt]').forEach(button => {
      button.onclick = () => dispatchIdea(button.dataset.canonicalPrompt);
    });
  }

  function renderIdeas(routeName) {
    const container = document.querySelector('.composer-ideas');
    const inline = $('ideasInline');
    const grid = $('ideasGrid');
    if (!container || !inline || !grid) return;
    const ideas = IDEAS[ideaKey(routeName)] || [];
    container.hidden = ideas.length === 0;
    setIdeasOpen(false, false);
    if (!ideas.length) {
      inline.innerHTML = '';
      grid.innerHTML = '';
      return;
    }
    inline.innerHTML = ideas.slice(0, 2).map(text => promptButton(text)).join('');
    grid.innerHTML = ideas.map(text => `<button class="ideas-card" type="button" data-canonical-prompt="${escapeHtml(text)}">
      ${sparkleIcon('ideas-card__sparkle')}
      <span>${escapeHtml(text)}</span>
    </button>`).join('');
    bindIdeaButtons(container);
  }

  function bindIdeasPanel() {
    const container = document.querySelector('.composer-ideas');
    const toggle = $('ideasToggle');
    const close = $('closeIdeasPanel');
    if (!container || !toggle || !close) return;
    toggle.addEventListener('click', event => {
      event.stopPropagation();
      setIdeasOpen(toggle.getAttribute('aria-expanded') !== 'true', false);
    });
    close.addEventListener('click', () => setIdeasOpen(false, true));
    container.addEventListener('click', event => event.stopPropagation());
    document.addEventListener('click', event => {
      const panel = $('suggestedPromptsPanel');
      if (!panel || panel.hidden || container.contains(event.target)) return;
      setIdeasOpen(false, true);
    });
    document.addEventListener('keydown', event => {
      const panel = $('suggestedPromptsPanel');
      if (event.key === 'Escape' && panel && !panel.hidden) setIdeasOpen(false, true);
    });
  }

  function renderOffline(message) {
    currentProposal = null;
    const dock = $('proposalDock');
    if (dock) {
      delete dock.dataset.routeEmpty;
      dock.innerHTML = assistantRow(`<article class="proposal-card proposal-card--offline">
          <strong>Backend offline</strong>
          <p>${escapeHtml(message || 'Assistant unavailable until the local backend is running.')}</p>
        </article>`);
    }
    setStatus('Backend offline - Assistant unavailable.');
  }

  function proposalContext(detail) {
    const state = window.CBState?.get?.() || {};
    const context = {
      request_type: detail.type,
      current_draft_id: state.activeDraftId || null,
      selected_identity_id: state.selectedIdentityId || null,
    };
    if (detail.run_id) context.current_run_id = detail.run_id;
    if (detail.play_index) context.selected_play_index = Number(detail.play_index);
    if (detail.user_override) context.user_override = detail.user_override;
    return context;
  }

  async function requestProposal(detail) {
    clearRouteEmpty();
    setStatus('Generating structured proposal...');
    const payload = {
      prompt: detail.text || '',
      context: proposalContext(detail),
    };
    const response = await fetchJson('/v1/assistant/propose', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    });
    currentProposal = response.proposal;
    editIndex = null;
    await renderProposal(currentProposal);
    updateProposalStatus();
  }

  async function handleRequest(event) {
    const detail = event.detail || {};
    if (detail.type === 'identity_selected') {
      const rows = await loadIdentities();
      const selected = rows.find(item => item.id === detail.identity_id);
      renderClarify(selected
        ? `Selected ${selected.display_name}. Tell me whether this draft should play offense or defense and how it should behave.`
        : 'Identity selected. Tell me what kind of coordinator to build.');
      return;
    }
    try {
      await requestProposal(detail);
    } catch (error) {
      renderOffline(readableError(error));
    }
  }

  function readableError(error) {
    try {
      const parsed = JSON.parse(error.message);
      return parsed.detail?.error?.message || error.message;
    } catch {
      return error.message || 'Assistant request failed.';
    }
  }

  function renderClarify(summary) {
    currentProposal = null;
    const dock = $('proposalDock');
    if (!dock) return;
    delete dock.dataset.routeEmpty;
    dock.innerHTML = assistantRow(`<article class="proposal-card proposal-card--clarify">
        <p class="eyebrow">Assistant</p>
        <h3>Clarify the request</h3>
        <p>${escapeHtml(summary)}</p>
        <button class="btn" type="button" data-focus-prompt>Reply to assistant</button>
      </article>`);
    dock.querySelector('[data-focus-prompt]')?.addEventListener('click', () => $('assistantPrompt')?.focus());
    setStatus('Assistant needs one more detail.');
  }

  function prettyParameter(parameter) {
    return label(parameter);
  }

  function changeInput(change, index) {
    if (enumOptions[change.parameter]) {
      return `<select data-edit-input="${index}">${enumOptions[change.parameter].map(value => `<option value="${escapeHtml(value)}" ${value === change.to ? 'selected' : ''}>${escapeHtml(label(value))}</option>`).join('')}</select>`;
    }
    const value = Number(change.to);
    return `<input data-edit-input="${index}" type="number" min="0" max="1" step="0.01" value="${Number.isFinite(value) ? value : 0.5}">`;
  }

  function formatValue(raw) {
    if (raw === null || raw === undefined) return 'new';
    if (typeof raw === 'number') return `${Math.round(raw * 100)}%`;
    return label(raw);
  }

  function numericOptionLabel(value, index) {
    if (index === 0) return `Conservative · ${value.toFixed(2)}`;
    if (index === 2) return `Aggressive · ${value.toFixed(2)}`;
    return `Balanced · ${value.toFixed(2)}`;
  }

  function optionValuesFor(change) {
    if (enumOptions[change.parameter]) {
      const base = [...enumOptions[change.parameter]];
      if (change.to && !base.includes(change.to)) base[Math.min(1, base.length - 1)] = change.to;
      return base.map(value => ({
        label: label(value),
        value,
        recommended: value === change.to,
      }));
    }
    if (numericControls.has(change.parameter)) {
      const to = Number(change.to);
      const mid = Number.isFinite(to) ? to : 0.5;
      return [Math.max(0, mid - 0.2), mid, Math.min(1, mid + 0.2)].map((value, index) => ({
        label: numericOptionLabel(value, index),
        value: Number(value.toFixed(2)),
        recommended: index === 1,
      }));
    }
    return [{ label: formatValue(change.to), value: change.to, recommended: true }];
  }

  function checkIcon() {
    return '<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><rect x="2.5" y="2.5" width="11" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M5 8l2 2 4-5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  }

  function updateProposalStatus() {
    const total = currentProposal?.proposed_changes?.length || 0;
    const resolved = (currentProposal?.proposed_changes || []).filter(change => change.__resolved).length;
    setStatus(`${resolved}/${total} POLICY PARAMS RESOLVED`);
  }

  function proposalMode(proposal) {
    if (proposal.intent === 'clarify') return 'clarify';
    if (proposal.intent === 'tweak') return 'tweak';
    return 'create';
  }

  async function renderProposal(proposal) {
    await loadParameterGlossary();
    const dock = $('proposalDock');
    if (!dock) return;
    if (!proposal || proposal.intent === 'clarify') {
      renderClarify(proposal?.summary || 'I need a bit more detail before proposing a policy change.');
      return;
    }
    const mode = proposalMode(proposal);
    const changes = proposal.proposed_changes || [];
    if (!changes.length && proposal.intent !== 'save_as_new') {
      renderClarify('No proposed changes remain. Send another prompt to continue.');
      return;
    }
    delete dock.dataset.routeEmpty;
    dock.innerHTML = `<article class="proposal-card" data-proposal-mode="${escapeHtml(mode)}">
      ${assistantRow(`<div class="chat-text">
        <p class="eyebrow">${escapeHtml(label(proposal.intent))} proposal</p>
        <h3>${escapeHtml(proposal.summary)}</h3>
        ${proposal.intent === 'tweak' ? '<span class="validation-badge is-ok">Draft update</span>' : '<span class="validation-badge is-ok">New saved draft</span>'}
      </div>`)}
      ${proposal.intent === 'tweak' ? '' : assistantRow(`<label class="draft-name-field"><span>Draft name</span><input id="proposalDraftName" type="text" value="${escapeHtml(defaultDraftName(proposal))}"></label>`)}
      <div class="proposal-change-list">
        ${changes.map((change, index) => changeRow(change, index)).join('')}
      </div>
      <div class="proposal-actions">
        <button class="btn btn--primary" type="button" data-accept-proposal>Accept</button>
        <button class="btn" type="button" data-clear-proposal>Clear</button>
      </div>
    </article>`;
    bindProposalActions();
    updateProposalStatus();
  }

  function defaultDraftName(proposal) {
    const identity = identities.find(item => item.id === proposal.target_identity_id);
    const prefix = identity ? identity.display_name : `Assistant ${label(proposal.target_side)}`;
    return prefix.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'assistant-draft';
  }

  function changeRow(change, index) {
    const glossary = parameterGlossary[change.parameter] || {};
    const helper = glossary.football_terms || change.reason;
    const options = optionValuesFor(change);
    const editor = editIndex === index
      ? `<div class="proposal-edit-row">${changeInput(change, index)}<button class="btn" type="button" data-commit-edit="${index}">Apply edit</button></div>`
      : '';
    return assistantRow(`<article class="param-card" data-change-index="${index}">
      <header class="param-card__head">
        <span class="param-card__check">${checkIcon()}</span>
        <strong>${escapeHtml(prettyParameter(change.parameter))}</strong>
      </header>
      <p class="param-card__desc">${escapeHtml(helper)}</p>
      <div class="param-card__options">
        ${options.map(option => `<button class="param-option ${option.recommended ? 'is-recommended' : ''} ${change.__resolved && String(option.value) === String(change.to) ? 'is-selected' : ''}" type="button" data-commit-edit="${index}" data-value="${escapeHtml(option.value)}">
          ${escapeHtml(option.label)}${option.recommended ? ' <span class="param-option__badge">Recommended</span>' : ''}
        </button>`).join('')}
        <button class="param-option param-option--ghost" type="button" data-reject-change="${index}" data-skip-change>Skip</button>
        <button class="sr-only" type="button" data-edit-change="${index}">Edit custom value</button>
      </div>
      ${editor}
    </article>`, 'chat-row--system');
  }

  function bindProposalActions() {
    const dock = $('proposalDock');
    dock?.querySelector('[data-accept-proposal]')?.addEventListener('click', acceptProposal);
    dock?.querySelector('[data-clear-proposal]')?.addEventListener('click', () => {
      currentProposal = null;
      editIndex = null;
      dock.innerHTML = '';
      delete dock.dataset.routeEmpty;
      setStatus('Ready for a prompt.');
    });
    dock?.querySelectorAll('[data-reject-change]').forEach(button => {
      button.addEventListener('click', async () => {
        currentProposal.proposed_changes.splice(Number(button.dataset.rejectChange), 1);
        editIndex = null;
        await renderProposal(currentProposal);
      });
    });
    dock?.querySelectorAll('[data-edit-change]').forEach(button => {
      button.addEventListener('click', async () => {
        editIndex = Number(button.dataset.editChange);
        await renderProposal(currentProposal);
      });
    });
    dock?.querySelectorAll('[data-commit-edit]').forEach(button => {
      button.addEventListener('click', async () => {
        const index = Number(button.dataset.commitEdit);
        const input = dock.querySelector(`[data-edit-input="${index}"]`);
        if (!currentProposal?.proposed_changes?.[index]) return;
        const change = currentProposal.proposed_changes[index];
        const rawValue = button.dataset.value ?? input?.value;
        if (rawValue === undefined) return;
        const next = numericControls.has(change.parameter) ? Number(rawValue) : rawValue;
        if (numericControls.has(change.parameter) && (!Number.isFinite(next) || next < 0 || next > 1)) {
          setStatus('Edit must be a value from 0 to 1.');
          return;
        }
        change.to = numericControls.has(change.parameter) ? Number(next.toFixed(2)) : next;
        change.__resolved = true;
        editIndex = null;
        await renderProposal(currentProposal);
      });
    });
  }

  async function acceptProposal() {
    if (!currentProposal) return;
    const draftName = $('proposalDraftName')?.value || defaultDraftName(currentProposal);
    setStatus('Saving validated draft...');
    try {
      const sanitizedProposal = {
        ...currentProposal,
        proposed_changes: (currentProposal.proposed_changes || []).map(({ __resolved, ...change }) => change),
      };
      const payload = await fetchJson('/v1/assistant/accept', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ proposal: sanitizedProposal, draft_name: draftName }),
      });
      const draft = payload.draft;
      await refreshDrafts(draft.id);
      currentProposal = null;
      editIndex = null;
      const dock = $('proposalDock');
      if (dock) {
        delete dock.dataset.routeEmpty;
        dock.innerHTML = assistantRow(`<article class="proposal-card proposal-card--saved">
          <strong>Draft saved</strong>
          <p>${escapeHtml(draft.name)} v${escapeHtml(draft.version)} is now active.</p>
        </article>`);
      }
      setStatus('Draft saved through the local backend.');
    } catch (error) {
      renderOffline(readableError(error));
    }
  }

  async function refreshDrafts(activeDraftId = null) {
    try {
      const payload = await fetchJson('/v1/drafts');
      const drafts = payload.drafts || [];
      const nextActive = activeDraftId || window.CBState?.get?.().activeDraftId || null;
      window.CBState?.set({
        garageDrafts: drafts,
        garageDraftSource: 'backend',
        activeDraftId: drafts.some(draft => draft.id === nextActive) ? nextActive : null,
      });
      renderDraftList();
      renderActiveConfigPanel();
      window.CBLeftRail?.refresh?.();
    } catch {
      window.CBState?.set({ garageDraftSource: 'offline' });
      renderDraftList();
      renderActiveConfigPanel();
    }
  }

  function renderDraftList() {
    const target = $('assistantDraftList');
    if (!target) return;
    const state = window.CBState?.get?.() || {};
    const drafts = state.garageDrafts || [];
    if (state.garageDraftSource === 'offline') {
      target.innerHTML = '<p class="offline-state">Backend offline. Draft persistence unavailable.</p>';
      return;
    }
    target.innerHTML = drafts.length
      ? drafts.map(draft => {
          const config = configFor(draft) || {};
          const active = draft.id === state.activeDraftId;
          return `<button class="draft-select-row ${active ? 'active' : ''}" type="button" data-active-draft="${escapeHtml(draft.id)}">
            <strong>${escapeHtml(draft.name)}</strong>
            <span>${escapeHtml(label(config.side || draft.side_eligibility))} · v${escapeHtml(draft.version)}</span>
          </button>`;
        }).join('')
      : '<p class="offline-state">No saved drafts yet. Use a suggested prompt to create one.</p>';
    target.querySelectorAll('[data-active-draft]').forEach(button => {
      button.addEventListener('click', () => {
        window.CBState?.set({ activeDraftId: button.dataset.activeDraft });
        renderDraftList();
        renderActiveConfigPanel();
      });
    });
  }

  function renderActiveConfigPanel() {
    const target = $('activeConfigPanel');
    if (!target) return;
    const draft = activeDraft();
    if (!draft) {
      target.innerHTML = `<details class="config-details"><summary>Active draft config</summary><p class="muted compact">No active draft selected.</p></details>`;
      return;
    }
    const config = configFor(draft) || {};
    const assistantParams = config.constraints?.assistant_parameters || {};
    const rows = Object.entries(assistantParams).length
      ? Object.entries(assistantParams).map(([key, raw]) => `<div class="kv"><span>${escapeHtml(label(key))}</span><span>${escapeHtml(formatValue(raw))}</span></div>`).join('')
      : Object.entries(config).filter(([, raw]) => typeof raw !== 'object').map(([key, raw]) => `<div class="kv"><span>${escapeHtml(label(key))}</span><span>${escapeHtml(formatValue(raw))}</span></div>`).join('');
    target.innerHTML = `<details class="config-details" open>
      <summary>Active draft config · ${escapeHtml(draft.name)} v${escapeHtml(draft.version)}</summary>
      <div class="config-grid">${rows || '<p class="muted compact">No inspectable parameters.</p>'}</div>
    </details>`;
  }

  function bindPromptForm() {
    const form = $('assistantPromptForm');
    const textarea = $('assistantPrompt');
    const send = form?.querySelector('button[type="submit"]');
    if (!form || !textarea || !send) return;
    textarea.disabled = false;
    send.disabled = false;
    textarea.addEventListener('keydown', event => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        if (!send.disabled) form.requestSubmit();
      }
    });
    form.onsubmit = event => {
      event.preventDefault();
      const text = textarea.value.trim();
      if (!text) return;
      textarea.value = '';
      clearRouteEmpty();
      window.dispatchEvent(new CustomEvent('coachbench:assistant:request', { detail: { type: 'free_text', text } }));
    };
    updateComposerForRoute(window.CBRouter?.current?.());
  }

  function updateComposerForRoute(route) {
    const form = $('assistantPromptForm');
    const textarea = $('assistantPrompt');
    const send = form?.querySelector('button[type="submit"]');
    if (!form || !textarea || !send || !route) return;
    renderIdeas(route.name);
    const replayLoaded = route.name === 'replay-detail';
    const filmEmpty = route.name === 'replays';
    textarea.disabled = false;
    send.disabled = filmEmpty;
    if (filmEmpty) {
      setStatus('NO FILM LOADED');
    } else if (replayLoaded) {
      const matchup = $('replayHeroMatchup')?.textContent;
      setStatus(matchup && matchup !== '-' ? `LOADED · ${matchup.toUpperCase()}` : 'LOADED FILM');
    } else if (route.name === 'garage' && currentProposal) {
      updateProposalStatus();
    } else if (!currentProposal) {
      setStatus('0/3 POLICY PARAMS RESOLVED');
    }
  }

  function bindGarageButtons() {
    $('newDraftButton')?.addEventListener('click', () => {
      window.CBState?.set({ activeDraftId: null });
      renderDraftList();
      renderActiveConfigPanel();
      $('assistantPrompt')?.focus();
      setStatus('New draft mode. Send a prompt to create a saved draft.');
    });
    $('saveDraftButton')?.addEventListener('click', async () => {
      const draft = activeDraft();
      if (!draft) {
        renderClarify('Select an active draft before saving a copy.');
        return;
      }
      const config = configFor(draft) || {};
      currentProposal = {
        summary: 'Save a new copy of the active draft.',
        intent: 'save_as_new',
        target_draft_id: draft.id,
        target_tier: draft.tier || config.access_tier || 'declarative',
        target_side: config.side || draft.side_eligibility,
        target_identity_id: draft.identity_id || null,
        proposed_changes: [],
        evidence_refs: [],
        requires_confirmation: true,
      };
      editIndex = null;
      await renderProposal(currentProposal);
    });
  }

  function init() {
    if (!$('appRoot')?.hasAttribute('data-shell-root')) return;
    bindIdeasPanel();
    bindPromptForm();
    bindGarageButtons();
    window.CBRouter?.subscribe?.(updateComposerForRoute);
    window.addEventListener('coachbench:assistant:request', handleRequest);
    window.CBState?.subscribe(() => {
      renderDraftList();
      renderActiveConfigPanel();
    });
    loadParameterGlossary();
    loadIdentities();
    refreshDrafts();
    renderDraftList();
    renderActiveConfigPanel();
  }

  window.CBAssistant = { refreshDrafts, renderDraftList, renderActiveConfigPanel, setComposerStatus };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
