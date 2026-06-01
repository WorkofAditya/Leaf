const app = { repo: '', data: null, selectedChange: '', selectedCommit: null };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const els = {
  repoPath: $('#repoPath'), loadRepo: $('#loadRepo'), initializeRepo: $('#initializeRepo'), connectionLabel: $('#connectionLabel'),
  sidebarBranch: $('#sidebarBranch'), repoTitle: $('#repoTitle'), repoSubtitle: $('#repoSubtitle'), currentBranch: $('#currentBranch'),
  headCommit: $('#headCommit'), changedCount: $('#changedCount'), stagedSummary: $('#stagedSummary'), commitCount: $('#commitCount'),
  latestCommit: $('#latestCommit'), repoHealth: $('#repoHealth'), mergeState: $('#mergeState'), refreshState: $('#refreshState'),
  stageAll: $('#stageAll'), unstageAll: $('#unstageAll'), stagedList: $('#stagedList'), unstagedList: $('#unstagedList'),
  commitForm: $('#commitForm'), commitMessage: $('#commitMessage'), diffTitle: $('#diffTitle'), selectedChangeStatus: $('#selectedChangeStatus'),
  diffOutput: $('#diffOutput'), commitTimeline: $('#commitTimeline'), commitDetailTitle: $('#commitDetailTitle'), commitDetails: $('#commitDetails'),
  branchSelector: $('#branchSelector'), branchStartPoint: $('#branchStartPoint'), branchList: $('#branchList'), newBranchName: $('#newBranchName'),
  createBranch: $('#createBranch'), mergeCandidates: $('#mergeCandidates'), mergeControls: $('#mergeControls'), continueMerge: $('#continueMerge'),
  abortMerge: $('#abortMerge'), fileSearch: $('#fileSearch'), fileList: $('#fileList'), newFile: $('#newFile'), editorTitle: $('#editorTitle'),
  editorPath: $('#editorPath'), fileEditor: $('#fileEditor'), saveFile: $('#saveFile'), deleteFile: $('#deleteFile'), remoteList: $('#remoteList'),
  remoteName: $('#remoteName'), remotePath: $('#remotePath'), addRemote: $('#addRemote'), fetchRemote: $('#fetchRemote'), pullRemote: $('#pullRemote'),
  pushRemote: $('#pushRemote'), checkIntegrity: $('#checkIntegrity'), activityLog: $('#activityLog'), toast: $('#toast'),
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add('show');
  window.setTimeout(() => els.toast.classList.remove('show'), 1800);
}

function apiUrl(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  return url;
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || data.stderr || 'Action failed');
  return data;
}

async function loadState(repo = app.repo) {
  const data = await request(apiUrl('/api/state', { repo }));
  app.repo = data.repo;
  app.data = data;
  els.repoPath.value = data.repo;
  render();
}

async function act(action, payload = {}, success = 'Done') {
  try {
    const result = await request('/api/action', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo: app.repo || els.repoPath.value, action, ...payload }),
    });
    app.data = result.state;
    app.repo = result.state.repo;
    els.activityLog.textContent = cleanOutput(result.stdout || result.stderr || success);
    render();
    showToast(success);
    return result;
  } catch (error) {
    els.activityLog.textContent = error.message;
    showToast(error.message);
    throw error;
  }
}

