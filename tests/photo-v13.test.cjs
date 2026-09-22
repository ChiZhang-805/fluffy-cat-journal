/* 输入：发布模块。输出：Node TAP。功能：验证照片草稿保护和营养校验，不发送真实API。 */
const test = require('node:test'), assert = require('node:assert/strict'), vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
/** 输入：无。输出：隔离模块。功能：装载交付源码，替换存储，拒绝实际网络请求。 */
function setup() {
 const c = vm.createContext({console,Date,Intl,Math,Object,String,Number,Array,JSON,Set,Map,WeakMap,Error,DOMException,AbortController,Promise,localStorage:{getItem:()=>null,setItem:()=>{}}});
 vm.runInContext('var __fluffyModules={};',c);
 for(const n of ['model','sleep-time','catalog','entry-i18n','photo-draft','cat-feedback','ai-policy','ai-journal']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../js',n+'.js'),'utf8'),c,{filename:n+'.js'});
 return n=>vm.runInContext(`__fluffyModules["${n}.js"]`,c);
}
/** 输入：跨VM对象。输出：普通对象。功能：只消除原型差异，不改变待测值。 */
const plain = x=>JSON.parse(JSON.stringify(x));
test('空字段可以回填，已有手动文字和数字不被照片覆盖',()=>{const P=setup()('photo-draft');const r=P.writable({foods:'米饭',calories:200,protein:6},{foods:'用户自己填的',calories:'123',protein:''},{foods:0,calories:0,protein:0},{foods:0,calories:0,protein:0});assert.deepEqual(plain(r),{fields:{protein:6},protectedCount:2});});
test('等待期间输入或主动清空优先于旧模型结果',()=>{const P=setup()('photo-draft');assert.deepEqual(plain(P.writable({foods:'旧照片内容'},{foods:''},{foods:2},{foods:1}).fields),{});});
test('自动回填的0有所有权，手动0不会被覆盖',()=>{const P=setup()('photo-draft');assert.deepEqual(plain(P.writable({fat:20},{fat:'0'},{fat:0},{fat:0}).fields),{});assert.equal(P.writable({fat:0},{fat:''},{fat:0},{fat:0}).fields.fat,0);});
test('换图只清除仍未被修改的旧照片值',()=>{const P=setup()('photo-draft'),owned={foods:{value:'米饭',version:0},protein:{value:'10',version:0},fat:{value:'5',version:0}};assert.deepEqual(plain(P.staleKeys({foods:'米饭',protein:'13',fat:'5'},{foods:0,protein:1,fat:1},owned)),['foods']);});
test('编辑后改回相同文本依然由用户拥有',()=>{assert.equal(setup()('photo-draft').staleKeys({foods:'米饭'},{foods:2},{foods:{value:'米饭',version:0}}).length,0);});
test('同一照片显式重试允许更新其仍拥有的字段',()=>{const P=setup()('photo-draft');assert.equal(P.writable({calories:520},{calories:'500'},{calories:0},{calories:0},{calories:{value:'500',version:0}}).fields.calories,520);});
test('所有权仅包括本轮实际回填，无图片或key',()=>{const P=setup()('photo-draft');assert.deepEqual(plain(P.remember({protein:6},{protein:'6',notes:'私有文字'},{protein:1,notes:0})),{protein:{value:'6',version:1}});});
test('删除旧所有权不会修改调用者对象',()=>{const P=setup()('photo-draft'),o={foods:{value:'饭',version:0}};P.remember({fat:9},{fat:'9'},{fat:0},o);assert.deepEqual(Object.keys(o),['foods']);});
test('未知营养null不能变成0，不把无效范围当点值',()=>{const A=setup()('ai-journal');const d=A.sanitize({fields:{foods:'米饭',calories:null,protein:'10-20',carbs:0,fat:''}},'food',{image:true});assert.equal(d.fields.calories,undefined);assert.equal(d.fields.protein,undefined);assert.equal(d.fields.carbs,0);assert.equal(d.fields.fat,'');});
test('目测小数适度取整，内部保留推算来源',()=>{const d=setup()('ai-journal').sanitize({fields:{foods:'意面',calories:823.471,protein:31.78,carbs:93.4,fat:28.42}},'food',{image:true});assert.equal(d.fields.calories,820);assert.equal(d.fields.protein,32);assert.equal(d.fields.carbs,93);assert.equal(d.fields.fat,28);assert.equal(d.estimated,true);});
test('文字中的明确营养数字不被图片取整规则修改',()=>{const d=setup()('ai-journal').sanitize({fields:{calories:823.4,protein:31.7}},'food',{image:false});assert.equal(d.fields.calories,823.4);assert.equal(d.fields.protein,31.7);});
test('负数、超范围、非有限数不填入',()=>{for(const value of [-1,Infinity,'NaN',1e30]){const d=setup()('ai-journal').sanitize({fields:{calories:value}},'food',{image:true});assert.equal(d.fields.calories,undefined);}});
test('照片不能猜用户的主观感受和餐次，提示保留用户上下文优先',()=>{const text=setup()('ai-journal').prompt('food','照片');assert.ok(text.includes('餐次meal只能来自用户输入'));assert.ok(text.includes('notes只保留用户自己说过'));assert.ok(text.includes('典型一份'));assert.ok(text.includes('整餐总量'));assert.ok(text.includes('未知数值用null而非0'));});
test('食物正常分析不生成长段免责声明',()=>{const text=setup()('ai-journal').prompt('food','照片');assert.ok(text.includes('正常情况下warnings为空'));assert.ok(text.includes('不要返回维生素'));});
test('照片字段仍是同一白名单且数据结构向后兼容',()=>{const C=setup()('catalog');assert.deepEqual(plain(C.category('food').fields.filter(f=>f.group).map(f=>f.key)),['calories','protein','carbs','fat']);});
test('保留部分结果的猫咪文案为两行，未承诺全部完整',()=>{const F=setup()('cat-feedback');for(const k of ['photo-food-partial','photo-food-unclear','photo-filled','photo-retry']){assert.equal(F.say(k).split('\n').length,2);assert.ok(!/估算|仅供参考/.test(F.say(k)));}});
test('输入准备不改变新增/编辑、日期或保存记录',()=>{const P=setup()('photo-draft');assert.deepEqual(Object.keys(P).sort(),['remember','staleKeys','writable']);});
