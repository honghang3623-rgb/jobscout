const assert=require('node:assert/strict');
const {createReconnect}=require('../web/reconnect.js');
(async()=>{
 let callbacks=new Map(),nextId=0,reads=0,failed=true,online=0,offline=0;
 const c=createReconnect({load:async()=>{reads++;if(failed)throw Error('offline');},
  offline:()=>offline++,online:()=>online++,schedule:(fn,delay)=>{callbacks.set(++nextId,{fn,delay});return nextId;},cancel:id=>callbacks.delete(id)});
 assert.equal(await c.retry(),false);
 assert.equal(reads,1);assert.equal(callbacks.size,1);assert.equal([...callbacks.values()][0].delay,1500);
 c.failed(Error('another failure'));assert.equal(callbacks.size,1,'overlapping failures share one retry timer');
 failed=false;await Promise.all([c.retry(),c.retry()]);
 assert.equal(reads,2,'concurrent reconnects share a read');assert.equal(online,1);assert.equal(callbacks.size,0);
 c.failed(Error('asleep'));assert.equal([...callbacks.values()][0].delay,1500,'success resets backoff');
 c.connected();assert.equal(callbacks.size,0,'manual refresh cancels pending retry');
 assert.ok(offline>=2);console.log('Reconnect recovery: passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
