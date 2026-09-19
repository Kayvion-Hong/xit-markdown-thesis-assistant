document.addEventListener('DOMContentLoaded',()=>{
  const log=document.querySelector('#compatLog');
  document.querySelector('#compatCheck').onclick=async()=>{
    try { log.textContent='正在检查…';log.textContent=(await api('/api/compatibility',{method:'POST',body:JSON.stringify({action:'diagnose'})})).output; }
    catch(error) {log.textContent=error.message;}
  };
  document.querySelector('#installTexPackage').onclick=async event=>{
    const button=event.currentTarget;
    const values=await askFields('联网补装宏包（只修改随包 TeX 环境）',[{name:'name',label:'确认需要联网后，填写 TeX Live 宏包名，例如 siunitx；不要填 .sty。取消则不安装。'}]);
    if(!values)return;
    button.disabled=true;log.textContent='正在联网安装，最多等待 5 分钟，请勿关闭助手…';
    try {
      const result=await api('/api/compatibility',{method:'POST',body:JSON.stringify({action:'install',name:values.name.trim()})});
      log.textContent=(result.ok?'安装完成。请重新生成 PDF。':'安装未完成。请查看网络、宏包名称与 TeX Live 年份提示。')+'\n'+result.output;
    }catch(error){log.textContent=error.message;}finally{button.disabled=false;}
  };
});
