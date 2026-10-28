'use strict';
// A browser-memory simulation. No fetch, credentials, storage, or remote mutations.
(function(root){
 const copy=value=>JSON.parse(JSON.stringify(value));
 const initial=copy(root.JOBSCOUT_DEMO_DATA);
 let state=copy(initial);
 const statuses=['new','shortlist','applied','interview','offer','rejected','ignored'];
 const notice='在线演示不执行实时采集或 AI 调用。请查看已生成的规则证据；完整功能可从 GitHub 下载后在本机使用。';
 const backend={
  async request(path,data){
   if(path==='/api/state')return copy(state);
   if(path==='/api/task')return {running:false,state:'completed',message:notice};
   if(data===undefined&&path.startsWith('/api/jobs/')){
    const job=state.jobs.find(x=>x.id===decodeURIComponent(path.slice('/api/jobs/'.length)));
    if(!job)throw Error('未找到该虚构示例岗位');
    return copy(job);
   }
   if(path==='/api/jobs/update'){
    const job=state.jobs.find(x=>x.id===data?.id);
    if(!job)throw Error('未找到该虚构示例岗位');
    if(data.status!==undefined){
     if(!statuses.includes(data.status))throw Error('无效的演示状态');
     if(job.status!==data.status)state.events.unshift({id:state.events.length+1,job_id:job.id,company:job.company,title:job.title,status:data.status,created:new Date().toISOString()});
     job.status=data.status;
    }
    if(data.notes!==undefined){if(typeof data.notes!=='string'||data.notes.length>2000)throw Error('演示备注最多 2000 字');job.notes=data.notes;}
    return {ok:true,demo:true};
   }
   throw Error(notice);
  },
  reset(){state=copy(initial);},
  exportCSV(market){
   const fields=['company','title','location','market','status','score','notes'];
   const quote=value=>{let text=String(value??'');if(/^[=+@\-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
   return '\uFEFF'+[fields,...state.jobs.filter(j=>market==='all'||j.market===market).map(j=>fields.map(k=>j[k]??''))].map(row=>row.map(quote).join(',')).join('\r\n');
  },
  notice
 };
 root.JobScoutDemo=backend;
 if(typeof document==='undefined')return;
 document.addEventListener('click',e=>{
  const reset=e.target.closest('#demo-reset');
  if(reset){e.preventDefault();e.stopImmediatePropagation();location.reload();return;}
  const exportLink=e.target.closest('a[href^="/api/export"]');
  if(exportLink){
   e.preventDefault();e.stopImmediatePropagation();const market=new URL(exportLink.href).searchParams.get('market')||'all';
   const blob=new Blob([backend.exportCSV(market)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
   a.href=url;a.download='jobscout-fictional-demo-'+market+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;
  }
  const action=e.target.closest('[data-action]')?.dataset.action;
  if(e.target.closest('#add-global')||['scan','scan-china','ai-detail','rescore','rescore-detail','company-editor','bulk-companies'].includes(action)){
   e.preventDefault();e.stopImmediatePropagation();root.setTimeout(()=>root.toast?.(notice),0);
  }
 },true);
})(globalThis);
