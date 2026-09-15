const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

let activeCampaignId = null;
let currentLeads = [];

async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error((await response.json()).detail || 'Request failed');
  return response.status === 204 ? null : response.json();
}

function formData(form) {
  return Object.fromEntries(new FormData(form));
}

async function loadWorkspace() {
  const profile = await request('/api/workspace');
  $('#setup').hidden = Boolean(profile);
  $('#app').hidden = !profile;
  if (profile) {
    for (const [key, value] of Object.entries(profile)) {
      const field = $('#workspace-form').elements[key];
      if (field) field.value = value || '';
    }
  }
  return profile;
}

async function loadCampaigns() {
  const campaigns = await request('/api/campaigns');
  if (!activeCampaignId && campaigns.length > 0) {
    activeCampaignId = campaigns[0].id;
  }

  $('#campaigns').innerHTML = campaigns.map((campaign) => `
    <article class="card ${campaign.id === activeCampaignId ? 'selected-card' : ''}">
      <strong>${esc(campaign.name)}</strong>
      <span class="muted">${esc(campaign.niche)} · ${esc(campaign.location)}</span>
      <span class="status">${esc(campaign.status)}</span>
      <div class="channel-row">${esc(campaign.primary_channel)}${campaign.secondary_channel ? ` · ${esc(campaign.secondary_channel)}` : ''}</div>
      <div class="card-actions">
        <button data-select="${campaign.id}" class="quiet">Select &amp; View Pipeline</button>
        <button data-run="${campaign.id}" ${['Queued', 'Researching', 'Drafting', 'Qualifying', 'Auditing'].includes(campaign.status) ? 'disabled' : ''}>
          ${campaign.status === 'Created' ? 'Run Campaign' : 'Rerun Campaign'}
        </button>
        <button class="quiet" data-delete="${campaign.id}">Delete</button>
      </div>
    </article>
  `).join('') || '<p class="muted">Create your first campaign.</p>';

  campaigns.forEach((campaign) => {
    const selectBtn = $(`[data-select="${campaign.id}"]`);
    if (selectBtn) selectBtn.onclick = () => { activeCampaignId = campaign.id; refresh(); };

    const runBtn = $(`[data-run="${campaign.id}"]`);
    if (runBtn) runBtn.onclick = async () => {
      if (campaign.status === 'Created' || campaign.status === 'Failed' || campaign.status === 'Awaiting Approval') {
        await request(`/api/campaigns/${campaign.id}/run`, { method: 'POST' });
        await refresh();
      }
    };

    const deleteBtn = $(`[data-delete="${campaign.id}"]`);
    if (deleteBtn) deleteBtn.onclick = async () => {
      if (confirm(`Delete campaign "${campaign.name}"?`)) {
        await request(`/api/campaigns/${campaign.id}`, { method: 'DELETE' });
        if (activeCampaignId === campaign.id) activeCampaignId = null;
        await refresh();
      }
    };
  });

  if (activeCampaignId) {
    await loadTracker(activeCampaignId);
  }
}

async function loadTracker(campaignId) {
  try {
    const dashboard = await request(`/api/campaigns/${campaignId}/dashboard`);
    $('#tracker-section').hidden = false;
    $('#tracker-title').textContent = `${dashboard.campaign.name} — Pipeline`;

    const counts = dashboard.counts;
    $('#dashboard-metrics').innerHTML = `
      <div class="metric-badge">Total: <strong>${counts.total_leads}</strong></div>
      <div class="metric-badge">Qualified: <strong>${counts['Qualified'] || 0}</strong></div>
      <div class="metric-badge">Contacted: <strong>${counts['Contacted'] || 0}</strong></div>
      <div class="metric-badge">Follow-ups: <strong>${counts['Follow-up Due'] || 0}</strong></div>
      <div class="metric-badge">Pending Drafts: <strong>${counts.pending_approval}</strong></div>
    `;

    currentLeads = await request(`/api/campaigns/${campaignId}/leads`);
    renderTrackerTable();
  } catch (err) {
    console.error(err);
  }
}

function renderTrackerTable() {
  const prioFilter = $('#filter-priority').value;
  const statusFilter = $('#filter-status').value;
  const search = $('#search-tracker').value.toLowerCase();

  const filtered = currentLeads.filter((lead) => {
    if (prioFilter && lead.priority !== prioFilter) return false;
    if (statusFilter && lead.status !== statusFilter) return false;
    if (search && !lead.business_name.toLowerCase().includes(search) && !String(lead.location ?? '').toLowerCase().includes(search)) return false;
    return true;
  });

  $('#tracker-table-body').innerHTML = filtered.map((lead) => `
    <tr>
      <td><span class="priority-chip priority-${esc(lead.priority || 'SKIP')}">${esc(lead.priority || 'SKIP')}</span></td>
      <td><strong>${lead.score ?? 0}</strong></td>
      <td><strong>${esc(lead.business_name)}</strong></td>
      <td>${esc(lead.location || 'N/A')}</td>
      <td>${esc(lead.recommended_channel || 'N/A')}</td>
      <td><span class="status-chip">${esc(lead.status)}</span></td>
      <td><button class="quiet" data-inspect="${lead.id}">Inspect Detail</button></td>
    </tr>
  `).join('') || '<tr><td colspan="7" class="muted">No leads match current filters.</td></tr>';

  document.querySelectorAll('[data-inspect]').forEach((btn) => {
    btn.onclick = () => openLeadModal(btn.dataset.inspect);
  });
}

