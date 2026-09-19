const token = document.querySelector('meta[name="xit-token"]').content;
const state = { project: null, currentPath: null, dirty: false };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body) headers['Content-Type'] = 'application/json';
  if (options.method && options.method !== 'GET') headers['X-XIT-Token'] = token;
  const response = await fetch(path, { ...options, headers });
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || '操作失败');
  return data;
}

function notice(message, error = false) {
  const box = $('#notice');
  box.textContent = message;
  box.classList.toggle('error', error);
  box.classList.remove('hidden');
  clearTimeout(notice.timer);
  notice.timer = setTimeout(() => box.classList.add('hidden'), 4500);
}

function setDirty(value) {
  state.dirty = value;
  $('#saveState').textContent = value ? '有未保存内容' : '内容已同步';
  $('#saveState').style.color = value ? '#a45b0b' : '';
  if (value) {
    if (state.currentPath) localDrafts.capture(state.currentPath, $('#editor').value, state.revision);
    scheduleSave();
    livePreview.changed();
  }
}

function showPanel(name) {
  document.body.classList.toggle('writing-mode', name === 'writing');
  $$('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === `panel-${name}`));
  $$('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.panel === name));
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (name === 'writing') livePreview.open(); else livePreview.close();
  if (name === 'home' && state.project) refreshHealth().catch(error => notice(error.message, true));
}

function updateProgress() {
  if (!state.project) return;
  const metadata = state.project.metadata;
  const required = ['title', 'english_title', 'author', 'student_id', 'major', 'grade', 'supervisor', 'date'];
  const completed = required.filter((key) => metadata[key] && !/请输入|请填写|TODO|TBD/i.test(metadata[key])).length;
  $('#progressText').textContent = `基本资料 ${completed}/${required.length} 项已填写`;
  $('#progressBar').textContent = `${state.project.chapter_count} 个章节 · 可随时增删`;
  window.onboardingReady?.(state.project);
}

function renderEnvironment(environment) {
  const names = { python: 'Python', pyyaml: 'PyYAML', pandoc: 'Pandoc', xelatex: 'XeLaTeX', biber: 'Biber', template: '原模板 ZIP', fonts: '模板常用字体' };
  $('#environmentGrid').innerHTML = Object.entries(environment).map(([key, item]) => `
    <div class="environment-item ${item.ok ? 'ok' : 'bad'}">
      <span class="status">${item.ok ? '✓' : '!'}</span>
      <div><strong>${names[key]}</strong><small title="${escapeHtml(item.version)}">${escapeHtml(item.version)}</small></div>
    </div>`).join('');
  const missing = Object.entries(environment).filter(([, item]) => !item.ok).map(([key]) => names[key]);
  const summary = $('#environmentSummary');
  summary.textContent = missing.length ? `缺少 ${missing.length} 项` : '程序就绪，请生成示例 PDF 验证';
  summary.className = `pill ${missing.length ? 'warn' : 'good'}`;
  const help = $('#environmentHelp');
  if (missing.length) {
    help.classList.remove('hidden');
    help.innerHTML = `<strong>还不能生成 PDF：缺少 ${missing.join('、')}</strong><p>${installHelp(missing)}</p>`;
  } else {
    help.classList.add('hidden');
  }
}

function installHelp(missing) {
  const messages = [];
  if (missing.includes('Pandoc')) messages.push('Windows 完整包已附带 Pandoc。请检查是否完整解压，以及 runtime/pandoc/pandoc.exe 是否存在。');
  if (missing.includes('XeLaTeX') || missing.includes('Biber')) messages.push('安装含 XeLaTeX 和 Biber 的 TeX Live；安装完成后重新启动论文助手。');
  if (missing.includes('原模板 ZIP')) messages.push('请把“厦门工学院毕业设计论文模板.zip”放回项目根目录。');
  if (missing.includes('模板常用字体')) messages.push('系统缺少原模板常用字体。请通过 Windows 的语言/字体设置补齐有授权的中文和西文字体，再编译检查；不要从来源不明的网站复制字体。');
  return messages.join(' ');
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
}

function renderMetadata(metadata) {
  const form = $('#metadataForm');
  Object.entries(metadata).forEach(([key, value]) => {
    if (form.elements[key]) form.elements[key].value = value ?? '';
  });
}

function renderDocuments(files) {
  const list = $('#documentList');
  list.innerHTML = '';
  files.forEach((file) => {
    const button = document.createElement('button');
    button.className = 'document-button';
    button.dataset.path = file.path;
    button.innerHTML = `${escapeHtml(file.label)}<small>${escapeHtml(file.path)}</small>`;
    button.addEventListener('click', () => loadFile(file));
    list.appendChild(button);
  });
}

async function loadProject(showMessage = false) {
  if (state.project && !(await flushSaves())) return;
  try {
    const project = await api('/api/project');
    state.project = project;
    localDrafts.init(project);
    renderTutorial(project.mode);
    renderEnvironment(project.environment);
    renderMetadata(project.metadata);
    renderDocuments(project.files);
    const current = project.files.find(file => file.path === state.currentPath) || project.files[0];
    if (current) await loadFile(current);
    livePreview.ready(project);
    updateProgress();
    $('#openPdf').classList.toggle('hidden', !project.pdf);
    $('#openPdf').textContent = project.portable_fonts ? '打开预览 PDF（替代字体，非原字体定稿）' : '打开生成的 PDF';
    if (showMessage) notice('状态已刷新。');
  } catch (error) {
    notice(error.message, true);
  }
}

async function saveMetadata() {
  if (state.metadataSaving) { try { await state.metadataSaving; } catch (_) { return false; } return saveMetadata(); }
  const metadata = Object.fromEntries(new FormData($('#metadataForm')).entries());
  try {
    state.metadataSaving = api('/api/metadata', { method: 'POST', body: JSON.stringify({ metadata }) });
    const result = await state.metadataSaving;
    localDrafts.acknowledge('@metadata', JSON.stringify(metadata));
    state.project.metadata = metadata;
    state.metadataDirty = JSON.stringify(metadata) !== JSON.stringify(Object.fromEntries(new FormData($('#metadataForm')).entries()));
    updateProgress();
    notice(result.message);
    return true;
  } catch (error) {
    notice(error.message, true);
    return false;
  } finally {
    state.metadataSaving = null;
  }
}

async function loadFile(file) {
  if (state.dirty && !(await flushSaves())) return;
  try {
    const result = await api(`/api/file?path=${encodeURIComponent(file.path)}`);
    state.currentPath = file.path;
    const writingFile = document.querySelector('#writingFile');
    if (writingFile) writingFile.value = file.path;
    state.revision = result.revision;
    $('#editor').value = result.text;
    attachEditHistory(file.path, result.text);
    $('#currentFileLabel').textContent = file.label;
    $('#currentFilePath').textContent = file.path;
    $('#fileHint').textContent = file.hint;
    $('.toolbar').classList.toggle('hidden', file.path.endsWith('.bib'));
    $$('.document-button').forEach((button) => button.classList.toggle('active', button.dataset.path === file.path));
    setDirty(false);
    updateWordCount();
  } catch (error) {
    notice(error.message, true);
  }
}

async function saveFile(quiet = false) {
  if (!state.currentPath) return true;
  if (state.saving) { try { await state.saving; } catch (_) { return false; } return state.dirty ? saveFile(quiet) : true; }
  const path = state.currentPath;
  const text = $('#editor').value;
  try {
    state.saving = api('/api/file', { method: 'POST', body: JSON.stringify({ path, text, revision: state.revision }) });
    const result = await state.saving;
    localDrafts.acknowledge(path, text);
    state.revision = result.revision;
    if (state.currentPath === path && $('#editor').value === text) setDirty(false);
    if (!quiet) notice(result.message);
    return true;
  } catch (error) {
    notice(error.message, true);
    return false;
  } finally {
    state.saving = null;
  }
}

function insertAtCursor(text, select = '') {
  const undoBefore = beforeAssistedEdit();
  const editor = $('#editor');
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  const before = editor.value.slice(0, start);
  const after = editor.value.slice(end);
  const selection = editor.value.slice(start, end) || select;
  const content = text.replace('__SELECTION__', selection);
  editor.value = before + content + after;
  editor.selectionStart = editor.selectionEnd = start + content.length;
  afterAssistedEdit(undoBefore);
  editor.focus();
  setDirty(true);
  updateWordCount();
}

const snippets = {
  section: '\n## 小节标题\n\n在这里写正文。\n',
  formula: '\n::: {#eq:model .equation}\n$$\ny = ax + b\n$$\n:::\n\n由[式](#eq:model)可知……\n',
  table: '\n| 指标 | 测试值 | 目标值 |\n| --- | --- | --- |\n| 准确率 | 96.5% | 95% |\n\n: 性能测试结果 {#tab:result}\n\n如[表](#tab:result)所示。\n',
  citation: '已有研究指出…… [@reference-key]。',
  code: '\n```python {#code:demo caption="示例代码"}\nprint("hello")\n```\n\n如[代码](#code:demo)所示。\n',
};

async function uploadImage(file) {
  if (!file) return;
  if (file.size > 20 * 1024 * 1024) return notice('单个图片不能超过 20 MB。', true);
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      const title = await askFields('图片说明', [{name:'title', label:'图片标题', value:'图片说明'}], panel => imagePreview(panel, file, reader.result));
      if (!title) return;
      const result = await api('/api/upload', { method: 'POST', body: JSON.stringify({ name: file.name, data: reader.result }) });
      const label = uniqueLabel('fig');
      insertAtCursor(`\n![${mdText(title.title)}](${result.path}){#${label} width=90%}\n\n如[图](#${label})所示。\n`);
      notice(`图片已保存到 ${result.path}`);
    } catch (error) {
      notice(error.message, true);
    }
  };
  reader.readAsDataURL(file);
}

