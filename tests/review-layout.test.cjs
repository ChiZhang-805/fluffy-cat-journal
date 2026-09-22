/* v10：纯几何与数值缩放，不读取真实记录、麦克风或API。 */
const test = require('node:test'), assert = require('node:assert/strict');
const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
/** 输入：无。输出：交付布局模块。功能：在无DOM环境验证同一份生产坐标与柱高换算。 */
function setup() {
    const ctx=vm.createContext({Object,Number,Math});
    vm.runInContext('const __fluffyModules={};',ctx);
    vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/review-layout.js'),'utf8'),ctx);
    return vm.runInContext('__fluffyModules["review-layout.js"]',ctx);
}
test('猫、气泡、点击区域、当天卡片同步上移44设计像素',()=>{
    const g=setup().geometry;
    assert.equal(g.actorY,45-44);assert.equal(g.petTop,164-44);
    assert.equal(g.bubbleTop,181-44);assert.equal(g.summaryTop,308-44);
    assert.equal(g.actorScaleX,.65);assert.equal(g.actorScaleY,.63);
});
test('卡片高度与间隔保持，近七天增加44像素且底部位置不变',()=>{
    const g=setup().geometry;
    assert.equal(g.summaryHeight,166);assert.equal(g.weekTop-g.summaryTop-g.summaryHeight,14);
    assert.equal(g.weekTop+g.weekHeight,710);assert.equal(g.weekHeight,222+44);
});
test('刻度可用高度完整落在卡片内且大于旧版79像素',()=>{
    const g=setup().geometry;
    assert.equal(g.plotHeight+131,g.weekHeight);assert.equal(g.plotHeight,135);assert.ok(g.plotHeight>79);
});
for(const [score,height] of [[0,0],[25,33.75],[50,67.5],[75,101.25],[100,135]])
    test(score+'分按相同比例映射至增高的绘图区',()=>assert.equal(setup().barHeight(score),height));
test('超出区间的分数钳制边界',()=>{const m=setup();assert.equal(m.barHeight(-20),0);assert.equal(m.barHeight(110),135);});
test('缺失值和非数值不能制造有效柱子高度',()=>{
    const m=setup();for(const v of [null,undefined,NaN,Infinity,'100',{},false])assert.equal(m.barHeight(v),0);
});
test('数值映射单调且精确，分数并未被布局改动',()=>{
    const m=setup();let previous=-1;
    for(let score=0;score<=100;score++){const h=m.barHeight(score);assert.ok(h>=previous&&h<=135);assert.ok(Math.abs(h/135-score/100)<1e-12);previous=h;}
});
test('CSS与Canvas取同一坐标且配置只读',()=>{
    const m=setup(), applied={};m.applyLayout({style:{setProperty(k,v){applied[k]=v;}}});
    assert.equal(applied['--review-summary-top'],'264px');assert.equal(applied['--review-plot-height'],'135px');
    assert.equal(applied['--review-week-top'],'444px');assert.equal(applied['--review-week-height'],'266px');
    assert.ok(Object.isFrozen(m.geometry));assert.equal(Object.keys(applied).length,7);
});
