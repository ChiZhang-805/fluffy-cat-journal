"""输入：交付源码。输出：真实UI操作的断言与截图。功能：隔离存储、听写与网络，回顾逻辑/流解析/按钮手势均执行生产代码。"""
from pathlib import Path
import asyncio,json,os,time
START=time.monotonic()
from playwright.async_api import async_playwright
from browser_helpers_v5 import test_document
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('V15_OUT',ROOT.parent/'verification/v15-browser'));OUT.mkdir(parents=True,exist_ok=True)
RESULT=[]
FIXTURE=(ROOT/'tests/chat-v15-fixture.js').read_text()

def check(name,ok):
    """输入：名称与断言。输出：记录。功能：失败即停止，不把未运行项目算成通过。"""
    RESULT.append({'name':name,'passed':bool(ok)});print(f'{time.monotonic()-START:.1f}s '+('PASS ' if ok else 'FAIL ')+name,flush=True);assert ok,name

async def screen(p,name):
    """输入：页面与文件名。输出：截图。功能：只截实际手机界面，无AI生成图。"""
    await p.locator('#phone').screenshot(path=str(OUT/(name+'.png')),timeout=8000)

async def open_review(p,category='sport',lang='zh'):
    """输入：类别与语言。输出：待机回顾。功能：构造测试入口，避免首次AI问候消耗测试响应。"""
    await p.evaluate('''([cat,lang])=>{FluffyDebug.apiTest.clear();FluffyDebug.changeLanguage(lang);FluffyDebug.navigate('review');FluffyDebug.review.open(cat);FluffyDebug.review.cancel(false);FluffyDebug.review.speech.env=__speechEnv;FluffyDebug.microphone.status=async()=>"granted";FluffyDebug.apiTest.setKey('sk-fixture-key-not-a-real-secret');__chatPlans=[];}''',[category,lang])
    await p.wait_for_timeout(150)

async def hold(p,text,plan=None,release=True):
    """输入：人工转写与模型计划。输出：无。功能：真实鼠标长按/松手，不直接伪造ReviewPage状态。"""
    await p.evaluate('([text,plan])=>{__spoken=text;if(plan)__chatPlans.push(plan)}',[text,plan])
    box=await p.locator('#review-chat').bounding_box();await p.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);await p.mouse.down()
    await p.wait_for_function('FluffyDebug.review.phase==="listening"',timeout=8000)
    await p.wait_for_timeout(65)
    if release:await p.mouse.up()

async def ready(p):
    """输入：页面。输出：无。功能：等待真实网络替身结束及至少一条气泡出现。"""
    await p.wait_for_function('FluffyDebug.review.phase==="speaking"&&!FluffyDebug.review.turn?.generating',timeout=8000)

