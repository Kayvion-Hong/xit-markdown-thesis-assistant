window.livePreview = (() => {
  let active=false, running=false, timer, version=0, compiledVersion=0, lastEdit=0, project;
  let viewer, pdf, pdfTask, page=1, zoom='width', generation=0, rows=[], positions=[], sourceMap={files:{}};
  let pdfLoading;
  let observer, rendering=false, pending=new Set(), scrollFrame, resizeTimer, syncBusy=false;
  const el = id => document.getElementById(id);
  const status = text => {el('previewStatus').textContent=text;};
  const syncStatus = text => {el('syncStatus').textContent=text;};
  const sha = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
  function currentLocation() {
    const host=el('pdfCanvasHost'), row=rows[page-1];
    return {page, fraction:row ? Math.max(0,(host.getBoundingClientRect().top-row.node.getBoundingClientRect().top)/row.node.offsetHeight):0};
  }
  function setPageNumber(value) {
    page=Math.max(1,Math.min(rows.length,value));
    if(document.activeElement!==el('pdfPage'))el('pdfPage').value=page;
    el('pdfPage').max=rows.length;
    el('pdfTotal').textContent='/ '+rows.length;
    el('pdfPrevious').disabled=page<=1;el('pdfNext').disabled=page>=rows.length;
  }
  function scrollToPage(value, fraction=0) {
    const row=rows[Math.max(1,Math.min(rows.length,Math.round(value)))-1];if(!row)return;
    const host=el('pdfCanvasHost');
    host.scrollTop+=row.node.getBoundingClientRect().top-host.getBoundingClientRect().top+fraction*row.node.offsetHeight-12;
    setPageNumber(row.number);queue(row);
  }
  function scaleFor(natural) {
    const host=el('pdfCanvasHost');
    const width=Math.max(.15,(host.clientWidth-32)/natural.width);
    if(zoom==='width')return width;
    if(zoom==='page')return Math.max(.15,Math.min(width,(host.clientHeight-32)/natural.height));
    return Number(zoom)/100*4/3;
  }
  function nearViewport(row) {
    const view=el('pdfCanvasHost').getBoundingClientRect(),rect=row.node.getBoundingClientRect();
    return rect.bottom>=view.top-600 && rect.top<=view.bottom+600;
  }
  function queue(row) {if(row && !row.rendered){pending.add(row);pump();}}
  async function pump() {
    if(rendering)return;rendering=true;
    try {
      while(pending.size) {
        const row=pending.values().next().value;pending.delete(row);
        if(row.generation!==generation || row.rendered || !nearViewport(row))continue;
        try {
          const canvas=document.createElement('canvas');
          const ratio=Math.min(window.devicePixelRatio||1,2);
          // Cap raster allocation at 8 megapixels per page; layout/text remain at selected zoom.
          const output=Math.min(ratio,Math.sqrt(8000000/(row.viewport.width*row.viewport.height)));
          canvas.width=Math.ceil(row.viewport.width*output);canvas.height=Math.ceil(row.viewport.height*output);
          canvas.style.width=row.viewport.width+'px';canvas.style.height=row.viewport.height+'px';
          canvas.setAttribute('aria-label','PDF 第 '+row.number+' 页');
          row.task=row.pdfPage.render({canvasContext:canvas.getContext('2d'),viewport:row.viewport,transform:[output,0,0,output,0,0]});
          await row.task.promise;
          if(row.generation!==generation || !nearViewport(row)){canvas.width=0;canvas.height=0;continue;}
          row.node.replaceChildren(canvas);
          const text=document.createElement('div');text.className='textLayer';
          text.style.setProperty('--total-scale-factor',row.viewport.scale);
          text.style.setProperty('--scale-round-x','1px');text.style.setProperty('--scale-round-y','1px');
          row.node.append(text);
          row.textTask=new viewer.TextLayer({textContentSource:await row.pdfPage.getTextContent(),container:text,viewport:row.viewport});
          await row.textTask.render();
          if(row.generation!==generation)continue;
          row.rendered=true;row.node.classList.add('rendered');
          if(row.highlightUntil>Date.now())paintHighlight(row,row.highlightY);
          row.task=null;row.textTask=null;
        } catch(error) {
          if(row.generation===generation && error.name!=='RenderingCancelledException' && error.name!=='AbortException') {
            row.node.dataset.error='本页显示失败，滚动回来可重试';status('PDF 页面显示失败：'+error.message);
          }
        }
      }
    } finally {rendering=false;}
  }
  function clearPages() {
    observer?.disconnect();pending.clear();generation++;
    for(const row of rows){row.task?.cancel();row.textTask?.cancel();}
    rows=[];
  }
  async function layoutPages(location={page,fraction:0}) {
    if(!pdf)return;
    clearPages();const expected=generation, current=pdf, host=el('pdfCanvasHost'), fragment=document.createDocumentFragment();
    const next=[];
    for(let number=1;number<=current.numPages;number++) {
      const pdfPage=await current.getPage(number);if(expected!==generation)return;
      const natural=pdfPage.getViewport({scale:1}),viewport=pdfPage.getViewport({scale:scaleFor(natural)});
      const node=document.createElement('div');node.className='pdf-page';node.dataset.page=number;
      node.style.width=viewport.width+'px';node.style.height=viewport.height+'px';node.setAttribute('aria-label','第 '+number+' 页');
      node.title='双击正文可定位到左侧对应段落';
      const row={number,node,pdfPage,viewport,natural,generation:expected,rendered:false};
      node.ondblclick=event=>reverseSync(row,event);fragment.append(node);next.push(row);
    }
    if(expected!==generation)return;
    rows=next;host.replaceChildren(fragment);setPageNumber(location.page);
    observer=new IntersectionObserver(entries=>{
      for(const entry of entries)if(entry.isIntersecting)queue(rows[Number(entry.target.dataset.page)-1]);
    },{root:host,rootMargin:'600px 0px'});
    rows.forEach(row=>observer.observe(row.node));
    scrollToPage(location.page,location.fraction);
    const actual=rows[page-1]?.viewport.scale||1;el('zoomPercent').value=Math.round(actual*75);
  }
  async function loadPDF() {
    if(pdfLoading)return pdfLoading;
    pdfLoading=loadPDFOnce();
    try {return await pdfLoading;} finally {pdfLoading=null;}
  }
  async function loadPDFOnce() {
    if(!viewer){viewer=await import('/vendor/pdfjs/build/pdf.mjs');viewer.GlobalWorkerOptions.workerSrc='/vendor/pdfjs/build/pdf.worker.mjs';}
    const response=await fetch('/preview.pdf?t='+Date.now());
    if(!response.ok)throw new Error('尚无成功编译的 PDF，请点击“立即编译”。');
    const bytes=new Uint8Array(await response.arrayBuffer()), hash=await sha(bytes);
    const nextTask=viewer.getDocument({data:bytes,cMapUrl:'/vendor/pdfjs/cmaps/',cMapPacked:true,
      standardFontDataUrl:'/vendor/pdfjs/standard_fonts/',wasmUrl:'/vendor/pdfjs/wasm/',isEvalSupported:false});
    const next=await nextTask.promise,oldTask=pdfTask,location=currentLocation();
    pdf=next;pdfTask=nextTask;sourceMap={files:{}};positions=[];
    await layoutPages(location);if(oldTask)await oldTask.destroy();
    el('previewDownload').classList.remove('hidden');el('previewDownload').href='/preview.pdf?t='+Date.now();
    try {
      const mapping=await (await fetch('/preview-map.json?t='+Date.now())).json();
      if(mapping.pdf_sha256!==hash){syncStatus('此 PDF 尚无对应定位数据，请立即编译一次。');return;}
      const destinations=await pdf.getDestinations(), refs=new Map(), mapped=[];
      for(const entry of mapping.anchors||[]) {
        const keyName=entry.destination||entry.anchor;
        const dest=destinations instanceof Map?destinations.get(keyName):destinations[keyName];if(!dest || dest[1]?.name!=='XYZ')continue;
        const key=JSON.stringify(dest[0]);
        if(!refs.has(key))refs.set(key,typeof dest[0]==='number'?dest[0]:await pdf.getPageIndex(dest[0]));
        const number=refs.get(key)+1,natural=(await pdf.getPage(number)).getViewport({scale:1});
        const [x,y]=natural.convertToViewportPoint(dest[2]??0,dest[3]??natural.height);
        mapped.push({...entry,page:number,x:x/natural.width,y:y/natural.height});
      }
      positions=mapped.sort((a,b)=>a.page-b.page||a.y-b.y);sourceMap=mapping;
      syncStatus(positions.length?'双击左侧段落 ↔ 右侧正文，可按内容块定位。':'此 PDF 未找到可用定位点，请重新编译。');
    }catch(error){syncStatus('定位数据加载失败：'+error.message+'。可继续阅读 PDF。');}
  }
  async function sourceIsCurrent(path,text) {
    return sourceMap.files[path] && await sha(new TextEncoder().encode(text))===sourceMap.files[path];
  }
  function flashPosition(position) {
    const row=rows[position.page-1];if(!row)return;
    scrollToPage(position.page,Math.max(0,position.y-.18));
    const host=el('pdfCanvasHost');host.scrollLeft+=row.node.getBoundingClientRect().left-host.getBoundingClientRect().left+position.x*row.node.clientWidth-host.clientWidth*.15;
    row.highlightUntil=Date.now()+3500;row.highlightY=position.y;paintHighlight(row,position.y);
  }
  async function forwardSync() {
    if(syncBusy)return;syncBusy=true;
    try {
      const editor=el('editor'),path=state.currentPath,text=editor.value;
      if(!(await sourceIsCurrent(path,text))){syncStatus('当前内容尚未与此 PDF 同步，请先编译成功后再定位。');return;}
      const line=text.slice(0,editor.selectionStart).split('\n').length;
      const candidates=positions.filter(p=>p.path===path);
      if(!candidates.length){syncStatus('此内容暂不支持定位，请手动翻页查看。');return;}
      const distance=p=>line<p.start?p.start-line:line>p.end?line-p.end:0;
      candidates.sort((a,b)=>distance(a)-distance(b));
      flashPosition(candidates[0]);syncStatus('已定位到 PDF 第 '+candidates[0].page+' 页，对应第 '+candidates[0].start+'–'+candidates[0].end+' 行内容块。');
    }catch(error){syncStatus(error.message);}finally{syncBusy=false;}
  }
  function paintHighlight(row,y) {
    row.node.querySelector('.pdf-jump-highlight')?.remove();
    const marker=document.createElement('div');marker.className='pdf-jump-highlight';marker.style.top=(y*100)+'%';
    row.node.append(marker);setTimeout(()=>marker.remove(),3500);
  }
  const normalizeText=text=>text.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  async function reverseSync(row,event) {
    if(syncBusy)return;syncBusy=true;
    try {
      const rect=row.node.getBoundingClientRect(),y=(event.clientY-rect.top)/rect.height;
      if(y<.075 || y>.94){syncStatus('页眉、页脚不属于 Markdown 正文，请双击正文区域。');return;}
      const candidates=positions.filter(p=>p.page===row.number);
      const previous=positions.filter(p=>p.page===row.number-1).at(-1);
      const clicked=normalizeText(event.target.closest('.textLayer span')?.textContent||'');
      const pool=previous?[...candidates,previous]:candidates;
      const textMatches=clicked.length>=4?pool.filter(p=>p.search?.includes(clicked)):[];
      const preceding=candidates.filter(p=>p.y<=y+.008);
      let chosen=preceding.at(-1)||candidates[0];
      if(textMatches.length)chosen=textMatches.sort((a,b)=>Math.abs((a.page-row.number)*1.1+a.y-y)-Math.abs((b.page-row.number)*1.1+b.y-y))[0];
      if(!chosen){syncStatus('此页没有可定位正文标记（如封面或目录），请通过功能菜单编辑。');return;}
      const file=state.project.files.find(f=>f.path===chosen.path);
      if(!file){syncStatus('对应章节已变更，请重新编译。');return;}
      const result=await api('/api/file?path='+encodeURIComponent(chosen.path));
      if(!(await sourceIsCurrent(chosen.path,result.text)) || (state.currentPath===chosen.path && !(await sourceIsCurrent(chosen.path,el('editor').value)))) {
        syncStatus('对应源文件已修改，请重新编译后再定位，避免跳错位置。');return;
      }
      if(state.currentPath!==chosen.path)await loadFile(file);
      if(state.currentPath!==chosen.path)return;
      const editor=el('editor');if(!(await sourceIsCurrent(chosen.path,editor.value)))return;
      const lines=editor.value.split('\n'),start=lines.slice(0,chosen.start-1).join('\n').length+(chosen.start>1?1:0);
      const end=lines.slice(0,chosen.end).join('\n').length;
      editor.focus();editor.setSelectionRange(start,end);scrollEditorTo(start);
      syncStatus('已定位到 '+file.label+' 第 '+chosen.start+'–'+chosen.end+' 行（内容块）。');
    }catch(error){syncStatus(error.message);}finally{syncBusy=false;}
  }
  function scrollEditorTo(offset) {
    const editor=el('editor'),style=getComputedStyle(editor),mirror=document.createElement('div');
    for(const prop of ['font','lineHeight','letterSpacing','padding','boxSizing','tabSize','wordBreak','overflowWrap'])mirror.style[prop]=style[prop];
    Object.assign(mirror.style,{position:'fixed',left:'-100000px',top:'0',width:editor.clientWidth+'px',whiteSpace:'pre-wrap'});
    mirror.textContent=editor.value.slice(0,offset);const mark=document.createElement('span');mark.textContent='|';mirror.append(mark);document.body.append(mirror);
    editor.scrollTop=Math.max(0,mark.offsetTop-editor.clientHeight*.3);mirror.remove();
  }
  function schedule(){clearTimeout(timer);if(active && el('autoPreview').checked)timer=setTimeout(compile,Math.max(0,3000-(Date.now()-lastEdit)));}
  function changed(){version++;lastEdit=Date.now();if(active){status(running?'编译中；新修改将在本轮结束后更新':el('autoPreview').checked?'内容已修改，等待保存和编译…':'内容已修改；请点击“立即编译”。');syncStatus('内容已修改，定位功能将检查源文件是否与 PDF 一致。');}schedule();}
  async function compile(){
    clearTimeout(timer);if(running)return;running=true;const target=version;el('compilePreview').disabled=true;status('正在保存并编译；可以继续编辑正文…');
    try {
      if(!(await flushSaves()))throw new Error('保存未成功，已停止编译。请先处理保存提示。');
      const result=await api('/api/preview',{method:'POST',body:'{}'});el('previewLog').textContent=result.output||'';
      if(!result.ok)throw new Error(result.busy?'另一个编译正在运行，请稍后重试。':(result.pdf?'本轮编译失败，下方仍为旧 PDF。':'本轮编译失败，尚无可显示的 PDF。')+'请展开错误详情，修正后重新编译。');
      await loadPDF();compiledVersion=target;
      status((result.portable_fonts?'替代字体预览，定稿需核对 · ':'')+(version===target && result.preview_status.state==='current'?'已更新 · ':'本轮完成，仍有新修改待编译 · ')+new Date().toLocaleTimeString());
    }catch(error){status(error.message);}finally{running=false;el('compilePreview').disabled=false;if(version!==target)schedule();}
  }
  function ready(value){project=value;const select=el('writingFile');select.replaceChildren();for(const file of value.files){const option=document.createElement('option');option.value=file.path;option.textContent=file.label;select.append(option);}select.value=state.currentPath||'';if(active && !pdf)open();}
  function open(){active=true;if(!project)return;if(version!==compiledVersion)schedule();if(!pdf && project.preview_pdf)loadPDF().then(()=>status(previewStatusText(project.preview_status))).catch(e=>status(e.message));else if(!pdf){lastEdit=Date.now();schedule();}else layoutPages(currentLocation()).catch(e=>status(e.message));}
  function chooseZoom(value){zoom=value;el('pdfZoom').value=['width','page','25','50','67','75','90','100','110','125','150','175','200','250','300'].includes(value)?value:'custom';if(pdf)layoutPages(currentLocation()).catch(e=>status(e.message));}
  document.addEventListener('DOMContentLoaded',()=>{
    const layout=document.querySelector('.editor-layout'),wrapper=document.createElement('div');wrapper.className='split-writing';layout.before(wrapper);wrapper.append(layout);
    const panel=document.createElement('section');panel.className='pdf-preview';panel.setAttribute('aria-label','PDF 连续预览');
    panel.innerHTML=`<div class="preview-controls"><strong>PDF 对照预览</strong><button id="compilePreview" class="button primary">立即编译</button><label><input id="autoPreview" type="checkbox" checked> 停止输入 3 秒后自动编译</label><a id="previewDownload" class="hidden" target="_blank">单独打开 PDF</a></div><p id="previewStatus" role="status">点击立即编译后，整篇 PDF 可连续滚动阅读。</p><div class="preview-pages"><button id="pdfPrevious" aria-label="上一页" disabled>‹</button><label>页 <input id="pdfPage" type="number" min="1" step="1" value="1"></label><span id="pdfTotal">/ —</span><button id="pdfNext" aria-label="下一页" disabled>›</button><select id="pdfZoom" aria-label="缩放模式"><option value="width">适合宽度</option><option value="page">适合整页</option>${[25,50,67,75,90,100,110,125,150,175,200,250,300].map(v=>`<option value="${v}">${v}%</option>`).join('')}<option value="custom">自定义</option></select><button id="zoomOut" aria-label="缩小">−</button><label><input id="zoomPercent" type="number" min="25" max="300" step="5" value="100" aria-label="自定义缩放百分比">%</label><button id="zoomIn" aria-label="放大">＋</button></div><p id="syncStatus" role="status">双击左侧段落或右侧正文，定位对应内容块。</p><div id="pdfCanvasHost" tabindex="0" aria-label="整篇 PDF，使用滚轮或上下方向键连续阅读"><p>首次编译可能需要几十秒。</p></div><details><summary>编译日志 / 错误详情</summary><pre id="previewLog"></pre></details>`;
    wrapper.append(panel);
    const files=document.createElement('label');files.className='writing-file';files.textContent='当前内容：';const select=document.createElement('select');select.id='writingFile';files.append(select);wrapper.before(files);
    select.onchange=()=>{const file=state.project.files.find(f=>f.path===select.value);if(file)loadFile(file);};
    const back=document.createElement('button');back.className='button ghost';back.textContent='返回功能菜单';back.onclick=()=>showPanel('home');document.querySelector('.editor-actions').prepend(back);
    const locate=document.createElement('button');locate.className='button ghost';locate.textContent='定位到 PDF';locate.title='也可以双击左侧正文';locate.onclick=forwardSync;document.querySelector('.editor-actions').append(locate);
    el('editor').addEventListener('dblclick',forwardSync);
    el('compilePreview').onclick=compile;
    el('autoPreview').onchange=event=>{if(event.target.checked){lastEdit=Date.now();schedule();}else{clearTimeout(timer);status(running?'当前编译会完成，后续自动编译已关闭':'自动编译已关闭，可点击“立即编译”。');}};
    el('pdfPrevious').onclick=()=>scrollToPage(page-1);el('pdfNext').onclick=()=>scrollToPage(page+1);
    el('pdfPage').onchange=event=>scrollToPage(Number(event.target.value)||1);
    el('pdfPage').onkeydown=event=>{if(event.key==='Enter'){scrollToPage(Number(event.target.value)||1);event.target.blur();}};
    el('pdfZoom').onchange=event=>{if(event.target.value==='custom')el('zoomPercent').focus();else chooseZoom(event.target.value);};
    const percentage=value=>{const clamped=Math.max(25,Math.min(300,Number(value)||100));el('zoomPercent').value=clamped;chooseZoom(String(clamped));};
    el('zoomPercent').onchange=event=>percentage(event.target.value);
    el('zoomPercent').onkeydown=event=>{if(event.key==='Enter'){percentage(event.target.value);event.target.blur();}};
    el('zoomOut').onclick=()=>percentage(Number(el('zoomPercent').value)-25);el('zoomIn').onclick=()=>percentage(Number(el('zoomPercent').value)+25);
    el('pdfCanvasHost').onscroll=()=>{cancelAnimationFrame(scrollFrame);scrollFrame=requestAnimationFrame(()=>{
      if(!rows.length)return;const host=el('pdfCanvasHost'),rect=host.getBoundingClientRect();
      const visible=row=>{const r=row.node.getBoundingClientRect();return Math.max(0,Math.min(r.bottom,rect.bottom)-Math.max(r.top,rect.top));};
      const closest=rows.reduce((a,b)=>visible(a)>=visible(b)?a:b);setPageNumber(closest.number);
      for(const row of rows)if(row.rendered && Math.abs(row.node.getBoundingClientRect().top-rect.top)>host.clientHeight*4+row.node.clientHeight){for(const canvas of row.node.querySelectorAll('canvas')){canvas.width=0;canvas.height=0;}row.node.replaceChildren();row.rendered=false;row.node.classList.remove('rendered');}
    });};
    let previousWidth=0;new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-previousWidth)<2)return;previousWidth=width;clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(active && pdf)layoutPages(currentLocation()).catch(e=>status(e.message));},200);}).observe(panel);
  });
  return {changed,ready,open,close(){active=false;clearTimeout(timer);}};
})();
