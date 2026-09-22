/* 以下网络、存储和音频环境均为显式测试替身，不代表真实模型准确率。 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
/** 输入：可选全局替身。输出：隔离的模块集合。功能：执行实际交付源码，不访问真实 Key、麦克风或网络。 */
function modules(extra = {}) {
    const storage = new Map();
    const ctx = vm.createContext({ console, Date, Intl, Math, Map, Set, Object, Number, String, Array, JSON, Error, TypeError, Promise,
        AbortController, DOMException, URL, Blob, TextDecoder, TextEncoder, ReadableStream, Response, Float32Array, Uint8Array,
        ArrayBuffer, DataView, setTimeout, clearTimeout, performance, btoa, localStorage: { getItem:k=>storage.get(k)??null, setItem:(k,v)=>storage.set(k,String(v)), removeItem:k=>storage.delete(k) }, ...extra });
    vm.runInContext('const __fluffyModules={};', ctx);
    for (const file of ['model.js','sleep-time.js','catalog.js','journal-store.js','home-board.js','bailian.js','audio-session.js','ai-journal.js'])
        vm.runInContext(fs.readFileSync(path.join(__dirname,'../js',file),'utf8'),ctx,{filename:file});
    return { get: name=>vm.runInContext(`__fluffyModules[${JSON.stringify(name)}]`,ctx), storage };
}
const M=modules(),Sleep=M.get('sleep-time.js'),C=M.get('catalog.js'),Board=M.get('home-board.js'),B=M.get('bailian.js'),A=M.get('audio-session.js'),AI=M.get('ai-journal.js');
const anchor={recordDate:'2026-09-22'};
/** 输入：JSON对象。输出：完成的模型响应。功能：协议测试的显式模型替身。 */
function response(body){return {choices:[{finish_reason:'stop',message:{content:JSON.stringify(body)}}]};}
/** 输入：SSE文本与分块大小。输出：字节流。功能：模拟网络把中文UTF8拆在任意位置的情况。 */
function stream(text,size=7){const bytes=new TextEncoder().encode(text);let index=0;return new ReadableStream({pull(c){if(index>=bytes.length){c.close();return;}c.enqueue(bytes.slice(index,index+size));index+=size;}});}

for(const [bed,wake,date,hours] of [['23:00','07:00','2026-09-21',8],['01:00','07:00','2026-09-22',6],['00:00','07:30','2026-09-22',7.5],['13:00','14:30','2026-09-22',1.5]])
    test(`时分 ${bed}→${wake} 推算本地日期`,()=>{const r=Sleep.resolve({bedtime:bed,wakeTime:wake},anchor);assert.equal(r.ok,true);assert.equal(r.value.bedDate,date);assert.equal(r.value.hours,hours);});
for(const [date,expected] of [['2026-01-01','2025-12-31'],['2024-03-01','2024-02-29'],['2026-03-01','2026-02-28']])
    test(`跨月/年 ${date}`,()=>assert.equal(Sleep.resolve({bedtime:'23:00',wakeTime:'07:00'},{recordDate:date}).value.bedDate,expected));
for(const [text,bed,wake,bedDate] of [
    ['11点到7点','23:00','07:00','2026-09-21'],['1点到7点','01:00','07:00','2026-09-22'],
    ['昨晚十一点半睡，今天早上七点一刻醒','23:30','07:15','2026-09-21'],
    ['上午十一点到晚上七点','11:00','19:00','2026-09-22'],['午睡，下午一点到两点','13:00','14:00','2026-09-22'],
    ['午睡，从下午一点到下午两点','13:00','14:00','2026-09-22'],
    ['凌晨一点零五分睡到早上七点三刻','01:05','07:45','2026-09-22'],
    ['昨晚凌晨一点睡到早上七点','01:00','07:00','2026-09-22'],
    ['昨天凌晨一点到昨天早上七点','01:00','07:00','2026-09-21'],
    ['昨晚十二点睡到早上七点','00:00','07:00','2026-09-22'],
    ['前晚十一点睡到昨天七点','23:00','07:00','2026-09-20'],
    ['２３：００睡到０７：００','23:00','07:00','2026-09-21']]) {
    test(`语义解析 ${text}`,()=>{const p=Sleep.fromSpeech(text,anchor);assert.equal(p.fields.bedtime,bed);assert.equal(p.fields.wakeTime,wake);if(bedDate)assert.equal(Sleep.resolve({...p.fields,...p.dates},anchor).value.bedDate,bedDate);});
}
for(const time of ['24:00','09:61','-1:00','1pm'])test(`拒绝非法时间 ${time}`,()=>assert.equal(Sleep.clock(time),''));
test('同一时刻不擅自猜24小时睡眠',()=>assert.equal(Sleep.resolve({bedtime:'07:00',wakeTime:'07:00'},anchor).ok,false));
test('旧版历史日期不被今天替代',()=>{const r=Sleep.resolve({bedtime:'2025-12-31T23:00',wakeTime:'2026-01-01T07:00'},anchor);assert.equal(r.value.bedDate,'2025-12-31');assert.equal(r.value.hours,8);});
test('非法历史日期不会被静默进位',()=>assert.equal(Sleep.resolve({bedtime:'2026-02-30T23:00',wakeTime:'2026-03-01T07:00'},anchor).ok,false));
test('多个时间要求确认，不取第一对',()=>assert.ok(Sleep.fromSpeech('十一点睡，一点醒过，七点起床',anchor).warnings.length));
test('夏令时不存在的本地时间拒绝',()=>{const old=process.env.TZ;process.env.TZ='America/New_York';try{assert.throws(()=>Sleep.localMoment('2026-03-08','02:30'));assert.equal(Sleep.resolve({bedtime:'00:00',wakeTime:'04:00'},{recordDate:'2026-03-08'}).value.hours,3);}finally{if(old===undefined)delete process.env.TZ;else process.env.TZ=old;}});

