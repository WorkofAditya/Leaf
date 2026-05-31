const state = { repo: '', data: null, selectedFile: '' };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const els = {
  repoPath: $('#repoPath'),
  loadRepo: $('#loadRepo'),
  repoHint: $('#repoHint'),
  repoState: $('#repoState'),
  repoLocation: $('#repoLocation'),
  currentBranch: $('#currentBranch'),
  headCommit: $('#headCommit'),
  fileCount: $('#fileCount'),
  stagedCount: $('#stagedCount'),
  integrityState: $('#integrityState'),
  mergeState: $('#mergeState'),
  lastCommand: $('#lastCommand'),
  commandOutput: $('#commandOutput'),
  statusOutput: $('#statusOutput'),
  diffOutput: $('#diffOutput'),
  fileList: $('#fileList'),
  fileSearch: $('#fileSearch'),
  editorTitle: $('#editorTitle'),
  editorPath: $('#editorPath'),
  fileEditor: $('#fileEditor'),
  saveFile: $('#saveFile'),
  deleteFile: $('#deleteFile'),
  newFile: $('#newFile'),
  commitTimeline: $('#commitTimeline'),
  refList: $('#refList'),
  remoteList: $('#remoteList'),
  metadataOutput: $('#metadataOutput'),
  commandSearch: $('#commandSearch'),
  commandGrid: $('#commandGrid'),
  toast: $('#toast'),
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

async function apiGet(path, params = {}) {
  const response = await fetch(apiUrl(path, params));
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || 'Request failed');
  return data;
}

async function apiPost(path, body = {}) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || 'Request failed');
  return data;
}

function shellSplit(input) {
  const args = [];
  let current = '';
  let quote = '';
  let escape = false;

  for (const char of input.trim()) {
    if (escape) {
      current += char;
      escape = false;
    } else if (char === '\\') {
      escape = true;
    } else if (quote) {
      if (char === quote) quote = '';
      else current += char;
    } else if (char === '"' || char === "'") {
      quote = char;
    } else if (/\s/.test(char)) {
      if (current) {
        args.push(current);
        current = '';
      }
    } else {
      current += char;
    }
  }
  if (current) args.push(current);
  return args;
}

function setOutput(result) {
  els.lastCommand.textContent = result.command || 'leaf';
  els.commandOutput.textContent = [result.stdout, result.stderr].filter(Boolean).join('\n') || '(no output)';
}

async function loadState(repo = state.repo) {
  try {
    const data = await apiGet('/api/state', { repo });
    state.repo = data.repo;
    state.data = data;
    els.repoPath.value = data.repo;
    renderState();
    return data;
  } catch (error) {
    showToast(error.message);
    throw error;
  }
}

async function runLeaf(command, args = []) {
  try {
    const result = await apiPost('/api/run', { repo: state.repo || els.repoPath.value, command, args });
    setOutput(result);
    state.data = result.state;
    state.repo = result.state.repo;
    renderState();
    showToast(result.ok ? `Ran ${result.command}` : `Leaf returned ${result.returncode}`);
    return result;
  } catch (error) {
    showToast(error.message);
    els.commandOutput.textContent = error.message;
    throw error;
  }
}

