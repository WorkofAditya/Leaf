const app = { repo: '', data: null, selectedChange: '', selectedCommit: null, page: 'code' };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const els = {
  repoPath: $('#repoPath'), loadRepo: $('#loadRepo'), initializeRepo: $('#initializeRepo'), connectionLabel: $('#connectionLabel'),
  repoTitle: $('#repoTitle'), repoSubtitle: $('#repoSubtitle'), currentBranch: $('#currentBranch'), headCommit: $('#headCommit'),
  changedCount: $('#changedCount'), stagedSummary: $('#stagedSummary'), commitCount: $('#commitCount'), latestCommit: $('#latestCommit'),
  repoHealth: $('#repoHealth'), mergeState: $('#mergeState'), branchSelector: $('#branchSelector'), refreshState: $('#refreshState'),
  fileSearch: $('#fileSearch'), fileList: $('#fileList'), newFile: $('#newFile'), editorTitle: $('#editorTitle'), editorPath: $('#editorPath'),
  fileEditor: $('#fileEditor'), saveFile: $('#saveFile'), deleteFile: $('#deleteFile'), stageAll: $('#stageAll'), stagedList: $('#stagedList'),
  unstagedList: $('#unstagedList'), commitForm: $('#commitForm'), commitMessage: $('#commitMessage'), commitTimeline: $('#commitTimeline'),
  commitDetailTitle: $('#commitDetailTitle'), commitDetails: $('#commitDetails'), commitDiffOutput: $('#commitDiffOutput'), branchList: $('#branchList'),
  newBranchName: $('#newBranchName'), branchStartPoint: $('#branchStartPoint'), createBranch: $('#createBranch'), branchMergeCandidates: $('#branchMergeCandidates'),
  mergeBaseBranch: $('#mergeBaseBranch'), mergeCompareBranch: $('#mergeCompareBranch'), mergeSelected: $('#mergeSelected'), mergeControls: $('#mergeControls'),
  continueMerge: $('#continueMerge'), abortMerge: $('#abortMerge'), mergeReview: $('#mergeReview'), mergeDiffOutput: $('#mergeDiffOutput'), remoteList: $('#remoteList'),
  remoteName: $('#remoteName'), remotePath: $('#remotePath'), addRemote: $('#addRemote'), fetchRemote: $('#fetchRemote'), pullRemote: $('#pullRemote'),
  pushRemote: $('#pushRemote'), ignorePath: $('#ignorePath'), ignoreButton: $('#ignoreButton'), checkIntegrity: $('#checkIntegrity'), activityLog: $('#activityLog'), toast: $('#toast'),
};

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add('show');
  window.setTimeout(() => els.toast.classList.remove('show'), 1800);
}

function apiUrl(path, params = {}) {
  const url = new URL(path, window.location.origin);
  Object.entries(params).forEach(([key, value]) => value ? url.searchParams.set(key, value) : null);
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
    app.repo = result.state.repo;
    app.data = result.state;
    if (els.activityLog) els.activityLog.textContent = cleanOutput(result.stdout || result.stderr || success);
    render();
    showToast(success);
    return result;
  } catch (error) {
    if (els.activityLog) els.activityLog.textContent = error.message;
    showToast(error.message);
    throw error;
  }
}

