/* v6 纯逻辑回归。只执行本地代码，网络与浏览器存储均为显式测试替身。 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
/** 输入：无。输出：隔离模块、存储。功能：加载实际业务代码，不访问账户或付费API。 */
function fixture() {
    const storage = new Map();
    const ctx = vm.createContext({ console, Date, Intl, Math, Map, Set, Object, Number, String, Array, JSON, Error, TypeError, Promise,
        AbortController, DOMException, URL, Blob, TextDecoder, TextEncoder, Response, setTimeout, clearTimeout, performance,
        localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, String(value)) } });
    vm.runInContext('const __fluffyModules={};', ctx);
    for (const file of ['model.js','sleep-time.js','catalog.js','journal-store.js','home-board.js','ai-journal.js','bubble-copy.js'])
        vm.runInContext(fs.readFileSync(path.join(__dirname, '../js', file), 'utf8'), ctx, { filename: file });
    return { module: name => vm.runInContext(`__fluffyModules["${name}.js"]`, ctx), storage };
}
const F = fixture(), C = F.module('catalog'), B = F.module('home-board'), AI = F.module('ai-journal'), Bubble = F.module('bubble-copy');
/** 输入：跨VM对象。输出：本realm JSON对象。功能：只比较数据，不比较跨VM原型。 */
function plain(value) { return JSON.parse(JSON.stringify(value)); }

test('运动只有项目、时长、备注，保留三项必填', () => {
    assert.deepEqual(plain(C.category('sport').fields.map(field => field.key)), ['activity','durationMinutes','notes']);
    assert.equal(C.validate('sport',{activity:'力量训练',durationMinutes:'45.5',notes:'深蹲4组，每组8次'}).ok,true);
    assert.equal(C.validate('sport',{activity:'力量训练',durationMinutes:'45'}).ok,false);
});
for (const [raw, expected] of [[3,'轻松；距离 3 公里'],['3.5','轻松；距离 3.5 公里'],[0,'轻松；距离 0 公里']]) {
    test(`旧距离${raw}保留在备注且不修改源对象`, () => {
        const original = {activity:'跑步',durationMinutes:20,distanceKm:raw,notes:'轻松'};
        const result = C.validate('sport',original);
        assert.equal(result.value.notes,expected);
        assert.equal('distanceKm' in result.value,false);
        assert.equal(original.notes,'轻松');
        assert.equal(C.validate('sport',result.value).value.notes,expected);
    });
}
for (const notes of ['跑了 3 公里','骑行3km，轻松','跑了3000米','游了 3000 m'])
    test(`备注已含等值距离不重复：${notes}`, () => assert.equal(C.sportData({distanceKm:3,notes}).notes, notes));