async function openLeadModal(leadId) {
  const lead = currentLeads.find((l) => l.id === leadId);
  if (!lead) return;

  $('#modal-business-name').textContent = lead.business_name;
  $('#modal-score').textContent = lead.score ?? 'N/A';
  $('#modal-priority').textContent = lead.priority ?? 'N/A';
  $('#lead-obs').textContent = (lead.research || {}).observation || 'N/A';
  $('#lead-opp').textContent = (lead.research || {}).opportunity || 'N/A';
  $('#modal-rec-chan').textContent = lead.recommended_channel || 'N/A';
  $('#modal-rec-reason').textContent = lead.recommended_channel_reason || '';

  // Links
  const links = [];
  if (lead.website) links.push(`<a href="${esc(lead.website)}" target="_blank">🌐 Website</a>`);
  if (lead.instagram) links.push(`<a href="${esc(lead.instagram)}" target="_blank">📸 Instagram</a>`);
  if (lead.linkedin) links.push(`<a href="${esc(lead.linkedin)}" target="_blank">💼 LinkedIn</a>`);
  if (lead.facebook) links.push(`<a href="${esc(lead.facebook)}" target="_blank">📘 Facebook</a>`);
  if (lead.google_maps) links.push(`<a href="${esc(lead.google_maps)}" target="_blank">📍 Maps</a>`);
  $('#lead-links-row').innerHTML = links.join(' · ') || '<span class="muted">No external links</span>';

  // Audit info
  $('#audit-working').textContent = 'Active business presence verified';
  $('#audit-missing').textContent = (lead.research || {}).observation || 'N/A';
  $('#audit-offer').textContent = 'Social Growth Strategy';
  $('#audit-note').textContent = `Focus observation: ${(lead.research || {}).observation || 'N/A'}`;

  // Evidence list
  const urls = (lead.research || {}).source_urls || [];
  $('#lead-evidence-list').innerHTML = urls.map((u) => `<li><a href="${esc(u)}" target="_blank">${esc(u)}</a></li>`).join('') || '<li class="muted">No source URLs logged</li>';

  // Drafts for lead
  const drafts = await request(`/api/campaigns/${lead.campaign_id}/drafts`);
  const leadDrafts = drafts.filter((d) => d.lead_id === lead.id);
  $('#modal-drafts-container').innerHTML = leadDrafts.map((d) => `
    <div class="draft">
      <div class="draft-head">
        <strong>${esc(d.channel.toUpperCase())} (${esc(d.status)})</strong>
      </div>
      ${d.subject ? `<input value="${esc(d.subject)}" readonly>` : ''}
      <textarea rows="4" readonly>${esc(d.body)}</textarea>
      <div class="draft-actions">
        <button class="quiet" data-copy-modal="${d.id}" data-body="${esc(d.body)}">Copy</button>
        ${d.channel !== 'email' ? `<button data-contact-modal="${d.id}" ${d.status === 'Approved' ? '' : 'disabled'}>Mark Contacted</button>` : ''}
        ${d.channel === 'email' ? `<button data-send-modal="${d.id}" ${d.status === 'Approved' ? '' : 'disabled'}>Send Email</button>` : ''}
      </div>
    </div>
  `).join('') || '<p class="muted">No drafts generated for this lead.</p>';

  document.querySelectorAll('[data-copy-modal]').forEach((b) => {
    b.onclick = async () => {
      await navigator.clipboard.writeText(b.dataset.body);
      b.textContent = 'Copied';
      setTimeout(() => { b.textContent = 'Copy'; }, 1200);
    };
  });

  document.querySelectorAll('[data-contact-modal]').forEach((b) => {
    b.onclick = async () => {
      await request(`/api/drafts/${b.dataset.contactModal}/mark-contacted`, { method: 'POST' });
      $('#lead-modal').close();
      await refresh();
    };
  });

  document.querySelectorAll('[data-send-modal]').forEach((b) => {
    b.onclick = async () => {
      await request(`/api/drafts/${b.dataset.sendModal}/send`, { method: 'POST' });
      $('#lead-modal').close();
      await refresh();
    };
  });

  $('#save-lead-status-btn').onclick = async () => {
    const newStatus = $('#update-lead-status-sel').value;
    await request(`/api/leads/${lead.id}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus, reason: 'Manual operator update' }),
    });
    $('#lead-modal').close();
    await refresh();
  };

  $('#lead-modal').showModal();
}

async function loadDrafts() {
  const campaigns = await request('/api/campaigns');
  const drafts = (await Promise.all(campaigns.map((campaign) => request(`/api/campaigns/${campaign.id}/drafts`)))).flat();
  $('#drafts').innerHTML = drafts.map((draft) => `
    <article class="draft" data-draft="${draft.id}">
      <div class="draft-head">
        <div><strong>${esc(draft.channel.toUpperCase())}</strong><span class="status">${esc(draft.status)}</span></div>
        <a href="${esc(draft.destination || '#')}" target="_blank" rel="noreferrer">Open profile/destination</a>
      </div>
      <input name="subject" placeholder="Subject (email only)" value="${esc(draft.subject || '')}" ${draft.channel === 'email' ? '' : 'hidden'}>
      <textarea name="body" rows="4">${esc(draft.body)}</textarea>
      <div class="draft-prompt">
        <input name="instruction" placeholder="Ask for a revision, e.g. make it warmer">
        <button class="quiet" data-revise="${draft.id}">Revise</button>
      </div>
      <div class="draft-actions">
        <button data-save="${draft.id}">Save edit</button>
        <button data-copy="${draft.id}" class="quiet">Copy message</button>
        <button data-approve="${draft.id}">Approve</button>
        ${draft.channel !== 'email' ? `<button data-contact="${draft.id}" class="quiet">Mark contacted</button>` : ''}
        ${draft.channel === 'email' ? `<button data-send="${draft.id}">Send Email</button>` : ''}
        <button data-reject="${draft.id}" class="quiet">Reject</button>
      </div>
    </article>
  `).join('') || '<p class="muted">No drafts yet. Run a campaign to start researching.</p>';

  document.querySelectorAll('[data-save]').forEach((button) => button.onclick = async () => { const draft = button.closest('.draft'); await request(`/api/drafts/${button.dataset.save}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subject: draft.querySelector('[name=subject]').value || null, body: draft.querySelector('[name=body]').value }) }); await loadDrafts(); });
  document.querySelectorAll('[data-revise]').forEach((button) => button.onclick = async () => { const draft = button.closest('.draft'); const instruction = draft.querySelector('[name=instruction]').value; if (!instruction) return; await request(`/api/drafts/${button.dataset.revise}/revise`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instruction }) }); await loadDrafts(); });
  document.querySelectorAll('[data-copy]').forEach((button) => button.onclick = async () => { await navigator.clipboard.writeText(button.closest('.draft').querySelector('[name=body]').value); button.textContent = 'Copied'; setTimeout(() => { button.textContent = 'Copy message'; }, 1200); });
  document.querySelectorAll('[data-approve]').forEach((button) => button.onclick = async () => { const draft = button.closest('.draft'); await request(`/api/drafts/${button.dataset.approve}/approval`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'approve', subject: draft.querySelector('[name=subject]').value || null, body: draft.querySelector('[name=body]').value }) }); await loadDrafts(); });
  document.querySelectorAll('[data-contact]').forEach((button) => button.onclick = async () => { await request(`/api/drafts/${button.dataset.contact}/mark-contacted`, { method: 'POST' }); await loadDrafts(); });
  document.querySelectorAll('[data-send]').forEach((button) => button.onclick = async () => { await request(`/api/drafts/${button.dataset.send}/send`, { method: 'POST' }); await loadDrafts(); });
  document.querySelectorAll('[data-reject]').forEach((button) => button.onclick = async () => { await request(`/api/drafts/${button.dataset.reject}/approval`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'reject' }) }); await loadDrafts(); });
}

