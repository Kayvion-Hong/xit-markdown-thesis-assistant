// A synchronous browser-local copy complements (not replaces) server autosave.
const localDrafts = (() => {
  let prefix = '', tabId = '', panel;
  function warn() {
    let box=document.querySelector('#draftWarning');
    if (!box) { box=document.createElement('div'); box.id='draftWarning'; box.className='callout'; document.querySelector('#notice').after(box); }
    box.textContent='浏览器草稿保护不可用或空间不足。请及时按 Ctrl+S，确认“内容已同步”；不要依赖意外关闭恢复。';
  }
  function records() {
    const items=[];
    if (!prefix) return items;
    try {
      for(let i=0;i<localStorage.length;i++) {
        const key=localStorage.key(i);
        if (!key.startsWith(prefix)) continue;
        try { const value=JSON.parse(localStorage.getItem(key)); if(value && typeof value.text==='string' && typeof value.path==='string') items.push({key,...value}); } catch (_) {}
      }
    } catch (_) { warn(); }
    return items.sort((a,b)=>b.time-a.time);
  }
  function capture(path,text,base) {
    if (!prefix) return;
    try {
      localStorage.setItem(prefix+tabId+':'+path, JSON.stringify({path,text,base,time:Date.now()}));
    } catch (_) { warn(); }
  }
  function acknowledge(path,text) {
    try {
      for(const item of records()) if(item.path===path && item.text===text) localStorage.removeItem(item.key);
    } catch (_) { warn(); }
    render();
  }
  async function recover(item) {
    try {
      if (!(await flushSaves())) return;
      const metadata=item.path==='@metadata';
      const file=state.project.files.find(file=>file.path===item.path);
      if(!metadata && !file) { notice('该文件已移出正文或不存在。请先恢复对应章节；草稿仍保留在这里。',true); return; }
      if(!metadata) await loadFile(file);
      const dialog=document.createElement('dialog');
      const title=document.createElement('h2'); title.textContent='恢复未同步草稿：'+(metadata?'基本资料':file.label);
      const help=document.createElement('p');
      help.textContent='草稿时间：'+new Date(item.time).toLocaleString()+'。请先核对内容。恢复会替换当前编辑内容并自动保存；原磁盘内容由文件历史保护。';
      if(!metadata && item.base!==state.revision) help.textContent+=' 文件在草稿之后可能已变化，请仔细比较，避免覆盖较新的内容。';
      const preview=document.createElement('textarea'); preview.readOnly=true; preview.value=item.text; preview.setAttribute('aria-label','待恢复草稿内容');
      const cancel=document.createElement('button'); cancel.textContent='暂不恢复（保留草稿）'; cancel.onclick=()=>dialog.close();
      const download=document.createElement('button'); download.textContent='下载草稿副本'; download.onclick=()=>{
        const url=URL.createObjectURL(new Blob([item.text],{type:'text/plain;charset=utf-8'}));
        const a=document.createElement('a'); a.href=url;a.download='恢复草稿-'+item.path.replace(/[^a-zA-Z0-9_.-]/g,'_')+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };
      const apply=document.createElement('button');apply.textContent='恢复这份草稿';
      apply.onclick=async()=>{
        apply.disabled=true;
        try {
          if(metadata) {
            const values=JSON.parse(item.text);
            renderMetadata(values); state.metadataDirty=true;
            capture('@metadata',item.text,'');
            if(!(await saveMetadata())) { apply.disabled=false; return; }
          } else {
            const before=beforeAssistedEdit(); document.querySelector('#editor').value=item.text;
            afterAssistedEdit(before);setDirty(true);updateWordCount();
            if(!(await saveFile(true))) { apply.disabled=false; return; }
          }
          acknowledge(item.path,item.text);dialog.close();showPanel(metadata?'metadata':'writing');notice('草稿已恢复并保存到论文文件。');
        } catch(error) { help.textContent=error.message;apply.disabled=false; }
      };
      dialog.append(title,help,preview,cancel,download,apply);dialog.onclose=()=>dialog.remove();document.body.append(dialog);dialog.showModal();cancel.focus();
    } catch(error) { notice(error.message,true); }
  }
  function render() {
    if(!prefix) return;
    if(!panel) {panel=document.createElement('div');panel.className='callout';panel.id='draftRecovery';document.querySelector('#notice').after(panel);}
    panel.replaceChildren();const items=records();panel.hidden=!items.length;
    if(!items.length)return;
    const title=document.createElement('strong');title.textContent='发现 '+items.length+' 份浏览器草稿（可能尚未同步）';panel.append(title);
    for(const item of items) {
      const row=document.createElement('p'); const button=document.createElement('button');
      button.textContent=(item.path==='@metadata'?'基本资料':item.path)+' · '+new Date(item.time).toLocaleString()+' · 查看 / 恢复';
      button.onclick=()=>recover(item);row.append(button);panel.append(row);
    }
  }
  function init(project) {
    prefix='xit-draft:'+project.project_id+':';
    try { tabId=sessionStorage.getItem('xit-draft-tab') || crypto.randomUUID();sessionStorage.setItem('xit-draft-tab',tabId); } catch (_) {tabId=crypto.randomUUID();warn();}
    render();
  }
  return {init,capture,acknowledge};
})();
