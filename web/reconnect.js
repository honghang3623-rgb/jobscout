'use strict';
// Retry reads only. Failed writes must remain an explicit user decision.
function createReconnect({load,offline=()=>{},online=()=>{},schedule=setTimeout,cancel=clearTimeout}){
 let timer=null,pending=null,delay=1500;
 function connected(){if(timer!==null)cancel(timer);timer=null;delay=1500;online();}
 function failed(error){
  offline(error);
  if(timer!==null)return;
  timer=schedule(()=>{timer=null;retry();},delay);
  delay=Math.min(delay*2,30000);
 }
 function retry(){
  if(pending)return pending;
  if(timer!==null)cancel(timer);timer=null;
  pending=Promise.resolve().then(load).then(()=>{connected();return true;},error=>{failed(error);return false;}).finally(()=>{pending=null;});
  return pending;
 }
 return {retry,failed,connected};
}
if(typeof module!=='undefined')module.exports={createReconnect};
