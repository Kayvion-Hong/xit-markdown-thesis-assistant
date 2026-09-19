async function openChapterManager() {
  if (!(await flushSaves())) return;
  const dialog = document.createElement('dialog');
  const heading = document.createElement('h2'); heading.textContent = '管理正文章节';
  const help = document.createElement('p');
  help.textContent = '五章只是示例。可增减与排序，至少保留一章；编号和目录在重新生成 PDF 时更新。总结、谢辞与附录单独管理。';
  const list = document.createElement('div');
  const status = document.createElement('p'); status.setAttribute('role', 'status');
  const add = document.createElement('button'); add.textContent = '＋ 新增一章';
  const close = document.createElement('button'); close.textContent = '完成'; close.onclick = () => dialog.close();
  dialog.append(heading, help, add, list, status, close); document.body.append(dialog);
  let snapshot;
  let pending = false;
  function busy(value) {
    pending = value;
    dialog.querySelectorAll('button').forEach(button => button.disabled = value);
  }
  async function refresh() {
    snapshot = await api('/api/chapters'); list.replaceChildren();
    function row(chapter, index, archived) {
      const box = document.createElement('div'); box.className = 'chapter-row';
      const title = document.createElement('strong'); title.textContent = archived ? chapter.title : `第 ${index + 1} 章：${chapter.title}`;
      const controls = document.createElement('div');
      const actions = archived ? [['restore', '恢复到正文末尾']] : [['rename','改名'],['up','上移'],['down','下移'],['remove','移出正文（保留文件）']];
      actions.forEach(([action, label]) => {
        const button = document.createElement('button'); button.textContent = label;
        button.disabled = action === 'up' && index === 0 || action === 'down' && index === snapshot.chapters.length - 1 || action === 'remove' && snapshot.chapters.length === 1;
        button.onclick = () => perform(action, chapter);
        controls.append(button);
      });
      box.append(title, controls); list.append(box);
    }
    snapshot.chapters.forEach((chapter, index) => row(chapter, index, false));
    if (snapshot.archived.length) {
      const title = document.createElement('h3'); title.textContent = '已移出正文（文件仍保留）'; list.append(title);
      snapshot.archived.forEach((chapter, index) => row(chapter, index, true));
    }
  }
  async function perform(action, chapter = {}) {
    if (pending) return;
    const payload = {action, path:chapter.path, revision:snapshot.revision};
    if (action === 'add' || action === 'rename') {
      const values = await askFields(action === 'add' ? '新增正文章节' : '修改章节名称', [{name:'title',label:'章节名称（例如“实验结果与分析”，不用填写“第六章”）',value:chapter.title || ''}]);
      if (!values) return;
      payload.title = values.title;
    }
    busy(true); status.textContent = '正在保存章节结构…';
    try {
      const result = await api('/api/chapters', {method:'POST',body:JSON.stringify(payload)});
      // A rename changes disk contents; don't write the previously loaded text back.
      state.currentPath = null; setDirty(false);
      await loadProject();
      livePreview.changed();
      const selected = state.project.files.find(file => file.path === result.path);
      if (selected) await loadFile(selected);
      state.project.pdf = false; $('#openPdf').classList.add('hidden'); updateProgress();
      status.textContent = action === 'remove' ? '已移出正文，原文件保留在项目中，可在下方恢复。请重新生成 PDF。' : '已保存。请重新生成 PDF 更新编号和目录。';
    } catch (error) { status.textContent = error.message; }
    finally { busy(false); await refresh(); }
  }
  add.onclick = () => perform('add');
  dialog.oncancel = event => { if (pending) event.preventDefault(); };
  dialog.onclose = () => dialog.remove();
  dialog.showModal();
  try { await refresh(); } catch (error) { status.textContent = error.message; }
}
document.addEventListener('DOMContentLoaded', () => {
  const button = document.createElement('button'); button.className = 'button secondary'; button.textContent = '管理章节（增减 / 排序）';
  $('#saveFile').before(button);
  button.onclick = () => openChapterManager().catch(error => notice(error.message, true));
});
