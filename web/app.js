'use strict';
// A saved webpage is an entry to the live local app, never a second database client.
if(location.protocol==='file:')location.replace('http://127.0.0.1:8765/'+(location.hash||'#overview'));
const $ = s => document.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const enc = encodeURIComponent;
const paths = {
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 briefcase:'<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V4h8v3M3 12c5 4 13 4 18 0M10 13h4v4h-4z"/>',
 spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3zM20 2v4M18 4h4"/>',
 columns:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>',
 building:'<rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1M10 21v-3h4v3"/>',
 shield:'<path d="M12 3 3.5 6v6c0 5 8.5 9 8.5 9s8.5-4 8.5-9V6z"/><path d="m8 12 3 3 5-6"/>',
 scan:'<path d="M8 3H4v4M16 3h4v4M4 17v4h4M20 17v4h-4M3 12h18M8 8v8M12 8v8M16 8v8"/>',
 settings:'<path d="m9 3-.5 3-2 1-3-.5-1.5 3L4 12l-2 2.5 1.5 3 3-.5 2 1L9 21h6l.5-3 2-1 3 .5 1.5-3L20 12l2-2.5-1.5-3-3 .5-2-1L15 3z"/><circle cx="12" cy="12" r="3"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
 plus:'<path d="M12 5v14M5 12h14"/>',
 arrow:'<path d="M4 12h15m-5-5 5 5-5 5"/>',
 external:'<path d="M14 3h7v7M21 3l-9 9M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
 refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 7A7 7 0 0 1 20 12M4 12a7 7 0 0 0 13.9 5"/>',
 calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M7 15h3M14 15h3"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 pin:'<path d="M18 10c0 5-6 11-6 11S6 15 6 10a6 6 0 0 1 12 0z"/><circle cx="12" cy="10" r="2"/>',
 search:'<circle cx="10" cy="10" r="7"/><path d="m15 15 6 6"/>',
 check:'<path d="m5 12 4 4L19 6"/>',
 download:'<path d="M12 3v12m-5-5 5 5 5-5M3 17v4h18v-4"/>',
 close:'<path d="m6 6 12 12M18 6 6 18"/>',
 file:'<path d="M14 2H5v20h14V7zM14 2v6h5M8 12h8M8 16h8"/>',
 trend:'<path d="m3 17 6-6 4 3 8-10M15 4h6v6"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',
 send:'<path d="m22 2-7 20-4-9L2 9zM11 13 22 2"/>',
 heart:'<path d="M20.5 4.5a5 5 0 0 0-7 0L12 6l-1.5-1.5a5 5 0 0 0-7 7L12 20l8.5-8.5a5 5 0 0 0 0-7z"/>',
 upload:'<path d="M12 16V3m-5 5 5-5 5 5M3 16v5h18v-5"/>',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
document.querySelectorAll('[data-icon]').forEach(el => el.innerHTML = icon(el.dataset.icon));
const labels = {overview:'今日概览',jobs:'美国求职',match:'JD 匹配分析',tracker:'投递追踪',companies:'目标公司',h1b:'H-1B 数据',scans:'扫描中心',settings:'资料与设置',china:'中国求职'};
const statusNames = {new:'新发现',shortlist:'待投递',applied:'已投递',interview:'面试中',offer:'Offer',rejected:'未通过',ignored:'已归档'};
const runNames = {china_scan:'国内自动采集',scheduled_china_scan:'国内每日采集',scan:'手动扫描',scheduled_scan:'每日扫描',rules:'初筛更新',ai:'AI 深度分析',h1b_import:'H-1B 数据导入'};

let usType='all',cnTab='jobs',cnSearch='',cnSector='all',cnTier='recommended',cnDeadline='7';
function usJobs(){return (S?.jobs||[]).filter(j=>(j.market||'us')==='us');}
function chinaJobs(){return (S?.jobs||[]).filter(j=>j.market==='cn');}

let S, page='overview', filters={search:'',status:'active',min:50,conflicts:true,ai:false}, detailJob=null, detailTab='analysis', toastTimer, pollTimer, wasRunning=false, stateVersion=0;

function toast(message,error=false){
 const t=$('#toast');t.textContent=message;t.className='show'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.className='',4500);
}
const connection=createReconnect({
 load:()=>refresh(!S),
 offline:()=>{
  const badge=$('.local-indicator');if(badge){badge.classList.add('disconnected');badge.innerHTML='<i></i> 连接中断 · 自动重试';}
  if(!S)$('#content').innerHTML=`<div class="empty"><h2>正在重新连接工作台</h2><p>后台启动或电脑唤醒后会自动恢复。若长时间未连接，请双击桌面的“启动 JobScout.command”。</p>${button('立即重连','reconnect','secondary','refresh')}</div>`;
 },
 online:()=>{const badge=$('.local-indicator');if(badge){badge.classList.remove('disconnected');badge.innerHTML='<i></i> 本地已连接';}}
});
async function api(path,data){
 const reading=data===undefined,controller=new AbortController();
 const timeout=reading?setTimeout(()=>controller.abort(),20000):null;
 let response;
 try{
  response=await fetch(path,{method:reading?'GET':'POST',headers:reading?{}:{'Content-Type':'application/json','X-JobScout-Token':S?.csrf||''},body:reading?undefined:JSON.stringify(data),signal:controller.signal});
 }catch(cause){
  const error=Error(reading?'暂时无法连接工作台，正在自动重试。':'连接中断，操作结果需核对；请重连后检查记录再操作。');
  connection.failed(error);throw error;
 }finally{if(timeout!==null)clearTimeout(timeout);}
 const result=await response.json();
 if(!response.ok){const error=Error(result.error||'请求失败');if(reading&&response.status>=500)connection.failed(error);throw error;}
 return result;
}

