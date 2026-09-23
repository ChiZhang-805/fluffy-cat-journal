"""输入：最终v17 HTML。输出：实际DOM检查与截图。功能：验证首用/回访/保存/原首页，使用隔离存储，不调用API。"""
from pathlib import Path
import asyncio, json, sys, datetime
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'NAVA-Fluffy-v17.html'
OUT=ROOT.parent/'verification/v17-browser';OUT.mkdir(parents=True,exist_ok=True)
HTML=SOURCE.read_text();CHECKS=[];ERRORS=[]
BASE={'version':4,'language':'zh','gender':'male','role':'student','age':'18-24','interests':['movement','games','outdoors'],'sleep':'7to8','exercise':'2to4','diet':['protein','restrictions']}
DONE={**BASE,'completedAt':'2026-09-23T10:00:00Z'}
DRAFT_KEY='nava-first-notes-draft-v1';PROFILE_KEY='nava-first-notes-v3'

def check(name,value):
    """输入：名称、布尔结果。输出：断言记录。功能：只报告实际执行的检查。"""
    CHECKS.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name

async def new_page(browser,store=None,lang='zh',width=1200,height=1000,reduce=True,debug=False):
    """输入：初始测试存储、视口。输出：运行实际HTML的页面。功能：about:blank隔离环境模拟本机存储，无网络或真实资料。"""
    p=await browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce' if reduce else 'no-preference')
    p.set_default_timeout(12000);p.on('pageerror',lambda e:ERRORS.append(str(e)))
    await p.evaluate('''([entries,debug])=>{window.FLUFFY_TEST=debug;window.__store=new Map(entries);window.__failSave=false;
        Object.defineProperty(window,'localStorage',{value:{getItem:k=>__store.get(k)??null,setItem:(k,v)=>{if(__failSave&&k==='nava-first-notes-v3')throw Error('quota fixture');__store.set(k,String(v));},removeItem:k=>__store.delete(k)}});
    }''',[list((store or {}).items()),debug])
    await p.set_content(HTML,wait_until='load')
    return p

async def first_frame(p):
    """输入：宿主页。输出：初始化后的真实引导frame。功能：等待素材而不伪造完成动作。"""
    await p.wait_for_selector('#nava-onboarding-frame')
    f=await p.locator('#nava-onboarding-frame').element_handle();f=await f.content_frame()
    await f.wait_for_function('window.NavaOnboarding?.getState().ready')
    return f

async def wait_step(f,step):
    """输入：frame、步骤。输出：无。功能：等待实际翻签动画完成后再操作。"""
    await f.wait_for_function('(s)=>NavaOnboarding.getStep()===s&&!NavaOnboarding.getState().transition',arg=step)

async def snapshot(p):
    """输入：运行页。输出：仅测试存储快照。功能：为下一独立文档模拟关闭后重开，不保留测试会话代码。"""
    return dict(await p.evaluate('[...__store.entries()]'))

async def summary_metrics(f):
    """输入：汇总frame。输出：布局测量。功能：检查首屏整行边界和统一间距。"""
    return await f.evaluate('''()=>{const s=document.querySelector('.summary-scroll'),b=s.getBoundingClientRect();return {height:s.clientHeight,scrollHeight:s.scrollHeight,top:s.scrollTop,last:s.dataset.firstLast,rows:[...s.querySelectorAll('.summary-row')].map(r=>({key:r.dataset.edit,top:r.offsetTop,h:r.offsetHeight,pad:getComputedStyle(r).paddingTop,visibleTop:r.getBoundingClientRect().top-b.top,visibleBottom:r.getBoundingClientRect().bottom-b.top}))};}''')

