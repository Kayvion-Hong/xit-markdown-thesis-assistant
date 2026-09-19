// Form helpers deliberately insert Markdown; no untrusted HTML preview is used.
function uniqueLabel(prefix) { return `${prefix}:${crypto.randomUUID()}`; }
function mdText(value) { return value.replace(/[\[\]{}|\r\n]/g, ' '); }
let saveTimer;
function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveFile(true), 1200);
}
async function flushSaves() {
  clearTimeout(saveTimer);
  if (!(await saveFile(true))) return false;
  if (state.metadataDirty && !(await saveMetadata())) return false;
  if (state.metadataDirty || state.dirty) return flushSaves();
  return true;
}
function askFields(title, fields, previewContent) {
  return new Promise(resolve => {
    const dialog = document.createElement('dialog');
    const form = document.createElement('form');
    const heading = document.createElement('h2'); heading.textContent = title; form.append(heading);
    fields.forEach(field => {
      const label = document.createElement('label'); label.textContent = field.label;
      const input = document.createElement(field.options ? 'select' : field.multiline ? 'textarea' : 'input');
      input.name = field.name; input.required = !field.optional;
      if (field.options) field.options.forEach(item => {
        const option = document.createElement('option'); option.value = item.value; option.textContent = item.label; input.append(option);
      });
      else input.value = field.value || '';
      if (field.options && field.options.length > 8) {
        const search = document.createElement('input'); search.type = 'search';
        search.placeholder = '输入标题或代号筛选'; search.setAttribute('aria-label', '筛选' + field.label);
        search.oninput = () => {
          const query = search.value.toLocaleLowerCase();
          input.replaceChildren();
          field.options.filter(item => item.value.startsWith('__') || item.label.toLocaleLowerCase().includes(query)).forEach(item => {
            const option = document.createElement('option'); option.value = item.value; option.textContent = item.label; input.append(option);
          });
        };
        form.append(search);
      }
      label.append(input); form.append(label);
    });
    const cancel = document.createElement('button'); cancel.type = 'button'; cancel.textContent = '取消'; cancel.onclick = () => dialog.close();
    const ok = document.createElement('button'); ok.textContent = '确定'; ok.className = 'button primary';
    if (previewContent) {
      const panel = document.createElement('div'); panel.className = 'insert-preview';
      form.append(panel);
      const refresh = () => previewContent(panel, Object.fromEntries(new FormData(form)));
      form.addEventListener('input', refresh); refresh();
    }
    form.append(cancel, ok); dialog.append(form); document.body.append(dialog);
    let result = null;
    form.onsubmit = event => { event.preventDefault(); result = Object.fromEntries(new FormData(form)); dialog.close(); };
    dialog.onclose = () => { dialog.remove(); resolve(result); };
    dialog.showModal();
  });
}
async function guidedInsert(kind) {
  try {
    if (kind === 'citation') return await chooseReference();
    if (kind === 'table') {
      const values = await askFields('插入三线表', [
        {name:'title', label:'表格标题'},
        {name:'cells', label:'从 Excel 复制表格粘贴到这里；首行为列名（以制表符分列）', multiline:true}
      ], tablePreview);
      if (!values) return;
      const rows = values.cells.trim().split(/\r?\n/).map(row => row.split('\t').map(mdText));
      if (rows.length < 2 || rows[0].length < 2 || rows.some(row => row.length !== rows[0].length)) return notice('请粘贴至少两行、两列且每行列数一致的表格。', true);
      const label = uniqueLabel('tab');
      const line = row => '| ' + row.join(' | ') + ' |';
      insertAtCursor('\n' + [line(rows[0]), line(rows[0].map(()=>'---')), ...rows.slice(1).map(line)].join('\n') + `\n\n: ${mdText(values.title)} {#${label}}\n\n如[表](#${label})所示。\n`);
      return;
    }
    if (kind === 'formula') {
      const values = await askFields('编号公式（编号和引用自动生成）', [{name:'formula', label:'公式内容：使用 LaTeX 数学语法，例如 y = ax + b；不用填写 $$', multiline:true, value:'y = ax + b'}], formulaPreview);
      if (values) {
        const label = uniqueLabel('eq');
        insertAtCursor(`\n::: {#${label} .equation}\n$$\n${values.formula}\n$$\n:::\n\n由[式](#${label})可知……\n`);
      }
      return;
    }
    let text = snippets[kind];
    if (kind === 'code') text = text.replaceAll('code:demo', uniqueLabel('code'));
    insertAtCursor(text);
  } catch (error) { notice(error.message, true); }
}
async function chooseReference() {
  const data = await api('/api/references');
  const choice = await askFields('选择文献或新建文献', [{name:'key', label:'已有文献代号（真实性请自行核实）', options:[
    {value:'__new', label:'＋ 填写新文献'}, {value:'__import', label:'＋ 导入 BibTeX 文件'}, ...data.references.map(r=>({value:r.key, label:r.title ? `${r.title} (${r.key})` : r.key}))
  ]}]);
  if (!choice) return;
  let key = choice.key;
  if (key === '__import') {
    const input = document.createElement('input'); input.type = 'file'; input.accept = '.bib';
    input.onchange = async () => {
      try {
        if (!input.files[0]) return;
        if (input.files[0].size > 2 * 1024 * 1024) throw new Error('文献库不能超过 2 MB。');
        const result = await api('/api/import-references', {method:'POST',body:JSON.stringify({text:await input.files[0].text()})});
        notice(`已导入 ${result.count} 条文献，请选择要引用的一条。`);
        await chooseReference();
      } catch(error) { notice(error.message, true); }
    };
    input.click(); return;
  }
  if (key === '__new') {
    const values = await askFields('添加文献：依据真实来源填写，多位作者用 and 分隔', [
      {name:'key', label:'唯一代号，例如 zhang2024'},
      {name:'type', label:'类型', options:[{value:'article',label:'期刊论文'},{value:'book',label:'图书'},{value:'online',label:'网页'}]},
      {name:'title',label:'标题'}, {name:'author',label:'作者'}, {name:'year',label:'年份'},
      {name:'journal',label:'期刊名称',optional:true}, {name:'publisher',label:'出版社',optional:true},
      {name:'doi',label:'DOI',optional:true}, {name:'url',label:'网址',optional:true}
    ]);
    if (!values) return;
    key = (await api('/api/reference', {method:'POST',body:JSON.stringify(values)})).key;
  }
  insertAtCursor(`[@${key}]`);
}
function renderIssues(issues, output) {
  let list = document.querySelector('#writingIssues');
  if (!list) { list = document.createElement('div'); list.id = 'writingIssues'; $('#buildLog').before(list); }
  list.replaceChildren();
  issues.forEach(issue => {
    const button = document.createElement('button');
    button.textContent = `${issue.path} 第 ${issue.line} 行：${issue.message}`;
    button.onclick = async () => {
      const file = state.project.files.find(f => f.path === issue.path);
      if (!file) return;
      await loadFile(file); showPanel('writing');
      const editor = $('#editor');
      const start = editor.value.split('\n').slice(0, issue.line - 1).join('\n').length + (issue.line > 1 ? 1 : 0);
      editor.focus(); editor.setSelectionRange(start, editor.value.indexOf('\n', start) < 0 ? editor.value.length : editor.value.indexOf('\n', start));
    };
    list.append(button);
  });
  const hints = [];
  if (/not found|not installed|找不到|未安装/i.test(output)) hints.push('先回到“开始”刷新环境检查；请确认完整解压 runtime 文件夹。');
  if (/fontspec|font.*not.*found|Missing character/i.test(output)) hints.push('字体问题：检查 Windows 字体是否齐全。不要用其他字体的编译结果直接定稿。');
  if (/XIT-TITLE-TOO-WIDE/.test(output)) hints.push('题目超过封面栏宽：到“填写资料”缩短题目，或请熟悉 LaTeX 的同学按学院要求调整封面。');
  if (/LaTeX Error: File.*not found/.test(output)) hints.push('缺少 TeX 宏包：先确认使用完整包；若自行添加了额外 LaTeX 命令，请把下方首个缺失文件名提供给维护者。');
  hints.forEach(hint => { const p = document.createElement('p'); p.textContent = hint; list.append(p); });
}
document.addEventListener('DOMContentLoaded', () => {
  let metadataTimer;
  $('#metadataForm').addEventListener('input', () => {
    state.metadataDirty = true;
    livePreview.changed();
    localDrafts.capture('@metadata', JSON.stringify(Object.fromEntries(new FormData($('#metadataForm')).entries())), '');
    clearTimeout(metadataTimer);
    metadataTimer = setTimeout(() => saveMetadata(), 1600);
  });
  const button = document.createElement('button'); button.className = 'button secondary'; button.textContent = '历史版本 / 恢复';
  $('#saveFile').after(button);
  button.onclick = async () => {
    if (!(await flushSaves())) return;
    const target = await askFields('选择要恢复的文件', [{name:'path', label:'文件', options:[{value:'metadata.yaml',label:'基本资料'}, ...state.project.files.map(f=>({value:f.path,label:f.label}))]}]);
    if (!target) return;
    const data = await api('/api/history?path=' + encodeURIComponent(target.path));
    if (!data.versions.length) return notice('该文件尚无历史版本。每次内容变化保存前会保留旧版本。');
    const version = await askFields('选择历史版本', [{name:'id',label:'保存时间',options:data.versions.map(v=>({value:v.id,label:v.time}))}]);
    if (!version) return;
    const selected = data.versions.find(v=>v.id===version.id);
    const preview = await askFields('确认恢复：当前版本也会保留在历史中', [{name:'preview',label:'内容预览（修改预览不会改写历史）',multiline:true,value:selected.text,optional:true}]);
    if (!preview) return;
    await api('/api/restore', {method:'POST',body:JSON.stringify({...target,...version})});
    if (target.path === 'metadata.yaml') await loadProject();
    else if (target.path === state.currentPath) await loadFile(state.project.files.find(f=>f.path===target.path));
    notice('已恢复历史版本。');
  };
});
