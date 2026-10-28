process.chdir(__dirname);
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const context=vm.createContext({console});
vm.runInContext(fs.readFileSync('dist/demo-data.js','utf8').replace('window.','globalThis.'),context);
vm.runInContext(fs.readFileSync('dist/demo-backend.js','utf8'),context);
(async()=>{
 const api=context.JobScoutDemo,base=await api.request('/api/state');
 assert.equal(base.jobs.length,8);assert.equal(base.jobs.filter(j=>j.market==='cn').length,4);
 for(const job of base.jobs){assert.ok(job.url.startsWith('https://example.com/'));assert.ok(job.analysis);}
 const id=base.jobs[0].id;await api.request('/api/jobs/update',{id,status:'shortlist',notes:'=not-a-formula'});
 assert.equal((await api.request('/api/jobs/'+encodeURIComponent(id))).status,'shortlist');
 assert.ok(api.exportCSV('all').includes("'=not-a-formula"));
 await assert.rejects(()=>api.request('/api/jobs/update',{id,status:'bad'}));
 await assert.rejects(()=>api.request('/api/settings',{api_key:'not-a-key'}));
 const snapshot=await api.request('/api/state');snapshot.jobs[0].title='mutated';assert.notEqual((await api.request('/api/state')).jobs[0].title,'mutated');
 api.reset();assert.equal((await api.request('/api/jobs/'+encodeURIComponent(id))).notes,'');
 assert.ok(base.jobs.some(j=>j.hard_conflict));
 console.log('Demo checks passed: fictional fixtures, independent markets, status/notes, safe CSV, rejected network-only features, reset and immutable snapshots.');
})().catch(e=>{console.error(e);process.exitCode=1});
