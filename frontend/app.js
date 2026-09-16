const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

// Application State
let activeCampaignId = null;
let currentCampaign = null;
let currentLeads = [];
let currentDrafts = [];
let workspaceProfile = null;
let activeTab = 'view-pipeline';
let isTableView = false;
let runningPollInterval = null;

// Toast Notification Helper
function showToast(message, type = 'info') {
  const container = $('#toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  
  let icon = '✨';
  if (type === 'success') icon = '✓';
  if (type === 'error') icon = '✕';
  
  toast.innerHTML = `<span>${icon}</span><span>${esc(message)}</span>`;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.2s ease';
    setTimeout(() => toast.remove(), 200);
  }, 2800);
}

// REST API Helper
async function request(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Request failed with status ${response.status}`);
    }
    return response.status === 204 ? null : response.json();
  } catch (err) {
    console.error(`API Error [${url}]:`, err);
    throw err;
  }
}

function getFormData(form) {
  return Object.fromEntries(new FormData(form));
}

// Navigation & View Switching
function switchView(viewId) {
  $$('.view-panel').forEach((panel) => panel.classList.remove('active'));
  const target = $(`#${viewId}`);
  if (target) target.classList.add('active');

  // Update tabs if in campaign mode
  $$('.workspace-tab-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.view === viewId);
  });
}

function updateNavbarState(campaign) {
  const title = $('#nav-campaign-title');
  const badge = $('#nav-status-badge');
  const statusText = $('#nav-status-text');
  const tabs = $('#nav-campaign-tabs');
  const activeActions = $('#nav-active-actions');
  const runBtn = $('#btn-nav-run-campaign');
  const runText = $('#btn-nav-run-text');
  const deleteBtn = $('#btn-nav-delete-campaign');

  if (!campaign) {
    title.textContent = 'New Campaign';
    badge.className = 'navbar-status-badge';
    badge.querySelector('.status-dot').className = 'status-dot created';
    statusText.textContent = 'Agent Ready';
    tabs.hidden = true;
    if (activeActions) activeActions.hidden = true;
    return;
  }

  title.textContent = campaign.name;
  tabs.hidden = false;
  if (activeActions) activeActions.hidden = false;

  const st = (campaign.status || 'Created').toLowerCase();
  badge.className = 'navbar-status-badge';
  const dot = badge.querySelector('.status-dot');
  const isRunning = ['queued', 'researching', 'qualifying', 'drafting'].includes(st);

  if (isRunning) {
    badge.classList.add('running');
    dot.className = 'status-dot running';
    statusText.textContent = campaign.status;
  } else if (st === 'awaiting approval' || st === 'awaiting') {
    badge.classList.add('awaiting');
    dot.className = 'status-dot awaiting';
    statusText.textContent = 'Awaiting Review';
  } else if (st === 'failed') {
    badge.classList.add('failed');
    dot.className = 'status-dot failed';
    statusText.textContent = 'Failed';
  } else {
    dot.className = 'status-dot created';
    statusText.textContent = campaign.status;
  }

  if (runBtn && runText) {
    runBtn.disabled = isRunning;
    runText.textContent = campaign.status === 'Created' ? 'Run Campaign' : 'Rerun Campaign';
    runBtn.onclick = async () => {
      try {
        await request(`/api/campaigns/${campaign.id}/run`, { method: 'POST' });
        showToast('Campaign execution started', 'success');
        await refresh();
      } catch (err) {
        showToast(err.message, 'error');
      }
    };
  }

  if (deleteBtn) {
    deleteBtn.disabled = isRunning;
    deleteBtn.onclick = () => deleteCampaign(campaign.id, campaign.name);
  }
}

// In-App Custom Confirmation Helper
function promptConfirm({ title = 'Confirm Action', message = 'Are you sure you want to proceed?', confirmText = 'Delete Campaign', isDanger = true }) {
  return new Promise((resolve) => {
    const modal = $('#confirm-modal');
    if (!modal) {
      resolve(window.confirm(message));
      return;
    }

    $('#confirm-modal-title').textContent = title;
    $('#confirm-modal-msg').textContent = message;

    const proceedBtn = $('#confirm-btn-proceed');
    const cancelBtn = $('#confirm-btn-cancel');

    proceedBtn.textContent = confirmText;
    if (isDanger) {
      proceedBtn.className = 'btn-danger';
      proceedBtn.style.background = 'var(--status-hot)';
      proceedBtn.style.color = '#ffffff';
    } else {
      proceedBtn.className = 'btn-primary';
      proceedBtn.style.background = '';
      proceedBtn.style.color = '';
    }

    const cleanup = () => {
      modal.close();
      cancelBtn.onclick = null;
      proceedBtn.onclick = null;
    };

    cancelBtn.onclick = () => {
      cleanup();
      resolve(false);
    };

    proceedBtn.onclick = () => {
      cleanup();
      resolve(true);
    };

    modal.showModal();
  });
}

