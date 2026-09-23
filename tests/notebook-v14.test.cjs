/* v14 纯几何与数据回归。合成笔画仅用于数学断言，不伪装成模型或用户数据。 */
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm'), path = require('node:path');
/** 输入：无。输出：隔离模块。功能：不访问真实存储、DOM、网络或API。 */
function fixture() {
    const ctx = vm.createContext({ Date, Intl, console });
    vm.runInContext('const __fluffyModules = {};', ctx);
    for (const file of ['model','sleep-time','catalog','notebook-layout']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/'+file+'.js'),'utf8'),ctx);
    return vm.runInContext('({ N:__fluffyModules["notebook-layout.js"], C:__fluffyModules["catalog.js"] })',ctx);
}
/** 输入：行数。输出：合成排版。功能：单独验证最后一行决定字段高度，时序不依赖真实渲染。 */
function line(count=1) { return {ruleOffsets:Array.from({length:count},(_,r)=>28+r*36.25),visualRows:Array.from({length:count},(_,r)=>({row:r,offset:r*36.25,start:r*2.1,end:r*2.1+2})),duration:count*2.1,measuredHeight:count*36.25}; }
const {N,C}=fixture();
for(const count of [1,2,3,4,5,8,14])test(`${count}行字段之后始终保留30px标题前留白`,()=>{
    const l=N.createLayout([line(1),line(count),line(2)]);
    for(let i=0;i<l.fields.length-1;i++) assert.ok(Math.abs(l.fields[i+1].titleTop-l.fields[i].top-l.fields[i].lastRule-N.PAPER.fieldGap)<1e-9);
});
for(const count of [1,3,4,7,12])test(`${count}字段循环实际总长，阅读只有一份`,()=>{
    const lines=Array.from({length:count},(_,i)=>line(i%4+1)),l=N.createLayout(lines),t=N.createTimeline(l,lines);
    assert.equal(t.schedule.length,count);assert.equal(t.segments.length,lines.reduce((n,x)=>n+x.visualRows.length,0));
    assert.equal(N.paperOffset(l,t,t.returnEnd),-l.period);
    for(let i=0;i<count;i++) {const p=N.positions(l,i,-l.period,true,0);assert.equal(p.length,1);assert.equal(p[0].y,N.PAPER.originY+l.fields[i].top);}
});
for(const count of [1,2,3,5,9])test(`${count}行内容归位前后同坐标且上一圈末线离开裁切区`,()=>{
    const lines=[line(1),line(2),line(count)],l=N.createLayout(lines),t=N.createTimeline(l,lines);
    const off=N.paperOffset(l,t,t.returnEnd);
    for(let i=0;i<3;i++) {const before=N.positions(l,i,off).find(p=>p.cycle===1),after=N.positions(l,i,off,true)[0];assert.ok(before);assert.equal(before.y,after.y);}
    const prev=N.PAPER.originY+l.fields.at(-1).top+off+l.fields.at(-1).lastRule;
    assert.ok(prev<N.PAPER.clipTop-1,`${prev} vs ${N.PAPER.clipTop}`);
});
test('最后一行到底时保留底部内边距，上下界不循环',()=>{
    const l=N.createLayout([line(5),line(5),line(5)]);
    assert.ok(l.maxScroll>0);
    for(const input of [l.maxScroll,l.maxScroll+1e4,Infinity]){
        const p=N.positions(l,2,0,true,input===Infinity?l.maxScroll+1e4:input)[0];
        assert.ok(Math.abs(p.y+l.fields[2].lastRule-(N.PAPER.clipBottom-N.PAPER.bottomPadding))<1);
    }
    assert.equal(N.positions(l,0,0,true,-100)[0].y,N.PAPER.originY);
});
test('短笔记没有额外的滚动尾巴',()=>{const l=N.createLayout([line(1),line(1),line(1)]);assert.equal(l.maxScroll,0);assert.equal(l.contentHeight,l.viewportHeight);});
test('纸面只在换行间移动，落笔区间完全停稳',()=>{
    const lines=[line(3),line(2)],l=N.createLayout(lines),t=N.createTimeline(l,lines);
    for(const s of t.segments) for(const k of [.01,.25,.5,.99]) assert.equal(N.paperOffset(l,t,s.start+(s.end-s.start)*k),s.offset);
});
test('所有送纸边界连续且整体只向上归位',()=>{
    const lines=[line(1),line(5),line(3)],l=N.createLayout(lines),t=N.createTimeline(l,lines),ends=t.segments.flatMap(s=>[s.start,s.end]);
    for(const time of [...ends,t.returnStart,t.returnEnd]) assert.ok(Math.abs(N.paperOffset(l,t,time-1e-6)-N.paperOffset(l,t,time+1e-6))<.001);
    let before=0;for(let time=0;time<t.returnEnd+.1;time+=.01){const off=N.paperOffset(l,t,time);assert.ok(off<=before+1e-8);before=off;}
});
test('长字段从第一行到最后一行都被写到，成稿时钟完整',()=>{
    const lines=[line(5)],l=N.createLayout(lines),t=N.createTimeline(l,lines);
    assert.equal(t.segments.length,5);assert.equal(N.fieldClock(t,lines,0,t.returnEnd),lines[0].duration);
    for(const s of t.segments) assert.ok(Math.abs(N.fieldClock(t,lines,0,(s.start+s.end)/2)-(s.from+s.to)/2)<1e-9);
});
test('非法布局受控拒绝',()=>{assert.throws(()=>N.createLayout([]));assert.throws(()=>N.createLayout([{height:Infinity}]));});
test('饮食完整保留食物份量四项营养与备注，不再压成3项',()=>{
    const rows=C.rows({category:'food',data:{meal:'午餐',foods:'意面',portion:'一盘',calories:700,protein:25,carbs:90,fat:23,notes:'好吃'}});
    assert.equal(rows.length,7);assert.equal(rows[0].label,'午餐');
    for(const [label,value]of [['Portion','一盘'],['Calories','700 kcal'],['Protein','25 g'],['Carbs','90 g'],['Fat','23 g'],['Notes','好吃']]) assert.equal(rows.find(r=>r.label===label).value,value);
});
test('营养零值保留，不把未知值编成零',()=>{
    const rows=C.rows({category:'food',data:{foods:'水',protein:0}});
    assert.equal(rows.find(r=>r.label==='Protein').value,'0 g');assert.equal(rows.find(r=>r.label==='Calories').value,'—');
});
test('面部眼周和皮肤都保留，不二选一',()=>{
    const rows=C.rows({category:'face',data:{feeling:'还好',eyeArea:'有阴影',skinAppearance:'有泛红',notes:'光线偏暗'}});
    assert.equal(rows.length,4);assert.equal(rows.find(r=>r.label==='Eye area').value,'有阴影');assert.equal(rows.find(r=>r.label==='Skin').value,'有泛红');
});
test('睡眠时段时长感受备注都在笔记中',()=>{
    const rows=C.rows({category:'sleep',data:{bedtime:'23:00',wakeTime:'07:00',hours:8,quality:'精神不错',notes:'醒过一次'}});
    assert.equal(rows.length,4);assert.equal(rows.find(r=>r.label==='Feeling').value,'精神不错');
});
for(const category of ['sport','mood','food','sleep','face','focus'])test(category+' 笔记投影不修改已保存原对象',()=>{
    const record={category,data:{activity:'跑步',durationMinutes:30,notes:'备忘',foods:'面条',task:'阅读',mood:'平静',hours:8,bedtime:'23:00',wakeTime:'07:00'}},before=JSON.stringify(record);
    const rows=C.rows(record);assert.ok(rows.every(r=>typeof r.value==='string'));assert.equal(JSON.stringify(record),before);
});
