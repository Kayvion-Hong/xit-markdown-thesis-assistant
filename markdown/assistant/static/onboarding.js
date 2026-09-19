function previewStatusText(info) {
  if (!info || info.state === 'missing') return '尚无可核验的对照预览，请先编译。';
  const time = info.time ? new Date(info.time).toLocaleString() : '时间未知';
  return (info.state === 'current' ? 'PDF 对应已保存内容' : 'PDF 已过期，请重新编译') +
    ' · ' + time + (info.portable_fonts ? ' · 使用替代字体' : '');
}

function formulaPreview(panel, values) {
  panel.replaceChildren();
  const help = document.createElement('p');
  help.textContent = '即时预览使用 KaTeX。部分 LaTeX 命令不受支持；最终公式、编号和分页以右侧编译 PDF 为准。';
  const math = document.createElement('div'); panel.append(help, math);
  try {
    katex.render(values.formula || '', math, {displayMode:true, throwOnError:true, trust:false, maxExpand:1000, maxSize:20});
  } catch (error) {
    math.textContent = '此处无法预览：' + error.message;
    math.className = 'preview-warning';
  }
}

function tablePreview(panel, values) {
  panel.replaceChildren();
  const rows = (values.cells || '').trim().split(/\r?\n/).map(row => row.split('\t'));
  const info = document.createElement('p');
  info.textContent = `预览：${rows.length} 行 × ${rows[0].length} 列（包括表头）。`;
  if (rows.some(row => row.length !== rows[0].length)) info.textContent += ' 每行列数不一致，请检查粘贴内容。';
  if (rows[0].length > 6 || rows.some(row => row.some(cell => cell.length > 30))) {
    info.textContent += ' 列数较多或单元格较长，可能超宽；建议精简文字，并在 PDF 中检查。';
  }
  const table = document.createElement('table');
  rows.slice(0, 30).forEach((row, index) => {
    const tr = document.createElement('tr');
    row.slice(0, 20).forEach(value => {
      const cell = document.createElement(index ? 'td' : 'th'); cell.textContent = value; tr.append(cell);
    }); table.append(tr);
  });
  panel.append(info, table);
  if (rows.length > 30 || rows[0].length > 20) info.textContent += ' 此处仅展示前 30 行、20 列，插入时保留完整表格。';
}

