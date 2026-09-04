const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));

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
  $('#campaigns').innerHTML = campaigns.map((campaign) => `<article class="card"><strong>${esc(campaign.name)}</strong><span class="muted">${esc(campaign.niche)} · ${esc(campaign.location)}</span><span class="status">${esc(campaign.status)}</span><div class="channel-row">${esc(campaign.primary_channel)}${campaign.secondary_channel ? ` · ${esc(campaign.secondary_channel)}` : ''}</div><div class="card-actions"><button data-run="${campaign.id}" ${['Queued', 'Researching', 'Drafting'].includes(campaign.status) ? 'disabled' : ''}>${campaign.status === 'Created' ? 'Research campaign' : 'Refresh drafts'}</button><button class="quiet" data-delete="${campaign.id}">Delete</button></div></article>`).join('') || '<p class="muted">Create your first campaign.</p>';
  campaigns.forEach((campaign) => {
    $(`[data-run="${campaign.id}"]`).onclick = async () => {
      if (campaign.status === 'Created' || campaign.status === 'Failed') await request(`/api/campaigns/${campaign.id}/run`, { method: 'POST' });
      await loadCampaigns();
    };
    $(`[data-delete="${campaign.id}"]`).onclick = async () => {
      if (confirm(`Delete campaign "${campaign.name}"?`)) { await request(`/api/campaigns/${campaign.id}`, { method: 'DELETE' }); await refresh(); }
    };
  });
}

async function loadDrafts() {
  const campaigns = await request('/api/campaigns');
  const drafts = (await Promise.all(campaigns.map((campaign) => request(`/api/campaigns/${campaign.id}/drafts`)))).flat();
  $('#drafts').innerHTML = drafts.map((draft) => `<article class="draft" data-draft="${draft.id}"><div class="draft-head"><div><strong>${esc(draft.channel)}</strong><span class="status">${esc(draft.status)}</span></div><a href="${esc(draft.destination || '#')}" target="_blank" rel="noreferrer">Open profile</a></div><input name="subject" placeholder="Subject (email only)" value="${esc(draft.subject || '')}" ${draft.channel === 'email' ? '' : 'hidden'}><textarea name="body" rows="5">${esc(draft.body)}</textarea><div class="draft-prompt"><input name="instruction" placeholder="Ask for a revision, e.g. make it warmer"><button class="quiet" data-revise="${draft.id}">Revise</button></div><div class="draft-actions"><button data-save="${draft.id}">Save edit</button><button data-copy="${draft.id}" class="quiet">Copy message</button><button data-approve="${draft.id}">Approve</button><button data-contact="${draft.id}" class="quiet">Mark contacted</button><button data-reject="${draft.id}" class="quiet">Reject</button></div></article>`).join('') || '<p class="muted">No drafts yet. Run a campaign to start researching.</p>';
  document.querySelectorAll('[data-save]').forEach((button) => button.onclick = async () => { const draft = button.closest('.draft'); await request(`/api/drafts/${button.dataset.save}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subject: draft.querySelector('[name=subject]').value || null, body: draft.querySelector('[name=body]').value }) }); await loadDrafts(); });
  document.querySelectorAll('[data-revise]').forEach((button) => button.onclick = async () => { const draft = button.closest('.draft'); const instruction = draft.querySelector('[name=instruction]').value; if (!instruction) return; await request(`/api/drafts/${button.dataset.revise}/revise`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ instruction }) }); await loadDrafts(); });
  document.querySelectorAll('[data-copy]').forEach((button) => button.onclick = async () => { await navigator.clipboard.writeText(button.closest('.draft').querySelector('[name=body]').value); button.textContent = 'Copied'; setTimeout(() => { button.textContent = 'Copy message'; }, 1200); });
  document.querySelectorAll('[data-approve]').forEach((button) => button.onclick = async () => { const draft = button.closest('.draft'); await request(`/api/drafts/${button.dataset.approve}/approval`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'approve', subject: draft.querySelector('[name=subject]').value || null, body: draft.querySelector('[name=body]').value }) }); await loadDrafts(); });
  document.querySelectorAll('[data-contact]').forEach((button) => button.onclick = async () => { await request(`/api/drafts/${button.dataset.contact}/mark-contacted`, { method: 'POST' }); await loadDrafts(); });
  document.querySelectorAll('[data-reject]').forEach((button) => button.onclick = async () => { await request(`/api/drafts/${button.dataset.reject}/approval`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'reject' }) }); await loadDrafts(); });
}

async function refresh() { await loadCampaigns(); await loadDrafts(); }

$('#workspace-form').onsubmit = async (event) => { event.preventDefault(); const data = formData(event.target); for (const key of ['website', 'instagram', 'linkedin']) if (!data[key]) data[key] = null; await request('/api/workspace', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); await loadWorkspace(); await refresh(); };
$('#campaign-form').onsubmit = async (event) => { event.preventDefault(); const data = formData(event.target); const channels = [...event.target.querySelectorAll('[name=channels]:checked')].map((input) => input.value); data.primary_channel = channels[0] || 'Instagram'; data.secondary_channel = channels[1] || null; data.lead_count = Number(data.lead_count); delete data.channels; await request('/api/campaigns', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); event.target.reset(); await refresh(); };
$('#edit-workspace').onclick = () => { $('#setup').hidden = false; $('#app').hidden = true; };
$('#refresh').onclick = refresh;
loadWorkspace().then(refresh).catch((error) => alert(error.message));
setInterval(() => { if (!document.querySelector('.draft textarea:focus, .draft input:focus')) refresh().catch(() => {}); }, 5000);
