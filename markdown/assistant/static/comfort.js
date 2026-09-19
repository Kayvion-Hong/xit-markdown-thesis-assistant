function confirmBackup(message) {
  return new Promise(resolve => {
    const dialog = document.createElement('dialog');
    const text = document.createElement('p'); text.style.whiteSpace = 'pre-wrap'; text.textContent = message;
    const cancel = document.createElement('button'); cancel.textContent = '取消，不恢复';
    const accept = document.createElement('button'); accept.textContent = '确认恢复';
    let approved = false;
    cancel.onclick = () => dialog.close();
    accept.onclick = () => { approved = true; dialog.close(); };
    dialog.onclose = () => { dialog.remove(); resolve(approved); };
    dialog.append(text,cancel,accept); document.body.append(dialog); dialog.showModal(); cancel.focus();
  });
}
document.addEventListener('DOMContentLoaded', () => {
  const button = document.createElement('button');
  button.className = 'button secondary'; button.textContent = '整篇备份 / 回退';
  document.querySelector('#saveFile').after(button);
  button.onclick = async () => {
    if (!(await flushSaves())) return;
    try {
      const dialog = document.createElement('dialog');
      const heading = document.createElement('h2'); heading.textContent = '整篇论文备份与回退';
      const help = document.createElement('p'); help.textContent = '包括资料、章节顺序、正文、文献、图片和文件历史。普通论文与 AI 练习分别备份。备份保存在本机，不会自动清理；请定期另存到其他磁盘。';
      const create = document.createElement('button'); create.textContent = '保存当前整篇备份';
      const list = document.createElement('div');
      const status = document.createElement('p'); status.setAttribute('role','status');
      const close = document.createElement('button'); close.textContent = '关闭'; close.onclick = () => dialog.close();
      dialog.append(heading,help,create,list,status,close); document.body.append(dialog);
      dialog.onclose = () => dialog.remove(); dialog.showModal();
      let busy = false;
      dialog.oncancel = event => { if (busy) event.preventDefault(); };
      async function run(action) {
        busy = true; dialog.querySelectorAll('button').forEach(b => b.disabled = true);
        try { await action(); } catch(error) { status.textContent = error.message; }
        finally { busy = false; dialog.querySelectorAll('button').forEach(b => b.disabled = false); }
      }
      async function refresh() {
        const data = await api('/api/backups'); list.replaceChildren();
        if (!data.backups.length) list.textContent = '尚无整篇备份。建议现在保存一份，之后每次大改前再保存。';
        data.backups.forEach(backup => {
          const row = document.createElement('p');
          const title = document.createElement('span'); title.textContent = `${backup.time} · ${backup.name} · ${backup.files} 个文件 `;
          const restore = document.createElement('button'); restore.textContent = '预览回退';
          restore.onclick = () => run(async () => {
            const details = await api('/api/backups?id=' + encodeURIComponent(backup.id));
            const message = `将恢复到：${backup.name}（${backup.time}）\n\n替换或补回 ${details.changed.length} 个文件：\n${details.changed.slice(0,12).join('\n') || '无'}\n\n从当前项目移出 ${details.removed.length} 个后来新增的文件：\n${details.removed.slice(0,12).join('\n') || '无'}\n\n恢复前会自动保存当前整篇备份，误选后可再恢复。历史记录也会回到该备份状态。生成的 PDF 需要重编译。请先关闭其他编辑页面和外部编辑器。确认回退？`;
            if (!(await confirmBackup(message))) return;
            status.textContent = '正在保护当前内容并恢复，请勿关闭窗口…';
            await api('/api/backups', {method:'POST',body:JSON.stringify({action:'restore',id:backup.id,revision:details.revision})});
            sessionStorage.setItem('xit-restored','1');
            location.reload();
          });
          row.append(title,restore); list.append(row);
        });
      }
      create.onclick = () => run(async () => {
        const values = await askFields('保存整篇备份', [{name:'name',label:'备份名称，例如“改第三章之前”或“提交导师版”',value:'修改前备份'}]);
        if (!values) return;
        const name = values.name;
        status.textContent = '正在保存整篇备份…';
        await api('/api/backups',{method:'POST',body:JSON.stringify({action:'create',name})});
        await refresh(); status.textContent = '备份成功，可以继续修改。';
      });
      await refresh();
    } catch(error) { notice(error.message, true); }
  };
  const size = document.createElement('button'); size.className = 'button ghost'; size.textContent = '大字阅读';
  document.querySelector('#saveFile').after(size);
  let large = false;
  size.onclick = () => { large = !large; document.querySelector('#editor').style.fontSize = large ? '20px' : ''; size.textContent = large ? '恢复字号' : '大字阅读'; };
  if (sessionStorage.getItem('xit-restored')) {
    sessionStorage.removeItem('xit-restored');
    const message = document.createElement('div'); message.className = 'callout';
    message.textContent = '整篇恢复已完成，恢复前内容已自动备份。请重新生成 PDF；其他旧页面需要刷新后才能继续保存。';
    document.querySelector('#notice').after(message);
  }
});