function cleanOutput(text) {
  return text.replace(/\x1b\[[0-9;]*m/g, '').trim() || 'Ready.';
}

function render() {
  const data = app.data;
  if (!data) return;
  const commits = data.log || [];
  const changes = data.changes || [];
  const staged = changes.filter((change) => change.staged);
  const mergeActive = Object.keys(data.merge_state || {}).length > 0;
  const branch = data.current_branch || 'Detached';

  els.connectionLabel.textContent = data.is_repo ? 'Connected to a Leaf repository' : 'Folder is not tracked yet';
  els.sidebarBranch.textContent = branch;
  els.repoTitle.textContent = data.is_repo ? shortPath(data.repo) : 'Start tracking this folder';
  els.repoSubtitle.textContent = data.repo;
  els.currentBranch.textContent = branch;
  els.headCommit.textContent = data.head ? `HEAD ${data.head}` : 'No commits yet';
  els.changedCount.textContent = String(changes.length);
  els.stagedSummary.textContent = `${staged.length} staged for commit`;
  els.commitCount.textContent = String(commits.length);
  els.latestCommit.textContent = commits.at(-1)?.message || 'No timeline yet';
  els.repoHealth.textContent = data.is_repo ? 'Connected' : 'Setup needed';
  els.mergeState.textContent = mergeActive ? `Merge from ${data.merge_state.source_branch || 'another branch'}` : 'No merge in progress';
  els.initializeRepo.classList.toggle('hidden', data.is_repo);
  els.commitForm.classList.toggle('hidden', staged.length === 0);
  els.mergeControls.classList.toggle('hidden', !mergeActive);

  renderChanges(changes);
  renderDiff();
  renderHistory(commits, data.tags || {});
  renderBranches(data.branches || {});
  renderFiles();
  renderRemotes(data.remotes || {});
}

function renderChanges(changes) {
  const staged = changes.filter((change) => change.staged);
  const unstaged = changes.filter((change) => !change.staged);
  els.stagedList.innerHTML = staged.length ? staged.map(changeRow).join('') : '<p class="empty-state muted">No staged changes.</p>';
  els.unstagedList.innerHTML = unstaged.length ? unstaged.map(changeRow).join('') : '<p class="empty-state muted">No unstaged changes.</p>';
}

function changeRow(change) {
  const action = change.staged ? 'Unstage' : 'Stage';
  return `<article class="change-row ${app.selectedChange === change.path ? 'selected' : ''}" data-path="${escapeHtml(change.path)}">
    <button class="change-main" data-select-change="${escapeHtml(change.path)}"><strong>${escapeHtml(change.path)}</strong><span>${escapeHtml(change.label || change.status || 'Changed')}</span></button>
    <button class="button compact" data-toggle-stage="${escapeHtml(change.path)}" data-staged="${change.staged ? 'true' : 'false'}">${action}</button>
  </article>`;
}

function renderDiff() {
  const diff = app.data?.diff_text || '';
  const change = (app.data?.changes || []).find((item) => item.path === app.selectedChange) || (app.data?.changes || [])[0];
  if (change && !app.selectedChange) app.selectedChange = change.path;
  els.diffTitle.textContent = change ? change.path : 'No changed file selected';
  els.selectedChangeStatus.textContent = change ? change.label || change.status : 'Clean';
  els.diffOutput.innerHTML = diff ? colorDiff(extractFileDiff(diff, app.selectedChange || change?.path)) : 'No differences found.';
}

function extractFileDiff(diff, path) {
  if (!path) return diff;
  const marker = `Diff: ${path}`;
  const start = diff.indexOf(marker);
  if (start === -1) return diff;
  const rest = diff.slice(start);
  const next = rest.indexOf('\n🌿 Diff:', 1);
  return next === -1 ? rest : rest.slice(0, next);
}

function colorDiff(diff) {
  return escapeHtml(cleanOutput(diff)).split('\n').map((line) => {
    const cls = line.startsWith('+') && !line.startsWith('+++') ? 'added-line' : line.startsWith('-') && !line.startsWith('---') ? 'removed-line' : 'context-line';
    return `<span class="${cls}">${line || ' '}</span>`;
  }).join('\n');
}

function renderHistory(commits, tags) {
  const tagsByCommit = Object.entries(tags).reduce((acc, [tag, commit]) => ({ ...acc, [commit]: [...(acc[commit] || []), tag] }), {});
  els.commitTimeline.innerHTML = commits.length ? [...commits].reverse().map((commit) => {
    const active = app.selectedCommit?.id === commit.id ? 'selected' : '';
    return `<li class="${active}" data-commit="${escapeHtml(commit.id)}"><span></span><button><strong>${escapeHtml(commit.message || 'Commit')}</strong><small>${escapeHtml(commit.id)} · ${escapeHtml(commit.branch || 'detached')} · ${escapeHtml(commit.time || '')}</small></button></li>`;
  }).join('') : '<li><span></span><button><strong>No commits yet</strong><small>Your first commit will appear here.</small></button></li>';

  if (!app.selectedCommit && commits.length) app.selectedCommit = commits.at(-1);
  const commit = app.selectedCommit;
  if (!commit) return;
  const tagText = (tagsByCommit[commit.id] || []).join(', ') || 'No tags';
  els.commitDetailTitle.textContent = commit.message || commit.id;
  els.commitDetails.innerHTML = `<dl><dt>Commit</dt><dd>${escapeHtml(commit.id)}</dd><dt>Branch</dt><dd>${escapeHtml(commit.branch || 'detached')}</dd><dt>Created</dt><dd>${escapeHtml(commit.time || '')}</dd><dt>Parents</dt><dd>${escapeHtml((commit.parents || []).join(', ') || 'Root commit')}</dd><dt>Tags</dt><dd>${escapeHtml(tagText)}</dd><dt>Files</dt><dd>${escapeHtml([...(commit.files || []), ...Object.keys(commit.changes || {})].join(', ') || 'No file list recorded')}</dd></dl>`;
}

function renderBranches(branches) {
  const current = app.data?.current_branch || '';
  const names = Object.keys(branches);
  els.branchSelector.innerHTML = names.map((name) => `<option value="${escapeHtml(name)}" ${name === current ? 'selected' : ''}>${escapeHtml(name)}</option>`).join('');
  els.branchStartPoint.innerHTML = '<option value="">Start from current HEAD</option>' + (app.data?.log || []).map((commit) => `<option value="${escapeHtml(commit.id)}">${escapeHtml(commit.message || commit.id)} · ${escapeHtml(commit.id)}</option>`).join('');
  els.branchList.innerHTML = names.map((name) => `<article class="branch-card ${name === current ? 'active' : ''}"><strong>${escapeHtml(name)}</strong><span>${escapeHtml(branches[name] || 'No commits')}</span></article>`).join('') || '<p class="muted">No branches yet.</p>';
  els.mergeCandidates.innerHTML = names.filter((name) => name !== current).map((name) => `<button class="merge-card" data-merge="${escapeHtml(name)}"><strong>${escapeHtml(name)}</strong><span>Merge into ${escapeHtml(current || 'current branch')}</span></button>`).join('') || '<p class="muted">No merge candidates.</p>';
}

function renderFiles() {
  const query = els.fileSearch.value.toLowerCase();
  const files = (app.data?.files || []).filter((file) => file.path.toLowerCase().includes(query));
  els.fileList.innerHTML = files.length ? files.map((file) => `<button class="file-row" data-path="${escapeHtml(file.path)}"><span>${escapeHtml(file.path)}</span><em>${file.size} bytes</em></button>`).join('') : '<p class="empty-state muted">No files found.</p>';
}

function renderRemotes(remotes) {
  els.remoteList.innerHTML = Object.entries(remotes).map(([name, path]) => `<p><strong>${escapeHtml(name)}</strong><br><span>${escapeHtml(path)}</span></p>`).join('') || '<p class="muted">No remotes configured.</p>';
}

async function openFile(path) {
  const file = await request(apiUrl('/api/file', { repo: app.repo, path }));
  els.editorPath.value = file.path;
  els.editorTitle.textContent = file.path;
  els.fileEditor.value = file.content;
}

function shortPath(path) {
  const parts = String(path).split('/').filter(Boolean);
  return parts.slice(-2).join('/') || path;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]);
}