function time(value,withTime=false){
 if(!value)return '尚无记录';const d=new Date(value);if(!Number.isFinite(+d))return esc(value);
 return d.toLocaleString('zh-CN',{timeZone:'America/Los_Angeles',month:'2-digit',day:'2-digit',...(withTime?{hour:'2-digit',minute:'2-digit'}:{})});
}
function today(){return new Date().toLocaleDateString('zh-CN',{timeZone:'America/Los_Angeles',month:'long',day:'numeric',weekday:'long'});}
const sameDay = value => value && new Date(value).toLocaleDateString('en-CA',{timeZone:'America/Los_Angeles'})===new Date().toLocaleDateString('en-CA',{timeZone:'America/Los_Angeles'});
const actionable = () => usJobs().filter(j=>j.is_open!==0&&!j.hard_conflict&&['new','shortlist'].includes(j.status));
function safeLink(url){return /^https?:\/\//i.test(url||'')?esc(url):'';}
const button = (text,action,cls='',ico='',extra='') => `<button class="button ${cls}" data-action="${action}" ${extra}>${ico?icon(ico):''}${text}</button>`;
function heading(title,sub,kicker='YOUR CAREER, IN FOCUS',action=''){
 return `<div class="page-heading"><div><div class="eyebrow">${kicker}</div><h1>${title}</h1><p>${sub}</p></div>${action||`<div class="date">${icon('calendar')}${today()}</div>`}</div>`;
}
function metric(label,value,hint,ico='briefcase',positive=false){return `<div class="metric"><div class="metric-top">${label}${icon(ico)}</div><div class="metric-value"><b>${value}</b><span class="${positive?'metric-positive':''}">${hint}</span></div></div>`;}
function companyAvatar(name){const initials={'Stripe':'S','Coinbase':'C','Ramp':'r','Robinhood':'R','OpenAI':'◎','Palantir':'P','Airbnb':'A','Plaid':'P'};return `<span class="company-avatar" data-company="${esc(name)}">${esc(initials[name]||name.slice(0,1).toUpperCase())}</span>`;}
function jobRow(job){
 const chips=[`<span class="tag">${esc(job.resume||'Technical')}</span>`,...(job.matched||[]).slice(0,3).map(x=>`<span class="tag">${esc(x)}</span>`)];
 if(job.market==='cn'){chips.unshift(`<span class="tag">${esc(job.sector||'国内岗位')}</span>`);if(job.source_id)chips.push(`<span class="tag green">${job.ats==='cn-public_browser'?'官网浏览器核实':'自动采集'}</span>`);if(job.match_tier==='priority')chips.unshift('<span class="tag green">方向匹配</span>');if(job.match_tier==='stretch')chips.unshift('<span class="tag amber">挑战方向</span>');const d=job.deadline_info;if(d)chips.push(`<span class="tag ${['urgent','conflict','expired'].includes(d.status)?'amber':''}">${d.date?esc(d.date)+' · ':''}${esc(d.label)}</span>`);}
 if(job.screen){const x=job.screen;chips.unshift(`<span class="tag">${esc(x.geo.label)} · ${esc(x.direction.label)}</span>`);if(job.market!=='cn')chips.push(`<span class="tag ${['no_future','opt_excluded','citizen'].includes(x.authorization.code)?'amber':''}">${esc(x.authorization.label)}</span>`);if(x.conflicts.length)chips.unshift(`<span class="tag amber">${esc(x.conflicts.slice(0,2).join(' / '))}</span>`);}
 if(job.preference?.preferred)chips.unshift('<span class="tag green">加州实习 · 优先</span>');
 if(job.hard_conflict)chips.unshift('<span class="tag amber">条件待核对</span>');
 if(job.flags)chips.push('<span class="tag amber">授权需复核</span>');
 if(job.method==='llm')chips.unshift('<span class="tag green">AI 已分析</span>');
 if(job.is_open===0)chips.unshift('<span class="tag amber">官网已不再列出</span>');
 return `<div class="job-row" role="button" tabindex="0" data-job="${esc(job.id)}">${companyAvatar(job.company)}<div class="job-main"><h3>${esc(job.title)}</h3><div class="job-meta"><span>${esc(job.company)}</span><span>${icon('pin')}${esc(job.location||'地点待确认')}</span></div><div class="tags">${chips.join('')}</div>${job.screen?`<div class="job-evidence-line">简历证据 ${job.screen.matched_count} 项 · 未证实技能 ${job.screen.gap_count} 项 · ${esc(job.screen.experience.label)}</div>`:''}</div><div class="job-score ${job.hard_conflict?'conflict':''}"><strong>${job.score??'—'}</strong><small>${job.stale?'待更新':job.method==='llm'?'AI 匹配分':'初筛参考'}</small></div></div>`;
}
function empty(message,action=''){return `<div class="empty">${icon('briefcase')}${message}${action?`<div>${action}</div>`:''}</div>`;}
async function refresh(renderPage=true){
 const version=++stateVersion;const data=await api('/api/state');if(version!==stateVersion)return;S=data;connection.connected();$('#nav-count').textContent=usJobs().length;$('#china-count').textContent=chinaJobs().length;updateTask(S.task);if(renderPage)render();
}
function go(next){if(!labels[next])next='overview';page=next;location.hash=next;$('#detail-dialog').close();render();window.scrollTo({top:0,behavior:'instant'});}
function render(){
 if(!S)return;$('#crumb').textContent=labels[page];document.querySelectorAll('#nav button').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
 const views={overview,jobs,match,tracker,companies,h1b,scans,settings,china};$('#content').innerHTML=(S.preferences.demo?'<div class="notice green">演示模式 · 候选人和示例岗位均为虚构；未包含作者的简历、投递记录或账号。</div>':'')+views[page]();bindForms();
}

function overview(){
 const shortlist=usJobs().filter(j=>j.status==='shortlist').length,applied=usJobs().filter(j=>['applied','interview','offer','rejected'].includes(j.status)).length;
 const ai=usJobs().filter(j=>j.method==='llm').length, rec=sortBoard(usJobs().filter(usRecommended),'us').slice(0,5), latest=S.runs.find(r=>['scan','scheduled_scan'].includes(r.kind));
 const newToday=usJobs().filter(j=>sameDay(j.first_seen)).length;
 const checks=[{done:true,title:'建立你的求职档案',sub:'个人资料已导入，支持随时修改',action:'settings'},
 {done:!!latest,title:'扫描目标公司的新岗位',sub:latest?`最近一次：${time(latest.started,true)}`:`已配置 ${S.companies.length} 家公司，开始首次扫描`,action:'scans'},
 {done:ai>0,title:'深度分析优先岗位',sub:S.ai.configured?'AI 已配置，选择岗位后开始分析':'连接 AI 后，获得要求与经历证据对照',action:S.ai.configured?'jobs':'settings'},
 {done:applied>0,title:'完成一次人工投递',sub:'读完 JD 后，再前往公司官网申请',action:'tracker'}];
 return heading('两地机会，各有一条清晰的路。','选择美国或中国板块，分别管理地点、招聘通道、简历匹配与投递进度。')+boardSwitch('')+
 `<section class="hero"><div class="hero-copy"><div class="eyebrow">A LITTLE CLARITY. A BETTER NEXT STEP.</div><h2>你的下一份工作，<em>从有依据的选择开始。</em></h2><p>目标公司扫描、岗位匹配、投递进度，在一个工作台里串起来。</p>${button('探索适合我的岗位','go-jobs','','arrow')}</div><div class="hero-art"><div class="orbit">${icon('briefcase')}</div><span class="orbit-dot"></span><div class="hero-chip">${icon('check')}每次投递，保留你的判断</div></div></section>`+
 `<section class="metrics">${metric('收录岗位',usJobs().length,`${S.companies.length} 家目标公司`,'briefcase')}${metric('今日新发现',newToday,'按首次发现时间','spark',newToday>0)}${metric('待投递清单',shortlist,'由你确认并加入','heart')}${metric('累计已投递',applied,`${usJobs().filter(j=>j.status==='interview').length} 个面试中`,'send')}</section>`+
 `<div class="dashboard-grid"><section class="panel"><div class="panel-head"><h2>${icon('spark')}值得先看一看</h2><button class="text-link" data-page="jobs">全部岗位 ${icon('arrow')}</button></div><div class="panel-note">根据资料初筛排序 · 已排除检测到的条件冲突 · 分数不代表录用概率</div>${rec.length?rec.map(jobRow).join(''):empty('当前没有符合条件的推荐岗位，试试扫描或手动添加。',button('添加 JD','go-match','secondary','plus'))}</section><div class="right-stack"><section class="panel"><div class="panel-head"><h2>今天的小目标</h2><span class="tag">${checks.filter(c=>c.done).length} / 4</span></div><div class="checklist">${checks.map(c=>`<div class="check-item ${c.done?'complete':''}"><span class="check-circle">${c.done?icon('check'):''}</span><div><button class="text-link" data-page="${c.action}"><strong>${c.title}</strong></button><small>${c.sub}</small></div></div>`).join('')}</div></section><section class="insight"><h3>${icon('shield')}雇主记录，需要放在语境里看</h3><p>历史 H-1B 或 LCA 记录是一条线索。当前岗位的授权要求，仍应以 JD 原文和雇主答复为准。</p><button class="text-link" data-page="h1b">查看我的雇主数据 ${icon('arrow')}</button></section></div></div>`+
 `<section class="panel activity"><div class="panel-head"><h2>工作台动态</h2><button class="text-link" data-page="scans">运行记录 ${icon('arrow')}</button></div><div class="activity-items"><div class="activity-item">${icon('file')}<div>本地 SQLite 数据库<small>示例数据与个人运行记录分开</small></div></div><div class="activity-item">${icon('clock')}<div>${latest?`最近扫描：${latest.detail.companies??0} 家成功`:(S.preferences.daily_enabled?'每日扫描已启用':'自动扫描未启用')}<small>${latest?time(latest.started,true):`${S.preferences.daily_time} · 美国太平洋时间 · 运行期间执行`}</small></div></div><div class="activity-item">${icon('spark')}<div>${ai} 个岗位完成 AI 分析<small>${S.ai.configured?'AI 服务已连接配置':'配置密钥后按需启用'}</small></div></div></div></section>`;
}

const boardFilters={us:{country:'us',geo:'all',track:'all',direction:'all',experience:'entry',skill:'all',fresh:'all',sort:'fit'},cn:{country:'cn',geo:'all',track:'all',direction:'all',experience:'entry',skill:'all',fresh:'all',sort:'fit'}};
function boardSwitch(active){return `<div class="market-switch" aria-label="选择求职市场"><button class="market-card ${active==='us'?'selected':''}" data-page="jobs"><span class="eyebrow">UNITED STATES</span><strong>美国求职</strong><span>全职与实习 · 独立地点偏好</span><small>${usJobs().length} 个收录 · 地点与授权独立筛选</small></button><button class="market-card ${active==='cn'?'selected':''}" data-page="china"><span class="eyebrow">CHINA MAINLAND</span><strong>中国求职</strong><span>互联网数据分析 · 银行 / 证券 / 基金</span><small>${chinaJobs().length} 个收录 · 校招 / 实习 / 社招分开</small></button></div>`;}
function facetSelect(m,key,label,options){return `<label class="facet-field"><span>${label}</span><select data-board="${m}" data-facet="${key}" aria-label="${m==='us'?'美国':'中国'}${label}">${options.map(([k,v])=>`<option value="${esc(k)}" ${boardFilters[m][key]===k?'selected':''}>${esc(v)}</option>`).join('')}</select></label>`;}
function advancedFilters(m){
 const cn=m==='cn',geo=cn?['北京','上海','杭州','深圳','广州','成都','南京','苏州','武汉','西安','天津','合肥','长沙','厦门','宁波']:['CA','NY','MA','WA','TX','IL','CT','NC','FL','VA','DC','CO','NJ','PA'];
 const stateNames={CA:'加州 CA',NY:'纽约 NY',MA:'马萨诸塞 MA',WA:'华盛顿 WA',TX:'得州 TX',IL:'伊利诺伊 IL',CT:'康涅狄格 CT',NC:'北卡 NC',FL:'佛罗里达 FL',VA:'弗吉尼亚 VA',DC:'华盛顿特区 DC',CO:'科罗拉多 CO',NJ:'新泽西 NJ',PA:'宾州 PA'};
 return `<section class="panel facet-panel"><div class="panel-head"><h2>把筛选条件说清楚</h2><span class="hint">两地筛选互不影响</span></div><div class="facet-grid">`+
 facetSelect(m,'country','国家 / 地区',cn?[['cn','中国大陆已明确'],['unknown','地点未明确'],['all','全部，含港澳台 / 境外']]:[['us','美国地点已明确'],['mixed','美国及其他国家并列'],['unknown','国家未明确，待核对'],['all','全部，含非美国记录']])+
 facetSelect(m,'geo',cn?'城市':'州 / 远程',[['all',cn?'全部城市':'美国州别不限'],...geo.map(v=>[v,cn?v:stateNames[v]]),['remote','远程（仍受国家限制）']])+
 facetSelect(m,'track','招聘通道',[['all','全部通道'],['graduate','应届 / 校园招聘'],['intern','实习'],['unclassified','未明确通道'],['experienced','社招 / 经验岗']])+
 facetSelect(m,'direction','岗位方向',[['all','全部方向'],['data','数据分析 / BI'],['product','产品 / 商业 / 增长'],['risk','风控 / 信用 / 反欺诈'],['research','金融 / 经济研究'],['quant','量化 / 算法挑战']])+
 facetSelect(m,'experience','经验年限',[['entry','未明确要求 2+ 年正式经验'],['all','全部，含经验要求较高']])+
 facetSelect(m,'skill','JD 技能要求',[['all','不限技能'],...['SQL','Python','Excel','BI','Stata / 计量','风控建模','A/B 实验','Tableau / Power BI'].map(v=>[v,v])])+
 (cn?facetSelect(m,'type','工作类型',[['all','全部类型'],['intern','实习'],['fulltime','全职 / 校招']]):facetSelect(m,'visa','授权与 sponsorship',[['all','全部，按原文提示'],['unknown','未说明，需问雇主'],['supports','JD 提及支持 sponsorship'],['no_future','未来 sponsorship 受限'],['opt_mentioned','JD 提及 OPT / CPT'],['opt_excluded','明确排除 OPT（通常不适合）'],['citizen','公民 / 安全许可要求']]))+
 facetSelect(m,'fresh','发布时效',[['all','不限发布时间'],['7','近 7 天发布 / 更新'],['30','近 30 天发布 / 更新']])+
 facetSelect(m,'sort','排序方式',[['fit','推荐优先：通道 / 方向 / 证据'],['new','最近发现优先'],...(cn?[['deadline','已知截止最早优先']]:[])])+
 `</div><p class="facet-note">推荐排序综合招聘通道、岗位方向与证据分；${cn?'国内校招与数据相关方向优先。':'美国全职与实习分开筛选。'}条件冲突、待核对要求和技能缺口分别展示。没有写年限 / 授权政策，不表示已经符合。发布时间由官网提供，可能是更新日期。</p></section>`;
}
function passesBoard(j,m){
 const f=boardFilters[m],x=j.screen||{},geo=x.geo||{};
 return (f.country==='all'||geo.country===f.country)&&(f.geo==='all'||f.geo==='remote'&&geo.remote||(geo.regions||[]).includes(f.geo))&&(f.track==='all'||x.track===f.track)&&(f.direction==='all'||x.direction?.code===f.direction)&&(f.experience!=='entry'||x.experience?.min_years==null||x.experience.min_years<2)&&(f.skill==='all'||(x.skills||[]).includes(f.skill))&&(!f.type||f.type==='all'||x.type===f.type)&&(!f.visa||f.visa==='all'||x.authorization?.code===f.visa)&&(f.fresh==='all'||j.posted&&Number.isFinite(+new Date(j.posted))&&Date.now()-new Date(j.posted)<=Number(f.fresh)*86400000&&new Date(j.posted)<=new Date());
}
function recommendationRank(j,m){const x=j.screen||{};let value=j.score||0;if(m==='us'){if(x.track==='graduate'&&x.type!=='intern')value+=15;if(x.direction?.code==='data'||x.direction?.code==='risk')value+=6;if(x.authorization?.code==='supports')value+=4;if(x.direction?.code==='quant')value-=10;if(x.direction?.code==='other')value-=12;}else{if(j.match_tier==='priority')value+=10;if(j.match_tier==='stretch')value-=20;}return value;}
function sortBoard(list,m){const type=boardFilters[m].sort;return list.sort((a,b)=>type==='new'?(b.first_seen||'').localeCompare(a.first_seen||''):type==='deadline'?(a.deadline_info?.date||'9999').localeCompare(b.deadline_info?.date||'9999'):recommendationRank(b,m)-recommendationRank(a,m));}
function usRecommended(j){return j.is_open!==0&&!j.hard_conflict&&j.screen?.geo.country==='us'&&j.score>=55&&!['citizen','opt_excluded'].includes(j.screen?.authorization.code);}
function usPlan(){return `<details class="panel work-plan"><summary>求职计划 · 示例资料，可在本机修改</summary><div><p>本项目使用虚构候选人资料。毕业月份、学历与实习地点偏好在本机 data/candidate.json 中配置；简历资料在“资料与设置”中修改。</p><p>实习与全职可并行筛选。岗位中的毕业窗口、返校要求及授权限制需要逐项核对。历史 H-1B / LCA 记录仅提供雇主背景，不证明当前岗位支持签证。</p><p>平台仅辅助筛选与整理，所有申请由使用者人工确认。</p></div></details>`;}
function filteredJobs(){return sortBoard(usJobs().filter(j=>passesBoard(j,'us')).filter(j=>usType==='all'||usType==='preferred'&&j.preference?.preferred||j.preference?.job_type===usType).filter(j=>(!filters.search||(j.company+' '+j.title+' '+j.location+' '+(j.matched||[]).join(' ')).toLowerCase().includes(filters.search.toLowerCase()))&&(filters.status==='all'||filters.status==='active'&&j.is_open!==0&&['new','shortlist'].includes(j.status)||j.status===filters.status)&&(j.score??0)>=filters.min&&(!filters.conflicts||!j.hard_conflict)&&(!filters.ai||j.method==='llm')),'us');}
function jobs(){
 const list=filteredJobs();return heading('美国求职，按你的毕业时间推进。','美国全职与实习独立筛选；地点偏好可调整。非美国、博士限定、返校与授权冲突单独核对。','UNITED STATES',`<a href="/api/export?market=us" class="button secondary">${icon('download')}导出美国岗位</a>`)+boardSwitch('us')+usPlan()+advancedFilters('us')+
 `<div class="toolbar"><select id="job-type" aria-label="岗位类型与地区偏好">${[['all','美国全部岗位'],['preferred','优先：加州实习'],['intern','全部美国实习'],['fulltime','全职 · 州别不限']].map(([k,v])=>`<option value="${k}" ${usType===k?'selected':''}>${v}</option>`).join('')}</select><div class="search">${icon('search')}<input id="job-search" placeholder="搜索职位、公司、地点或技能" value="${esc(filters.search)}" aria-label="搜索岗位"></div><select id="job-status" aria-label="按投递状态筛选">${[['active','待处理岗位'],['all','全部状态'],...Object.entries(statusNames)].map(([k,v])=>`<option value="${k}" ${filters.status===k?'selected':''}>${v}</option>`).join('')}</select><select id="job-min" aria-label="最低初筛分">${[0,40,50,60,70,80].map(n=>`<option value="${n}" ${filters.min===n?'selected':''}>${n===0?'全部分数':n+' 分以上'}</option>`).join('')}</select></div>`+
 `<div class="result-count"><span id="result-count">${list.length} 个岗位</span><div style="display:flex;gap:16px;flex-wrap:wrap"><label class="inline-check"><input id="hide-conflicts" type="checkbox" ${filters.conflicts?'checked':''}>隐藏条件冲突</label><label class="inline-check"><input id="only-ai" type="checkbox" ${filters.ai?'checked':''}>只看 AI 分析</label></div></div><section class="panel" id="job-list">${list.length?list.map(jobRow).join(''):empty('没有符合筛选条件的岗位。',button('重置筛选','reset-filters','secondary'))}</section>`;
}
function match(){return heading('把一份 JD，变成清晰的判断。','粘贴完整岗位描述，与你的真实经历逐条对照。','MATCH WITH EVIDENCE')+
 `<div class="section-grid"><section class="panel form-panel"><form id="match-form"><div class="form-row"><div class="field"><label for="manual-company">公司名称 *</label><input id="manual-company" name="company" required placeholder="例如 Stripe" maxlength="150"></div><div class="field"><label for="manual-title">职位名称 *</label><input id="manual-title" name="title" required placeholder="例如 Data Analyst" maxlength="250"></div></div><div class="form-row"><div class="field"><label for="manual-location">工作地点</label><input id="manual-location" name="location" placeholder="例如 New York, NY" maxlength="250"></div><div class="field"><label for="manual-url">原职位链接</label><input id="manual-url" name="url" type="url" placeholder="https://…"></div></div><div class="field"><label for="manual-jd">岗位描述全文 *</label><textarea id="manual-jd" name="description" required minlength="80" maxlength="100000" rows="12" placeholder="粘贴职责、任职要求、地点和工作授权说明。完整的 JD 会让判断更准确。"></textarea></div><div class="form-actions"><span class="hint">先保存并进行免费初筛；AI 分析由你单独启动。</span><button class="button" type="submit">${icon('spark')}保存并分析</button></div></form></section><div><div class="match-intro"><strong>分析会回答什么？</strong>01 &nbsp; 地点、职级、经验是否匹配<br>02 &nbsp; 哪些技能有你的经历支撑<br>03 &nbsp; 哪些要求仍缺少证据<br>04 &nbsp; 适合使用哪一版简历<br>05 &nbsp; 工作授权有哪些待确认项</div><section class="insight" style="margin-top:18px"><h3>${icon('file')}围绕真实经历来分析</h3><p>个人资料中的缺口不会算作已掌握技能。没有证据的经历，不会通过关键词匹配自动补上。</p><button class="text-link" data-page="settings">检查我的个人资料 ${icon('arrow')}</button></section></div></div>`;}
function tracker(){
 const applied=usJobs().filter(j=>['applied','interview','offer','rejected'].includes(j.status)).length;
 return heading('每一步进展，都有迹可循。','确认岗位、记录投递、跟进面试。点击卡片查看详情与备注。','YOUR APPLICATION PIPELINE',`<a href="/api/export?market=us" class="button secondary">${icon('download')}导出记录</a>`)+
 `<section class="metrics">${metric('已投递',applied,'包括后续流程','send')}${metric('面试中',usJobs().filter(j=>j.status==='interview').length,'当前状态','calendar')}${metric('收到 Offer',usJobs().filter(j=>j.status==='offer').length,'当前状态','check')}${metric('待投递',usJobs().filter(j=>j.status==='shortlist').length,'人工确认清单','heart')}</section>`+
 `<div class="board">${['shortlist','applied','interview','offer','rejected'].map(status=>{const list=usJobs().filter(j=>j.status===status);return `<section class="board-column"><div class="board-heading"><i></i>${statusNames[status]}<b>${list.length}</b></div>${list.length?list.map(j=>`<article class="board-card" data-job="${esc(j.id)}" tabindex="0" role="button"><div class="board-card-head">${companyAvatar(j.company)}${esc(j.company)}</div><h3>${esc(j.title)}</h3><small>${esc(j.location||'地点待确认')}</small><div class="tags"><span class="tag">${esc(j.resume)}</span>${j.method==='llm'?'<span class="tag green">AI</span>':''}</div><select aria-label="${esc(j.company)} 投递状态" data-job-status="${esc(j.id)}">${Object.entries(statusNames).map(([k,v])=>`<option value="${k}" ${k===j.status?'selected':''}>${v}</option>`).join('')}</select></article>`).join(''):'<div class="empty" style="font-size:10px;padding:30px 5px">下一步进展，从这里开始</div>'}</section>`}).join('')}</div>`;
}
function companies(){
 const latest=S.runs.find(r=>['scan','scheduled_scan'].includes(r.kind));
 const results=latest?.detail?.company_results||[];
 return heading('把目光，放在目标公司上。',`已配置 ${S.companies.length} 家公司。每次扫描会验证招聘接口，并记录成功与失败。`,'YOUR WATCHLIST',button('管理公司列表','company-editor','secondary','plus'))+
 `<div class="notice">当前为 ${S.companies.length} 家已配置公司，支持扩展到 140 家以上。填写招聘页真实 ATS / slug 后，通过扫描验证有效性。</div><div class="company-grid">${S.companies.map(c=>{const result=results.find(r=>r.company===c.name);return `<section class="panel company-card"><div class="company-card-top">${companyAvatar(c.name)}<div><h3>${esc(c.name)}</h3><p>${esc(c.ats)} / ${esc(c.slug)}</p></div></div><div class="tags"><span class="tag">${c.job_count} 个收录岗位</span><span class="tag ${c.h1b?'green':'amber'}">${c.h1b?'有历史雇主记录':'H-1B 数据待导入'}</span></div><div class="company-card-bottom"><span>${result?result.ok?'最近扫描成功':'最近扫描失败':'接口尚待验证'}</span><button data-company-jobs="${esc(c.name)}">查看岗位 →</button></div></section>`}).join('')}</div>`;
}
function h1b(){
 const hasData=S.imports.length>0;
 return heading('把雇主历史，变成参考证据。','关联 DOL LCA 与 USCIS 数据，保留来源、财年和匹配到的法人名称。','EMPLOYER INTELLIGENCE')+
 `<div class="notice">LCA 认证不等于 H-1B 请愿获批；历史记录不代表当前岗位提供 sponsorship。没有匹配结果，也不代表雇主从未申报。</div><div class="section-grid"><div><section class="panel"><div class="panel-head"><h2>已导入的数据</h2><span class="tag">${S.imports.length} 组</span></div>${hasData?`<div class="table-scroll"><table><thead><tr><th>来源</th><th>财年</th><th>雇主数</th><th>统计总量</th></tr></thead><tbody>${S.imports.map(r=>`<tr><td>${r.source==='lca'?'DOL LCA 认证职位':'USCIS 批准'}</td><td>FY${esc(r.fiscal_year)}</td><td>${r.employers.toLocaleString()}</td><td>${r.total.toLocaleString()}</td></tr>`).join('')}</tbody></table></div>`:empty('还没有导入官方雇主数据。<br>下载 CSV 或 XLSX 后，在右侧导入。')}</section><section class="panel" style="margin-top:20px"><div class="panel-head"><h2>目标公司关联结果</h2><span class="hint">按规范化法人名精确关联</span></div><div class="table-scroll"><table><thead><tr><th>公司</th><th>匹配到的法人</th><th>来源与财年</th></tr></thead><tbody>${S.companies.map(c=>`<tr><td>${esc(c.name)}</td><td>${c.h1b?esc(c.h1b.matched):'<span class="muted">尚无匹配记录</span>'}</td><td>${c.h1b?c.h1b.rows.map(r=>`<span class="tag">${r.source==='lca'?'LCA':'USCIS'} FY${esc(r.fiscal_year)} · ${r.count.toLocaleString()}</span>`).join(' '):'—'}</td></tr>`).join('')}</tbody></table></div></section></div><section class="panel form-panel"><h2>导入官方数据</h2><p class="hint">支持 CSV / XLSX，最大 200MB。相同来源和财年的雇主记录会更新。</p><form id="h1b-form"><div class="field"><label for="h1b-kind">数据来源</label><select id="h1b-kind" name="kind" style="width:100%"><option value="lca">DOL LCA</option><option value="uscis">USCIS Employer Data Hub</option></select></div><div class="field"><label for="h1b-fy">财年</label><input id="h1b-fy" name="fy" required pattern="20[0-9]{2}" placeholder="例如 2025"></div><div class="field"><label for="h1b-file">CSV 或 XLSX 文件</label><input id="h1b-file" type="file" accept=".csv,.xlsx" required></div><button class="button" type="submit">${icon('upload')}导入数据</button></form><div class="settings-meta">官方下载入口<br><a href="https://www.dol.gov/agencies/eta/foreign-labor/performance" target="_blank" rel="noopener">DOL 披露数据 ↗</a><br><a href="https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub" target="_blank" rel="noopener">USCIS Employer Data Hub ↗</a></div></section></div>`;
}
function scans(){
 const latest=S.runs.find(r=>['scan','scheduled_scan'].includes(r.kind));
 const success=latest?.detail.companies;
 return heading('让发现机会，成为日常。','扫描公开 ATS 招聘接口；新增岗位自动去重并进行免费初筛。','DISCOVERY ENGINE')+
 `<section class="metrics">${metric('已配置公司',S.companies.length,'Greenhouse / Lever / Ashby','building')}${metric('最近成功扫描',success??'—',latest?`${latest.detail.errors?.length??0} 家失败`:'尚未扫描','scan')}${metric('最近新增',latest?.detail.new??'—','去重后写入数据库','spark')}${metric('每日扫描',S.preferences.daily_enabled?S.preferences.daily_time:'关闭','美国太平洋时间','clock')}</section>`+
 `<section class="panel"><div class="panel-head"><h2>${icon('scan')}扫描与分析</h2><span class="tag green">仅访问公开职位接口</span></div><div class="scan-status">${icon('info')}每日任务在应用运行期间执行；电脑休眠或应用关闭时不会扫描。</div><div class="scan-actions">${button('扫描新岗位','scan','','refresh')}${button('更新免费初筛','rescore','secondary','spark')}${button('设置每日时间','go-settings','secondary','clock')}</div></section>`+
 `<section class="panel" style="margin-top:22px"><div class="panel-head"><h2>运行记录</h2><span class="hint">最近 20 次</span></div>${S.runs.length?`<div class="table-scroll"><table><thead><tr><th>任务</th><th>开始时间</th><th>状态</th><th>结果</th></tr></thead><tbody>${S.runs.map(r=>`<tr><td>${runNames[r.kind]||esc(r.kind)}</td><td>${time(r.started,true)}</td><td><span class="tag ${r.state==='completed'?'green':r.state==='failed'?'red':'amber'}">${({running:'运行中',completed:'已完成',partial:'部分完成',failed:'失败',interrupted:'已中断'})[r.state]||esc(r.state)}</span></td><td>${runSummary(r)}</td></tr>`).join('')}</tbody></table></div>`:empty('还没有运行记录。点击“扫描新岗位”开始。')}</section>`;
}
function runSummary(r){
 const d=r.detail||{};if(d.error)return `<span class="error-text">${esc(d.error)}</span>`;
 let summary='';if(d.configured!==undefined)summary=`${d.companies}/${d.configured} 家成功 · 发现 ${d.seen} · 保留 ${d.kept} · 新增 ${d.new}`;
 else if(d.analyzed!==undefined)summary=`AI 分析 ${d.analyzed} 个岗位`;
 else if(d.scored!==undefined)summary=`更新 ${d.scored} 个岗位`;
 else if(d.employers!==undefined)summary=`导入 ${d.employers} 个雇主 · FY${esc(d.fiscal_year)}`;
 else summary=r.state==='running'?'处理中…':r.state==='interrupted'?'应用退出导致任务中断，可重新运行':'—';
 if(d.errors?.length)summary+=`<details style="margin-top:7px"><summary>${d.errors.length} 条失败详情</summary>${d.errors.map(e=>`<div class="error-text">${esc(e)}</div>`).join('')}</details>`;
 return summary;
}
function settings(){
 return heading('让工作台，更了解你。','所有匹配围绕你的真实资料展开；修改目标后，记得更新初筛。','MAKE IT YOURS')+
 `<div class="settings-layout"><div><section class="panel form-panel"><h2>个人资料</h2><p class="hint">当前为虚构示例资料。英文和中文档案独立保存；修改后可重新分析。</p><form id="profile-form"><div class="field"><label for="profile-text">经历、技能与已知缺口</label><textarea id="profile-text" name="profile" rows="17" required minlength="20">${esc(S.profile)}</textarea></div><div class="form-actions"><span class="hint">仅保存到本机；AI 分析时会发送相关资料至 Anthropic。</span><button class="button" type="submit">保存资料</button></div></form></section><section class="panel form-panel"><h2>AI 深度分析</h2><p class="hint">按需调用 Anthropic API。每次分析会发送个人资料、JD 与关联雇主记录，并产生 API 费用。</p><form id="ai-settings-form"><div class="field"><label for="api-key">Anthropic API 密钥 ${S.ai.configured?'· 已配置，留空保留':''}</label><input id="api-key" name="api_key" type="password" autocomplete="off" placeholder="${S.ai.configured?'已安全保存，不在页面回显':'sk-ant-…'}"></div><div class="field"><label for="ai-model">模型名称</label><input id="ai-model" name="model" value="${esc(S.ai.model)}" required></div><div class="form-actions"><label class="inline-check"><input name="clear_key" type="checkbox">清除已保存的密钥</label><button class="button" type="submit">保存 AI 设置</button></div></form><div class="settings-meta">密钥仅保存在本机 data/local.json，文件权限为仅当前用户可读写。AI 分析不会自动提交申请。</div></section></div><div><section class="panel form-panel"><h2>求职目标与日程</h2><p class="hint">扫描时区固定为 America/Los_Angeles。</p><form id="preferences-form"><div class="field"><label for="goal-select">当前求职目标</label><select id="goal-select" name="goal" style="width:100%">${['2027 毕业后全职','2027 暑期实习','实习和全职都看'].map(x=>`<option ${S.preferences.goal===x?'selected':''}>${x}</option>`).join('')}</select></div><div class="field"><label for="intern-region">美国实习地区偏好</label><select id="intern-region" name="intern_region" style="width:100%"><option value="california" ${S.preferences.intern_region==='california'?'selected':''}>优先加州，其他地区保留备选</option><option value="any_us" ${S.preferences.intern_region==='any_us'?'selected':''}>美国地区不限</option></select><p class="hint" style="margin-top:9px">美国全职：州别不限。国内岗位：单独管理，城市暂不限。</p></div><div class="label-row"><label for="daily-enabled">每天扫描新岗位<br><span class="hint">应用运行期间执行</span></label><label class="switch"><input id="daily-enabled" name="daily_enabled" type="checkbox" ${S.preferences.daily_enabled?'checked':''}><span></span></label></div><div class="field"><label for="daily-time">扫描时间 · 太平洋时间</label><input id="daily-time" name="daily_time" type="time" value="${esc(S.preferences.daily_time)}" required></div><button class="button" type="submit">保存目标与日程</button></form></section><section class="insight"><h3>${icon('lock')}属于你的本地工作台</h3><p>岗位、分析、备注与进度保存在当前项目的 SQLite 数据库。原来的下载目录与数据保持独立。</p><p>AI 未配置时，免费初筛、扫描、追踪和 CSV 导入都能使用。</p><div class="settings-meta">版本 ${esc(S.version)}<br>访问地址 127.0.0.1:8765</div></section></div></div>`;
}

function bindForms(){
 bindChinaForms();
 $('#job-type')?.addEventListener('change',e=>{usType=e.target.value;renderJobList();});
 const search=$('#job-search');if(search)search.addEventListener('input',()=>{filters.search=search.value;renderJobList();});
 for(const [sel,key] of [['#job-status','status'],['#job-min','min'],['#hide-conflicts','conflicts'],['#only-ai','ai']]){
  $(sel)?.addEventListener('change',e=>{filters[key]=e.target.type==='checkbox'?e.target.checked:key==='min'?Number(e.target.value):e.target.value;renderJobList();});
 }
 $('#match-form')?.addEventListener('submit',async e=>{e.preventDefault();const form=e.target;await submitting(form,async()=>{const r=await api('/api/jobs/add',Object.fromEntries(new FormData(form)));await refresh();toast(r.existing?'这个岗位已经收录，已打开原记录':'岗位已保存并完成免费初筛');await openDetail(r.id);});});
 for(const [sel,path,message] of [['#profile-form','/api/profile','资料已保存；请更新初筛'],['#ai-settings-form','/api/settings','AI 设置已保存'],['#preferences-form','/api/preferences','目标与日程已保存']]){
  $(sel)?.addEventListener('submit',async e=>{e.preventDefault();const form=e.target;await submitting(form,async()=>{const data=Object.fromEntries(new FormData(form));if(sel==='#ai-settings-form')data.clear_key=form.elements.clear_key.checked;if(sel==='#preferences-form'){data.daily_enabled=form.elements.daily_enabled.checked;data.intern_region=form.elements.intern_region.value;}await api(path,data);await refresh();toast(message);});});
 }
 $('#h1b-form')?.addEventListener('submit',async e=>{e.preventDefault();const form=e.target;await submitting(form,async()=>{const file=$('#h1b-file').files[0];if(!file)return;if(file.size>200*1024*1024)throw Error('请选择 200MB 以内的文件');const q=new URLSearchParams({kind:form.elements.kind.value,fy:form.elements.fy.value,filename:file.name});const response=await fetch('/api/h1b/import?'+q,{method:'POST',headers:{'X-JobScout-Token':S.csrf},body:file});const r=await response.json();if(!response.ok)throw Error(r.error);toast('上传完成，后台正在导入');await refresh(false);poll();});});
 $('#company-form')?.addEventListener('submit',async e=>{e.preventDefault();await submitting(e.target,async()=>{const rows=[...document.querySelectorAll('.company-editor')].map(el=>Object.fromEntries([...el.querySelectorAll('[name]')].map(x=>[x.name,x.value]))).filter(c=>c.name||c.slug);await api('/api/companies',{companies:rows});$('#detail-dialog').close();await refresh();toast('公司列表已保存，扫描后可验证接口');});});
}
function renderJobList(){const list=filteredJobs();$('#job-list').innerHTML=list.length?list.map(jobRow).join(''):empty('没有符合筛选条件的岗位。',button('重置筛选','reset-filters','secondary'));$('#result-count').textContent=list.length+' 个岗位';}
async function submitting(form,fn){const b=form.querySelector('[type=submit]');if(b.disabled)return;b.disabled=true;try{await fn();}catch(e){toast(e.message,true);}finally{b.disabled=false;}}

async function openDetail(id){
 const dialog=$('#detail-dialog');detailJob=null;detailTab='analysis';$('#detail-content').innerHTML='<div class="loading"><div class="spinner"></div>读取岗位详情…</div>';if(!dialog.open)dialog.showModal();
 try{const job=await api('/api/jobs/'+enc(id));if(!dialog.open)return;detailJob=job;renderDetail();}catch(e){dialog.close();toast(e.message,true);}
}
function screenEvidence(j){const x=j.screen;return `<section class="side-card screen-evidence"><h3>逐项筛选依据</h3><p>${esc(x.geo.label)} · ${esc(x.direction.label)} · ${esc(x.experience.label)}</p>${j.market!=='cn'?`<p><strong>${esc(x.authorization.label)}</strong><br>${esc(x.authorization.evidence)}<br>E-Verify：${esc(x.authorization.everify)}；I-983：${esc(x.authorization.i983)}</p>`:''}<p>${x.conflicts.length?'不符合：'+esc(x.conflicts.join('、')):'尚未检测到明确冲突；仍需核对完整 JD'}</p></section>`;}
function renderDetail(){
 const j=detailJob;if(!j)return;const a=j.analysis;
 $('#detail-content').innerHTML=`<div class="detail-header"><div class="detail-header-top"><span class="eyebrow" style="margin:0">OPPORTUNITY / ${j.method==='llm'?'AI ANALYSIS':'RULE-BASED SCREENING'}</span><button class="icon-button" data-action="close-dialog" aria-label="关闭岗位详情">${icon('close')}</button></div><div class="detail-header-title">${companyAvatar(j.company)}<div><h2>${esc(j.title)}</h2><p>${esc(j.company)} &nbsp; · &nbsp; ${esc(j.location||'地点待确认')}</p></div></div><div class="detail-tabs">${[['analysis','匹配分析'],['evidence','要求与证据'],['jd','JD 原文'],['employer',j.market==='cn'?'校招提醒':'雇主记录']].map(([key,label])=>`<button data-detail-tab="${key}" class="${detailTab===key?'active':''}">${label}</button>`).join('')}</div></div><div class="detail-body"><div>${j.screen?screenEvidence(j):''}${j.stale?'<div class="notice">个人资料或求职目标已变化，此分析需要更新。</div>':''}${detailMain(j,a)}</div><aside class="detail-side"><section class="side-card"><h3>我的下一步</h3><label for="detail-status">投递状态 · 仅记录，不提交申请</label><select id="detail-status">${Object.entries(statusNames).map(([k,v])=>`<option value="${k}" ${k===j.status?'selected':''}>${v}</option>`).join('')}</select>${safeLink(j.url)?`<a class="button secondary" href="${safeLink(j.url)}" target="_blank" rel="noopener">${icon('external')}打开官网岗位</a>`:'<p style="margin-top:10px">这个岗位尚未添加原文链接。</p>'}${button('AI 深度分析','ai-detail','', 'spark',S.task.running?'disabled':'')}${button('更新免费初筛','rescore-detail','secondary','refresh',S.task.running?'disabled':'')}<p style="margin-top:10px">AI 分析将发送你的资料及 JD 至 Anthropic，并产生 API 费用。</p></section><section class="side-card"><h3>推荐简历版本</h3><span class="tag green">${esc(a.resume||'Technical')}</span><p style="margin-top:9px">用于方向参考，投递前核对简历内容与岗位要求。</p></section><section class="side-card"><label for="detail-notes">我的备注</label><textarea id="detail-notes" placeholder="记录投递日期、联系人或待确认问题…">${esc(j.notes)}</textarea>${button('保存备注','save-notes','secondary')}<p id="note-state" style="margin-top:7px"></p></section><p class="hint" style="padding:0 5px">首次发现 ${time(j.first_seen)}<br>最近扫描 ${time(j.last_seen)}<br>分析时间 ${time(j.scored_at,true)}</p></aside></div>`;
 $('#detail-status').addEventListener('change',async e=>{try{await api('/api/jobs/update',{id:j.id,status:e.target.value});j.status=e.target.value;await refresh(false);toast('进度已保存');if(page==='tracker'||page==='china')render();}catch(error){toast(error.message,true);}});
}
function detailMain(j,a){
 if(detailTab==='jd')return `<div class="detail-section"><h3>${icon('file')}岗位描述原文</h3><div class="detail-jd">${esc(j.description||'暂无岗位描述')}</div></div>`;
 if(detailTab==='employer'&&j.market==='cn')return '<div class="notice green">国内岗位使用中文简历，独立判断毕业批次、到岗时间、实习天数及经验要求；不使用 H-1B 记录评分。</div>';
 if(detailTab==='employer')return `<div class="detail-section"><h3>${icon('shield')}雇主历史记录</h3><div class="notice">雇主历史记录不代表当前岗位提供 sponsorship。LCA 与 USCIS 批准结果分别展示。</div>${j.h1b?`<section class="panel form-panel"><p class="hint">匹配到的法人：${esc(j.h1b.matched)}<br>匹配方式：规范化名称精确匹配</p><div style="margin-top:16px">${j.h1b.rows.map(r=>`<div class="tracking-row"><span>${r.source==='lca'?'DOL LCA 认证职位':'USCIS 批准'}<br><small>FY${esc(r.fiscal_year)}</small></span><b>${r.count.toLocaleString()}</b></div>`).join('')}</div></section>`:empty('尚无匹配记录。请先导入官方数据，并核对公司法人别名。',button('前往 H-1B 数据','go-h1b','secondary'))}</div>`;
 if(detailTab==='evidence')return `<div class="detail-section"><h3>${icon('file')}JD 要求与你的经历</h3><p class="hint" style="margin-bottom:15px">${j.method==='llm'?'由 AI 对照 JD 与个人资料生成，仍需人工复核。':'当前为技能关键词与资料原句对照；完整要求证据分析需启用 AI。'}</p>${a.evidence?.length?a.evidence.map(e=>`<div class="evidence-row"><div class="evidence-row-top">${esc(e.req)}<span class="tag ${e.strength==='无'?'amber':'green'}">${esc(e.strength)}证据</span></div><p>${esc(e.evidence)}</p></div>`).join(''):empty('尚无可提取的证据，请确认 JD 内容完整。')}</div>`;
 const list=(arr)=>arr?.length?`<ul>${arr.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p>暂无记录</p>';
 return `<section class="panel analysis-summary"><div class="score-ring"><b>${j.score??'—'}</b><small>${j.method==='llm'?'AI 匹配分':'初筛参考'}</small></div><div><h3>${esc(a.verdict||'待分析')}</h3><p>${esc(a.summary||'请更新初筛后查看分析。')}</p></div></section>${j.method!=='llm'?'<div class="notice green">当前使用免费规则初筛。关键词覆盖不等于真实匹配度，也不代表录用概率。</div>':''}${a.fit_reasons?.length?`<section class="detail-section"><h3>${icon('spark')}与你的简历相关在哪里</h3>${list(a.fit_reasons)}</section>`:''}<section class="detail-section"><h3>${icon('shield')}硬性条件与待确认项</h3>${(a.hard||[]).map(h=>`<div class="hard-item"><span class="tag ${h.status==='符合'?'green':h.status==='不符合'?'red':'amber'}">${esc(h.status)}</span><div><strong>${esc(h.item)}</strong><p>${esc(h.note)}</p></div></div>`).join('')||'<p>暂无硬性条件分析</p>'}</section><section class="detail-section"><div class="result-grid"><div class="result-box"><h3>已找到的技能证据</h3>${a.matched?.length?a.matched.map(x=>`<span class="tag green">${esc(x)}</span>`).join(''):'<p>暂无</p>'}</div><div class="result-box"><h3>尚缺少证据</h3>${a.gaps?.length?a.gaps.map(x=>`<span class="tag amber">${esc(x)}</span>`).join(''):'<p>暂无</p>'}</div></div></section>${Object.keys(a.dims||{}).length?`<section class="detail-section"><h3>分项参考</h3>${Object.entries(a.dims).map(([name,value])=>`<div class="dim"><span>${esc(name)}</span><div class="bar"><i style="width:${Math.max(0,Math.min(100,Number(value)||0))}%"></i></div><b>${Math.max(0,Math.min(100,Number(value)||0))}</b></div>`).join('')}</section>`:''}${a.risks?.length?`<section class="detail-section"><h3>${icon('info')}风险与待确认问题</h3>${list(a.risks)}</section>`:''}${a.edits?.length?`<section class="detail-section"><h3>${icon('file')}简历修改建议</h3>${list(a.edits)}</section>`:''}${a.opening?`<section class="detail-section"><h3>Cover letter 开头建议</h3><div class="detail-jd">${esc(a.opening)}</div></section>`:''}`;
}

function companyEditor(){
 detailJob=null;const dialog=$('#detail-dialog');$('#detail-content').innerHTML=`<div class="detail-header"><div class="detail-header-top"><h2>管理目标公司</h2><button class="icon-button" data-action="close-dialog" aria-label="关闭">${icon('close')}</button></div><p>填写真实招聘页里的 ATS 标识；法人别名用分号分隔。</p></div><section class="form-panel"><form id="company-form"><div id="company-rows">${S.companies.map(c=>companyEditorRow(c)).join('')}</div><div class="form-actions">${button('添加一家公司','add-company-row','secondary','plus')}<button class="button" type="submit">保存全部公司</button></div><div class="field" style="margin-top:28px"><label for="company-bulk">批量添加 · 每行：公司名称,ATS,slug,法人别名（选填）</label><textarea id="company-bulk" rows="4" placeholder="Example,greenhouse,example,Example Inc."></textarea><p class="hint" style="margin:8px 0">ATS 支持 greenhouse、lever、ashby；适合粘贴 140 家以上的目标清单。</p>${button('加入上方列表','bulk-companies','secondary','plus')}</div></form></section>`;if(!dialog.open)dialog.showModal();bindForms();
}
function companyEditorRow(c={name:'',ats:'greenhouse',slug:'',h1b_names:[]}){return `<div class="company-editor"><input name="name" aria-label="公司名称" placeholder="公司名称" value="${esc(c.name)}" required><select name="ats" aria-label="ATS 类型">${['greenhouse','lever','ashby'].map(a=>`<option ${a===c.ats?'selected':''}>${a}</option>`).join('')}</select><input name="slug" aria-label="招聘页 slug" placeholder="slug" value="${esc(c.slug)}" required pattern="[a-zA-Z0-9_-]+"><div class="wide" style="display:flex;gap:10px"><input name="h1b_names" aria-label="法人别名" placeholder="法人名称，多个用分号分隔" value="${esc(Array.isArray(c.h1b_names)?c.h1b_names.join('; '):c.h1b_names)}"><button class="icon-button" type="button" data-action="remove-company-row" aria-label="移除本行">${icon('close')}</button></div></div>`;}

function updateTask(task){
 const banner=$('#task-banner');banner.hidden=!task.running;
 if(task.running){banner.innerHTML=`<div class="spinner"></div><div>${esc(task.message)}${task.total?` · ${task.done}/${task.total}`:''}</div>`;if(!pollTimer)poll();}
}
function poll(){
 if(pollTimer)return;wasRunning=true;
 const tick=async()=>{
  try{const task=await api('/api/task');S.task=task;updateTask(task);if(!task.running){clearTimeout(pollTimer);pollTimer=null;const openId=$('#detail-dialog').open?detailJob?.id:null;await refresh();if(openId){detailJob=await api('/api/jobs/'+enc(openId));renderDetail();}toast(task.message,task.state==='failed'||task.state==='partial');return;}}
  catch(e){toast('连接中断，正在尝试重新连接',true);}
  pollTimer=setTimeout(tick,1800);
 };
 pollTimer=setTimeout(tick,1200);
}
async function startTask(path,data={}){await api(path,data);await refresh(false);poll();toast('任务已开始，可以继续浏览工作台');if(page==='scans')render();}

document.addEventListener('click',async e=>{
 const nav=e.target.closest('[data-page]');if(nav){go(nav.dataset.page);return;}
 const detailButton=e.target.closest('[data-detail-tab]');if(detailButton){detailTab=detailButton.dataset.detailTab;renderDetail();return;}
 const company=e.target.closest('[data-company-jobs]');if(company){filters={search:company.dataset.companyJobs,status:'all',min:50,conflicts:true,ai:false};go('jobs');return;}
 if(e.target.closest('select,input,textarea,a'))return;
 const job=e.target.closest('[data-job]');if(job){await openDetail(job.dataset.job);return;}
 const actionButton=e.target.closest('[data-action]');if(!actionButton)return;const action=actionButton.dataset.action;
 try{
  if(action.startsWith('go-')){go(action.slice(3));return;}
  if(action==='close-dialog'){$('#detail-dialog').close();return;}
  if(action==='reset-filters'){filters={search:'',status:'active',min:50,conflicts:true,ai:false};render();return;}
  if(action==='scan'){await startTask('/api/scan');return;}
  if(action==='scan-china'){await startTask('/api/china/scan');return;}
  if(action==='rescore'||action==='rescore-detail'){await startTask('/api/rescore');return;}
  if(action==='save-notes'){await api('/api/jobs/update',{id:detailJob.id,notes:$('#detail-notes').value});detailJob.notes=$('#detail-notes').value;$('#note-state').textContent='已保存到本机';toast('备注已保存');await refresh(false);return;}
  if(action==='ai-detail'){
   if(!S.ai.configured){$('#detail-dialog').close();go('settings');toast('先配置 Anthropic API 密钥，再开始 AI 分析');return;}
   await startTask('/api/ai',{ids:[detailJob.id]});return;
  }
  if(action==='company-editor'){companyEditor();return;}
  if(action==='add-company-row'){$('#company-rows').insertAdjacentHTML('beforeend',companyEditorRow());return;}
  if(action==='remove-company-row'){actionButton.closest('.company-editor').remove();return;}
  if(action==='bulk-companies'){
   const lines=$('#company-bulk').value.trim().split('\n').filter(Boolean);
   const rows=lines.map(line=>{const parts=line.includes('\t')?line.split('\t'):line.split(',');if(parts.length<3)throw Error('每行至少需要：公司名称,ATS,slug');const [name,ats,slug,...aliases]=parts.map(p=>p.trim());if(!['greenhouse','lever','ashby'].includes(ats)||!/^[-\w]+$/.test(slug))throw Error('批量列表中有无效 ATS 或 slug');return {name,ats,slug,h1b_names:aliases.join(',')};});
   $('#company-rows').insertAdjacentHTML('beforeend',rows.map(companyEditorRow).join(''));$('#company-bulk').value='';toast(`已加入 ${rows.length} 行，点击保存后生效`);return;
  }
 }catch(error){toast(error.message,true);}
});
document.addEventListener('change',async e=>{const id=e.target.dataset.jobStatus;if(!id)return;try{await api('/api/jobs/update',{id,status:e.target.value});await refresh();toast('进度已保存');}catch(error){toast(error.message,true);}});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('[data-job]')){e.preventDefault();openDetail(e.target.dataset.job);}});
$('#detail-dialog').addEventListener('click',e=>{if(e.target===$('#detail-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('#detail-dialog').addEventListener('close',()=>{detailJob=null;});
$('#refresh').addEventListener('click',async()=>{try{await refresh();toast('数据已刷新');}catch(e){toast(e.message,true);}});
$('#add-global').addEventListener('click',()=>{if(page==='china'){if(!$('#cn-manual-intake')){cnTab='jobs';render();}$('#cn-manual-intake').open=true;$('#cn-description')?.focus();}else go('match');});
window.addEventListener('hashchange',()=>{const next=location.hash.slice(1);if(labels[next]&&next!==page){page=next;render();}});
page=labels[location.hash.slice(1)]?location.hash.slice(1):'overview';
if(location.protocol!=='file:')connection.retry();
window.addEventListener('online',()=>connection.retry());
document.addEventListener('click',e=>{if(e.target.closest('[data-action="reconnect"]'))connection.retry();});


function cnAvailable(j){return j.is_open!==0&&!j.hard_conflict&&j.screen?.geo.country==='cn'&&!['expired','conflict'].includes(j.deadline_info?.status);}
function cnRecommended(j){return cnAvailable(j)&&['priority','related'].includes(j.match_tier)&&(j.match_tier==='priority'?j.score>=55:j.score>=65);}
function deadlineView(){
 const eligible=chinaJobs().filter(cnRecommended), known=eligible.filter(j=>j.deadline_info?.date&&j.deadline_info.days_left>=0).sort((a,b)=>a.deadline_info.date.localeCompare(b.deadline_info.date));
 const list=cnDeadline==='unknown'?eligible.filter(j=>j.deadline_info?.status==='unknown'):cnDeadline==='conflict'?chinaJobs().filter(j=>j.deadline_info?.status==='conflict'):known.filter(j=>cnDeadline==='all'||j.deadline_info.days_left<=Number(cnDeadline));
 return `<div class="notice green">国内截止按北京时间（UTC+8）计算。只有日期时，具体截止时刻需点开官网确认。未公布日期不代表滚动招聘；日期冲突单列复核。推荐仍需核对专业、毕业批次和到岗安排。</div><div class="toolbar"><select id="cn-deadline" aria-label="截止日期范围">${[['3','未来 3 天'],['7','未来 7 天'],['30','未来 30 天'],['all','全部已知日期'],['unknown','未公布截止日期'],['conflict','日期冲突需核对']].map(([v,t])=>`<option value="${v}" ${cnDeadline===v?'selected':''}>${t}</option>`).join('')}</select></div><section class="panel"><div class="panel-head"><h2>截止优先清单</h2><span class="tag">${list.length} 个</span></div>${list.length?list.map(j=>jobRow(j)+(j.deadline_note?`<div class="panel-note">${esc(j.deadline_note)}</div>`:'')).join(''):empty('该范围没有符合简历初筛的岗位。可切换日期范围，或查看平台线索。')}</section>`;
}
function intelligenceView(){
 const intel=S.recruitment_intelligence||{};
 return `<div class="notice green">官网职位自动更新；以下平台提供发现线索的入口。第三方日期不进入已确认截止清单，线索不计入采集岗位数。最近人工核查：${esc(intel.checked_at||'尚无')}。小红书搜索需要登录，本次未读取笔记。</div><section class="panel"><div class="panel-head"><h2>近期核查与待确认线索</h2></div>${(intel.leads||[]).map(l=>`<article class="intel-lead"><div class="tags"><span class="tag ${l.verification==='platform_lead'?'amber':'green'}">${esc(l.source_type)}</span><span class="tag">${l.deadline?`${l.verification==='platform_lead'?'平台称截止':'截止'} ${esc(l.deadline)}`:'截止未确认'}</span></div><h3>${esc(l.company)} · ${esc(l.title)}</h3><p class="hint">${esc(l.note)}</p><div class="tags"><a class="text-link" href="${safeLink(l.source_url)}" target="_blank" rel="noopener">查看来源 ↗</a><a class="text-link" href="${safeLink(l.official_url)}" target="_blank" rel="noopener">企业官网 ↗</a></div></article>`).join('')}</section><h2 class="intel-heading">跨平台发现入口</h2><div class="china-portals">${(intel.platforms||[]).map(p=>`<section class="panel company-card"><h3>${esc(p.name)}</h3><p class="hint">${esc(p.note)}</p><a class="text-link" href="${safeLink(p.url)}" target="_blank" rel="noopener">打开平台 ↗</a></section>`).join('')}</div>`;
}
function filteredChinaJobs(){
 const ranks={priority:0,related:1,stretch:2,low:3};
 return sortBoard(chinaJobs().filter(j=>passesBoard(j,'cn')).filter(j=>(!cnSearch||(j.company+' '+j.title+' '+j.location).toLowerCase().includes(cnSearch.toLowerCase()))&&(cnSector==='all'||(j.sector||'').includes(cnSector))&&(cnTier==='all'||cnTier==='recommended'&&cnRecommended(j)||j.match_tier===cnTier&&cnAvailable(j))).sort((a,b)=>(ranks[a.match_tier]??1)-(ranks[b.match_tier]??1)||( /银行|证券|公募|私募|金融科技/.test(a.sector||'')?0:1)-( /银行|证券|公募|私募|金融科技/.test(b.sector||'')?0:1)||(b.score||0)-(a.score||0)),'cn');
}
function china(){
 const all=chinaJobs(),list=filteredChinaJobs(),sources=S.china_sources||[],scan=S.china_scan;
 const recommended=all.filter(cnRecommended);
 const tracked=all.filter(j=>!['new','ignored'].includes(j.status));
 const form=`<section class="panel form-panel"><h2>补充国内岗位 JD</h2><p class="hint">自动采集之外，也可补充内推或其他渠道的岗位，使用同一份中文简历匹配。</p><form id="china-job-form"><input name="market" type="hidden" value="cn"><div class="field"><label for="cn-company">公司 *</label><input id="cn-company" name="company" required placeholder="例如 招商基金"></div><div class="field"><label for="cn-title">职位 *</label><input id="cn-title" name="title" required placeholder="例如 数据分析岗 / 风控策略"></div><div class="field"><label for="cn-location">国内城市</label><input id="cn-location" name="location" placeholder="例如 杭州 / 上海 / 深圳"></div><div class="field"><label for="cn-url">岗位官网链接</label><input id="cn-url" type="url" name="url" placeholder="https://…"></div><div class="field"><label for="cn-description">JD 全文 *</label><textarea id="cn-description" name="description" required minlength="80" rows="8" placeholder="粘贴职责、要求、毕业批次、到岗时间和实习天数，至少 80 字。"></textarea></div><button class="button" type="submit">${icon('spark')}保存并匹配中文简历</button></form></section>`;
 let body='';
 if(cnTab==='deadlines')body=deadlineView();
 else if(cnTab==='intel')body=intelligenceView();
 else if(cnTab==='sources')body=`<div class="notice green">每天随工作台扫描更新，也可点击“自动采集国内岗位”。接口失败或需要人工访问的渠道单独显示，不计入成功采集数。${scan?`最近自动采集成功 ${scan.companies||0} 家，浏览器部分收录 ${scan.browser_snapshots||0} 家；新增 ${scan.new||0} 个相关岗位。`:''}</div><div class="china-portals">${sources.map(c=>`<section class="panel company-card"><div class="company-card-top">${companyAvatar(c.name)}<div><h3>${esc(c.name)}</h3><p>${esc(c.sector)}</p></div></div><div class="tags"><span class="tag ${c.health?.ok?'green':c.adapter==='manual'?'amber':'red'}">${c.health?.status==='browser_snapshot'?'浏览器核实（部分）':c.health?.ok?'最近采集成功':c.health?.status==='manual'||c.adapter==='manual'?'人工入口':c.health?'读取失败':'待首次采集'}</span>${c.health?.ok?`<span class="tag">相关 ${c.health.kept||0} 个</span>${c.health.complete===false?'<span class="tag amber">部分采集</span>':''}`:''}</div><p class="hint" style="margin-top:10px">${esc(c.health?.error||c.reason||(c.health?.checked_at?'最近读取 '+time(c.health.checked_at,true):'等待验证公开职位数据'))}</p><div class="company-card-bottom"><a href="${safeLink(c.url)}" target="_blank" rel="noopener">招聘官网 ↗</a><button data-cn-company="${esc(c.name)}">补充 JD</button></div></section>`).join('')}</div>`;
 else if(cnTab==='portals')body=`<div class="notice green">以下展示官网实际收录的相关岗位。点击“查看岗位”会清除该板块的额外筛选，显示该公司全部收录结果；经验、毕业时间等冲突仍会标注。采集失败不代表企业没有招聘。</div><div class="china-portals">${(S.china_portals||[]).map(c=>{const ids=c.source_ids||[],rows=all.filter(j=>ids.includes(j.source_id)),feeds=sources.filter(x=>ids.includes(x.id)),ok=feeds.some(x=>x.health?.ok),snapshot=feeds.some(x=>x.health?.status==='browser_snapshot'),error=feeds.map(x=>x.health?.error||x.reason).filter(Boolean).join('；');return `<section class="panel company-card"><div class="company-card-top">${companyAvatar(c.name)}<div><h3>${esc(c.name)}</h3><p>${esc(c.category)}</p></div></div><div class="tags"><span class="tag ${ok?'green':'amber'}">${snapshot?'浏览器核实（部分）':ok?'官网自动采集':'待完成接入'}</span><span class="tag">已收录 ${rows.length} 个</span><span class="tag green">推荐 / 备选 ${rows.filter(cnRecommended).length} 个</span></div><p class="hint" style="margin-top:14px">${esc(snapshot?'已收录完整 JD，部分覆盖；未接通每日接口更新。核实于 '+time(feeds.find(x=>x.health?.snapshot_at)?.health.snapshot_at,true):ok?'已读取职位详情；实际资格以 JD 为准。':error||'公开查询尚未完成验证。')}</p><div class="company-card-bottom"><a href="${safeLink(c.url)}" target="_blank" rel="noopener">招聘官网 ↗</a><button data-cn-view-company="${esc(c.name)}">查看岗位（${rows.length}）</button></div></section>`;}).join('')}</div>`;
 else if(cnTab==='tracker')body=`<section class="panel"><div class="panel-head"><h2>国内投递进度</h2><a class="text-link" href="/api/export?market=cn">导出国内记录 ${icon('download')}</a></div>${tracked.length?tracked.map(j=>`<div class="cn-tracked"><div>${jobRow(j)}</div><select data-job-status="${esc(j.id)}" aria-label="${esc(j.company)} 国内投递状态">${Object.entries(statusNames).map(([k,v])=>`<option value="${k}" ${j.status===k?'selected':''}>${v}</option>`).join('')}</select></div>`).join(''):empty('还没有国内投递记录。<br>打开采集到的岗位，读完 JD 后加入“待投递”，即可在这里跟进。')}</section>`;
 else body=`<div class="notice green">按本机候选人资料中的技能、项目和经验进行初筛。互联网与金融均可选择；量化与算法研发单列挑战方向。<br>默认显示中国大陆岗位；美国的地点与授权偏好不会影响这里。</div><div class="toolbar"><div class="search">${icon('search')}<input id="cn-search" aria-label="搜索国内岗位" placeholder="搜索公司、职位或城市" value="${esc(cnSearch)}"></div><select id="cn-sector" aria-label="国内行业">${[['all','全部行业'],['银行','银行'],['证券','证券公司'],['公募基金','公募基金'],['私募基金','私募基金'],['互联网','互联网 / 金融科技']].map(([k,v])=>`<option value="${k}" ${cnSector===k?'selected':''}>${v}</option>`).join('')}</select><select id="cn-tier" aria-label="国内匹配方向">${[['recommended','推荐与相关备选'],['priority','直接匹配方向'],['related','相关备选'],['stretch','挑战岗位'],['all','全部含待核对 / 下架']].map(([k,v])=>`<option value="${k}" ${cnTier===k?'selected':''}>${v}</option>`).join('')}</select></div>${advancedFilters('cn')}<section class="panel"><div class="panel-head"><h2>按简历筛选的国内岗位</h2><span class="tag" id="cn-filter-count">${list.length} / ${all.length} 个</span></div><div id="cn-job-list">${list.length?list.map(jobRow).join(''):empty('当前筛选下没有岗位。<br>可切换行业或查看全部，也可手动补充 JD。',button('自动采集国内岗位','scan-china','secondary','refresh'))}</div></section>`;
 return heading('中国求职，金融与互联网两条线。','数据 / BI、产品商业分析、金融风控与经济研究；城市、招聘通道与实习出勤单独核对。','CHINA MAINLAND',button('自动采集国内岗位','scan-china','','refresh',S.task.running?'disabled':''))+boardSwitch('cn')+
 `<section class="metrics">${metric('国内收录岗位',all.length,'自动采集 + 手动补充','briefcase')}${metric('推荐与相关备选',recommended.length,'排除已知条件冲突及下架','spark')}${metric('已投递 / 后续流程',all.filter(j=>['applied','interview','offer','rejected'].includes(j.status)).length,'国内记录独立统计','send')}${metric('采集成功 / 目标',`${scan?.companies??'—'} / ${sources.length}`,'渠道状态分别展示','scan')}</section><div class="filter-tabs">${[['jobs','按简历推荐'],['deadlines','近期截止'],['intel','平台线索'],['tracker','国内投递进度'],['sources','采集源与状态'],['portals','重点公司岗位'],['profile','中文简历资料']].map(([k,label])=>`<button class="filter-tab ${cnTab===k?'active':''}" data-cn-tab="${k}">${label}</button>`).join('')}</div>`+
 (cnTab==='profile'?`<section class="panel form-panel"><h2>中文候选人资料</h2><p class="hint">独立用于国内匹配，不与美国授权规则混用。电话与邮箱未加入分析资料。</p><form id="china-profile-form"><input name="market" type="hidden" value="cn"><div class="field"><label for="cn-profile-text">中文简历资料</label><textarea id="cn-profile-text" name="profile" rows="22" minlength="20" required>${esc(S.profile_cn||'')}</textarea></div><button class="button" type="submit">保存中文资料</button></form></section>`:`<div>${body}<details class="panel manual-intake" id="cn-manual-intake"><summary>补充内推或其他渠道的岗位 JD</summary>${form}</details></div>`);
}
function updateChinaList(){const list=filteredChinaJobs();$('#cn-job-list').innerHTML=list.length?list.map(jobRow).join(''):empty('没有符合当前筛选条件的国内岗位。');$('#cn-filter-count').textContent=list.length+' / '+chinaJobs().length+' 个';}

function bindChinaForms(){
 $('#cn-deadline')?.addEventListener('change',e=>{cnDeadline=e.target.value;render();});
 $('#china-job-form')?.addEventListener('submit',async e=>{e.preventDefault();await submitting(e.target,async()=>{const r=await api('/api/jobs/add',Object.fromEntries(new FormData(e.target)));await refresh();toast(r.existing?'已打开国内岗位原记录':'国内岗位已保存，中文简历初筛完成');await openDetail(r.id);});});
 $('#china-profile-form')?.addEventListener('submit',async e=>{e.preventDefault();await submitting(e.target,async()=>{await api('/api/profile',Object.fromEntries(new FormData(e.target)));await refresh();toast('中文资料已保存，请更新初筛');});});
 $('#cn-search')?.addEventListener('input',e=>{cnSearch=e.target.value;updateChinaList();});
 $('#cn-sector')?.addEventListener('change',e=>{cnSector=e.target.value;updateChinaList();});
 $('#cn-tier')?.addEventListener('change',e=>{cnTier=e.target.value;updateChinaList();});
}
// These controls only navigate locally; no application is submitted.
 document.addEventListener('click',e=>{
  const tab=e.target.closest('[data-cn-tab]');if(tab){cnTab=tab.dataset.cnTab;render();return;}
  const company=e.target.closest('[data-cn-view-company]');if(company){cnTab='jobs';cnSearch=company.dataset.cnViewCompany;cnSector='all';cnTier='all';for(const key of Object.keys(boardFilters.cn)){if(key!=='sort')boardFilters.cn[key]='all';}render();return;}
  const c=e.target.closest('[data-cn-company]');if(c){$('#cn-manual-intake').open=true;$('#cn-company').value=c.dataset.cnCompany;$('#cn-title').focus();return;}
  if(e.target.closest('[data-action="cn-portals"]')){cnTab='portals';render();}
 });

// Each market owns its filters; changing them never alters an application record.
document.addEventListener('change',e=>{const m=e.target.dataset.board,k=e.target.dataset.facet;if(!m||!k)return;boardFilters[m][k]=e.target.value;if(m==='us')renderJobList();else updateChinaList();});
