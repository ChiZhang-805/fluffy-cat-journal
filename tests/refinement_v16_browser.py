"""输入：交付源码。输出：v16浏览器断言/截图。功能：真实DOM交互，外部听写/API响应明确替身。"""
from pathlib import Path
import asyncio,json,os,time
from playwright.async_api import async_playwright
from browser_helpers_v5 import test_document
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('V16_OUT',ROOT.parent/'verification/v16-browser'));OUT.mkdir(parents=True,exist_ok=True)
RESULT=[]
FIXTURE=(ROOT/'tests/chat-v15-fixture.js').read_text()
DATA={
 'sport':{'activity':'跑步','durationMinutes':30,'notes':'跑了三公里，感觉有点累'},
 'food':{'meal':'午餐','foods':'米饭与鸡肉','portion':'米饭一碗，鸡肉100克','calories':620,'protein':32,'carbs':80,'fat':19,'notes':'和朋友一起吃饭'},
 'sleep':{'bedtime':'23:00','wakeTime':'07:00','quality':'还有点困','notes':'夜里醒过一次'},
 'mood':{'mood':'有点失落，也松了一口气','reason':'完成了工作','notes':'慢慢来'},
 'face':{'feeling':'有点累','eyeArea':'有阴影','skinAppearance':'局部泛红','notes':'室内光线'},
 'focus':{'task':'读论文的方法部分','durationMinutes':25,'notes':'记下两个关键点'}
}

def check(name,value):
    """输入：名称/结果。输出：断言记录。功能：不把未执行测试当通过。"""
    RESULT.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name

async def screenshot(p,name):
    """输入：页面/名称。输出：运行截图。功能：展示真实生产界面，不合成UI。"""
    await p.locator('#phone').screenshot(path=str(OUT/(name+'.png')))

async def open_entry(p,id,values=None):
    """输入：类别/字段。输出：打开的表单。功能：使用公开测试钩子导航，渲染仍由生产代码实现。"""
    await p.evaluate('([id,v])=>{FluffyDebug.apiTest.clear();FluffyDebug.openEntry(id,v||{});}',[id,values])
    await p.wait_for_timeout(70)

async def start_job(p,text,result,wait=False):
    """输入：人工原话/模型响应。输出：进行中的整理。功能：只替换网络响应，执行真实字段契约/校验/状态生命周期。"""
    await p.evaluate('''([text,fields,wait])=>{
        const d=FluffyDebug; window.__entryCalls=[];
        d.apiTest.setKey('sk-fixture-not-a-real-key');
        d.apiTest.fetch=async(url,o)=>{
            const payload=JSON.parse(o.body);__entryCalls.push(payload);
            if(wait) return new Promise(resolve=>{window.__resolveEntry=()=>resolve(Response.json({choices:[{finish_reason:'stop',message:{content:JSON.stringify({fields,warnings:[],emotion:{basis:"explicit",evidence:"合成测试明确自述"}})}}]}));});
            return Response.json({choices:[{finish_reason:'stop',message:{content:JSON.stringify({fields,warnings:[],emotion:{basis:"explicit",evidence:"合成测试明确自述"}})}}]});
        };
        const pending={category:d.state.category,date:d.state.recordDate,editingId:d.state.editingId,versions:{...d.state.versions},current:d.rawForm(),question:d.state.lastQuestion,text,interim:false};
        d.state.pendingUtterance=pending;window.__job=d.organizeWords(pending,d.state.serial);
    }''',[text,result,wait])
    if not wait:await p.evaluate('__job')