function renderState() {
  const data = state.data;
  if (!data) return;
  const log = data.log || [];
  const branches = data.branches || {};
  const tags = data.tags || {};
  const remotes = data.remotes || {};
  const index = data.index || {};
  const merge = data.merge_state || {};

  els.repoHint.textContent = data.is_repo ? 'Connected to a Leaf repository.' : 'Not initialized yet. Run leaf init.';
  els.repoState.textContent = data.is_repo ? 'Leaf repo' : 'Not initialized';
  els.repoLocation.textContent = data.repo;
  els.currentBranch.textContent = data.current_branch || 'Detached';
  els.headCommit.textContent = data.head ? `HEAD ${data.head}` : 'No commits yet';
  els.fileCount.textContent = String((data.files || []).length);
  els.stagedCount.textContent = `${Object.keys(index).length} staged path(s)`;
  els.integrityState.textContent = data.is_repo ? 'Connected' : 'Setup needed';
  els.mergeState.textContent = Object.keys(merge).length ? `Merge from ${merge.source_branch || 'branch'}` : 'No merge in progress';
  els.statusOutput.textContent = data.status_text || 'No status output.';
  els.diffOutput.textContent = data.diff_text || 'No differences found.';

  renderFiles();
  renderHistory(log, tags);
  renderRefs(branches, tags);
  renderRemotes(remotes);
  renderSelects(branches);

  els.metadataOutput.textContent = JSON.stringify(
    { head: data.head, current_branch: data.current_branch, branches, tags, remotes, index, merge_state: merge },
    null,
    2,
  );
}

function renderFiles() {
  const query = els.fileSearch.value.toLowerCase();
  const files = (state.data?.files || []).filter((file) => file.path.toLowerCase().includes(query));
  els.fileList.innerHTML = files.length
    ? files.map((file) => `<button class="file-row" data-path="${escapeHtml(file.path)}"><span>${escapeHtml(file.path)}</span><em>${file.size} bytes</em></button>`).join('')
    : '<p class="muted empty-state">No files found.</p>';
}

function renderHistory(log, tags) {
  const tagsByCommit = Object.entries(tags).reduce((acc, [tag, commit]) => {
    acc[commit] = [...(acc[commit] || []), tag];
    return acc;
  }, {});
  els.commitTimeline.innerHTML = log.length
    ? [...log]
        .reverse()
        .map((commit) => {
          const tagText = tagsByCommit[commit.id] ? ` · tags: ${tagsByCommit[commit.id].join(', ')}` : '';
          const parents = (commit.parents || []).length > 1 ? ' · merge commit' : '';
          return `<li><span></span><div><strong>${escapeHtml(commit.id)}</strong><p>${escapeHtml(commit.message || 'save')} · ${escapeHtml(commit.branch || 'detached')}${parents}${tagText}<br>${escapeHtml(commit.time || '')}</p></div></li>`;
        })
        .join('')
    : '<li><span></span><div><strong>No commits yet</strong><p>Save your first change from the command center.</p></div></li>';
}

function renderRefs(branches, tags) {
  const branchHtml = Object.entries(branches).map(([name, commit]) => `<span><b>branch</b>${escapeHtml(name)} <em>${escapeHtml(commit || 'empty')}</em></span>`);
  const tagHtml = Object.entries(tags).map(([name, commit]) => `<span><b>tag</b>${escapeHtml(name)} <em>${escapeHtml(commit || '')}</em></span>`);
  els.refList.innerHTML = [...branchHtml, ...tagHtml].join('') || '<p class="muted">No refs yet.</p>';
}

function renderRemotes(remotes) {
  els.remoteList.innerHTML = Object.entries(remotes)
    .map(([name, path]) => `<p><strong>${escapeHtml(name)}</strong><br><span>${escapeHtml(path)}</span></p>`)
    .join('') || '<p class="muted">No remotes configured.</p>';
}

function renderSelects(branches) {
  const options = Object.keys(branches).map((branch) => `<option value="${escapeHtml(branch)}">${escapeHtml(branch)}</option>`).join('');
  $('#checkoutBranch').innerHTML = options;
  $('#mergeBranch').innerHTML = options;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[char]);
}

async function openFile(path) {
  const file = await apiGet('/api/file', { repo: state.repo, path });
  state.selectedFile = file.path;
  els.editorPath.value = file.path;
  els.editorTitle.textContent = file.path;
  els.fileEditor.value = file.content;
}