async def run():
    """输入：无。输出：验证报告。功能：针对第二轮以后与随时打断验证实际交付逻辑。"""
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=await b.new_page(viewport={'width':1100,'height':1000});errors=[];p.set_default_timeout(8000);p.on('pageerror',lambda e:errors.append(str(e)))
        await p.set_content(test_document(extra=FIXTURE));await p.wait_for_function('window.FluffyDebug&&FluffyDebug.animation.ready',timeout=15000)
        await p.evaluate('''()=>{const S=__fluffyModules['journal-store.js'],d=S.dayKey();for(let i=0;i<7;i++){const date=__fluffyModules['review-data.js'].shiftDate(d,-i);S.save({id:'test-'+i,category:'sport',recordDate:date,createdAt:date+'T10:00:00',data:{activity:'跑步',durationMinutes:12+i*3,notes:'人工演示记录'}})}}''')
        await open_review(p)
        initial_store=await p.evaluate('JSON.stringify([...__testStore])')
        baseline=await p.locator('#review-week').bounding_box()
        # 第一阶段：连续20轮，每轮来自真实按压，上一轮没显示完也可继续。
        for i in range(20):
            await hold(p,f'这是第{i+1}次，我想继续聊聊',{'text':f'第{i+1}次我也在听。你慢慢说给我听呀。'})
            await ready(p)
            check(f'第{i+1}轮长按成功，当前回答匹配',f'第{i+1}次' in await p.locator('#review-bubble').inner_text())
        check('20次转写都在当前会话且没有重复用户消息',await p.evaluate('FluffyDebug.review.history().filter(x=>x.role==="user").length===20'))
        check('按压20次后麦克风全部关闭',await p.evaluate('__stops>=20&&!FluffyDebug.review.speech.active&&!FluffyDebug.review.speech.recognition'))
        check('连续聊天未修改记录或分数存储',initial_store==await p.evaluate('JSON.stringify([...__testStore])'))
        check('连续聊天没有移动图表',baseline==await p.locator('#review-week').bounding_box())
        check('正文请求都移除了JSON模式',await p.evaluate('__chatRequests.every(x=>x.stream===true&&!x.response_format)'))
        check('最后一轮带有之前的用户话语',await p.evaluate('__chatRequests.at(-1).messages.some(x=>x.role==="user"&&x.content.includes("第19次"))'))
        # 第二阶段：一页显示时打断，尚未展示的尾句不能作为说过的内容送出。
        await hold(p,'我想说今天只有十二分钟',{'text':'今天这十二分钟，也是认真付出呀。还有一个没说完的问题。后面这句不该进入历史。'})
        await ready(p);await screen(p,'reply-first')
        before=await p.evaluate('FluffyDebug.review.memory().turns.at(-1).id')
        await hold(p,'我不是时间不够，是现在有点累',{'text':'那就歇一会儿。今天不用赶自己。'},release=False)
        check('回复尚未播完时长按立即进入倾听',await p.evaluate('FluffyDebug.review.phase==="listening"&&FluffyDebug.review.queue.length===0'))
        check('录音波形在绿色按钮，图表仍可见',await p.locator('#review-chat-wave').is_visible() and await p.locator('#review-week').is_visible())
        await screen(p,'listening');await p.mouse.up();await ready(p)
        check('未展示尾句没有带进下一轮',await p.evaluate('!JSON.stringify(__chatRequests.at(-1).messages).includes("后面这句不该进入历史")&&!JSON.stringify(__chatRequests.at(-1).messages).includes("还有一个没说完的问题")'))
        check('被打断轮次有明确标记',await p.evaluate('(id)=>FluffyDebug.review.memory().turns.find(t=>t.id===id).status==="interrupted"',before))
        check('普通感受解释不被当作修改记录',await p.evaluate('!FluffyDebug.review.pendingIntent'))
        await screen(p,'reply-next')
        # 第三阶段：思考中、淡出中、听写收尾中及旧响应晚到。
        await hold(p,'这句等待网络',{'wait':True});await p.wait_for_function('FluffyDebug.review.phase==="thinking"&&!!__streams.at(-1).controller')
        stream_index=await p.evaluate('__streams.length-1')
        await hold(p,'不等了，我先说新的',{'text':'好呀，我接着听。'})
        await ready(p)
        check('思考时再次长按取消旧网络流',await p.evaluate('(i)=>__streams[i].cancelled',stream_index))
        check('思考打断后没有旧错误盖住新回复','我接着听' in await p.locator('#review-bubble').inner_text())
        await hold(p,'看看淡出时能否说话',{'text':'我在听你说。下一句还没出现。'})
        await ready(p);await p.evaluate('()=>{const r=FluffyDebug.review;r.queueElapsed=r.queueDuration;r.tick()}');await p.wait_for_function('document.getElementById("review-bubble").classList.contains("fading")')
        await hold(p,'淡出中我又开口了',{'text':'现在先听你说。'})
        await ready(p);check('淡出过程中重新长按不会卡在透明气泡',not await p.locator('#review-bubble').evaluate('e=>e.classList.contains("fading")'))
        await p.evaluate('__tailDelay=1000');await hold(p,'迟到的旧转写',{'text':'旧的结果。'});await p.wait_for_function('FluffyDebug.review.phase==="settling"')
        request_count=await p.evaluate('__chatRequests.length');await p.evaluate('__chatPlans=[];__tailDelay=35')
        await hold(p,'新的转写才算数',{'text':'新的一句听到了。'})
        await ready(p);await p.wait_for_timeout(650)
        check('等待转写尾句时可打断，旧转写未提交',await p.evaluate('(n)=>__chatRequests.length===n+1&&!__chatRequests.at(-1).messages.at(-1).content.includes("迟到的旧")',request_count))
        # 即使测试网络故意忽略abort、在新轮后才返回旧HTTP头，也不能插入旧答案。
        await hold(p,'旧请求等着回头',{'lateHeaders':True});await p.wait_for_function('!!window.__lateHeaders')
        await hold(p,'这一次新问题优先',{'text':'这次先听新的话。'});await ready(p)
        await p.evaluate('()=>{__lateHeaders()}');await p.wait_for_timeout(100)
        check('忽略abort的迟到HTTP响应不能覆盖新轮', '新的话' in await p.locator('#review-bubble').inner_text())
        check('旧请求未显示内容不进入聊天历史',await p.evaluate('!JSON.stringify(FluffyDebug.review.history()).includes("迟到的旧答案")'))
        # 重复松手只发送一次。
        request_count=await p.evaluate('__chatRequests.length')
        await hold(p,'只提交一遍这句',{'text':'只记这一轮。'},release=False)
        await p.mouse.up();await p.evaluate('FluffyDebug.review.release();FluffyDebug.review.release()');await ready(p)
        check('重复松手回调不重复请求',await p.evaluate('(n)=>__chatRequests.length===n+1',request_count))
        # 第四阶段：空回复、有限重试、失败后原话恢复。
        request_count=await p.evaluate('__chatRequests.length')
        await p.evaluate('__chatPlans=[{text:""},{text:"刚才没接上，现在听到啦。"}]')
        await hold(p,'这句只需重试一次');await ready(p)
        check('明确空回复自动恢复一次',await p.evaluate('(n)=>__chatRequests.length===n+2',request_count))
        await p.evaluate('__chatPlans=[{text:""},{text:""}]');await hold(p,'失败也留住我的话')
        await p.wait_for_function('FluffyDebug.review.retryPending',timeout=8000)
        logical=await p.evaluate('FluffyDebug.review.pendingMessage.turnId');await screen(p,'retry')
        count_users=await p.evaluate('FluffyDebug.review.history().filter(x=>x.role==="user").length')
        await p.evaluate('__chatPlans=[{text:"你的话我听到啦。"}]');await p.locator('#review-bubble').click();await ready(p)
        check('点气泡重试使用同一消息，不重复用户历史',await p.evaluate('([n,id])=>FluffyDebug.review.history().filter(x=>x.role==="user").length===n&&FluffyDebug.review.memory().turns.at(-1).id===id',[count_users,logical]))
        check('重试成功清除旧失败状态',await p.evaluate('!FluffyDebug.review.retryPending&&!FluffyDebug.review.pendingMessage'))
        # 流中途截断只保留完整短句。
        request_count=await p.evaluate('__chatRequests.length')
        await hold(p,'接收一部分也别从头重播',{'text':'这一句已经收到了。后面还没说完','finish':'length'})
        await ready(p)
        check('截断后没有从头自动重试',await p.evaluate('(n)=>__chatRequests.length===n+1',request_count))
        check('不完整尾句没有上屏/入历史',await p.evaluate('!FluffyDebug.review.history().at(-1).content.includes("后面还没说完")'))
        await hold(p,'断开后我接着说',{'text':'好呀，你继续说。'});await ready(p)
        check('失败后直接下一轮仍正常','你继续说' in await p.locator('#review-bubble').inner_text())
        # 辅助意图错误不能改聊天结果。
        await p.evaluate('()=>{window.__intentOld=__fluffyModules["record-intent.js"].infer;__fluffyModules["record-intent.js"].infer=async()=>{throw new Error("fixture side task failed")}}')
        await hold(p,'帮我记录今天又跑了三分钟',{'text':'我们就慢慢聊。'});await ready(p);await p.wait_for_timeout(80)
        check('记事辅助任务失败不遮住正常聊天','我们就慢慢聊' in await p.locator('#review-bubble').inner_text())
        await p.evaluate('()=>{__fluffyModules["record-intent.js"].infer=__intentOld}')
        # 听写失败不是模型失败。
        await hold(p,'',None,release=False);await p.evaluate('__recognition.onerror({error:"network"})');await p.mouse.up();await p.wait_for_timeout(100)
        check('听写网络故障由气泡明确说明','听写服务' in await p.locator('#review-bubble').inner_text())
        # 隔离日期板块、英文、键盘与所有视口。
        for cat in ['sport','food','sleep','mood','face','focus']:
            await open_review(p,cat)
            await hold(p,'在这个板块聊一句',{'text':'我会认真听你说。'});await ready(p)
            check(cat+'回顾可多轮对话，不导航离开',await p.evaluate('(c)=>FluffyDebug.review.view.id===c&&FluffyDebug.animation.scene==="review"',cat))
        await open_review(p,'sport','en');await hold(p,'Can we keep talking?',{'text':'Yes, I am here. We can take our time.'});await ready(p)
        check('英文短句不含汉字',not await p.locator('#review-bubble').evaluate('e=>/[\u3400-\u9fff]/.test(e.textContent)'))
        await screen(p,'english')
        await open_review(p,'sport')
        await p.evaluate('__chatPlans=[{text:"今天这十二分钟，也是认真付出呀。"}];__spoken="检查长句排版"')
        await p.locator('#review-chat').focus();await p.keyboard.down('Space');await p.wait_for_function('FluffyDebug.review.phase==="listening"');await p.keyboard.up('Space');await ready(p)
        check('空格长按和松开使用同一套多轮流程','十二分钟' in await p.locator('#review-bubble').inner_text())
        for w,h in [(1440,1000),(1100,1000),(393,852),(375,812),(320,740),(430,932)]:
            await p.set_viewport_size({'width':w,'height':h});await p.wait_for_timeout(120)
            check(f'{w}视口气泡没有溢出且至多两行',await p.locator('#review-bubble').evaluate('e=>e.scrollWidth<=e.clientWidth+1&&e.textContent.split("\\n").length<=2'))
        await p.set_viewport_size({'width':1100,'height':1000})
        check('所有诊断事件不含原话/Key/模型回复',await p.evaluate('!JSON.stringify(FluffyChatDiagnostics.snapshot()).includes("sk-")&&!JSON.stringify(FluffyChatDiagnostics.snapshot()).includes("十二分钟")'))
        check('当前会话数据不写浏览器持久存储',await p.evaluate('![...__testStore.keys()].some(k=>/chat|conversation|turn/i.test(k))'))
        check('全过程没有脚本异常',not errors)
        await screen(p,'final')
        await b.close()
    (OUT/'results.json').write_text(json.dumps({'passed':len(RESULT),'results':RESULT,'pageErrors':errors,'scope':'In-memory document executes delivered source. SSE, speech events and storage are explicit test fixtures; not a real microphone/API test.'},ensure_ascii=False,indent=2))
if __name__=='__main__':asyncio.run(run())