test('不同距离不会误判为同一信息，旧数据不凭空消失',()=>assert.equal(C.sportData({distanceKm:13,notes:'先走了3公里'}).notes,'先走了3公里；距离 13 公里'));
test('空备注的合法旧距离可以迁移，坏距离不生成新数据',()=>{
    assert.equal(C.sportData({distanceKm:3,notes:''}).notes,'距离 3 公里');
    assert.equal(C.sportData({distanceKm:'NaN',notes:'原话'}).notes,'原话');
});
test('历史、导出、二次保存均保留距离且ID不变',()=>{
    const f=fixture(),store=f.module('journal-store');
    const old={id:'old-one',category:'sport',createdAt:'2026-09-20T08:00:00Z',data:{activity:'跑步',distanceKm:3,durationMinutes:20,notes:'轻松'}};
    f.storage.set(store.KEY,JSON.stringify([old]));
    const record=store.records()[0];assert.equal(record.id,old.id);assert.equal(record.data.notes,'轻松；距离 3 公里');
    assert.equal(JSON.parse(f.storage.get(store.KEY))[0].data.distanceKm,3,'只读迁移不破坏旧存储');
    assert.equal(store.save(record),true);assert.equal(store.save(record),true);
    assert.equal(store.records().length,1);assert.equal(store.records()[0].data.notes,record.data.notes);
    assert.equal(JSON.stringify(store.records()).includes('distanceKm'),false);
});
test('手写运动项目不再拼公里，首页主要显示分钟',()=>{
    const record={category:'sport',data:{activity:'骑车',durationMinutes:25,distanceKm:8,notes:'沿河骑行'}};
    const rows=C.rows(record);assert.equal(rows[0].value,'骑车');assert.equal(rows[1].value,'25 min');assert.ok(rows[2].value.includes('8 公里'));
    assert.equal(C.summary(record).value,'25 min');
});
test('运动语音提示将组数重量距离都归入备注',()=>{
    const text=AI.prompt('sport','原始音频');
    for (const keyword of ['三个字段','组数','次数','重量','距离不是必填项','不返回distanceKm']) assert.ok(text.includes(keyword));
    const result=AI.sanitize({fields:{activity:'深蹲',durationMinutes:30,notes:'4组，每组8次',distanceKm:99}},'sport');
    assert.equal(result.fields.distanceKm,undefined);assert.equal(result.fields.notes,'4组，每组8次');
});
test('右下角迁移只移动禁放区组件，其他五项位置不变',()=>{
    const old=['mood','food','sport',null,'sleep','focus',null,null,'face'];
    const migrated=B.normalizeSlots(old);assert.equal(migrated[8],null);assert.equal(migrated[3],'face');
    for (const i of [0,1,2,4,5]) assert.equal(migrated[i],old[i]);
    assert.equal(migrated.filter(Boolean).length,6);
});
test('九宫格中始终两空位加一个气泡区，重复与坏值可修复',()=>{
    for(const raw of [null,[],['mood','mood','constructor','food',null,null,null,null,'face']]) {
        const slots=B.normalizeSlots(raw);assert.equal(slots.length,9);assert.equal(slots[8],null);
        assert.equal(slots.filter(Boolean).length,6);assert.equal(new Set(slots.filter(Boolean)).size,6);
    }
});
for (const index of [0,1,2,3,4,5,6,7])
    test(`第${index+1}个有效槽支持移动`,()=>{const next=B.exchange(B.DEFAULT_SLOTS,0,index);assert.equal(next[8],null);assert.equal(next[index],'mood');});
test('拖入禁放区、无效索引都不改变布局',()=>{
    for(const index of [8,9,-1,NaN,1.5]) assert.deepEqual(plain(B.exchange(B.DEFAULT_SLOTS,0,index)),plain(B.DEFAULT_SLOTS));
    assert.equal(B.slotAt(316,454),-1);assert.equal(B.slotAt(258,400),-1);assert.equal(B.slotAt(372,508),-1);
});
test('气泡与六类问候只用完整一行或长度平衡的两行',()=>{
    const texts=[...Object.values(Bubble.COPY),...Object.values(C.CATEGORIES).map(c=>c.greeting)];
    for(const text of texts){const lines=text.split('\n');assert.ok(lines.length<=2);assert.ok(lines.every(line=>[...line].length<=7));if(lines.length===2) assert.ok(Math.abs([...lines[0]].length-[...lines[1]].length)<=1,text);}
});
test('错误文案不会被写成整理成功，也不丢详细故障信息',()=>{
    const result=Bubble.prepare('麦克风权限被拒绝，请先在网站设置允许麦克风。',true);
    assert.equal(result.text,Bubble.COPY.error);assert.ok(result.detail.includes('麦克风权限'));
});
test('成功估时简短陪伴，不重复暗示不可靠',()=>{
    const result=Bubble.prepare('estimated');assert.equal(result.text,'时间安排好啦\n我们一起开始');assert.equal(result.detail,'');
});
test('合并时间行仍保存独立字段和日期，跨午夜算法未改变',()=>{
    const out=C.validate('sleep',{bedtime:'23:00',wakeTime:'07:00',quality:'精神不错',notes:'睡得安稳'},true,{recordDate:'2026-09-22'});
    assert.equal(out.ok,true);assert.equal(out.value.hours,8);assert.equal(out.value.bedDate,'2026-09-21');
});