async def run():
    """输入：无。输出：回归报告。功能：覆盖六类流程、两秒跳过、字段保护、后台恢复及真实流解析。"""
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=await b.new_page(viewport={'width':1100,'height':1050});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_default_timeout(8000)
        await p.set_content(test_document(extra=FIXTURE));await p.wait_for_function('window.FluffyDebug&&FluffyDebug.animation.ready',timeout=15000)
        check('实际页面资源全部就绪',await p.evaluate('FluffyDebug.animation.ready'))
        # 保存长笔记：实际等待两秒，不通过动画跳时间解锁。
        await open_entry(p,'food',DATA['food']);await p.evaluate('FluffyDebug.confirmManual()')
        check('饮食进入实际书写页',await p.evaluate('FluffyDebug.animation.scene==="record"'))
        await p.locator('#primary').click(force=True)
        check('两秒内点击无效且没有提示文本',await p.evaluate('FluffyDebug.animation.scene==="record"&&__fluffyModules["journal-store.js"].records().length===0&&document.getElementById("phone-toast").hidden'))
        check('两秒内没有改按钮文字或展示倒计时',await p.locator('#primary-label').inner_text()=='继续')
        await p.evaluate('FluffyDebug.animation.playing=false')
        await p.wait_for_timeout(2050)
        check('暂停动画后两秒门闩与无障碍状态仍独立开放',await p.locator('#primary').get_attribute('aria-disabled')=='false')
        check('长笔记仍在书写但两秒门闩已开放',await p.evaluate('FluffyDebug.animation.time<FluffyDebug.animation.writeEnd&&FluffyDebug.continueGate.ready()'))
        await p.evaluate('FluffyDebug.animation.playing=true')
        await screenshot(p,'writing-skippable')
        await p.locator('#primary').click();await p.evaluate('FluffyDebug.primaryAction()')
        check('跳过后进入庆祝只保存一条',await p.evaluate('FluffyDebug.animation.scene==="celebrate"&&__fluffyModules["journal-store.js"].records().length===1'))
        rec=await p.evaluate('__fluffyModules["journal-store.js"].records()[0].data')
        check('尚未画出的完整饮食营养也保存',all(rec.get(k)==v for k,v in DATA['food'].items()))
        await p.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render();FluffyDebug.primaryAction()')
        check('庆祝完成进入同一板块回顾',await p.evaluate('FluffyDebug.animation.scene==="review"&&FluffyDebug.review.view.id==="food"'))
        # 六类表单/AI字段契约/确认与回顾。
        for id in DATA:
            await open_entry(p,id)
            await start_job(p,'合成测试：本轮'+id,DATA[id])
            raw=await p.evaluate('FluffyDebug.rawForm()')
            check(id+'：AI字段通过真实校验回填',all(str(raw.get(k))==str(v) for k,v in DATA[id].items()))
            check(id+'：一次整理只有一个模型请求',await p.evaluate('__entryCalls.length===1'))
            check(id+'：请求关闭思考且含每个字段的含义',await p.evaluate('__entryCalls[0].thinking.type==="disabled"&&__entryCalls[0].messages[0].content.includes("逐字段填写说明")'))
            await p.evaluate('FluffyDebug.apiTest.clear();FluffyDebug.confirmManual()')
            if id=='focus':
                check('专注不被书写跳过绕过计时',await p.evaluate('FluffyDebug.animation.scene==="focus"&&FluffyDebug.timer.state==="running"'))
                await p.evaluate('FluffyDebug.timer.pause();FluffyDebug.navigate("home")')
                continue
            await p.wait_for_timeout(2010);await p.locator('#primary').click()
            check(id+'：书写跳过保存到正确类别',await p.evaluate('(id)=>__fluffyModules["journal-store.js"].records().some(r=>r.category===id)',id))
            await p.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render();FluffyDebug.primaryAction()')
            check(id+'：回顾入口及无底部报错条',await p.evaluate('(id)=>FluffyDebug.review.view.id===id&&document.getElementById("phone-toast").hidden',id))
        # 同日已存在记录，整理也不等待第二次意图模型。
        await open_entry(p,'sport')
        await start_job(p,'跑了半小时，三公里',DATA['sport'])
        check('有旧记录仍直接回填，不额外串行意图请求',await p.evaluate('__entryCalls.length===1&&FluffyDebug.state.phase==="idle"'))
        # 追问上下文：用户只答“半小时”也有明确字段。
        await open_entry(p,'sport',{'activity':'跑步','notes':'三公里'})
        await p.locator('#confirm-entry').click();await p.wait_for_timeout(60)
        check('缺时长时问题状态确实绑定到已显示气泡',await p.evaluate('FluffyDebug.state.lastQuestion.field==="durationMinutes"'))
        await start_job(p,'半小时',{'durationMinutes':30})
        check('简短回答请求含lastQuestion与原表单，不擦掉项目备注',await p.evaluate('__entryCalls[0].messages[1].content.includes("lastQuestion")&&document.getElementById("field-activity").value==="跑步"&&document.getElementById("field-notes").value==="三公里"'))
        await screenshot(p,'followup-filled')
        # 后台仍有限处理已经提交的文字，不留下假思考；已有最终结果返回即可继续。
        await open_entry(p,'sleep')
        await start_job(p,'昨晚23:00睡到07:00，还有点困',DATA['sleep'],True)
        await p.wait_for_function('__entryCalls.length===1')
        check('模型未结束明确睡眠时间已形成草稿',await p.evaluate('document.getElementById("field-bedtime").value==="23:00"&&document.getElementById("field-wakeTime").value==="07:00"'))
        await screenshot(p,'sleep-early-draft')
        await p.evaluate('Object.defineProperty(document,"hidden",{value:true,configurable:true});document.dispatchEvent(new Event("visibilitychange"))')
        check('后台不取消已提交的文本整理',await p.evaluate('FluffyDebug.state.phase==="thinking"&&!FluffyDebug.state.task.signal.aborted'))
        await p.evaluate('__resolveEntry();__job')
        await p.evaluate('Object.defineProperty(document,"hidden",{value:false,configurable:true});document.dispatchEvent(new Event("visibilitychange"))')
        check('回来后按钮和气泡结束思考',await p.evaluate('FluffyDebug.state.phase==="idle"&&!document.getElementById("entry-bubble").textContent.includes("整理你的话")'))
        # 取消后旧响应不得覆盖；气泡可恢复，输入保留。
        await open_entry(p,'sport')
        await start_job(p,'今天跑了30分钟',DATA['sport'],True)
        await p.evaluate('FluffyDebug.cancelWork(false)')
        check('取消后不残留思考文案，原话可重试',await p.evaluate('FluffyDebug.state.speechRetry&&document.getElementById("entry-bubble").textContent.includes("停下")'))
        await p.evaluate('__resolveEntry();__job')
        check('被取消的迟到结果未回填',await p.locator('#field-activity').input_value()=='')
        # 等待期间手工改值优先，包括清空。
        await open_entry(p,'sport')
        await start_job(p,'跑步三十分钟',DATA['sport'],True)
        await p.locator('#field-durationMinutes').fill('25');await p.locator('#field-notes').fill('我的新备注')
        await p.evaluate('__resolveEntry();__job')
        check('用户新输入不会被迟到响应覆盖',await p.locator('#field-durationMinutes').input_value()=='25' and await p.locator('#field-notes').input_value()=='我的新备注')
        # 明确清空只改一项；真正修正不新增行数。
        saved=await p.evaluate('__fluffyModules["journal-store.js"].records().find(r=>r.category==="sport")')
        await p.evaluate('(r)=>FluffyDebug.openEntry("sport",r.data,r)',saved)
        await start_job(p,'时长改成25分钟',{'durationMinutes':25})
        check('编辑补丁保留原项目与备注',await p.locator('#field-activity').input_value()==saved['data']['activity'] and await p.locator('#field-notes').input_value()==saved['data']['notes'])
        n=await p.evaluate('__fluffyModules["journal-store.js"].records().length')
        await p.evaluate('FluffyDebug.apiTest.clear();FluffyDebug.confirmManual()');await p.wait_for_timeout(2010);await p.locator('#primary').click()
        check('编辑保存更新原ID而不新增',await p.evaluate('([id,n])=>{const a=__fluffyModules["journal-store.js"].records();return a.length===n&&a.find(r=>r.id===id).data.durationMinutes===25}',[saved['id'],n]))
        # save failure does not celebrate and gate unlocks
        await open_entry(p,'sport',DATA['sport']);await p.evaluate('FluffyDebug.confirmManual()');await p.wait_for_timeout(2010)
        await p.evaluate('window.__save=__fluffyModules["journal-store.js"].save;__fluffyModules["journal-store.js"].save=()=>false')
        await p.locator('#primary').click()
        check('保存失败留在笔记页可重试，未假庆祝',await p.evaluate('FluffyDebug.animation.scene==="record"&&!FluffyDebug.continueGate.locked'))
        await p.evaluate('__fluffyModules["journal-store.js"].save=__save')
        # 前两秒按下后跨边界松开
        await open_entry(p,'sport',DATA['sport']);await p.evaluate('FluffyDebug.confirmManual()')
        box=await p.locator('#primary').bounding_box();await p.mouse.move(box['x']+50,box['y']+25);await p.mouse.down();await p.wait_for_timeout(2100);await p.mouse.up()
        check('两秒内按下两秒后松手仍无效',await p.evaluate('FluffyDebug.animation.scene==="record"'))
        await p.locator('#primary').click();check('下一次新点击正常继续',await p.evaluate('FluffyDebug.animation.scene==="celebrate"'))
        # 可爱短句和英文错误均不出底部条
        await open_entry(p,'sport');await p.evaluate('FluffyDebug.confirmManual()');await screenshot(p,'question-sport')
        await p.evaluate('FluffyDebug.changeLanguage("en")');await p.evaluate('FluffyDebug.confirmManual()')
        check('英文缺项提示不混中文',not any('\u3400'<=c<='\u9fff' for c in await p.locator('#entry-bubble').inner_text()))
        await screenshot(p,'question-english')
        # 直接用真实流播放器检查加强后的语气提示确实进入API
        await p.evaluate('''()=>{FluffyDebug.changeLanguage('zh');FluffyDebug.apiTest.clear();FluffyDebug.navigate('review');FluffyDebug.review.open('sport');FluffyDebug.review.cancel(false);FluffyDebug.apiTest.fetch=window.fetch;FluffyDebug.apiTest.setKey('sk-fixture-not-real');__chatPlans=[{text:'今天有些累了呀。先缓一缓也很好。是身体累，还是心里累呀？'}];window.__talk=FluffyDebug.review.send('今天有点累');}''')
        await p.evaluate('__talk');await p.wait_for_timeout(100)
        check('回顾聊天请求实际包含疲惫/抱怨/不追问规则',await p.evaluate('__chatRequests.at(-1).messages[0].content.includes("被抱怨/辱骂")'))
        check('回复依旧16字以内、最多两行',await p.evaluate('(()=>{const a=document.getElementById("review-bubble").textContent;return [...a.replace(/\\s/g,"")].length<=16&&a.split("\\n").length<=2})()'))
        await screenshot(p,'supportive-reply')
        check('不同整理轮次有独立计时记录',await p.evaluate('FluffyDebug.Trace.read().filter(r=>r.events.some(e=>e.stage==="extract")).length>=8'))
        check('诊断只含时序，不含字段内容或凭据',await p.evaluate('!JSON.stringify(FluffyDebug.Trace.read()).includes("三公里")&&!JSON.stringify(FluffyDebug.Trace.read()).includes("sk-")'))
        check('无JavaScript未捕获异常',not errors)
        (OUT/'results.json').write_text(json.dumps({'passed':len(RESULT),'checks':RESULT,'pageErrors':errors,'boundary':'API and microphone are explicit fixtures; not a live model evaluation.'},ensure_ascii=False,indent=2))
        await b.close()
if __name__=='__main__':asyncio.run(run())