async function runAction(action) {
  if (state.dirty && !(await saveFile(true))) return;
  if (!(await saveMetadata())) return;
  const labels = { check: '正在检查论文…', pdf: '正在生成 PDF…', 'pdf-portable': '正在使用随包替代字体生成预览 PDF…', 'final-check': '正在进行定稿检查…' };
  $('#busyText').textContent = labels[action] || '正在检查并导出定稿 PDF…';
  $('#busy').classList.remove('hidden');
  try {
    const result = await api('/api/action', { method: 'POST', body: JSON.stringify({ action }) });
    const box = $('#buildResult');
    box.className = `build-result has-log ${result.ok ? 'success' : 'failure'}`;
    box.querySelector('strong').textContent = result.ok ? (action.startsWith('pdf') ? 'PDF 已成功生成' : '检查已通过') : '发现需要处理的问题';
    box.querySelector('p').textContent = result.ok ? '可以继续写作；正式提交前仍需人工检查页面效果。' : '先处理日志中最前面的错误，再重新运行。';
    $('#buildLog').textContent = result.output || '没有额外输出。';
    renderIssues(result.issues || [], result.output || '');
    $('#openPdf').classList.toggle('hidden', !result.pdf);
    $('#openPdf').textContent = result.portable_fonts ? '打开预览 PDF（替代字体，非原字体定稿）' : '打开生成的 PDF';
    if (result.pdf) $('#openPdf').href = `/build/thesis.pdf?t=${Date.now()}`;
    state.project.pdf = result.pdf;
    updateProgress();
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } catch (error) {
    notice(error.message, true);
  } finally {
    $('#busy').classList.add('hidden');
  }
}