els.loadRepo.addEventListener('click', () => loadState(els.repoPath.value));
els.initializeRepo.addEventListener('click', () => act('initialize', {}, 'Workspace tracking started'));
els.refreshState.addEventListener('click', () => loadState().then(() => showToast('Workspace refreshed')));
els.stageAll.addEventListener('click', () => act('stage_all', {}, 'All changes staged'));
els.unstageAll.addEventListener('click', async () => {
  for (const change of (app.data?.changes || []).filter((item) => item.staged)) await act('unstage_file', { path: change.path }, `Unstaged ${change.path}`);
});

$('#changes').addEventListener('click', (event) => {
  const select = event.target.closest('[data-select-change]');
  const toggle = event.target.closest('[data-toggle-stage]');
  if (select) { app.selectedChange = select.dataset.selectChange; render(); }
  if (toggle) act(toggle.dataset.staged === 'true' ? 'unstage_file' : 'stage_file', { path: toggle.dataset.toggleStage }, toggle.dataset.staged === 'true' ? 'Change unstaged' : 'Change staged');
});

els.commitForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const message = els.commitMessage.value.trim();
  if (!message) return showToast('Write a commit message first');
  act('commit', { message }, 'Commit created').then(() => { els.commitMessage.value = ''; app.selectedCommit = app.data?.log?.at(-1) || null; });
});