async function refresh() {
  await loadCampaigns();
  await loadDrafts();
}

$('#workspace-form').onsubmit = async (event) => {
  event.preventDefault();
  const data = formData(event.target);
  for (const key of ['website', 'instagram', 'linkedin']) if (!data[key]) data[key] = null;
  await request('/api/workspace', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  await loadWorkspace();
  await refresh();
};

$('#campaign-form').onsubmit = async (event) => {
  event.preventDefault();
  const data = formData(event.target);
  const channels = [...event.target.querySelectorAll('[name=channels]:checked')].map((input) => input.value);
  data.primary_channel = channels[0] || 'Instagram';
  data.secondary_channel = channels[1] || null;
  data.lead_count = Number(data.lead_count);
  delete data.channels;

  const campaign = await request('/api/campaigns', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  activeCampaignId = campaign.id;
  event.target.reset();
  await refresh();
};

$('#filter-priority').onchange = renderTrackerTable;
$('#filter-status').onchange = renderTrackerTable;
$('#search-tracker').oninput = renderTrackerTable;

$('#close-modal-btn').onclick = () => $('#lead-modal').close();

document.querySelectorAll('.tab-btn').forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
    btn.classList.add('active');
    $(`#${btn.dataset.tab}`).classList.add('active');
  };
});

$('#edit-workspace').onclick = () => { $('#setup').hidden = false; $('#app').hidden = true; };
$('#refresh').onclick = refresh;

loadWorkspace().then(refresh).catch((error) => alert(error.message));
setInterval(() => {
  if (!document.querySelector('.draft textarea:focus, .draft input:focus, dialog[open]')) {
    refresh().catch(() => {});
  }
}, 5000);

