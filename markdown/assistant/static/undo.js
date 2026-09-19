// Editing history is scoped to a file and the current page session.
class EditHistory {
  constructor(value) { this.items = [value]; this.index = 0; this.last = null; }
  record(before, after, kind, now = Date.now()) {
    if (before.text === after.text) return;
    const typing = ['insertText','deleteContentBackward','deleteContentForward'].includes(kind);
    const merge = typing && this.last && this.last.kind === kind && now-this.last.time < 1000 &&
      this.index === this.items.length-1 && this.last.end === before.start && before.start === before.end;
    this.items[this.index] = before;
    this.items.splice(this.index+1);
    if (merge) this.items[this.index] = after;
    else { this.items.push(after); this.index++; }
    if (this.items.length > 101) { this.items.shift(); this.index--; }
    this.last = typing ? {kind,time:now,end:after.end} : null;
  }
  move(delta) {
    const next = this.index + delta;
    if (next < 0 || next >= this.items.length) return null;
    this.index = next; this.last = null; return this.items[next];
  }
}
if (typeof module !== 'undefined') module.exports = {EditHistory};

if (typeof document !== 'undefined') {
  const editHistories = new Map();
  let currentHistory, pendingEdit, composing = false, compositionStart;
  const captureEdit = () => {
    const editor = document.querySelector('#editor');
    return {text:editor.value,start:editor.selectionStart,end:editor.selectionEnd};
  };
  function updateEditButtons() {
    const undo = document.querySelector('#undoEdit'), redo = document.querySelector('#redoEdit');
    if (!undo) return;
    undo.disabled = !currentHistory || currentHistory.index === 0;
    redo.disabled = !currentHistory || currentHistory.index === currentHistory.items.length-1;
  }
  window.attachEditHistory = (path, text) => {
    currentHistory = editHistories.get(path);
    if (!currentHistory || currentHistory.items[currentHistory.index].text !== text) {
      currentHistory = new EditHistory({text,start:0,end:0}); editHistories.set(path,currentHistory);
    }
    currentHistory.last = null; pendingEdit = null; updateEditButtons();
  };
  window.beforeAssistedEdit = () => captureEdit();
  window.afterAssistedEdit = before => {
    if (currentHistory) currentHistory.record(before,captureEdit(),'assisted');
    updateEditButtons();
  };
  function moveEdit(delta) {
    if (composing || !currentHistory) return;
    const value = currentHistory.move(delta);
    if (!value) return;
    const editor = document.querySelector('#editor');
    editor.value = value.text; editor.focus(); editor.setSelectionRange(value.start,value.end);
    setDirty(true); updateWordCount(); updateEditButtons();
  }
  document.addEventListener('DOMContentLoaded', () => {
    const editor = document.querySelector('#editor');
    for (const [id,label,delta] of [['undoEdit','↶ 撤销',-1],['redoEdit','↷ 重做',1]]) {
      const button = document.createElement('button'); button.id=id; button.className='button secondary';
      button.textContent=label; button.title=delta<0?'撤销上一步（Ctrl+Z）':'重做（Ctrl+Y / Ctrl+Shift+Z）';
      button.onclick=()=>moveEdit(delta); document.querySelector('#saveFile').before(button);
    }
    editor.addEventListener('beforeinput', event => {
      if (event.inputType==='historyUndo' || event.inputType==='historyRedo') {
        event.preventDefault(); moveEdit(event.inputType==='historyUndo'?-1:1); return;
      }
      if (!composing) pendingEdit=captureEdit();
    });
    editor.addEventListener('input', event => {
      if (composing || event.isComposing) return;
      if (currentHistory) currentHistory.record(pendingEdit || currentHistory.items[currentHistory.index],captureEdit(),event.inputType);
      pendingEdit=null; updateEditButtons();
    });
    editor.addEventListener('compositionstart',()=>{ composing=true; compositionStart=captureEdit(); });
    editor.addEventListener('compositionend',()=>{
      composing=false;
      if (currentHistory) currentHistory.record(compositionStart,captureEdit(),'composition');
      pendingEdit=captureEdit(); updateEditButtons();
    });
    editor.addEventListener('blur',()=>{ if(currentHistory) currentHistory.last=null; });
    editor.addEventListener('keydown', event => {
      if (event.isComposing || composing || !(event.ctrlKey || event.metaKey) || event.altKey) return;
      const key=event.key.toLowerCase();
      if (key==='z' || key==='y') {
        event.preventDefault(); moveEdit(key==='y' || event.shiftKey ? 1 : -1);
      }
    });
    updateEditButtons();
  });
}