test('九个位置，六个卡片、三个空位',()=>{const s=Board.normalizeSlots();assert.equal(s.length,9);assert.equal(s.filter(Boolean).length,6);assert.equal(new Set(s.filter(Boolean)).size,6);});
test('旧六项顺序迁移到同一错落位置',()=>{const s=Board.normalizeSlots(['sport','food','mood','focus','face','sleep']);assert.equal(s[0],'sport');assert.equal(s[4],'mood');assert.equal(s[7],'sleep');assert.equal(s[2],null);});
test('重复/原型字段布局不能构造第七卡片',()=>{const s=Board.normalizeSlots(['constructor','sport','sport',null,'food','x','mood','mood']);assert.equal(s.filter(Boolean).length,6);assert.equal(s.includes('constructor'),false);});
test('移动到空位只改变源与目标',()=>{const s=Board.exchange(Board.DEFAULT_SLOTS,0,2);assert.equal(s[0],null);assert.equal(s[2],'mood');assert.equal(s[1],'food');assert.equal(Board.DEFAULT_SLOTS[0],'mood');});
test('占位交换不会挤动第三者',()=>{const s=Board.exchange(Board.DEFAULT_SLOTS,0,5);assert.equal(s[0],'sport');assert.equal(s[5],'mood');assert.equal(s[4],'focus');});
test('网格外/坏索引不会提交',()=>{assert.equal(Board.slotAt(-1,200),-1);assert.equal(Board.slotAt(80,600),-1);assert.equal(Board.exchange(Board.DEFAULT_SLOTS,0,-1).join(),Board.DEFAULT_SLOTS.join());});
test('八个槽中心命中，右下角始终禁放',()=>{Board.SLOTS.forEach(([x,y],i)=>assert.equal(Board.slotAt(x+56,y+55),i===8?-1:i));});

test('饮食字段无维生素，情绪无强度或枚举',()=>{assert.equal(C.category('food').fields.some(f=>f.key==='vitamins'),false);assert.equal(C.category('mood').fields.some(f=>f.key==='intensity'),false);assert.equal(C.category('mood').fields.find(f=>f.key==='mood').options,undefined);});
test('睡眠醒来感受任意文字，起止仅time',()=>{assert.equal(C.category('sleep').fields.find(f=>f.key==='bedtime').type,'time');assert.equal(C.validate('sleep',{bedtime:'23:00',wakeTime:'07:00',quality:'仍有点困，但比昨天好'},true,anchor).ok,true);});
test('旧记录显示/导出删除弃用字段，不删整条记录',()=>{const m=modules(),s=m.get('journal-store.js');m.storage.set(s.KEY,JSON.stringify([{id:'one',category:'food',createdAt:'2026-09-20T08:00:00Z',data:{meal:'午餐',foods:'米饭',vitamins:'C',calories:200}},{id:'two',category:'mood',createdAt:'2026-09-20T08:00:00Z',data:{mood:'平静',intensity:5}}]));const rows=s.records();assert.equal(rows.length,2);assert.equal(JSON.stringify(rows).includes('vitamins'),false);assert.equal(JSON.stringify(rows).includes('intensity'),false);});

