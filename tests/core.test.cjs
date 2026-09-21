const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
/**
 * 输入：模块文件名。
 * 输出：该文件导出的模块对象。
 * 功能：在隔离上下文执行真实源码，不引入浏览器或真实网络。
 */
function moduleOf(name) {
    const context = vm.createContext({console, Intl});
    vm.runInContext('const __fluffyModules = Object.create(null);', context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'js', name), 'utf8'), context);
    return vm.runInContext(`__fluffyModules[${JSON.stringify(name)}]`, context);
}
const { MicrophonePermission } = moduleOf('microphone-permission.js');
const { validateRecord, mayApplyField, circularPositions } = moduleOf('model.js');

// 输入：两个并发授权调用。输出：同一 Promise、一次申请和一次释放。功能：防止重复弹框。
test('concurrent authorization is single-flight and stops every acquired track', async () => {
    let calls=0, stops=0, resolve;
    const mic = new MicrophonePermission({mediaDevices:{getUserMedia(){calls++;return new Promise(r=>resolve=r);}}});
    const a=mic.authorize(), b=mic.authorize();
    assert.equal(a,b); assert.equal(calls,1);
    resolve({getTracks:()=>[{stop(){stops++;}},{stop(){stops++;}}]});
    assert.equal(await a,true); assert.equal(stops,2); assert.equal(mic.task,null);
});
// 输入：浏览器已授予或撤销的权限。输出：以浏览器状态为准。功能：不把本地标志当作权限。
test('browser permission state overrides an earlier cached grant', async () => {
    let state='granted'; const mic = new MicrophonePermission({permissions:{query:async()=>({state})}});
    assert.equal(await mic.status(),'granted');
    state='denied';assert.equal(await mic.status(),'denied');assert.equal(mic.granted,false);
});
// 输入：没有 microphone 查询能力的浏览器。输出：仅本页实际授权后才记住授权事实。功能：兼容性回退。
test('unsupported permission query does not prompt or invent a grant', async () => {
    let calls=0;
    const mic = new MicrophonePermission({permissions:{query:async()=>{throw Error('unsupported');}},mediaDevices:{getUserMedia:async()=>{calls++;return {getTracks:()=>[{stop(){}}]};}}});
    assert.equal(await mic.status(),'unknown'); assert.equal(calls,0);
    await mic.authorize();assert.equal(await mic.status(),'granted');assert.equal(calls,1);
});
// 输入：一次被拒绝的许可请求。输出：拒绝且任务清空。功能：允许后续由用户主动重试。
test('denied authorization leaves no success flag or stuck promise', async () => {
    const mic = new MicrophonePermission({mediaDevices:{getUserMedia:async()=>{const e=new Error('denied');e.name='NotAllowedError';throw e;}}});
    await assert.rejects(mic.authorize(),{name:'NotAllowedError'});
    assert.equal(mic.granted,false);assert.equal(mic.task,null);
});
// 输入：用户填写的四项数字与文字。输出：规范化记录。功能：防止界面精简改变原有校验。
test('manual fields accept decimal kilometres and minutes', () => {
    const result=validateRecord({activity:'跑步',distanceKm:'5.25',durationMinutes:'32.5',notes:'轻松'});
    assert.equal(result.ok,true);assert.equal(result.value.durationMinutes,32.5);
    assert.equal(validateRecord({activity:'跑步',distanceKm:'5',durationMinutes:'30',notes:''}).ok,false);
});
// 输入：正在返回的模型结果和被用户修改的版本。输出：禁止覆盖。功能：保护用户编辑。
test('late model responses cannot replace manually edited fields', () => {
    assert.equal(mayApplyField('notes',{notes:1},{notes:2}),false);
    assert.equal(mayApplyField('activity',{activity:1},{activity:1}),true);
});
// 输入：相差一整圈的滚动位置。输出：同一可见分布。功能：已写内容循环时不会消失。
test('record rows preserve seamless circular positioning', () => {
    assert.deepEqual(Array.from(circularPositions(1,-90)),Array.from(circularPositions(1,-360)));
});