els.loadRepo.addEventListener('click', () => loadState(els.repoPath.value));
els.fileSearch.addEventListener('input', renderFiles);
els.fileList.addEventListener('click', (event) => {
  const row = event.target.closest('[data-path]');
  if (row) openFile(row.dataset.path);
});
els.newFile.addEventListener('click', () => {
  state.selectedFile = '';
  els.editorPath.value = 'new-file.txt';
  els.editorTitle.textContent = 'New file';
  els.fileEditor.value = '';
});
els.saveFile.addEventListener('click', async () => {
  const result = await apiPost('/api/file', { repo: state.repo, path: els.editorPath.value, content: els.fileEditor.value });
  state.data = result.state;
  renderState();
  showToast(`Saved ${els.editorPath.value}`);
});
els.deleteFile.addEventListener('click', async () => {
  const path = els.editorPath.value;
  if (!path || !window.confirm(`Delete ${path}?`)) return;
  const response = await fetch(apiUrl('/api/file', { repo: state.repo, path }), { method: 'DELETE' });
  const result = await response.json();
  if (!response.ok || result.ok === false) throw new Error(result.error || 'Delete failed');
  state.data = result.state;
  els.fileEditor.value = '';
  renderState();
  showToast(`Deleted ${path}`);
});

$$('[data-run]').forEach((button) => {
  button.addEventListener('click', () => runLeaf(button.dataset.run, JSON.parse(button.dataset.args || '[]')));
});

$('#customCommand').addEventListener('submit', (event) => {
  event.preventDefault();
  runLeaf($('#commandName').value, shellSplit($('#commandArgs').value));
});

$('#createBranch').addEventListener('click', () => runLeaf('branch', [$('#branchName').value, $('#branchCommit').value].filter(Boolean)));
$('#checkoutSelected').addEventListener('click', () => runLeaf('checkout', [$('#checkoutBranch').value]));
$('#mergeSelected').addEventListener('click', () => runLeaf('merge', [$('#mergeBranch').value]));
$('#restoreCommit').addEventListener('click', () => runLeaf('restore', [$('#targetCommit').value]));
$('#softReset').addEventListener('click', () => runLeaf('reset', ['--soft', $('#targetCommit').value]));
$('#hardReset').addEventListener('click', () => runLeaf('reset', ['--hard', $('#targetCommit').value]));
$('#revertCommit').addEventListener('click', () => runLeaf('revert', [$('#targetCommit').value]));
$('#createTag').addEventListener('click', () => runLeaf('tag', [$('#tagName').value, $('#tagCommit').value].filter(Boolean)));
$('#ignoreButton').addEventListener('click', () => runLeaf('ignore', [$('#ignorePath').value]));
$('#addRemote').addEventListener('click', () => runLeaf('remote', ['add', $('#remoteName').value, $('#remotePath').value]));
$('#fetchRemote').addEventListener('click', () => runLeaf('fetch', [$('#remoteName').value]));
$('#pullRemote').addEventListener('click', () => runLeaf('pull', [$('#remoteName').value, 'main']));
$('#pushRemote').addEventListener('click', () => runLeaf('push', [$('#remoteName').value, 'main']));
$('#cloneRepo').addEventListener('click', () => runLeaf('clone', [$('#cloneSource').value, $('#cloneDest').value].filter(Boolean)));

els.commandSearch.addEventListener('input', (event) => {
  const query = event.target.value.trim().toLowerCase();
  $$('#commandGrid article').forEach((card) => {
    const text = `${card.textContent} ${card.dataset.keywords}`.toLowerCase();
    card.classList.toggle('hidden', query && !text.includes(query));
  });
});

const navLinks = $$('.nav-list a');
const sections = navLinks.map((link) => document.querySelector(link.getAttribute('href'))).filter(Boolean);
const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    navLinks.forEach((link) => link.classList.toggle('active', link.getAttribute('href') === `#${visible.target.id}`));
  },
  { rootMargin: '-25% 0px -60% 0px', threshold: [0.15, 0.3, 0.6] },
);
sections.forEach((section) => observer.observe(section));

loadState(new URLSearchParams(window.location.search).get('repo') || '').then(() => runLeaf('status')).catch(() => {});