function cleanOutput(text) {
  return String(text || '').replace(/\x1b\[[0-9;]*m/g, '').trim() || 'Ready.';
}

function render() {
  const data = app.data;
  if (!data) return;
  const commits = data.log || [];
  const changes = data.changes || [];
  const staged = changes.filter((change) => change.staged);
  const mergeActive = Object.keys(data.merge_state || {}).length > 0;
  const branch = data.current_branch || 'Detached';

  els.connectionLabel.textContent = data.is_repo ? `${branch} · ${changes.length} changed` : 'Folder is not tracked yet';
  els.repoTitle.textContent = data.is_repo ? shortPath(data.repo) : 'Start tracking this folder';
  els.repoSubtitle.textContent = data.repo;
  els.currentBranch.textContent = branch;
  els.headCommit.textContent = data.head ? `HEAD ${data.head}` : 'No commits yet';
  els.changedCount.textContent = String(changes.length);
  els.stagedSummary.textContent = `${staged.length} staged`;
  els.commitCount.textContent = String(commits.length);
  els.latestCommit.textContent = commits.at(-1)?.message || 'No history yet';
  els.repoHealth.textContent = data.is_repo ? 'Connected' : 'Setup needed';
  els.mergeState.textContent = mergeActive ? `Merge from ${data.merge_state.source_branch || 'branch'}` : 'No merge in progress';
  els.initializeRepo.classList.toggle('hidden', data.is_repo);
  els.commitForm.classList.toggle('hidden', staged.length === 0);
  els.mergeControls.classList.toggle('hidden', !mergeActive);

  renderPages();
  renderFiles();
  renderChanges(changes);
  renderHistory(commits, data.tags || {});
  renderBranches(data.branches || {});
  renderMergeRequest(changes);
  renderRemotes(data.remotes || {});
}

function renderPages() {
  $$('.repo-page').forEach((page) => page.classList.toggle('active', page.dataset.page === app.page));
  $$('[data-page-link]').forEach((link) => link.classList.toggle('active', link.dataset.pageLink === app.page));
}

function renderFiles() {
  const query = els.fileSearch.value.toLowerCase();
  const changed = new Map((app.data?.changes || []).map((change) => [change.path, change]));
  const files = (app.data?.files || []).filter((file) => file.path.toLowerCase().includes(query));
  els.fileList.innerHTML = files.length ? files.map((file) => {
    const change = changed.get(file.path);
    const badge = change ? `<em>${escapeHtml(change.label || change.status)}</em>` : '<em>clean</em>';
    return `<button class="file-row" data-path="${escapeHtml(file.path)}"><span>${escapeHtml(file.path)}</span>${badge}</button>`;
  }).join('') : '<p class="empty-state muted">No files found.</p>';
}

function renderChanges(changes) {
  const staged = changes.filter((change) => change.staged);
  const unstaged = changes.filter((change) => !change.staged);
  els.stagedList.innerHTML = staged.length ? staged.map(changeRow).join('') : '<p class="empty-state muted">Nothing staged.</p>';
  els.unstagedList.innerHTML = unstaged.length ? unstaged.map(changeRow).join('') : '<p class="empty-state muted">No unstaged changes.</p>';
}

function changeRow(change) {
  const action = change.staged ? 'Unstage' : 'Stage';
  return `<article class="change-row ${app.selectedChange === change.path ? 'selected' : ''}">
    <button class="change-main" data-select-change="${escapeHtml(change.path)}"><strong>${escapeHtml(change.path)}</strong><span>${escapeHtml(change.label || change.status || 'Changed')}</span></button>
    <button class="button compact" data-toggle-stage="${escapeHtml(change.path)}" data-staged="${change.staged ? 'true' : 'false'}">${action}</button>
  </article>`;
}

function renderHistory(commits, tags) {
  const tagsByCommit = Object.entries(tags).reduce((acc, [tag, commit]) => ({ ...acc, [commit]: [...(acc[commit] || []), tag] }), {});
  if (!app.selectedCommit && commits.length) app.selectedCommit = commits.at(-1);
  els.commitTimeline.innerHTML = commits.length ? [...commits].reverse().map((commit) => `<li class="${app.selectedCommit?.id === commit.id ? 'selected' : ''}" data-commit="${escapeHtml(commit.id)}"><span></span><button><strong>${escapeHtml(commit.message || 'Commit')}</strong><small>${escapeHtml(commit.id)} · ${escapeHtml(commit.branch || 'detached')} · ${escapeHtml(commit.time || '')}</small></button></li>`).join('') : '<li><span></span><button><strong>No commits yet</strong><small>Commit history will appear here.</small></button></li>';

  const commit = app.selectedCommit;
  if (!commit) return;
  const tagText = (tagsByCommit[commit.id] || []).join(', ') || 'No tags';
  els.commitDetailTitle.textContent = commit.message || commit.id;
  els.commitDetails.innerHTML = `<dl><dt>Commit</dt><dd>${escapeHtml(commit.id)}</dd><dt>Branch</dt><dd>${escapeHtml(commit.branch || 'detached')}</dd><dt>Created</dt><dd>${escapeHtml(commit.time || '')}</dd><dt>Parents</dt><dd>${escapeHtml((commit.parents || []).join(', ') || 'Root commit')}</dd><dt>Tags</dt><dd>${escapeHtml(tagText)}</dd><dt>Files</dt><dd>${escapeHtml([...(commit.files || []), ...Object.keys(commit.changes || {})].join(', ') || 'No file list recorded')}</dd></dl>`;
  els.commitDiffOutput.innerHTML = colorDiff(app.data?.diff_text || 'No working-tree diff available.');
}

function renderBranches(branches) {
  const current = app.data?.current_branch || '';
  const names = Object.keys(branches);
  const options = names.map((name) => `<option value="${escapeHtml(name)}" ${name === current ? 'selected' : ''}>${escapeHtml(name)}</option>`).join('');
  els.branchSelector.innerHTML = options;
  els.mergeBaseBranch.innerHTML = options;
  els.mergeCompareBranch.innerHTML = names.filter((name) => name !== current).map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
  els.branchStartPoint.innerHTML = '<option value="">Start from current HEAD</option>' + (app.data?.log || []).map((commit) => `<option value="${escapeHtml(commit.id)}">${escapeHtml(commit.message || commit.id)} · ${escapeHtml(commit.id)}</option>`).join('');
  els.branchList.innerHTML = names.map((name) => `<article class="branch-card ${name === current ? 'active' : ''}"><div><strong>${escapeHtml(name)}</strong><span>${escapeHtml(branches[name] || 'No commits')}</span></div><button class="button compact ghost" data-switch-branch="${escapeHtml(name)}">Switch</button></article>`).join('') || '<p class="muted">No branches yet.</p>';
  els.branchMergeCandidates.innerHTML = names.filter((name) => name !== current).map((name) => `<button class="merge-card" data-merge="${escapeHtml(name)}"><strong>${escapeHtml(name)}</strong><span>Merge into ${escapeHtml(current || 'current branch')}</span></button>`).join('') || '<p class="muted">No merge candidates.</p>';
}

function renderMergeRequest(changes) {
  els.mergeReview.innerHTML = changes.length ? changes.map((change) => `<article><strong>${escapeHtml(change.path)}</strong><span>${escapeHtml(change.label || change.status)}</span></article>`).join('') : '<p class="muted">No current working-tree changes to review.</p>';
  els.mergeDiffOutput.innerHTML = colorDiff(app.data?.diff_text || 'No diff available.');
}

function renderRemotes(remotes) {
  els.remoteList.innerHTML = Object.entries(remotes).map(([name, path]) => `<article><strong>${escapeHtml(name)}</strong><span>${escapeHtml(path)}</span></article>`).join('') || '<p class="muted">No remotes configured.</p>';
}

async function openFile(path) {
  const file = await request(apiUrl('/api/file', { repo: app.repo, path }));
  els.editorPath.value = file.path;
  els.editorTitle.textContent = file.path;
  els.fileEditor.value = file.content;
}

function colorDiff(diff) {
  return escapeHtml(cleanOutput(diff)).split('\n').map((line) => {
    const cls = line.startsWith('+') && !line.startsWith('+++') ? 'added-line' : line.startsWith('-') && !line.startsWith('---') ? 'removed-line' : 'context-line';
    return `<span class="${cls}">${line || ' '}</span>`;
  }).join('\n');
}

function shortPath(path) {
  const parts = String(path).split('/').filter(Boolean);
  return parts.slice(-2).join('/') || path;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]);
}

