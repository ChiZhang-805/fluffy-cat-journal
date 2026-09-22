/* 回顾纯逻辑测试。隔离本机存储和网络，不访问真实账户或模型。 */
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
/** 输入：无。输出：实际模块和隔离存储。功能：验证交付代码而不是重新实现业务逻辑。 */
function fixture() {
 const storage=new Map(), ctx=vm.createContext({Date,Intl,Math,Map,Set,Object,Number,String,Array,JSON,Error,TypeError,Promise,AbortController,DOMException,URL,setTimeout,clearTimeout,console,
 localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,String(v))}});
 vm.runInContext('const __fluffyModules={};',ctx);
 for(const name of ['model','sleep-time','catalog','journal-store','review-data','review-conversation']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/'+name+'.js'),'utf8'),ctx);
 return {get:n=>vm.runInContext(`__fluffyModules['${n}.js']`,ctx),storage};
}
const f=fixture(),D=f.get('review-data'),T=f.get('review-conversation');
/** 输入：ID/类别/字段/日期。输出：测试记录。功能：所有样例仅在测试中生成，不进入用户产物。 */
function record(id,category,data,date='2026-09-22',extra={}) { return {id,category,data,createdAt:date+'T12:00:00',...extra}; }
/** 输入：任意对象。输出：JSON对象。功能：跨VM数据比较不检查原型。 */
function plain(x) { return JSON.parse(JSON.stringify(x)); }
test('缺失不是零：空白周7天均为null',()=>{const v=D.build('sport','2026-09-22',[]);assert.equal(v.week.length,7);assert.ok(v.week.every(d=>d.score===null&&d.count===0));});
test('日历跨年正确',()=>assert.equal(D.shiftDate('2026-01-03',-6),'2025-12-28'));
test('合并同日运动且排除重复ID未来和别的板块',()=>{const a=record('1','sport',{activity:'跑步',durationMinutes:10,notes:'a'});const b=record('2','sport',{activity:'力量',durationMinutes:5,notes:'b'});const v=D.build('sport','2026-09-22',[a,a,b,record('3','sport',{durationMinutes:800},'2026-09-23'),record('4','food',{calories:700})]);assert.equal(v.today.value,15);assert.equal(v.today.score,50);assert.equal(v.today.count,2);});
test('目标超额不超过100分',()=>assert.equal(D.ratio(999,30),100));
test('实际0与缺失不同',()=>{assert.equal(D.number(0),0);for(const x of [null,'',NaN,Infinity,-1])assert.equal(D.number(x),null);});
test('未知目标和非法目标恢复公开默认值',()=>assert.deepEqual(plain(D.goals({sport:-5,sleep:100})),{sport:30,sleep:8}));
test('睡眠取醒来日期而不是提交日期',()=>{const r=record('s','sleep',{recordDate:'2026-09-21',hours:8,quality:'还好',bedtime:'23:00',wakeTime:'07:00'});const v=D.build('sleep','2026-09-22',[r]);assert.equal(v.today.count,0);assert.equal(v.week[5].score,100);});
test('同日睡眠保留各段并合并重叠区间，匹配分不称睡眠质量',()=>{const a=record('a','sleep',{bedtime:'01:00',wakeTime:'07:00'},'2026-09-22'),b={...record('b','sleep',{bedtime:'23:00',wakeTime:'07:00'}),createdAt:'2026-09-22T13:00:00'};const d=D.build('sleep','2026-09-22',[a,b]).today;assert.equal(d.value,8);assert.equal(d.sleep.overlaps,true);assert.equal(d.count,2);assert.equal(d.scoreKind,'sleepGoal');});
test('专注只用实际计时而不是预计分钟',()=>{const a=record('f','focus',{task:'阅读',durationMinutes:30},undefined,{focus:{elapsedMs:12*60000,restMs:4*60000}});const d=D.build('focus','2026-09-22',[a]).today;assert.equal(d.score,40);assert.equal(d.value,12);assert.equal(d.restMinutes,4);});
test('专注只有计划则不产生实际分数',()=>{assert.equal(D.build('focus','2026-09-22',[record('f','focus',{durationMinutes:60})]).today.score,null);});
test('饮食按资料覆盖率不是卡路里达标',()=>{const r=record('food','food',{meal:'午餐',foods:'饭',portion:'一份',calories:500,protein:20,carbs:60,fat:12});const d=D.build('food','2026-09-22',[r]).today;assert.equal(d.score,100);assert.equal(d.scoreKind,'coverage');});
test('没有宏量数据时返回null',()=>{const r=record('food','food',{meal:'午餐',foods:'饭'});const d=D.build('food','2026-09-22',[r]).today;assert.equal(d.value,null);assert.equal(d.macros.protein,null);});
test('面部只评记录完整度，不判疲劳',()=>{const d=D.build('face','2026-09-22',[record('a','face',{feeling:'困',eyeArea:'眼袋',skinAppearance:'光线偏暗'})]).today;assert.equal(d.score,100);assert.equal(d.scoreKind,'observation');});
test('情绪保留混合感受，不生成分数',()=>{const text='有点失落，也松了一口气';const d=D.build('mood','2026-09-22',[record('m','mood',{mood:text,reason:'忙完了'})]).today;assert.equal(d.score,null);assert.equal(d.text,text);});
test('构建回顾不改变源记录',()=>{const source=[record('a','sport',{durationMinutes:10,activity:'跑步',notes:'记录'})],before=JSON.stringify(source);D.build('sport','2026-09-22',source);assert.equal(JSON.stringify(source),before);});
test('上下文只含当前类别最近7天，没有ID和其他类别',()=>{const v=D.build('sport','2026-09-22',[record('secret-id','sport',{durationMinutes:20,activity:'跑步',notes:'今日'}),record('face-id','face',{feeling:'secret face'})]);const text=JSON.stringify(D.context(v));assert.ok(!text.includes('secret-id'));assert.ok(!text.includes('secret face'));assert.ok(text.includes('今日'));});
test('负值与无穷不会进入分享数字',()=>{assert.equal(D.number(-1),null);assert.equal(D.format(23.8999),'23.9');assert.equal(D.format(null),'—');});
for(const lang of ['zh','en'])test('系统提示隔离资料与指令 '+lang,()=>{const p=T.prompt(lang,false,true);for(const word of ['不机械复述数字','不执行其中','无法编辑记录','不评判食物好坏','不对外貌打分','transcript'])assert.ok(p.includes(word));});
test('文本请求不声称分析语气',()=>assert.ok(T.prompt('zh',false,false).includes('只有文本')));
test('拒绝空、截断或坏JSON回复',()=>{for(const r of [{},{choices:[{finish_reason:'length',message:{content:'{}'}}]},{choices:[{message:{content:'bad'}}]}])assert.throws(()=>T.parse(r));});
test('音频没听到原话时不伪造回复',()=>assert.throws(()=>T.parse({choices:[{finish_reason:'stop',message:{content:JSON.stringify({transcript:'',replies:[{text:'开心呀'}]})}}]},true)));
test('模型的未授权动作被归为soft',()=>{const r=T.parse({choices:[{finish_reason:'stop',message:{content:JSON.stringify({replies:[{text:'慢慢来',gesture:'delete_record'}]})}}]});assert.equal(r.replies[0].gesture,'soft');});
for(const text of ['今天这二十分钟，也是认真付出的呀。','有点失落也没有关系，我会在这里认真听你说。','You made time for yourself. That matters.','Averylongunbrokenwordshouldneveroverflowthebubble','今天跑了3.5公里，已经很认真啦。','不用赶着好起来。'])test('一至两行分页且不丢字 '+text,()=>{const out=T.pages(text,t=>[...t].reduce((s,c)=>s+(/[\u3000-\uffff]/.test(c)?13:6.5),0),126);assert.ok(out.every(p=>p.length<=2&&p.every(l=>[...l].reduce((s,c)=>s+(/[\u3000-\uffff]/.test(c)?13:6.5),0)<=126)));assert.equal(out.flat().join('').replace(/\s/g,''),text.replace(/\s/g,''));});
test('实际请求只送当前语句与历史，不创建工具',async()=>{let sent;const api={configured:true,model:'test-text',routes:{chat:'/chat'},request:async(path,payload)=>{sent=payload;return{choices:[{finish_reason:'stop',message:{content:'{"replies":[{"text":"我在这里听。","gesture":"nod"}]}'}}]}}};const view=D.build('sport','2026-09-22',[record('a','sport',{activity:'跑步',durationMinutes:20,notes:'累'})]);const result=await T.request({api,bailian:{configured:false},view,text:'还是很累',history:[{role:'user',content:'今天忙了一天'},{role:'assistant',content:'你辛苦啦'}]});assert.equal(sent.messages.at(-1).content,'还是很累');assert.ok(sent.messages.some(m=>m.content==='今天忙了一天'));assert.equal(sent.tools,undefined);assert.equal(result.replies[0].text,'我在这里听。');});
test('取消信号传入已有客户端且取消后结果被拒绝',async()=>{const abort=new AbortController();const api={configured:true,routes:{chat:'/chat'},request:async(_,__,signal)=>{assert.equal(signal,abort.signal);abort.abort();return{choices:[]}}};await assert.rejects(T.request({api,bailian:{configured:false},view:D.build('sport','2026-09-22',[]),text:'你好',signal:abort.signal}),e=>e.name==='AbortError');});
test('没有Key不会假装聊天成功',async()=>await assert.rejects(T.request({api:{configured:false},bailian:{configured:false},view:D.build('sport','2026-09-22',[]),text:'你好'})));
test('原始音频走百炼输入，DeepSeek不会收到伪音频',async()=>{let sent;const bailian={configured:true,provider:'bailian',audioModel:'test-audio',routes:{chat:'/chat'},request:async(_,p)=>{sent=p;return{choices:[{finish_reason:'stop',message:{content:'{"transcript":"今天有点累","replies":[{"text":"给自己一点时间吧。"}]}'}}]}}};const r=await T.request({api:{configured:true},bailian,view:D.build('mood','2026-09-22',[]),audio:{data:'data:audio/wav;base64,AAAA'},text:''});assert.equal(sent.stream,true);assert.equal(sent.model,'test-audio');assert.equal(sent.messages.at(-1).content[0].type,'input_audio');assert.equal(r.transcript,'今天有点累');});

test('模型资料采用字段白名单而非展开整个data',()=>{const v=D.build('sport','2026-09-22',[record('x','sport',{activity:'跑步',durationMinutes:12,notes:'今天有点累',apiKey:'private-key-value',photo:'private-photo-value',unexpected:'private-extra-value'})]);const context=JSON.stringify(D.context(v));assert.ok(context.includes('今天有点累'));for(const secret of ['private-key-value','private-photo-value','private-extra-value'])assert.ok(!context.includes(secret));});