function imagePreview(panel, file, data) {
  panel.replaceChildren();
  const info = document.createElement('p');
  info.textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB。`;
  panel.append(info);
  if (!/^image\/(png|jpeg)$/.test(file.type)) {
    info.textContent += ' PDF 图片请在编译结果中检查清晰度。'; return;
  }
  const img = document.createElement('img'); img.alt = '待插入图片预览';
  img.onload = () => {
    info.textContent += ` ${img.naturalWidth} × ${img.naturalHeight} 像素。`;
    if (img.naturalWidth < 1200) info.textContent += ' 若按约 14 厘米宽打印，可能不够清晰；建议使用高清原图或矢量 PDF。';
  };
  img.onerror = () => { info.textContent += ' 浏览器无法读取该图片，请检查文件是否损坏。'; };
  img.src = data; panel.append(img);
}

async function projectManager() {
  if (!(await flushSaves())) return;
  const data = await api('/api/projects');
  const choice = await askFields('我的论文', [{name:'action', label:'选择要做的事', options:[
    {value:'thesis',label:'新建论文（从附带模板复制）'},
    {value:'ai',label:'新建 AI 教学练习'}, {value:'copy',label:'复制当前论文，保留原项目'},
    {value:'import-legacy',label:'导入旧版 0.5 论文（复制，保留旧目录）'},
    ...data.projects.filter(p => !p.error).map(p => ({value:p.path,label:'打开：' + p.name})),
    {value:'open',label:'打开其他论文文件夹 / 解压的项目备份'}
  ]}]);
  if (!choice) return;
  let body;
  if (['thesis','ai','copy'].includes(choice.action)) {
    const name = await askFields('给论文起个名字', [{name:'name',label:'项目名称（不会改变封面题目）',value:choice.action==='ai'?'AI 教学练习':'我的毕业论文'}]);
    if (!name) return;
    body = {action:'create', mode:choice.action, name:name.name};
  } else if (choice.action === 'import-legacy') {
    const old = await askFields('导入旧版论文', [{name:'path',label:'先在旧版保存 / 恢复浏览器草稿，再粘贴旧版 XIT 文件夹路径'}]);
    if (!old) return;
    body = {action:'import-legacy',path:old.path.trim().replace(/^"|"$/g,'')};
  } else {
    let path = choice.action;
    if (path === 'open') {
      const location = await askFields('打开已有论文', [{name:'path',label:'粘贴包含 project.yaml 的文件夹完整路径；备份 ZIP 请先解压',value:data.home}]);
      if (!location) return;
      path = location.path.trim().replace(/^"|"$/g, '');
    }
    body = {action:'open',path};
  }
  notice('正在打开项目，请稍候…');
  const result = await api('/api/projects', {method:'POST',body:JSON.stringify(body)});
  location.href = result.url;
}

async function exportProject() {
  if (!(await flushSaves())) return;
  const response = await fetch('/api/project-export', {method:'POST',headers:{'Content-Type':'application/json','X-XIT-Token':token},body:'{}'});
  if (!response.ok) throw new Error((await response.json()).error || '导出失败');
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement('a'); a.href = url; a.download = `XIT-project-${new Date().toISOString().slice(0,10)}.zip`;
  a.click(); setTimeout(() => URL.revokeObjectURL(url), 60000);
  notice('项目备份已交给浏览器下载。请将 ZIP 另存到其他磁盘或可信云盘。');
}

function findInEditor() {
  const editor = $('#editor'), dialog = document.createElement('dialog');
  dialog.innerHTML = '<h2>查找与替换 · 当前文件</h2><label>查找文字<input id="findText"></label><label>替换为<input id="replaceText"></label><p>按原文精确匹配，区分大小写。替换可用 Ctrl+Z 撤销。</p><p class="find-result" role="status"></p><button data-find="next">下一处</button> <button data-find="one">替换这一处</button> <button data-find="all">全部替换</button> <button data-find="close">关闭</button>';
  document.body.append(dialog); dialog.onclose = () => {dialog.remove(); editor.focus();};
  const find = dialog.querySelector('#findText'), replacement = dialog.querySelector('#replaceText'), result = dialog.querySelector('.find-result');
  find.value = editor.value.slice(editor.selectionStart, editor.selectionEnd);
  function next() {
    if (!find.value) {result.textContent = '请先输入查找文字。'; return false;}
    let start = editor.value.indexOf(find.value, editor.selectionEnd);
    if (start < 0) start = editor.value.indexOf(find.value);
    if (start < 0) {result.textContent = '没有找到。'; return false;}
    editor.setSelectionRange(start, start + find.value.length);
    result.textContent = `已定位第 ${editor.value.slice(0,start).split('\n').length} 行。关闭窗口可查看选中内容。`;
    return true;
  }
  dialog.onclick = event => {
    const action = event.target.dataset.find;
    if (action === 'close') return dialog.close();
    if (action === 'next') return next();
    if (!['one','all'].includes(action) || !find.value) return;
    if (action === 'one' && editor.value.slice(editor.selectionStart, editor.selectionEnd) !== find.value && !next()) return;
    const before = beforeAssistedEdit();
    if (action === 'all') {
      const count = editor.value.split(find.value).length - 1;
      editor.value = editor.value.split(find.value).join(replacement.value);
      result.textContent = `已替换 ${count} 处；支持撤销。`;
    } else {
      const start = editor.selectionStart, end = editor.selectionEnd;
      editor.value = editor.value.slice(0,start) + replacement.value + editor.value.slice(end);
      editor.setSelectionRange(start, start + replacement.value.length);
      result.textContent = '已替换选中内容；支持撤销。';
    }
    afterAssistedEdit(before); setDirty(true); updateWordCount();
  };
  dialog.showModal(); find.focus();
}

window.onboardingReady = project => {
  const info = $('#projectLocation'); if (!info) return;
  info.textContent = `${project.project_name} · v${project.app_version}\n保存位置：${project.project_directory}\n` +
    (project.external_project ? '论文与程序分开保存；升级时保留此文件夹。' : '这是旧版程序内的论文，请使用“我的论文 → 复制当前论文”迁移。');
  refreshHealth().catch(error => {$('#healthList').textContent = '状态读取失败：' + error.message;});
};

async function refreshHealth() {
  const health = await api('/api/health');
  const list = $('#healthList'); list.replaceChildren();
  for (const text of [previewStatusText(health.preview_status), `当前可识别的写作问题：${health.issues.length} 项（图片路径、引用和重复标签）`, `整篇本地备份：${health.backups} 份；不等同于异地备份`]) {
    const li = document.createElement('li'); li.textContent = text; list.append(li);
  }
  if (state.project) state.project.preview_status = health.preview_status;
}

document.addEventListener('DOMContentLoaded', () => {
  const home = $('#panel-home'), card = document.createElement('section'); card.className = 'callout project-card';
  card.innerHTML = '<h2>我的论文</h2><p id="projectLocation"></p><button id="manageProjects" class="button primary">新建 / 打开论文</button> <button id="exportProject" class="button secondary">下载项目备份 ZIP</button><h3>本机检查结果</h3><ul id="healthList"><li>正在读取…</li></ul><button id="refreshHealth" class="button ghost">重新检查状态</button><p>这里只检查文件和编译状态，不判断研究质量、引用真实性或是否符合学校全部要求。</p>';
  home.prepend(card);
  home.querySelector('.hero').remove();
  home.querySelector('.step-grid').remove();
  for (const [id, action] of [['manageProjects',projectManager],['exportProject',exportProject],['refreshHealth',refreshHealth]]) {
    $('#' + id).onclick = () => action().catch(error => notice(error.message,true));
  }
  const wizard = document.createElement('section'); wizard.className = 'callout';
  wizard.innerHTML = '<h2>第一次使用，跟着完成四步</h2><p>每一步都会打开实际操作页面。先用 AI 示例练习，再新建自己的论文。</p><div class="wizard-steps"><button data-step="home">① 检查下方环境</button><button data-step="metadata">② 填写封面资料</button><button data-step="writing">③ 改一行正文并等待保存</button><button data-step="preview">④ 编译并核对 PDF</button></div><p>看到“内容已同步”表示已保存到论文文件夹；“等待编译”表示右侧 PDF 还未更新。两者不是同一件事。</p>';
  card.after(wizard);
  wizard.onclick = event => {
    const step = event.target.dataset.step; if (!step) return;
    showPanel(step === 'preview' ? 'writing' : step);
    if (step === 'preview') {$('#compilePreview').focus(); notice('点击“立即编译”，等待 PDF 出现；观察刚才修改的文字。');}
    if (step === 'home') $('#environmentGrid').scrollIntoView({behavior:'smooth'});
  };
  const advanced = document.createElement('label'); advanced.className = 'advanced-toggle';
  advanced.innerHTML = '<input type="checkbox"> 显示高级工具'; $('.top-actions').prepend(advanced);
  advanced.querySelector('input').onchange = event => document.body.classList.toggle('advanced-mode',event.target.checked);
  $('#installTexPackage').closest('.callout').classList.add('advanced-only');
  const button = document.createElement('button'); button.textContent = '查找 / 替换'; button.className = 'button secondary';
  button.onclick = findInEditor; $('#saveFile').after(button);
  $('#editor').addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'f') {event.preventDefault(); findInEditor();}
  });
  document.addEventListener('visibilitychange', () => {if (!document.hidden && state.project) refreshHealth().catch(error => notice(error.message,true));});
});