function navigate(page) {
  app.page = page;
  window.location.hash = page;
  renderPages();
}

$$('[data-page-link]').forEach((link) => link.addEventListener('click', (event) => { event.preventDefault(); navigate(link.dataset.pageLink); }));
els.loadRepo.addEventListener('click', () => loadState(els.repoPath.value));
els.initializeRepo.addEventListener('click', () => act('initialize', {}, 'Repository tracking started'));
els.refreshState.addEventListener('click', () => loadState().then(() => showToast('Repository refreshed')));
els.branchSelector.addEventListener('change', () => act('switch_branch', { branch: els.branchSelector.value }, `Switched to ${els.branchSelector.value}`));
els.fileSearch.addEventListener('input', renderFiles);
els.fileList.addEventListener('click', (event) => { const row = event.target.closest('[data-path]'); if (row) openFile(row.dataset.path); });
els.newFile.addEventListener('click', () => { els.editorTitle.textContent = 'New file'; els.editorPath.value = 'new-file.txt'; els.fileEditor.value = ''; });
els.saveFile.addEventListener('click', async () => { const result = await request('/api/file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ repo: app.repo, path: els.editorPath.value, content: els.fileEditor.value }) }); app.data = result.state; render(); showToast('File saved'); });
els.deleteFile.addEventListener('click', async () => { const path = els.editorPath.value; if (!path || !window.confirm(`Delete ${path}?`)) return; const result = await request(apiUrl('/api/file', { repo: app.repo, path }), { method: 'DELETE' }); app.data = result.state; els.fileEditor.value = ''; render(); showToast('File deleted'); });
els.stageAll.addEventListener('click', () => act('stage_all', {}, 'All changes staged'));
$('#page-code').addEventListener('click', (event) => { const toggle = event.target.closest('[data-toggle-stage]'); if (toggle) act(toggle.dataset.staged === 'true' ? 'unstage_file' : 'stage_file', { path: toggle.dataset.toggleStage }, toggle.dataset.staged === 'true' ? 'Change unstaged' : 'Change staged'); });
els.commitForm.addEventListener('submit', (event) => { event.preventDefault(); const message = els.commitMessage.value.trim(); if (!message) return showToast('Write a commit message first'); act('commit', { message }, 'Commit created').then(() => { els.commitMessage.value = ''; app.selectedCommit = app.data?.log?.at(-1) || null; }); });
els.commitTimeline.addEventListener('click', (event) => { const item = event.target.closest('[data-commit]'); if (!item) return; app.selectedCommit = (app.data?.log || []).find((commit) => commit.id === item.dataset.commit); render(); });
els.branchList.addEventListener('click', (event) => { const button = event.target.closest('[data-switch-branch]'); if (button) act('switch_branch', { branch: button.dataset.switchBranch }, `Switched to ${button.dataset.switchBranch}`); });
els.createBranch.addEventListener('click', () => { if (!els.newBranchName.value.trim()) return showToast('Name the new branch first'); act('create_branch', { name: els.newBranchName.value.trim(), commit: els.branchStartPoint.value }, 'Branch created').then(() => { els.newBranchName.value = ''; }); });
els.branchMergeCandidates.addEventListener('click', (event) => { const card = event.target.closest('[data-merge]'); if (card) act('merge_branch', { branch: card.dataset.merge }, `Merged ${card.dataset.merge}`); });
els.mergeSelected.addEventListener('click', () => act('merge_branch', { branch: els.mergeCompareBranch.value }, `Merged ${els.mergeCompareBranch.value}`));
els.continueMerge.addEventListener('click', () => act('merge_continue', {}, 'Merge completed'));
els.abortMerge.addEventListener('click', () => act('merge_abort', {}, 'Merge aborted'));
els.addRemote.addEventListener('click', () => act('add_remote', { remote: els.remoteName.value, remote_path: els.remotePath.value }, 'Remote added'));
els.fetchRemote.addEventListener('click', () => act('fetch_remote', { remote: els.remoteName.value }, 'Fetched remote'));
els.pullRemote.addEventListener('click', () => act('pull_remote', { remote: els.remoteName.value, branch: app.data?.current_branch || 'main' }, 'Pulled branch'));
els.pushRemote.addEventListener('click', () => act('push_remote', { remote: els.remoteName.value, branch: app.data?.current_branch || 'main' }, 'Pushed branch'));
els.ignoreButton.addEventListener('click', () => act('ignore_path', { path: els.ignorePath.value }, 'Ignore rule added'));
els.checkIntegrity.addEventListener('click', () => act('check_integrity', {}, 'Repository checked'));

const initialPage = window.location.hash.replace('#', '') || 'code';
app.page = ['code', 'commits', 'branches', 'merge-requests', 'remotes', 'settings'].includes(initialPage) ? initialPage : 'code';
loadState(new URLSearchParams(window.location.search).get('repo') || '').catch((error) => showToast(error.message));