test('百炼拒绝非官方与重定向式端点',()=>{for(const url of ['http://dashscope.aliyuncs.com/compatible-mode/v1','https://evil.test/compatible-mode/v1','https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1','https://sk-secret@dashscope.aliyuncs.com/compatible-mode/v1','https://dashscope.aliyuncs.com/other'])assert.throws(()=>B.officialBase(url));});
test('百炼合法地区与工作空间端点可配置',()=>{assert.ok(B.officialBase('https://dashscope-intl.aliyuncs.com/compatible-mode/v1/').endsWith('/v1'));assert.ok(B.officialBase('https://workspace-id.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'));});
test('百炼Key私有、不参与JSON序列化',()=>{const client=new B.BailianClient();client.setKey('sk-unit-test-private');assert.equal(client.configured,true);assert.equal(JSON.stringify(client).includes('sk-unit-test'),false);client.clear();assert.equal(client.configured,false);});
test('校验Key只GET模型列表，不产生聊天请求',async()=>{let called;const c=new B.BailianClient({fetchImpl:async(url,options)=>{called={url,options};return new Response(JSON.stringify({data:[{id:'model'}]}),{status:200});}});c.setKey('sk-unit-test-only');assert.equal((await c.check())[0],'model');assert.ok(called.url.endsWith('/models'));assert.equal(called.options.method,'GET');assert.equal(called.options.body,undefined);assert.equal(called.options.redirect,'error');assert.equal(called.options.credentials,'omit');});
test('Key绝不发给任意path',async()=>{let sent=false;const c=new B.BailianClient({fetchImpl:async()=>{sent=true;}});c.setKey('sk-unit-test-only');await assert.rejects(c.request('https://evil.test',{}));assert.equal(sent,false);});
test('401错误不回显上游正文中的秘密',async()=>{const c=new B.BailianClient({fetchImpl:async()=>new Response('secret-private-token',{status:401})});c.setKey('sk-unit-test-only');await assert.rejects(c.check(),e=>e.message.includes('地域')&&!e.message.includes('secret'));});
test('取消传播到fetch信号',async()=>{let captured;const c=new B.BailianClient({fetchImpl:async(url,o)=>{captured=o.signal;await new Promise((r,j)=>o.signal.addEventListener('abort',()=>j(new DOMException('canceled','AbortError'))));}});c.setKey('sk-unit-test-only');const abort=new AbortController(),p=c.check(abort.signal);abort.abort();await assert.rejects(p,e=>e.name==='AbortError');assert.equal(captured.aborted,true);});
test('SSE中文拆字、CRLF与推理字段隔离',async()=>{const s='data: '+JSON.stringify({choices:[{delta:{reasoning_content:'不可展示',content:'你好'}}]})+'\r\n\r\ndata: '+JSON.stringify({choices:[{delta:{content:'小猫'},finish_reason:'stop'}]})+'\n\ndata: [DONE]\n\n';const r=await B.readSSE(stream(s,1));assert.equal(r.choices[0].message.content,'你好小猫');});
test('SSE被截断不能当作完成',async()=>{const s='data: '+JSON.stringify({choices:[{delta:{content:'片段'}}]})+'\n\n';await assert.rejects(B.readSSE(stream(s)));});
test('SSE长度截断/错误事件拒绝',async()=>{for(const s of ['data: {"error":{"message":"upstream"}}\n\n','data: {"choices":[{"delta":{"content":"a"},"finish_reason":"length"}]}\n\n'])await assert.rejects(B.readSSE(stream(s)));});

