/* v9：运行交付源码的按钮规则，所有值均为测试夹具，不读取个人记录或调用API。 */
const test = require('node:test'), assert = require('node:assert/strict');
const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
/** 输入：无。输出：交付模块。功能：在无DOM环境执行真实状态规则，保证不依赖照片/密钥等UI节点。 */
function setup() {
    const ctx = vm.createContext({ Date, Intl, Math, Object, Array, String, Number, JSON, Error, console });
    vm.runInContext('const __fluffyModules={};', ctx);
    for (const name of ['model','sleep-time','catalog','entry-action']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../js',name+'.js'),'utf8'),ctx);
    return vm.runInContext('__fluffyModules["entry-action.js"]',ctx);
}
const full = {
    sport: { activity:'力量训练', durationMinutes:'40.5', notes:'深蹲四组' },
    food: { meal:'午餐', foods:'米饭和鸡肉', portion:'一碗', calories:'600', protein:'30', carbs:'70', fat:'20', notes:'吃得很舒服' },
    mood: { mood:'开心又有点累', reason:'完成实验', notes:'慢慢来' },
    sleep: { bedtime:'23:00', wakeTime:'07:00', quality:'精神不错', notes:'夜里没醒' },
    face: { feeling:'还不错', eyeArea:'无特别变化', skinAppearance:'自然光下记录', notes:'留个纪念' },
    focus: { task:'读论文', durationMinutes:'25', notes:'方法部分' }
};
for (const [category,raw] of Object.entries(full)) {
    test(category+'空表单是长按邀请且不禁用按钮',()=>{const m=setup(),s=m.inspect(category,{});assert.equal(s.complete,false);const d=m.describe({category,complete:s.complete});assert.equal(d.mode,'invite');assert.equal(d.label,'长按向小猫倾诉');assert.equal(d.disabled,false);});
    test(category+'填写所有记录项后切换',()=>{const m=setup(),s=m.inspect(category,raw,{recordDate:'2026-09-22'});assert.equal(s.complete,true);assert.equal(s.canSubmit,true);assert.equal(m.describe({category,complete:true}).label,category==='focus'?'开始专注':'完成并继续');});
    test(category+'任意一项删除回到邀请',()=>{const m=setup();for(const key of Object.keys(raw)){assert.equal(m.inspect(category,{...raw,[key]:' \n '},{recordDate:'2026-09-22'}).complete,false,key);}});
}
test('照片和API字段不会影响饮食/面部完成度',()=>{const m=setup();for(const id of ['food','face']){assert.equal(m.inspect(id,full[id]).complete,true);assert.equal(m.inspect(id,{...full[id],photo:null,apiKey:'',image:''}).complete,true);}});
test('有效的零营养数值不是空白',()=>{assert.equal(setup().inspect('food',{...full.food,calories:0,protein:0,carbs:0,fat:0}).complete,true);});
test('无效或负时长不能显示继续',()=>{const m=setup();for(const n of ['abc','-2','Infinity','0','1e500']){const result=m.inspect('sport',{...full.sport,durationMinutes:n});assert.equal(result.complete,false);assert.ok(result.invalid.includes('durationMinutes'));}});
test('起止时间相同和不存在的时间不显示继续',()=>{const m=setup();assert.equal(m.inspect('sleep',{...full.sleep,wakeTime:'23:00'}).complete,false);assert.equal(m.inspect('sleep',{...full.sleep,bedtime:'25:30'}).complete,false);});
test('合法跨午夜和历史日期保留',()=>{assert.equal(setup().inspect('sleep',full.sleep,{recordDate:'2026-01-01'}).complete,true);});
test('完整度不是新增必填规则：未知营养可以按原提交规则留空',()=>{const result=setup().inspect('food',{meal:'午餐',foods:'一份午餐'});assert.equal(result.complete,false);assert.equal(result.canSubmit,true);});
test('状态计算不修改用户输入对象',()=>{const raw={...full.sport};const before=JSON.stringify(raw);setup().inspect('sport',raw);assert.equal(JSON.stringify(raw),before);});
test('超长备注有值但不算合格的完成状态',()=>{assert.equal(setup().inspect('sport',{...full.sport,notes:'字'.repeat(61)}).complete,false);});
for(const phase of ['requesting','authorizing','listening','thinking'])test(phase+'优先于完成度且保留取消语义',()=>{const m=setup();for(const complete of [false,true]){const result=m.describe({category:'sport',phase,complete});assert.equal(result.mode,'busy');assert.equal(result.disabled,phase==='authorizing');if(phase==='listening')assert.equal(result.label,'松开结束');if(phase==='thinking')assert.equal(result.label,'停止整理');}});
test('英文邀请和英文继续都有正确的无障碍描述',()=>{const m=setup();assert.equal(m.describe({category:'food',language:'en'}).label,'Hold to tell your cat');const result=m.describe({category:'sport',language:'en',complete:true});assert.equal(result.label,'Finish & continue');assert.ok(result.help.includes('Escape'));assert.ok(result.accessibleLabel.includes('hold to speak'));});
test('未就绪不开放交互，填满也不绕过素材准备',()=>{assert.equal(setup().describe({category:'sport',complete:true,loaded:false}).disabled,true);});
test('专注继续区分新计时、过去补记与修改',()=>{const m=setup();assert.equal(m.describe({category:'focus',complete:true,past:true}).label,'补记专注');assert.equal(m.describe({category:'focus',complete:true,past:true,editing:true}).label,'保存修改');assert.equal(m.describe({category:'focus',complete:true,editing:true,language:'en'}).label,'Save changes');});
test('不完整的专注编辑也先显示语音邀请',()=>{assert.equal(setup().describe({category:'focus',editing:true,past:true,complete:false}).mode,'invite');});
