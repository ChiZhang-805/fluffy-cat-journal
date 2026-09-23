/** 输入：v17个人资料模块。输出：node:test报告。功能：独立校验首次完成、草稿、旧资料与存储隔离，不调用模型。 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, 'js/first-notes-profile.js'), 'utf8'), ctx);
const P = ctx.NavaFirstNotesProfile;
const base = { version: 4, language: 'zh', gender: 'private', role: 'student', age: '18-24', interests: ['reading','music'], sleep: '7to8', exercise: '2to4', diet: ['light','plant'] };
/** 输入：初始值。输出：内存存储替身。功能：验证写入白名单，避免读写用户真实数据。 */
function store(entries=[]) { const map = new Map(entries); return { map, getItem:k=>map.get(k)??null, setItem:(k,v)=>map.set(k,v), removeItem:k=>map.delete(k) }; }
/** 输入：对象。输出：普通JSON副本。功能：跨vm比较不受原型差异影响。 */
function plain(x) { return JSON.parse(JSON.stringify(x)); }

test('七项完整资料可规范化，按稳定语义键而非界面标签保存',()=>assert.deepEqual(plain(P.normalize(base)),base));
test('完整资料之外的字段不会写入个人资料或每日记录',()=>{let x=P.normalize({...base,records:['fake'],apiKey:'fixture',score:100});assert.equal(x.records,undefined);assert.equal(x.apiKey,undefined);assert.equal(x.score,undefined);});
test('缺任一单选、多选为空均不能标记完成',()=>{for(const k of ['gender','role','age','sleep','exercise'])assert.equal(P.normalize({...base,[k]:null}),null);for(const k of ['interests','diet'])assert.equal(P.normalize({...base,[k]:[]}),null);});
test('无特殊偏好和具体偏好互斥；重复值与非法枚举拒绝',()=>{for(const diet of [['none','light'],['light','light'],['unknown']])assert.equal(P.normalize({...base,diet}),null);assert.equal(P.normalize({...base,gender:'guessed'}),null);});
test('没有completedAt、日期无效、非支持版本均不能跳过引导',()=>{assert.equal(P.completed(base),null);assert.equal(P.completed({...base,completedAt:'bad'}),null);assert.equal(P.completed({...base,version:999,completedAt:'2026-09-23T10:00:00Z'}),null);});
test('旧版v3完成资料兼容，不要求旧用户重复回答',()=>{let x=P.completed({...base,version:3,completedAt:'2026-09-20T09:00:00Z'});assert.equal(x.version,4);assert.equal(x.completedAt,'2026-09-20T09:00:00Z');});
test('恶意或损坏JSON不会启动应用，不删除日记',()=>{let s=store([[P.KEY,'{broken'],['fluffy-six-journal-v1','keep']]);assert.equal(P.completed(P.read(s)),null);assert.equal(s.getItem('fluffy-six-journal-v1'),'keep');});
test('完成只写个人资料并删除自己的草稿，保留记录、待办、计时和排列',()=>{const keys=['fluffy-six-journal-v1','fluffy-six-tasks-v1','fluffy-active-focus-v1','fluffy-home-layout-v3'];let s=store(keys.map(k=>[k,k+'original']));s.setItem(P.DRAFT_KEY,'draft');let r=P.save(s,base);assert.equal(r.ok,true);for(const k of keys)assert.equal(s.getItem(k),k+'original');assert.equal(s.getItem(P.DRAFT_KEY),null);});
test('重复确认保留首次完成时间，只更新修改时间',()=>{let s=store();let a=P.save(s,base,null,new Date('2026-09-20T10:00:00Z'));let b=P.save(s,{...base,sleep:'8to9'},a.profile,new Date('2026-09-23T10:00:00Z'));assert.equal(b.profile.completedAt,a.profile.completedAt);assert.equal(b.profile.updatedAt,'2026-09-23T10:00:00.000Z');assert.equal(s.map.size,1);});
test('存储禁用或额度失败不声称已完成',()=>{let s={getItem:()=>null,setItem:()=>{throw Error('quota');}};assert.equal(P.save(s,base).ok,false);assert.equal(P.save(null,base).ok,false);});
test('写后读回不一致拒绝成功，不依赖单独布尔完成标记',()=>assert.equal(P.save({setItem(){},getItem(){return null;}},base).ok,false));
test('中途草稿可以恢复，但未填步骤不能跳到summary',()=>{let raw={...base,age:null,interests:[],sleep:null,exercise:null,diet:[]};let d=P.draft({profile:raw,step:'summary'});assert.equal(d.step,'age');assert.equal(P.completed(d.profile),null);});
test('草稿返回前页保留，未支持的complete步骤被拒绝',()=>{assert.equal(P.draft({profile:base,step:'gender'}).step,'gender');assert.equal(P.draft({profile:base,step:'complete'}),null);});
test('中英文均使用相同选项键；未知语言拒绝',()=>{assert.equal(P.normalize({...base,language:'en'}).sleep,'7to8');assert.equal(P.normalize({...base,language:'de'}),null);});
test('成品没有额外完成页，sleep标签有紧凑表述，列表有限滚动',()=>{const h=fs.readFileSync(path.join(root,'onboarding.html'),'utf8');assert.match(h,/＜5 小时/);assert.match(h,/function fitSummary/);assert.match(h,/\.summary-scroll\{[^}]*overflow-y:auto/);assert.ok(!h.includes("'diet','summary','complete'"));assert.ok(!h.includes('function complete(content)'));assert.ok(!h.includes('第一页，收好啦。'));});
test('宿主核验source、origin、随机channel；没有本地存储清空',()=>{const h=fs.readFileSync(path.join(root,'js/first-run.js'),'utf8');assert.match(h,/event\.source !== sourceFrame\.contentWindow/);assert.match(h,/event\.origin !== location\.origin/);assert.match(h,/event\.data\?\.channel !== channel/);assert.ok(!h.includes('localStorage.clear'));assert.ok(!h.includes('fetch('));});