test('图像只走百炼，不偷偷退回DeepSeek',async()=>{let called=false;await assert.rejects(AI.extract({provider:'deepseek',request:async()=>{called=true;}},'food','米饭','data:image/png;base64,AA'));assert.equal(called,false);});
test('v12关闭旧Omni直接整理，保留接口但不发音频',async()=>{let called=false;const api={provider:'bailian',request:async()=>{called=true;}};await assert.rejects(AI.extractAudio(api,'mood',{data:'data:audio/wav;base64,UklGRg==',format:'wav'}));assert.equal(called,false);});
test('无法听清时不填造情绪',()=>assert.throws(()=>AI.sanitize({fields:{mood:'开心'},transcript:''},'mood',{audio:true})));
test('明确自述优先，不强加不确定前缀',()=>{const r=AI.sanitize({fields:{mood:'失落但也释然',intensity:5},emotion:{basis:'explicit',acousticEvidence:'音量小'}},'mood',{text:'我失落但也释然'});assert.equal(r.fields.mood,'失落但也释然');assert.equal('intensity'in r.fields,false);assert.equal(r.emotion.acousticEvidence,'');});
test('隐式候选必须可确认且有谨慎措辞',()=>{const r=AI.sanitize({fields:{mood:'失落'},emotion:{basis:'inferred',evidence:'又白忙一天'}},'mood');assert.ok(r.fields.mood.startsWith('可能'));assert.equal(r.emotion.needsConfirmation,true);assert.ok(r.warnings.length);});
test('禁止原型注入与未知字段',()=>{const r=AI.sanitize(JSON.parse('{"fields":{"mood":"平静","__proto__":{"polluted":true},"key":"secret"},"emotion":{"basis":"explicit"}}'),'mood');assert.equal(Object.hasOwn(r.fields,'__proto__'),false);assert.equal(r.fields.key,undefined);assert.equal({}.polluted,undefined);});
test('照片营养未知不能变成0或维生素',()=>{const r=AI.sanitize({fields:{foods:'米饭',calories:null,protein:null,vitamins:'随意'},estimated:true},'food',{image:true});assert.equal(r.fields.calories,undefined);assert.equal(r.fields.vitamins,undefined);assert.equal(r.estimated,true);});
test('睡眠语音规则校正模型给的11→07',()=>{const r=AI.sanitize({fields:{bedtime:'11:00',wakeTime:'07:00',quality:'不错'}},'sleep',{text:'11点睡7点醒',...anchor});assert.equal(r.fields.bedtime,'23:00');assert.equal(r.fields.wakeTime,'07:00');});
test('多组时间时不接受模型擅自挑选',()=>{const r=AI.sanitize({fields:{bedtime:'23:00',wakeTime:'01:00'}},'sleep',{text:'十一点睡，一点醒过，七点起',...anchor});assert.equal(r.fields.bedtime,undefined);assert.ok(r.warnings.length);});
test('提示覆盖否定、反讽、混合、转述及音质',()=>{const p=AI.prompt('mood','音频');for(const s of ['否定','反讽','混合','转述','音质','自述优先','不输出强度/分数'])assert.ok(p.includes(s));});
test('面部提示禁止从图像推断内心/身份',()=>{const p=AI.prompt('face','照片');for(const s of ['feeling只能提取用户自述','身份','不评分'])assert.ok(p.includes(s));});

test('PCM输入编码真实WAV头与16k时长',()=>{const samples=new Float32Array(48000).fill(.5),buf=A.encodeWAV([samples],48000),v=new DataView(buf);assert.equal(buf.byteLength,32044);assert.equal(v.getUint32(24,true),16000);assert.equal(v.getUint16(22,true),1);assert.equal(v.getUint16(34,true),16);assert.equal(v.getInt16(44,true),16384);assert.equal(String.fromCharCode(...new Uint8Array(buf,0,4)),'RIFF');});
test('WAV对正负溢出限幅',()=>{const v=new DataView(A.encodeWAV([new Float32Array([2,-2])],16000));assert.equal(v.getInt16(44,true),32767);assert.equal(v.getInt16(46,true),-32768);});
test('长录音Base64不会参数栈溢出',()=>{const a=new Uint8Array(300000).fill(32);assert.equal(Buffer.from(A.base64(a.buffer),'base64').length,a.length);});
/** 输入：可选延迟授权。输出：采集器与音频测试环境。功能：模拟音频回调和资源释放，不声称实际录音通过。 */
function audioFixture(pending=false){let stopped=0,closed=0,resolvePermission;const node={connect(){},disconnect(){}};const stream={getTracks:()=>[{stop:()=>stopped++}]};class Context{constructor(){this.sampleRate=16000;this.state='running';this.destination={};}async resume(){}createMediaStreamSource(){return {...node};}createGain(){return {...node,gain:{value:1}};}createScriptProcessor(){return {...node};}async close(){this.state='closed';closed++;}}
const env={AudioContext:Context,mediaDevices:{getUserMedia:()=>pending?new Promise(r=>{resolvePermission=r;}):Promise.resolve(stream)}};const session=new A.AudioSession({},env);return {session,resolve:()=>resolvePermission(stream),counts:()=>({stopped,closed})};}
test('授权晚到不会开始录音，立即关轨道',async()=>{const f=audioFixture(true),p=f.session.start();f.session.cancel();f.resolve();assert.equal(await p,false);assert.ok(f.counts().stopped>0);assert.equal(f.session.active,false);});
test('松手输出实际样本WAV并释放全部引用',async()=>{const f=audioFixture();await f.session.start();f.session.accept(new Float32Array(16000).fill(.1));const r=await f.session.stop();await Promise.resolve();assert.equal(r.canceled,false);assert.equal(r.duration,1);assert.ok(r.audio.data.startsWith('data:audio/wav;base64,'));assert.equal(f.session.context,null);assert.equal(f.session.chunks.length,0);assert.equal(f.session.stopPromise,null);assert.ok(f.counts().closed>0);});
test('静音会停止并报错，不提交假转写',async()=>{const f=audioFixture();await f.session.start();f.session.accept(new Float32Array(16000));await assert.rejects(f.session.stop(),/没有录到/);assert.equal(f.session.context,null);});