els.commitTimeline.addEventListener('click', (event) => {
  const item = event.target.closest('[data-commit]');
  if (!item) return;
  app.selectedCommit = (app.data?.log || []).find((commit) => commit.id === item.dataset.commit);
  render();
});
els.branchSelector.addEventListener('change', () => act('switch_branch', { branch: els.branchSelector.value }, `Switched to ${els.branchSelector.value}`));
els.createBranch.addEventListener('click', () => {
  if (!els.newBranchName.value.trim()) return showToast('Name the new branch first');
  act('create_branch', { name: els.newBranchName.value.trim(), commit: els.branchStartPoint.value }, 'Branch created').then(() => { els.newBranchName.value = ''; });
});
els.mergeCandidates.addEventListener('click', (event) => {
  const card = event.target.closest('[data-merge]');
  if (card) act('merge_branch', { branch: card.dataset.merge }, `Merged ${card.dataset.merge}`);
});
els.continueMerge.addEventListener('click', () => act('merge_continue', {}, 'Merge completed'));
els.abortMerge.addEventListener('click', () => act('merge_abort', {}, 'Merge aborted'));

els.fileSearch.addEventListener('input', renderFiles);
els.fileList.addEventListener('click', (event) => { const row = event.target.closest('[data-path]'); if (row) openFile(row.dataset.path); });
els.newFile.addEventListener('click', () => { els.editorTitle.textContent = 'New file'; els.editorPath.value = 'new-file.txt'; els.fileEditor.value = ''; });
els.saveFile.addEventListener('click', async () => {
  const result = await request('/api/file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo: app.repo, path: els.editorPath.value, content: els.fileEditor.value }) });
  app.data = result.state; render(); showToast('File saved');
});
els.deleteFile.addEventListener('click', async () => {
  const path = els.editorPath.value;
  if (!path || !window.confirm(`Delete ${path}?`)) return;
  const result = await request(apiUrl('/api/file', { repo: app.repo, path }), { method: 'DELETE' });
  app.data = result.state; els.fileEditor.value = ''; render(); showToast('File deleted');
});

els.addRemote.addEventListener('click', () => act('add_remote', { remote: els.remoteName.value, remote_path: els.remotePath.value }, 'Remote added'));
els.fetchRemote.addEventListener('click', () => act('fetch_remote', { remote: els.remoteName.value }, 'Fetched remote changes'));
els.pullRemote.addEventListener('click', () => act('pull_remote', { remote: els.remoteName.value, branch: app.data?.current_branch || 'main' }, 'Pulled remote branch'));
els.pushRemote.addEventListener('click', () => act('push_remote', { remote: els.remoteName.value, branch: app.data?.current_branch || 'main' }, 'Pushed current branch'));
els.checkIntegrity.addEventListener('click', () => act('check_integrity', {}, 'Repository checked'));

const navLinks = $$('.studio-nav a');
const observer = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navLinks.forEach((link) => link.classList.toggle('active', link.getAttribute('href') === `#${visible.target.id}`));
}, { rootMargin: '-25% 0px -60% 0px', threshold: [0.15, 0.3, 0.6] });
navLinks.map((link) => document.querySelector(link.getAttribute('href'))).filter(Boolean).forEach((section) => observer.observe(section));

loadState(new URLSearchParams(window.location.search).get('repo') || '').catch((error) => showToast(error.message));
