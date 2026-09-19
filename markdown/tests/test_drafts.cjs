const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=new Map();
const storage={get length(){return data.size},key:i=>[...data.keys()][i],getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k)};
const element=()=>({append(){},after(){},replaceChildren(){},setAttribute(){}});
const context=vm.createContext({localStorage:storage,sessionStorage:{getItem:()=> 'tab',setItem(){}},crypto:{randomUUID:()=> 'tab'},document:{querySelector:element,createElement:element},Date,JSON});
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../assistant/static/drafts.js'),'utf8')+'\nglobalThis.testDrafts=localDrafts;',context);
const d=context.testDrafts;
d.init({project_id:'A'});d.capture('chapter.md','old','rev1');d.capture('chapter.md','new','rev1');
d.acknowledge('chapter.md','old');assert.equal(data.size,1); // delayed save must not erase newer draft
d.init({project_id:'B'});d.acknowledge('chapter.md','new');assert.equal(data.size,1);
d.init({project_id:'A'});d.acknowledge('chapter.md','new');assert.equal(data.size,0);
d.capture('@metadata','{"author":"测试"}','');assert.equal(data.size,1);
storage.setItem=()=>{throw new Error('quota')};assert.doesNotThrow(()=>d.capture('chapter.md','x',''));
console.log('PASS: synchronous draft persistence, stale acknowledgement, project isolation, metadata, storage failure warning');