async function deleteCampaign(campaignId, campaignName) {
  const confirmed = await promptConfirm({
    title: `Delete "${campaignName}"?`,
    message: 'Are you sure you want to permanently delete this campaign? All discovered leads, evidence, and generated outreach drafts will be removed.',
    confirmText: 'Delete Campaign',
    isDanger: true,
  });

  if (!confirmed) return;

  try {
    await request(`/api/campaigns/${campaignId}`, { method: 'DELETE' });
    showToast(`Campaign "${campaignName}" deleted`, 'info');
    if (activeCampaignId === campaignId) {
      activeCampaignId = null;
      currentCampaign = null;
    }
    await refresh();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 1. Workspace Profile
async function loadWorkspace() {
  try {
    workspaceProfile = await request('/api/workspace');
    if (workspaceProfile) {
      $('#sidebar-user-name').textContent = workspaceProfile.person_name || 'Operator';
      $('#sidebar-business-name').textContent = workspaceProfile.business_name || 'My Workspace';
      
      const initials = (workspaceProfile.person_name || 'AG')
        .split(' ')
        .map((n) => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase();
      $('#sidebar-avatar').textContent = initials || 'AG';

      // Populate form
      const form = $('#workspace-form');
      for (const [key, val] of Object.entries(workspaceProfile)) {
        if (form.elements[key]) form.elements[key].value = val || '';
      }
    }
  } catch (err) {
    console.error('Failed to load workspace:', err);
  }
}

// 2. Campaigns List & Sidebar
async function loadCampaigns() {
  try {
    const campaigns = await request('/api/campaigns');
    const container = $('#sidebar-campaigns');

    if (!campaigns || campaigns.length === 0) {
      container.innerHTML = `
        <div style="padding: 16px 12px; font-size: 12.5px; color: var(--text-muted); text-align: center;">
          No campaigns found.<br>Create one to start prospecting.
        </div>
      `;
      activeCampaignId = null;
      currentCampaign = null;
      updateNavbarState(null);
      switchView('view-setup-campaign');
      return;
    }

    if (!activeCampaignId || !campaigns.find((c) => c.id === activeCampaignId)) {
      activeCampaignId = campaigns[0].id;
    }

    container.innerHTML = campaigns.map((c) => {
      const isSelected = c.id === activeCampaignId;
      const statusClass = (c.status || 'created').toLowerCase().replace(/\s+/g, '-');
      return `
        <div class="campaign-nav-item ${isSelected ? 'active' : ''}" data-campaign-id="${c.id}">
          <div class="campaign-nav-row">
            <span class="campaign-nav-name">${esc(c.name)}</span>
            <div class="campaign-nav-actions">
              <span class="status-dot ${statusClass}" title="${esc(c.status)}"></span>
              <button class="btn-campaign-delete" data-delete-campaign="${c.id}" data-campaign-name="${esc(c.name)}" title="Delete campaign">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
            </div>
          </div>
          <div class="campaign-nav-meta">
            <span>${esc(c.niche || '')}</span>
            <span>·</span>
            <span>${esc(c.location || '')}</span>
          </div>
        </div>
      `;
    }).join('');

    // Attach click events
    container.querySelectorAll('.campaign-nav-item').forEach((item) => {
      item.onclick = (e) => {
        if (e.target.closest('.btn-campaign-delete')) return;
        selectCampaign(item.dataset.campaignId);
      };
    });

    container.querySelectorAll('.btn-campaign-delete').forEach((btn) => {
      btn.onclick = (e) => {
        e.stopPropagation();
        deleteCampaign(btn.dataset.deleteCampaign, btn.dataset.campaignName);
      };
    });

    if (activeCampaignId) {
      await selectCampaign(activeCampaignId, false);
    }
  } catch (err) {
    console.error('Error loading campaigns:', err);
  }
}

// 3. Campaign Selection & Dashboard
async function selectCampaign(campaignId, forcePipelineView = true) {
  activeCampaignId = campaignId;
  const campaigns = await request('/api/campaigns');
  currentCampaign = campaigns.find((c) => c.id === campaignId);
  if (!currentCampaign) return;

  updateNavbarState(currentCampaign);

  // Update active sidebar item
  $$('.campaign-nav-item').forEach((el) => {
    el.classList.toggle('active', el.dataset.campaignId === campaignId);
  });

  const isRunning = ['queued', 'researching', 'qualifying', 'drafting'].includes(currentCampaign.status.toLowerCase());

  if (isRunning) {
    renderRunningView(currentCampaign);
    switchView('view-running-campaign');
  } else {
    await loadTracker(campaignId);
    await loadDrafts(campaignId);
    await loadBrief(campaignId);

    if (forcePipelineView) {
      switchView(activeTab);
    }
  }
}

// 4. Running View Experience
function renderRunningView(campaign) {
  const status = campaign.status;
  const stepTitle = $('#running-step-title');
  const stepDesc = $('#running-step-desc');
  const bar = $('#running-progress-bar');

  $$('.wf-step-item').forEach((s) => {
    s.classList.remove('active', 'completed');
  });

  const stream = $('#running-activity-stream');

  let pct = 20;
  if (status === 'Queued') {
    pct = 15;
    stepTitle.textContent = 'Initializing Campaign Mission';
    stepDesc.textContent = 'Queuing autonomous agent workflow for web intelligence gathering...';
    $('#step-init').classList.add('active');
  } else if (status === 'Researching') {
    pct = 40;
    stepTitle.textContent = 'Searching & Analyzing Web Presence';
    stepDesc.textContent = `Gathering target prospects for "${campaign.niche}" in ${campaign.location}...`;
    $('#step-init').classList.add('completed');
    $('#step-search').classList.add('active');
  } else if (status === 'Qualifying') {
    pct = 70;
    stepTitle.textContent = '8-Factor Fit Qualification & Auditing';
    stepDesc.textContent = 'Evaluating digital maturity, identifying growth gaps, and calculating score...';
    $('#step-init').classList.add('completed');
    $('#step-search').classList.add('completed');
    $('#step-extract').classList.add('completed');
    $('#step-score').classList.add('active');
  } else if (status === 'Drafting') {
    pct = 90;
    stepTitle.textContent = 'Crafting Tailored Outreach Drafts';
    stepDesc.textContent = 'Personalizing outreach angles across preferred channels for review...';
    $('#step-init').classList.add('completed');
    $('#step-search').classList.add('completed');
    $('#step-extract').classList.add('completed');
    $('#step-score').classList.add('completed');
    $('#step-draft').classList.add('active');
  }

  bar.style.width = `${pct}%`;

  // Fetch live counts
  request(`/api/campaigns/${campaign.id}/dashboard`).then((dash) => {
    const c = dash.counts || {};
    $('#cnt-discovered').textContent = c.total_leads || 0;
    $('#cnt-qualified').textContent = c['Qualified'] || 0;
    $('#cnt-pages').textContent = (c.total_leads || 0) * 2;
    $('#cnt-drafts').textContent = c.total_drafts || 0;
  }).catch(() => {});

  // Append stream log
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const logItem = `
    <div class="activity-item success">
      <span class="activity-item-time">${time}</span>
      <span class="activity-item-msg">Agent active in <strong>${esc(status)}</strong> phase for "${esc(campaign.name)}"</span>
    </div>
  `;
  if (!stream.innerHTML.includes(status)) {
    stream.insertAdjacentHTML('afterbegin', logItem);
  }
}

// 5. Lead Tracker & Pipeline
async function loadTracker(campaignId) {
  try {
    const dashboard = await request(`/api/campaigns/${campaignId}/dashboard`);
    const counts = dashboard.counts || {};

    const hotCount = (currentLeads || []).filter((l) => l.priority === 'HOT').length;

    $('#pipeline-metrics-bar').innerHTML = `
      <div class="metric-pill-card">
        <div class="metric-pill-info">
          <span class="metric-pill-title">Total Discovered</span>
          <span class="metric-pill-number">${counts.total_leads || 0}</span>
        </div>
      </div>
      <div class="metric-pill-card">
        <div class="metric-pill-info">
          <span class="metric-pill-title">Qualified Leads</span>
          <span class="metric-pill-number" style="color: var(--accent-text);">${counts['Qualified'] || 0}</span>
        </div>
      </div>
      <div class="metric-pill-card">
        <div class="metric-pill-info">
          <span class="metric-pill-title">High Priority (HOT)</span>
          <span class="metric-pill-number" style="color: var(--status-hot);">${hotCount}</span>
        </div>
      </div>
      <div class="metric-pill-card">
        <div class="metric-pill-info">
          <span class="metric-pill-title">Contacted</span>
          <span class="metric-pill-number">${counts['Contacted'] || 0}</span>
        </div>
      </div>
      <div class="metric-pill-card">
        <div class="metric-pill-info">
          <span class="metric-pill-title">Pending Review</span>
          <span class="metric-pill-number" style="color: var(--status-warm);">${counts.pending_approval || 0}</span>
        </div>
      </div>
    `;

    currentLeads = await request(`/api/campaigns/${campaignId}/leads`);
    renderLeads();
  } catch (err) {
    console.error('Error loading tracker:', err);
  }
}

function renderLeads() {
  const prioFilter = $('#filter-priority').value;
  const statusFilter = $('#filter-status').value;
  const search = $('#filter-search').value.toLowerCase().trim();

  const filtered = (currentLeads || []).filter((lead) => {
    if (prioFilter && lead.priority !== prioFilter) return false;
    if (statusFilter && lead.status !== statusFilter) return false;
    if (search) {
      const matchName = (lead.business_name || '').toLowerCase().includes(search);
      const matchLoc = (lead.location || '').toLowerCase().includes(search);
      const matchNiche = (lead.niche || '').toLowerCase().includes(search);
      if (!matchName && !matchLoc && !matchNiche) return false;
    }
    return true;
  });

  const cardsContainer = $('#pipeline-cards-container');
  const tableBody = $('#pipeline-table-body');

  if (filtered.length === 0) {
    cardsContainer.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 48px 20px; background: var(--bg-surface); border: 1px dashed var(--border-medium); border-radius: var(--radius-lg);">
        <p style="font-size: 15px; font-weight: 600; color: var(--text-secondary);">No leads found matching criteria</p>
        <p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">Run the campaign or adjust your search filters.</p>
        ${currentCampaign && ['Created', 'Failed'].includes(currentCampaign.status) ? `
          <button class="btn-primary" style="margin-top: 16px;" id="btn-run-from-empty">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            Run Campaign Search
          </button>
        ` : ''}
      </div>
    `;
    const emptyRunBtn = $('#btn-run-from-empty');
    if (emptyRunBtn) {
      emptyRunBtn.onclick = async () => {
        await request(`/api/campaigns/${currentCampaign.id}/run`, { method: 'POST' });
        showToast('Campaign launched!', 'success');
        await refresh();
      };
    }
    tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">No leads matching filters.</td></tr>';
    return;
  }

  // 1. Cards View
  cardsContainer.innerHTML = filtered.map((lead) => {
    const prio = lead.priority || 'SKIP';
    const score = Math.round(lead.score ?? 0);
    const obs = (lead.research || {}).observation || 'Public digital footprint analyzed.';

    const links = [];
    if (lead.website) links.push(`<a class="link-chip" href="${esc(lead.website)}" target="_blank">🌐 Website</a>`);
    if (lead.instagram) links.push(`<a class="link-chip" href="${esc(lead.instagram)}" target="_blank">📸 Instagram</a>`);
    if (lead.linkedin) links.push(`<a class="link-chip" href="${esc(lead.linkedin)}" target="_blank">💼 LinkedIn</a>`);
    if (lead.facebook) links.push(`<a class="link-chip" href="${esc(lead.facebook)}" target="_blank">📘 Facebook</a>`);
    if (lead.google_maps) links.push(`<a class="link-chip" href="${esc(lead.google_maps)}" target="_blank">📍 Maps</a>`);

    return `
      <article class="lead-item-card" data-lead-id="${lead.id}">
        <div class="lead-card-header">
          <div>
            <h4 class="lead-card-name">${esc(lead.business_name)}</h4>
            <div class="lead-card-niche">${esc(lead.niche || currentCampaign?.niche || '')} · ${esc(lead.location || '')}</div>
          </div>
          <span class="priority-chip priority-${prio}">
            ${prio === 'HOT' ? '🔥' : prio === 'WARM' ? '⚡' : prio === 'COLD' ? '❄️' : '·'} ${prio} (${score})
          </span>
        </div>

        <div class="lead-snippet-box">
          ${esc(obs)}
        </div>

        <div class="lead-links-chips">
          ${links.length ? links.join('') : '<span style="font-size: 11px; color: var(--text-muted);">No external links logged</span>'}
        </div>

        <div class="lead-card-footer">
          <span class="channel-tag-pill">
            Channel: <strong style="color: var(--text-primary);">${esc(lead.recommended_channel || 'Email')}</strong>
          </span>
          <button class="btn-secondary" style="padding: 6px 12px; font-size: 12px;" data-inspect="${lead.id}">
            Inspect Detail
          </button>
        </div>
      </article>
    `;
  }).join('');

  // 2. Table View
  tableBody.innerHTML = filtered.map((lead) => {
    const prio = lead.priority || 'SKIP';
    const score = Math.round(lead.score ?? 0);
    return `
      <tr>
        <td><span class="priority-chip priority-${prio}">${prio}</span></td>
        <td><strong style="font-family: var(--font-mono);">${score}</strong></td>
        <td><strong>${esc(lead.business_name)}</strong></td>
        <td>${esc(lead.location || 'N/A')}</td>
        <td>${esc(lead.recommended_channel || 'Email')}</td>
        <td><span class="navbar-status-badge" style="padding: 2px 8px; font-size: 11px;">${esc(lead.status)}</span></td>
        <td>
          <button class="btn-secondary" style="padding: 5px 10px; font-size: 11.5px;" data-inspect="${lead.id}">Inspect</button>
        </td>
      </tr>
    `;
  }).join('');

  // Attach inspect click handler
  $$('[data-inspect]').forEach((btn) => {
    btn.onclick = () => openLeadInspector(btn.dataset.inspect);
  });
}

// 6. Lead Detail Inspector Modal
async function openLeadInspector(leadId) {
  const lead = (currentLeads || []).find((l) => l.id === leadId);
  if (!lead) return;

  $('#modal-lead-title').textContent = lead.business_name;
  $('#modal-lead-subtitle').textContent = `${lead.niche || ''} · ${lead.location || ''} · ${lead.country || ''}`;

  // Research Tab
  $('#lead-modal-obs').textContent = (lead.research || {}).observation || 'No observation recorded.';
  $('#lead-modal-opp').textContent = (lead.research || {}).opportunity || 'No opportunity angle recorded.';

  const links = [];
  if (lead.website) links.push(`<a class="link-chip" href="${esc(lead.website)}" target="_blank">🌐 Website</a>`);
  if (lead.instagram) links.push(`<a class="link-chip" href="${esc(lead.instagram)}" target="_blank">📸 Instagram</a>`);
  if (lead.linkedin) links.push(`<a class="link-chip" href="${esc(lead.linkedin)}" target="_blank">💼 LinkedIn</a>`);
  if (lead.facebook) links.push(`<a class="link-chip" href="${esc(lead.facebook)}" target="_blank">📘 Facebook</a>`);
  if (lead.google_maps) links.push(`<a class="link-chip" href="${esc(lead.google_maps)}" target="_blank">📍 Maps</a>`);
  $('#lead-modal-links').innerHTML = links.join('') || '<span style="font-size: 12px; color: var(--text-muted);">No external links found</span>';

  const sourceUrls = (lead.research || {}).source_urls || [];
  $('#lead-modal-evidence').innerHTML = sourceUrls.map((u) => `
    <li>
      <a href="${esc(u)}" target="_blank" style="font-size: 12.5px; color: var(--accent-text); text-decoration: none;">
        ↗ ${esc(u)}
      </a>
    </li>
  `).join('') || '<li style="font-size: 12px; color: var(--text-muted);">No source URLs logged.</li>';

  // Audit Tab
  const prio = lead.priority || 'SKIP';
  $('#modal-score-val').textContent = Math.round(lead.score ?? 0);
  $('#modal-priority-badge').innerHTML = `<span class="priority-chip priority-${prio}">${prio}</span>`;
  $('#audit-working-val').textContent = 'Active business operations and public digital presence verified.';
  $('#audit-missing-val').textContent = (lead.research || {}).observation || 'N/A';
  $('#audit-offer-val').textContent = workspaceProfile?.service_offer || 'Tailored Growth Strategy';

  // Outreach Tab
  $('#modal-rec-chan-val').textContent = lead.recommended_channel || 'Email';
  $('#modal-rec-reason-val').textContent = lead.recommended_channel_reason || '';

  const leadDrafts = (currentDrafts || []).filter((d) => d.lead_id === lead.id);
  $('#modal-drafts-list').innerHTML = leadDrafts.map((d) => `
    <div class="content-card" style="padding: 16px; margin-bottom: 0;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span class="draft-channel-badge">${esc(d.channel.toUpperCase())}</span>
        <span style="font-size: 11.5px; color: var(--text-muted);">${esc(d.status)}</span>
      </div>
      ${d.subject ? `<input class="input-field" value="${esc(d.subject)}" readonly style="margin-bottom: 8px;">` : ''}
      <textarea class="textarea-field" readonly rows="3">${esc(d.body)}</textarea>
      <div style="margin-top: 10px; display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn-secondary" data-copy-modal="${d.id}" data-body="${esc(d.body)}">Copy</button>
        ${d.channel !== 'email' ? `<button class="btn-primary" data-contact-modal="${d.id}" ${d.status === 'Approved' ? '' : 'disabled'}>Mark Contacted</button>` : ''}
        ${d.channel === 'email' ? `<button class="btn-primary" data-send-modal="${d.id}" ${d.status === 'Approved' ? '' : 'disabled'}>Send Email</button>` : ''}
      </div>
    </div>
  `).join('') || '<p style="font-size: 13px; color: var(--text-muted);">No drafts generated for this lead.</p>';

  // Attach modal copy/send events
  $$('[data-copy-modal]').forEach((b) => {
    b.onclick = async () => {
      await navigator.clipboard.writeText(b.dataset.body);
      showToast('Copied to clipboard!', 'success');
      b.textContent = 'Copied!';
      setTimeout(() => { b.textContent = 'Copy'; }, 1500);
    };
  });

  $$('[data-contact-modal]').forEach((b) => {
    b.onclick = async () => {
      await request(`/api/drafts/${b.dataset.contactModal}/mark-contacted`, { method: 'POST' });
      showToast('Marked as contacted!', 'success');
      $('#lead-modal').close();
      await refresh();
    };
  });

  $$('[data-send-modal]').forEach((b) => {
    b.onclick = async () => {
      await request(`/api/drafts/${b.dataset.sendModal}/send`, { method: 'POST' });
      showToast('Email sent successfully!', 'success');
      $('#lead-modal').close();
      await refresh();
    };
  });

  // Timeline Tab
  $('#modal-status-select').value = lead.status;
  $('#btn-save-modal-status').onclick = async () => {
    const newStatus = $('#modal-status-select').value;
    await request(`/api/leads/${lead.id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, reason: 'Manual operator update' }),
    });
    showToast(`Lead status updated to ${newStatus}`, 'success');
    $('#lead-modal').close();
    await refresh();
  };

  $('#modal-timeline-list').innerHTML = `
    <li class="activity-item info">
      <span class="activity-item-time">${new Date(lead.created_at || Date.now()).toLocaleTimeString()}</span>
      <span class="activity-item-msg">Discovered &amp; qualified as <strong>${esc(lead.status)}</strong></span>
    </li>
    ${lead.contacted_at ? `
      <li class="activity-item success">
        <span class="activity-item-time">${new Date(lead.contacted_at).toLocaleTimeString()}</span>
        <span class="activity-item-msg">Outreach sent via ${esc(lead.last_contacted_channel || 'DM')}</span>
      </li>
    ` : ''}
  `;

  $('#lead-modal').showModal();
}