function updateWordCount() {
  const text = $('#editor').value;
  const chinese = (text.match(/[\u3400-\u9fff]/g) || []).length;
  const words = (text.replace(/[\u3400-\u9fff]/g, ' ').match(/[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*/g) || []).length;
  $('#wordCount').textContent = `${chinese + words} 个字词 · ${text.length} 个字符`;
}

$$('.nav-item').forEach((item) => item.addEventListener('click', () => showPanel(item.dataset.panel)));
$$('[data-go]').forEach((button) => button.addEventListener('click', async () => {
  if (button.dataset.go === 'writing') await saveMetadata();
  showPanel(button.dataset.go);
}));
$('#saveMetadata').addEventListener('click', saveMetadata);
$('#saveFile').addEventListener('click', () => saveFile());
$('#reloadFile').addEventListener('click', () => {
  if (state.dirty && !confirm('重新载入会放弃页面中尚未保存的内容。请先复制要保留的文字。继续吗？')) return;
  setDirty(false);
  clearTimeout(saveTimer);
  const file = state.project.files.find((item) => item.path === state.currentPath);
  if (file) loadFile(file);
});
$('#editor').addEventListener('input', () => { setDirty(true); updateWordCount(); });
$$('[data-insert]').forEach((button) => button.addEventListener('click', () => guidedInsert(button.dataset.insert)));
$('#imageInput').addEventListener('change', (event) => { uploadImage(event.target.files[0]); event.target.value = ''; });
$$('[data-action]').forEach((button) => button.addEventListener('click', () => runAction(button.dataset.action)));
$('#refreshButton').addEventListener('click', () => loadProject(true));
$('#shutdownButton').addEventListener('click', async () => {
  if (!(await flushSaves())) return;
  try { await api('/api/shutdown', { method: 'POST', body: '{}' }); } catch (_) {}
  document.body.innerHTML = '<main style="max-width:620px;margin:18vh auto;font-family:Segoe UI,Microsoft YaHei,sans-serif;text-align:center"><h1>论文助手已关闭</h1><p>现在可以关闭这个页面。</p></main>';
});
document.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault();
    flushSaves();
  }
});
window.addEventListener('beforeunload', (event) => {
  if (state.dirty || state.metadataDirty) { event.preventDefault(); event.returnValue = ''; }
});

loadProject();