async def run():
    """输入：无。输出：证据JSON与真实程序截图。功能：覆盖两种语言、恢复、权限校验、长汇总与原记录流程。"""
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=await new_page(b);f=await first_frame(p)
        check('第一次打开是欢迎页，不先闪出记录首页',await f.evaluate('NavaOnboarding.getStep()==="welcome"') and not await p.locator('.provider-toolbar').is_visible())
        check('生产文件没有注入测试数据或真人API Key',not any(x in HTML for x in ['window.__store=new Map','FixtureRecognition','fixture-sport-v17']))
        await f.locator('#device').screenshot(path=str(OUT/'welcome.png'))
        # Forged completion from an unrelated Window/source cannot bypass the wizard.
        await p.evaluate('(data)=>window.dispatchEvent(new MessageEvent("message",{data:{channel:document.getElementById("nava-onboarding-frame").name,type:"complete",profile:data},origin:location.origin,source:window}))',BASE)
        check('伪造完成消息不能绕过来源校验',await p.evaluate('localStorage.getItem("nava-first-notes-v3")===null'))
        await f.locator('#next').click();await wait_step(f,'gender')
        await p.keyboard.press('Alt+ArrowRight');await f.wait_for_timeout(120)
        check('未填写时无法向后翻',await f.evaluate('NavaOnboarding.getStep()==="gender"'))
        for key,indices in [('gender',[0]),('role',[0]),('age',[0]),('interests',[0,3,4]),('sleep',[0]),('exercise',[3]),('diet',[2,5])]:
            await wait_step(f,key)
            if key=='sleep':
                lines=await f.locator('.sleep .option-label').evaluate_all('(a)=>a.map(n=>({text:n.textContent,height:n.clientHeight,line:parseFloat(getComputedStyle(n).lineHeight),overflow:n.scrollWidth>n.clientWidth+1}))')
                check('睡眠第一项为＜5 小时，不拆出第二行',lines[0]['text']=='＜5 小时' and all(n['height']<=n['line']+1 and not n['overflow'] for n in lines))
                await f.locator('#device').screenshot(path=str(OUT/'sleep.png'))
            for i in indices: await f.locator(f'[data-question="{key}"][data-index="{i}"]').click()
            if key in ['interests','diet']:await f.locator('#next').click()
        await wait_step(f,'summary');await f.wait_for_timeout(50)
        check('汇总页标题已改，不再称第一页写好',await f.locator('#headline').inner_text()=='从今天起，慢慢认识你。')
        check('未点最终按钮之前没有完成标记',await p.evaluate('localStorage.getItem("nava-first-notes-v3")===null'))
        m=await summary_metrics(f);visible=m['rows'][:6]
        check('三项喜欢换为两行后，首屏准确到运动',m['last']=='exercise' and abs(visible[-1]['top']+visible[-1]['h']-m['height'])<=1)
        check('饮食偏好在首屏裁切线之外，没有半行残字',m['rows'][6]['top']>=m['height']-.5)
        check('汇总各字段上下间距统一',len(set(r['pad'] for r in m['rows']))==1)
        check('长汇总有真实有限滚动而非删掉末项',m['scrollHeight']>m['height'])
        await f.locator('#device').screenshot(path=str(OUT/'summary.png'))
        await f.locator('.summary-scroll').evaluate('(n)=>n.scrollTop=n.scrollHeight')
        m=await summary_metrics(f)
        check('滑到底完整看到饮食偏好',m['rows'][6]['visibleTop']>=0 and m['rows'][6]['visibleBottom']<=m['height']+1)
        check('到底后有明确终点',abs(m['top']-(m['scrollHeight']-m['height']))<=1)
        await f.locator('#device').screenshot(path=str(OUT/'summary-bottom.png'))
        # Existing summary edit affordance and return/swipe preserve all choices.
        await f.locator('[data-edit="sleep"]').click();await wait_step(f,'sleep')
        check('点汇总旧项回改保留选择',await f.locator('[data-option="under5"]').get_attribute('aria-checked')=='true')
        await f.locator('[data-option="7to8"]').click();await wait_step(f,'exercise')
        await p.keyboard.press('Alt+ArrowRight');await wait_step(f,'diet');await f.locator('#next').click();await wait_step(f,'summary')
        await f.locator('#next').click();await p.wait_for_selector('#nava-first-run',state='detached')
        check('开启NAVA之旅直接到原首页，没有额外结束页',await p.locator('#screen').get_attribute('data-scene')=='home' and len(p.frames)==1)
        check('进入原首页后AI工具栏与六入口恢复可操作',await p.locator('.provider-toolbar').is_visible() and await p.locator('.home-widget').count()==6)
        check('引导没有生成任何今日记录或评分',await p.evaluate('JSON.parse(localStorage.getItem("fluffy-six-journal-v1")||"[]").length===0'))
        check('完成成功才保存七项资料',await p.evaluate('JSON.parse(localStorage.getItem("nava-first-notes-v3")).sleep==="7to8"'))
        await p.locator('#phone').screenshot(path=str(OUT/'home.png'))
        saved=await snapshot(p);await p.close()
        # A new document is used, equivalent to a browser restart with retained origin storage.
        p=await new_page(b,saved);await p.wait_for_selector('.home-widget[data-category="sport"]')
        check('再次打开不再建立引导frame',len(p.frames)==1 and await p.locator('#nava-first-run').count()==0)
        for key in ['mood','food','sport','sleep','face','focus']:
            await p.locator(f'.home-widget[data-category="{key}"]').click()
            check(key+'：原首页到对应记录页仍通',await p.locator('#screen').get_attribute('data-scene')=='entry' and await p.locator('#entry-form .field').count()>0)
            await p.locator('#back').click()
        # Finish a real manually typed sport record using the unchanged two-second continue guard.
        await p.locator('.home-widget[data-category="sport"]').click()
        for key,value in {'activity':'力量训练','durationMinutes':'25','notes':'测试：练习四组深蹲'}.items():await p.locator('#field-'+key).fill(value)
        await p.locator('#confirm-entry').click();await p.wait_for_function('document.getElementById("screen").dataset.scene==="record"')
        await p.locator('#primary').click(force=True)
        check('接入引导后原来的两秒防误触仍有效',await p.locator('#screen').get_attribute('data-scene')=='record')
        await p.wait_for_timeout(2100);await p.locator('#primary').click()
        check('书写继续保存到原日记库而不是个人资料',await p.evaluate('JSON.parse(localStorage.getItem("fluffy-six-journal-v1")).length===1'))
        await p.wait_for_timeout(5050);await p.locator('#primary').click()
        check('记录庆祝后到运动回顾，原链路不被引导替换',await p.locator('#screen').get_attribute('data-scene')=='review' and '运动回顾' in await p.locator('#review-title').inner_text())
        old=await snapshot(p);original=old['fluffy-six-journal-v1'];await p.close()
        # An old installation without onboarding completion retains its diary byte-for-byte.
        old.pop(PROFILE_KEY,None);old.pop(DRAFT_KEY,None)
        p=await new_page(b,old);f=await first_frame(p)
        check('旧版本无引导资料时只增加引导，不删除旧手记',await p.evaluate('localStorage.getItem("fluffy-six-journal-v1")')==original)
        await p.close()
        # Interrupted progress resumes at the same safely validated step.
        p=await new_page(b);f=await first_frame(p);await f.locator('#next').click();await wait_step(f,'gender');await f.locator('[data-option="female"]').click();await wait_step(f,'role')
        snap=await snapshot(p);await p.close();p=await new_page(b,snap);f=await first_frame(p)
        check('中途重开恢复到未完成步骤，非假完成',await f.evaluate('NavaOnboarding.getStep()==="role"&&NavaOnboarding.getState().answers.gender===1') and await p.evaluate('localStorage.getItem("nava-first-notes-v3")===null'))
        await p.close()
        # Max selection summaries: no half row at initial boundary in either language.
        for lang in ['zh','en']:
            profile={**BASE,'language':lang,'interests':['movement','reading','music','games','outdoors','creative'],'diet':['light','protein','lowcarb','plant','restrictions']}
            initial={DRAFT_KEY:json.dumps({'profile':profile,'step':'summary'},ensure_ascii=False)}
            p=await new_page(b,initial,width=390,height=844);f=await first_frame(p)
            m=await summary_metrics(f);edge=next(r for r in m['rows'] if r['key']==m['last'])
            check(lang+'最大多选：首屏仍停在完整条目边界',abs(edge['top']+edge['h']-m['height'])<=1)
            check(lang+'最大多选：无横向溢出',await f.locator('.summary-scroll').evaluate('(n)=>n.scrollWidth<=n.clientWidth+1'))
            check(lang+'窄屏按钮和安全区不重叠',await f.evaluate('document.getElementById("footer").offsetTop+document.getElementById("next").offsetHeight<document.querySelector(".home-indicator").offsetTop'))
            if lang=='en':
                check('英文引导汇总可见文字不混中文',not any('\u3400'<=c<='\u9fff' for c in await f.locator('#device').inner_text()))
                await f.locator('#device').screenshot(path=str(OUT/'summary-en.png'))
                await f.locator('#next').click();await p.wait_for_selector('#nava-first-run',state='detached')
                check('引导英文选择同步原APP显示语言',await p.evaluate('document.documentElement.lang==="en"'))
            await p.close()
        # Saving failure stays on the only final page; re-click after repair completes once.
        initial={DRAFT_KEY:json.dumps({'profile':BASE,'step':'summary'}),'fluffy-six-journal-v1':original}
        p=await new_page(b,initial);f=await first_frame(p);await p.evaluate('__failSave=true');await f.locator('#next').click();await f.wait_for_timeout(100)
        check('本机保存失败不进入首页、不显示假的完成页',await f.evaluate('NavaOnboarding.getStep()==="summary"&&!NavaOnboarding.getState().completed') and await f.locator('#next').is_enabled())
        check('保存失败原记录未变',await p.evaluate('localStorage.getItem("fluffy-six-journal-v1")')==original)
        await p.evaluate('__failSave=false');await f.locator('#next').click();await p.wait_for_selector('#nava-first-run',state='detached')
        check('保存重试后进入首页且旧记录仍原样',await p.evaluate('localStorage.getItem("fluffy-six-journal-v1")')==original)
        await p.locator('.home-widget[data-category="sport"]').click()
        check('今天已记过的入口仍直接到原回顾页',await p.locator('#screen').get_attribute('data-scene')=='review')
        await p.locator('#review-home').click();await p.locator('[data-nav="profile"]').click()
        await p.get_by_role('button',name='初见手记',exact=True).click();f=await first_frame(p)
        check('我的页面可以直接翻看已保存初见手记',await f.evaluate('NavaOnboarding.getStep()==="summary"'))
        await f.locator('#next').click();await p.wait_for_selector('#nava-first-run',state='detached')
        check('翻看后仍直达首页不增加记录',await p.locator('#screen').get_attribute('data-scene')=='home' and await p.evaluate('localStorage.getItem("fluffy-six-journal-v1")')==original)
        await p.close()
        # Non-reduced animation retains the same actor and progresses while paper turns.
        p=await new_page(b,reduce=False);f=await first_frame(p)
        a=await f.evaluate('NavaOnboarding.getVisualState()');await f.wait_for_timeout(650);z=await f.evaluate('NavaOnboarding.getVisualState()')
        check('非减少动效：真实手写时间和小猫时钟继续前进',z['elapsed']>a['elapsed'] and z['inkTime']['zh']>a['inkTime']['zh'])
        await f.locator('#next').click();await f.wait_for_timeout(160)
        check('翻页是过渡中的双纸面，不是静态截图切换',await f.locator('.paper-face').count()==2 and await f.evaluate('NavaOnboarding.getState().transition'))
        await wait_step(f,'gender');check('动画结束后旧纸面已清理',await f.locator('.paper-face').count()==1)
        await p.close()
        check('所有页面没有未捕获JavaScript异常',not ERRORS)
        check('交付物未分发字体文件',not any(x in HTML for x in ['data:font','data:application/font','@font-face']))
        (OUT/'results.json').write_text(json.dumps({'passed':len(CHECKS),'checks':CHECKS,'errors':ERRORS,'boundary':'Production single-file HTML; isolated in-memory localStorage because navigations are blocked in this browser environment. API keys, media, and real deployment are not used. Screenshots show explicit synthetic selections.'},ensure_ascii=False,indent=2))
        await b.close()
if __name__=='__main__':asyncio.run(run())