// 7. Draft Studio
async function loadDrafts(campaignId) {
  try {
    currentDrafts = await request(`/api/campaigns/${campaignId}/drafts`);
    const container = $('#drafts-container');

    if (!currentDrafts || currentDrafts.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 20px; color: var(--text-muted);">
          <p style="font-size: 14px; font-weight: 600;">No outreach drafts generated yet.</p>
          <p style="font-size: 12.5px; margin-top: 4px;">Run the campaign to research leads and synthesize messages.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = currentDrafts.map((draft) => `
      <article class="draft-card-modern" data-draft-id="${draft.id}">
        <div class="draft-header-row">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="draft-channel-badge">${esc(draft.channel.toUpperCase())}</span>
            <span class="navbar-status-badge" style="font-size: 11.5px;">${esc(draft.status)}</span>
          </div>
          ${draft.destination ? `<a class="draft-destination-link" href="${esc(draft.destination)}" target="_blank">↗ Open Recipient Profile</a>` : ''}
        </div>

        <div class="draft-body-area">
          ${draft.channel === 'email' ? `
            <div style="margin-bottom: 8px;">
              <label class="form-label" style="margin-bottom: 4px;">Subject</label>
              <input class="input-field draft-subject-input" value="${esc(draft.subject || '')}" placeholder="Email subject">
            </div>
          ` : ''}
          <label class="form-label" style="margin-bottom: 4px;">Message Body</label>
          <textarea class="textarea-field draft-body-input" rows="4">${esc(draft.body)}</textarea>
        </div>

        <div class="ai-revision-bar">
          <input class="draft-revise-input" placeholder="Prompt AI revision (e.g. 'Make it punchier and mention their podcast')...">
          <button class="btn-secondary" style="padding: 6px 12px;" data-revise="${draft.id}">Revise</button>
        </div>

        <div class="draft-actions-row">
          <button class="btn-secondary" data-save="${draft.id}">Save Edit</button>
          <button class="btn-secondary" data-copy="${draft.id}">Copy Message</button>
          <button class="btn-primary" data-approve="${draft.id}">Approve</button>
          ${draft.channel !== 'email' ? `<button class="btn-secondary" data-contact="${draft.id}">Mark Contacted</button>` : ''}
          ${draft.channel === 'email' ? `<button class="btn-primary" data-send="${draft.id}">Send Email</button>` : ''}
          <button class="btn-danger" data-reject="${draft.id}">Reject</button>
        </div>
      </article>
    `).join('');

    // Attach Draft Event Listeners
    container.querySelectorAll('[data-save]').forEach((b) => {
      b.onclick = async () => {
        const card = b.closest('.draft-card-modern');
        const subject = card.querySelector('.draft-subject-input')?.value || null;
        const body = card.querySelector('.draft-body-input').value;
        await request(`/api/drafts/${b.dataset.save}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ subject, body }),
        });
        showToast('Draft changes saved', 'success');
        await loadDrafts(campaignId);
      };
    });

    container.querySelectorAll('[data-revise]').forEach((b) => {
      b.onclick = async () => {
        const card = b.closest('.draft-card-modern');
        const instruction = card.querySelector('.draft-revise-input').value;
        if (!instruction) return;
        b.textContent = 'Revising...';
        b.disabled = true;
        try {
          await request(`/api/drafts/${b.dataset.revise}/revise`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction }),
          });
          showToast('Draft revised by AI agent', 'success');
          await loadDrafts(campaignId);
        } catch (err) {
          showToast(err.message, 'error');
        }
      };
    });

    container.querySelectorAll('[data-copy]').forEach((b) => {
      b.onclick = async () => {
        const card = b.closest('.draft-card-modern');
        const body = card.querySelector('.draft-body-input').value;
        await navigator.clipboard.writeText(body);
        showToast('Message copied to clipboard!', 'success');
        b.textContent = 'Copied!';
        setTimeout(() => { b.textContent = 'Copy Message'; }, 1500);
      };
    });

    container.querySelectorAll('[data-approve]').forEach((b) => {
      b.onclick = async () => {
        const card = b.closest('.draft-card-modern');
        const subject = card.querySelector('.draft-subject-input')?.value || null;
        const body = card.querySelector('.draft-body-input').value;
        await request(`/api/drafts/${b.dataset.approve}/approval`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'approve', subject, body }),
        });
        showToast('Draft approved for outreach', 'success');
        await refresh();
      };
    });

    container.querySelectorAll('[data-contact]').forEach((b) => {
      b.onclick = async () => {
        await request(`/api/drafts/${b.dataset.contact}/mark-contacted`, { method: 'POST' });
        showToast('Marked as contacted manually', 'success');
        await refresh();
      };
    });

    container.querySelectorAll('[data-send]').forEach((b) => {
      b.onclick = async () => {
        await request(`/api/drafts/${b.dataset.send}/send`, { method: 'POST' });
        showToast('Email sent via Gmail API!', 'success');
        await refresh();
      };
    });

    container.querySelectorAll('[data-reject]').forEach((b) => {
      b.onclick = async () => {
        await request(`/api/drafts/${b.dataset.reject}/approval`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'reject' }),
        });
        showToast('Draft rejected', 'info');
        await refresh();
      };
    });
  } catch (err) {
    console.error('Error loading drafts:', err);
  }
}

// 8. AI Strategy Brief & Chat Assistant
async function loadBrief(campaignId) {
  try {
    const messages = await request(`/api/campaigns/${campaignId}/messages`);
    const history = $('#brief-chat-history');

    history.innerHTML = (messages || []).map((m) => `
      <div class="chat-bubble ${m.role}">
        ${esc(m.content)}
      </div>
    `).join('') || '<div style="font-size: 13px; color: var(--text-muted); padding: 8px;">No brief chat history yet. Ask the assistant to refine ICP or search keywords.</div>';
    history.scrollTop = history.scrollHeight;

    const briefObj = await request(`/api/campaigns/${campaignId}/brief`);
    if (briefObj && briefObj.brief_data) {
      const data = briefObj.brief_data;
      $('#brief-icp').value = data.ideal_customer_profile || '';
      $('#brief-tiers').value = (data.industry_tiers || []).join(', ');
      $('#brief-signals').value = (data.buying_signals || []).join(', ');
      $('#brief-excluded').value = (data.excluded_business_types || []).join(', ');
      $('#brief-angles').value = (data.offer_angles || []).join(', ');
    }
  } catch (err) {
    console.error('Error loading brief:', err);
  }
}

// Global Refresh Helper
async function refresh() {
  await loadWorkspace();
  await loadCampaigns();
}

// DOM Event Bindings
document.addEventListener('DOMContentLoaded', () => {
  // Sidebar New Campaign CTA & Brand Link
  $('#btn-new-campaign').onclick = () => {
    activeCampaignId = null;
    currentCampaign = null;
    updateNavbarState(null);
    switchView('view-setup-campaign');
    $$('.campaign-nav-item').forEach((el) => el.classList.remove('active'));
  };

  $('#brand-home-link').onclick = (e) => {
    e.preventDefault();
    $('#btn-new-campaign').click();
  };

  // Mobile Sidebar Toggle
  $('#btn-toggle-sidebar').onclick = () => {
    $('#sidebar').classList.toggle('open');
  };

  // Workspace Settings Modal Trigger
  $('#btn-open-workspace').onclick = () => {
    $('#workspace-modal').showModal();
  };
  $('#btn-close-workspace-modal').onclick = () => $('#workspace-modal').close();
  $('#btn-cancel-workspace').onclick = () => $('#workspace-modal').close();

  // Lead Inspector Close
  $('#btn-close-lead-modal').onclick = () => $('#lead-modal').close();

  // Modal Tabs Navigation
  $$('.modal-tab-btn').forEach((btn) => {
    btn.onclick = () => {
      $$('.modal-tab-btn').forEach((b) => b.classList.remove('active'));
      $$('.modal-tab-pane').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      $(`#${btn.dataset.modaltab}`).classList.add('active');
    };
  });

  // Top Workspace Nav Tabs Switching
  $$('.workspace-tab-btn').forEach((btn) => {
    btn.onclick = () => {
      activeTab = btn.dataset.view;
      switchView(activeTab);
    };
  });

  // Cards / Table View Toggle
  $('#btn-view-cards').onclick = () => {
    isTableView = false;
    $('#btn-view-cards').classList.add('active');
    $('#btn-view-table').classList.remove('active');
    $('#pipeline-cards-container').style.display = 'grid';
    $('#pipeline-table-container').style.display = 'none';
  };

  $('#btn-view-table').onclick = () => {
    isTableView = true;
    $('#btn-view-table').classList.add('active');
    $('#btn-view-cards').classList.remove('active');
    $('#pipeline-cards-container').style.display = 'none';
    $('#pipeline-table-container').style.display = 'block';
  };

  // Filters & Search in Pipeline
  $('#filter-priority').onchange = renderLeads;
  $('#filter-status').onchange = renderLeads;
  $('#filter-search').oninput = renderLeads;

  // Running View "View Pipeline" Override
  $('#btn-cancel-view-running').onclick = () => {
    switchView('view-pipeline');
  };

  // Manual Refresh Button
  $('#btn-refresh').onclick = async () => {
    showToast('Refreshing agent data...', 'info');
    await refresh();
  };

  // Workspace Form Submission
  $('#workspace-form').onsubmit = async (e) => {
    e.preventDefault();
    const data = getFormData(e.target);
    for (const k of ['website', 'instagram', 'linkedin']) {
      if (!data[k]) data[k] = null;
    }
    await request('/api/workspace', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    showToast('Workspace profile saved', 'success');
    $('#workspace-modal').close();
    await loadWorkspace();
  };

  // Campaign Setup Form Submission
  $('#campaign-form').onsubmit = async (e) => {
    e.preventDefault();
    const data = getFormData(e.target);
    const checked = [...e.target.querySelectorAll('[name=channels]:checked')].map((i) => i.value);
    data.primary_channel = checked[0] || 'Instagram';
    data.secondary_channel = checked[1] || null;
    data.lead_count = Number(data.lead_count) || 10;
    delete data.channels;

    const btn = $('#btn-submit-campaign');
    btn.disabled = true;
    btn.innerHTML = 'Creating Campaign...';

    try {
      const campaign = await request('/api/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      showToast(`Campaign "${campaign.name}" created!`, 'success');
      activeCampaignId = campaign.id;
      e.target.reset();

      // Launch campaign run automatically
      await request(`/api/campaigns/${campaign.id}/run`, { method: 'POST' });
      showToast('Agent prospecting mission started', 'success');
      await refresh();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        Start Campaign
      `;
    }
  };

  // AI Brief Chat Form Submission
  $('#brief-chat-form').onsubmit = async (e) => {
    e.preventDefault();
    if (!activeCampaignId) return;
    const input = $('#brief-chat-input');
    const content = input.value.trim();
    if (!content) return;

    input.value = '';
    const history = $('#brief-chat-history');
    history.insertAdjacentHTML('beforeend', `<div class="chat-bubble user">${esc(content)}</div>`);
    history.scrollTop = history.scrollHeight;

    try {
      await request(`/api/campaigns/${activeCampaignId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      await loadBrief(activeCampaignId);
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  // Save Finalized Brief Button
  $('#btn-save-brief').onclick = async () => {
    if (!activeCampaignId) return;
    const briefData = {
      ideal_customer_profile: $('#brief-icp').value,
      industry_tiers: $('#brief-tiers').value.split(',').map((s) => s.trim()).filter(Boolean),
      buying_signals: $('#brief-signals').value.split(',').map((s) => s.trim()).filter(Boolean),
      excluded_business_types: $('#brief-excluded').value.split(',').map((s) => s.trim()).filter(Boolean),
      priority_locations: [],
      offer_angles: $('#brief-angles').value.split(',').map((s) => s.trim()).filter(Boolean),
      proof_points: [],
      prohibited_claims: [],
      channel_preferences: [],
      operator_notes: null,
    };

    await request(`/api/campaigns/${activeCampaignId}/brief`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(briefData),
    });
    showToast('Targeting brief finalized', 'success');
  };

  // Initial Load
  refresh().then(() => {
    // If no workspace is saved, open profile modal on first visit
    if (!workspaceProfile?.business_name) {
      $('#workspace-modal').showModal();
    }
  });

  // Polling for real-time campaign updates
  setInterval(() => {
    if (!document.querySelector('dialog[open], .draft-revise-input:focus, .draft-body-input:focus, #brief-chat-input:focus')) {
      if (activeCampaignId && currentCampaign && ['Queued', 'Researching', 'Qualifying', 'Drafting'].includes(currentCampaign.status)) {
        refresh().catch(() => {});
      }
    }
  }, 3500);
});
