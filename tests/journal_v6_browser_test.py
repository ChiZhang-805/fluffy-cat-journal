"""v6 交付代码浏览器检查：内存装载真实源码；仅测试存储与估时接口使用明确替身。"""
from pathlib import Path
import asyncio, io, json, os
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
from browser_helpers_v5 import test_document

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tests' / 'results'
OUT.mkdir(exist_ok=True)
REVIEW = Path(os.environ.get('FLUFFY_REVIEW', str(OUT / 'v6-review')))
REVIEW.mkdir(parents=True, exist_ok=True)
RESULTS = []


def check(name, condition):
    """输入：断言名、条件。输出：失败时抛错。功能：只记录真实执行结果，不把替身当作真实API验证。"""
    RESULTS.append({'name': name, 'passed': bool(condition)})
    print(('PASS ' if condition else 'FAIL ') + name, flush=True)
    assert condition, name


async def load(browser, seed=None, width=1440, height=1080, touch=False):
    """输入：浏览器与显式测试存储/窗口参数。输出：就绪页面。功能：在受限环境里运行原代码，不绕过导航策略。"""
    context = await browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1.5, timezone_id='Asia/Shanghai', has_touch=touch)
    page = await context.new_page()
    page.errors = []
    page.set_default_timeout(7000)
    page.on('pageerror', lambda error: page.errors.append(str(error)))
    await page.set_content(test_document(seed))
    await page.wait_for_function('window.FluffyDebug?.animation.ready')
    await page.wait_for_timeout(320)
    return page


async def entry(page, category, values=None):
    """输入：页面、类别与可选字段。输出：无。功能：进入真实表单，等候连续角色过渡和布局测量。"""
    await page.evaluate('([id,values])=>FluffyDebug.openEntry(id,values)', [category, values])
    await page.wait_for_timeout(420)


async def capture(page, name):
    """输入：页面、文件名。输出：PNG。功能：截取实际运行的手机容器，不画静态原型。"""
    await page.locator('#phone').screenshot(path=str(REVIEW / (name + '.png')))


async def center(page, slot):
    """输入：槽位号。输出：缩放后的视口坐标。功能：真实指针拖到对应位置。"""
    return await page.evaluate('i=>{const r=document.querySelector("#home-board").getBoundingClientRect(),s=r.width/393;return [r.left+(18+i%3*121+56)*s,r.top+(151+Math.floor(i/3)*124+55)*s]}', slot)


async def drag(page, category, target, cancel=False):
    """输入：组件、落点、取消标志。输出：无。功能：真实长按移动松手，不直接改布局数据。"""
    card = page.locator('.home-widget[data-category="' + category + '"]')
    await card.evaluate('(n)=>Promise.all(n.getAnimations().map(a=>a.finished.catch(()=>{})))')
    box = await card.bounding_box()
    await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
    await page.mouse.down()
    await page.wait_for_function('(id)=>FluffyDebug.board.press?.id===id&&FluffyDebug.board.press.held',arg=category)
    await page.mouse.move(*target, steps=12)
    if cancel:
        await page.evaluate('window.dispatchEvent(new Event("blur"))')
    await page.mouse.up()
    await page.wait_for_timeout(350)


def picture(width, height):
    """输入：图片尺寸。输出：PNG字节。功能：生成无个人信息的几何夹具，测量照片等比显示。"""
    image = Image.new('RGB', (width, height), (211, 235, 238))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width-1, height-1), outline=(65, 108, 121), width=5)
    draw.ellipse((width*.2, height*.2, width*.8, height*.8), fill=(225, 205, 166))
    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()


async def bounds(page):
    """输入：页面。输出：设计坐标中的元素边界。功能：不凭截图猜测是否被裁切，直接核对几何位置。"""
    return await page.evaluate('''()=>{const p=document.querySelector('#entry-panel'),pr=p.getBoundingClientRect(),s=document.querySelector('#screen').getBoundingClientRect().width/393;
    const nodes=[...document.querySelectorAll('#entry-form > .field')].map(n=>({key:n.dataset.field||'range',top:(n.getBoundingClientRect().top-pr.top)/s,bottom:(n.getBoundingClientRect().bottom-pr.top)/s}));
    return {height:p.clientHeight,scrollHeight:p.scrollHeight,scrollTop:p.scrollTop,fields:nodes,bottom:parseFloat(getComputedStyle(p).paddingBottom),bar:getComputedStyle(p).scrollbarWidth};}''')


async def run():
    """输入：CHROMIUM_BIN、FLUFFY_REVIEW可选环境变量。输出：断言报告与运行截图。功能：覆盖本轮改动及主要回归路径。"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN') or None, headless=True, args=['--no-sandbox'])
        # 阶段一：旧布局与旧记录迁移，真实拖放和气泡避让。
        legacy = ['mood','food','sport',None,'sleep','focus',None,None,'face']
        old_record = {'id':'old-run','category':'sport','data':{'activity':'跑步','distanceKm':3,'durationMinutes':20,'notes':'轻松'},'createdAt':'2026-09-21T23:00:00Z'}
        page = await load(browser, {'fluffy-home-slots-v2':json.dumps(legacy),'fluffy-six-journal-v1':json.dumps([old_record])})
        order = await page.evaluate('FluffyDebug.board.order')
        check('旧右下角组件迁到第一个空位', order[8] is None and order[3] == 'face')
        check('其他旧组件位置保留', all(order[i] == legacy[i] for i in [0,1,2,4,5]))
        check('八位置新布局已保存', await page.evaluate('JSON.parse(localStorage.getItem("fluffy-home-slots-v3"))[8]===null'))
        check('只有六个功能组件', await page.locator('.home-widget').count() == 6)
        check('运动首页改为20min而非3km', await page.locator('.home-widget[data-category=sport] .widget-value').inner_text() == '20 min')
        await drag(page, 'mood', await center(page,8))
        check('拖到禁放区不移动也不打开记录', await page.evaluate('JSON.stringify(FluffyDebug.board.order)') == json.dumps(order,separators=(',',':')) and await page.evaluate('FluffyDebug.animation.scene') == 'home')
        await drag(page, 'mood', await center(page,6))
        check('可拖到合法空位', await page.evaluate('FluffyDebug.board.order[6]==="mood"&&FluffyDebug.board.order[0]===null'))
        await drag(page, 'mood', await center(page,1))
        check('可与占位组件交换', await page.evaluate('FluffyDebug.board.order[1]==="mood"&&FluffyDebug.board.order[6]==="food"'))
        before = await page.evaluate('JSON.stringify(FluffyDebug.board.order)')
        await drag(page,'mood',await center(page,0),cancel=True)
        check('失焦取消拖动回到原位置', await page.evaluate('JSON.stringify(FluffyDebug.board.order)') == before)
        await page.locator('.home-widget[data-category=focus]').focus()
        await page.keyboard.press('Alt+ArrowDown')
        check('键盘也不能占用气泡位置', await page.evaluate('FluffyDebug.board.order[8]===null'))
        await page.evaluate('FluffyDebug.board.reset();FluffyDebug.homeBubble("home")')
        await page.wait_for_timeout(350)
        bubble = await page.evaluate('''()=>{const b=document.querySelector('#home-bubble'),r=b.getBoundingClientRect(),s=document.querySelector('#screen').getBoundingClientRect();return {top:(r.top-s.top)/(s.width/393),bottom:(r.bottom-s.top)/(s.width/393),width:r.width/(s.width/393),text:b.textContent,clip:b.scrollWidth>b.clientWidth}}''')
        check('首页气泡在猫耳上方且不是满格卡片', bubble['bottom'] < 519 and bubble['width'] < 112 and bubble['top'] >= 399)
        check('首页气泡两行均六字且不裁切', all(len(x)==6 for x in bubble['text'].split('\n')) and not bubble['clip'])
        await capture(page,'home')
        await page.locator('.home-widget[data-category=sport]').click()
        check('普通点击仍进入记录页', await page.evaluate('FluffyDebug.animation.scene==="entry"&&FluffyDebug.state.category==="sport"'))

        # 阶段二：三项短表单、旧公里数、完整书写与实际保存。
        check('运动页只显示三个输入字段', await page.locator('#entry-form > .field').count()==3 and await page.locator('#field-distanceKm').count()==0)
        await entry(page,'sport',{'activity':'力量训练','durationMinutes':'45','notes':'深蹲4组，每组8次'})
        data=await bounds(page)
        check('运动备注底部完整可见无需滚动',data['scrollHeight']==data['height'] and data['fields'][-1]['bottom']<=data['height']-data['bottom']+.5)
        await capture(page,'sport')
        await page.locator('#confirm-entry').click()
        check('力量训练无需距离也能确认',await page.evaluate('FluffyDebug.animation.scene==="record"&&FluffyDebug.state.record.data.distanceKm===undefined'))
        check('写字三行仍是项目时长备注',await page.evaluate('FluffyDebug.animation.rows.map(r=>r.label).join(",")==="Activity,Time,Notes"'))
        await page.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.schedule[2].start+1.5;FluffyDebug.animation.render()')
        await capture(page,'writing')
        check('笔尖与活动备注行数据有效',await page.evaluate('Number.isFinite(FluffyDebug.animation.metrics.paperOffset)&&FluffyDebug.animation.rows[2].value==="深蹲4组，每组8次"'))
        await page.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+10;FluffyDebug.animation.render()')
        await page.locator('#primary').click()
        check('保存后进入庆祝',await page.evaluate('FluffyDebug.animation.scene==="celebrate"'))
        await page.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render()')
        await page.locator('#primary').click()
        check('庆祝后返回首页',await page.evaluate('FluffyDebug.animation.scene==="home"'))
        await page.evaluate('const s=__fluffyModules["journal-store.js"];const r=s.records().find(r=>r.id==="old-run");FluffyDebug.openEntry("sport",r.data,r)')
        check('旧公里数在编辑备注里', '3 公里' in await page.locator('#field-notes').input_value())
        check('旧备注的原感受仍保留', '轻松' in await page.locator('#field-notes').input_value())
        await page.evaluate("FluffyDebug.openEntry('sport',{activity:'力量训练',durationMinutes:30,notes:'深蹲卧推练习'.repeat(10)});FluffyDebug.confirmManual()")
        check('60字备注完整容纳书写区',await page.evaluate('FluffyDebug.animation.lines[2].ruleOffsets.every(y=>y<=54)'))

        # 阶段三：等待相框与图片比例；面部滚到底正好从眼周开始。
        await entry(page,'food')
        data=await bounds(page)
        food=next(x for x in data['fields'] if x['key']=='foods')
        portion=next(x for x in data['fields'] if x['key']=='portion')
        check('饮食首屏完整显示食物输入框',food['bottom']<=298.5)
        check('饮食下一字段没有露出半截标题',portion['top']>=data['height'])
        check('等待相框缩短且按钮稍矮',await page.evaluate('document.querySelector("#photo-preview").offsetHeight<110&&document.querySelector(".photo-tool").offsetHeight===38'))
        check('营养字段保持单列无维生素',await page.evaluate('[...document.querySelectorAll(".nutrition-fields .field")].every(n=>n.offsetWidth>270)&&!document.querySelector("#field-vitamins")'))
        await capture(page,'food')
        await entry(page,'face')
        data=await bounds(page)
        feeling=next(x for x in data['fields'] if x['key']=='feeling')
        eye=next(x for x in data['fields'] if x['key']=='eyeArea')
        check('面部首屏完整显示感受且隐藏整项眼周',feeling['bottom']<=298.5 and eye['top']>=306)
        await capture(page,'face-top')
        await page.locator('#entry-panel').evaluate('(p)=>p.scrollTop=p.scrollHeight')
        data=await bounds(page)
        check('面部滚到底时眼周为第一完整字段',abs(next(x for x in data['fields'] if x['key']=='eyeArea')['top'])<=.5)
        check('面部加高备注完整贴合底部',abs(data['fields'][-1]['bottom']-298)<=.5 and await page.locator('#field-notes').evaluate('(n)=>n.offsetHeight')>=110)
        await capture(page,'face-bottom')
        for width,height in [(800,400),(400,800)]:
            await page.locator('#photo-library').set_input_files({'name':'geometry.png','mimeType':'image/png','buffer':picture(width,height)})
            await page.wait_for_timeout(500)
            ratio=await page.locator('#photo-preview').evaluate('(n)=>n.clientHeight/n.clientWidth')
            check(f'照片{width}×{height}仍完整等比显示',abs(ratio-height/width)<.015)
            await page.locator('#entry-panel').evaluate('(p)=>p.scrollTop=p.scrollHeight')
            data=await bounds(page)
            check(f'上传{width}×{height}后面部底部仍正确对齐',abs(next(x for x in data['fields'] if x['key']=='eyeArea')['top'])<=1)
            await page.locator('.photo-remove').click()
            await page.wait_for_timeout(350)
            check(f'移除{width}×{height}照片恢复空相框',await page.evaluate('!document.querySelector("#photo-preview").classList.contains("has-image")'))

        # 阶段四：睡眠下拉控件的鼠标、键盘、语音回填和跨夜日期。
        await entry(page,'sleep')
        check('睡眠只有三个视觉字段',await page.locator('#entry-form > .field').count()==3)
        check('睡眠不用原生日期/时钟控件',await page.locator('#entry-form input[type=time],#entry-form input[type=datetime-local]').count()==0)
        check('合并时间区间有四个可访问数字入口',await page.get_by_role('combobox').count()==4)
        await page.get_by_role('combobox',name='入睡小时',exact=True).click()
        check('小时列表24项且菜单风格正确',await page.get_by_role('option').count()==24 and await page.locator('#sleep-time-options').evaluate('(n)=>getComputedStyle(n).borderRadius')=='17px')
        await capture(page,'time-picker')
        await page.get_by_role('option',name='23',exact=True).click()
        await page.get_by_role('combobox',name='醒来小时',exact=True).click()
        await page.get_by_role('option',name='07',exact=True).click()
        check('小时选择自动保留00分钟',await page.evaluate('FluffyDebug.rawForm().bedtime==="23:00"&&FluffyDebug.rawForm().wakeTime==="07:00"'))
        await page.get_by_role('combobox',name='入睡分钟',exact=True).click()
        await page.keyboard.press('End')
        check('End定位59但还不修改字段',await page.evaluate('document.querySelector("[role=option].active").textContent==="59"&&FluffyDebug.rawForm().bedtime==="23:00"'))
        await page.keyboard.press('Escape')
        check('Escape取消候选并关闭菜单',await page.locator('#sleep-time-options').is_hidden() and await page.locator('#field-bedtime').input_value()=='23:00')
        await page.get_by_role('combobox',name='入睡分钟',exact=True).focus()
        await page.keyboard.press('ArrowDown');await page.keyboard.press('3');await page.keyboard.press('0');await page.keyboard.press('Enter')
        check('键盘数字定位和确认30分钟',await page.locator('#field-bedtime').input_value()=='23:30')
        await page.get_by_role('combobox',name='醒来分钟',exact=True).click()
        heading = await page.locator('#entry-heading').bounding_box()
        await page.mouse.click(heading['x']+heading['width']/2,heading['y']+10)
        check('点外面关闭时间菜单',await page.locator('#sleep-time-options').is_hidden())
        await page.evaluate('FluffyDebug.fillForm({bedtime:"23:00",wakeTime:"07:00",quality:"醒来很精神",notes:"昨晚睡得安稳"})')
        check('AI回填的标准时分同步按钮显示',await page.get_by_role('combobox',name='入睡小时',exact=True).inner_text()=='23')
        check('睡眠三项无需滚动',(await bounds(page))['scrollHeight']==306)
        await capture(page,'sleep')
        await page.locator('#confirm-entry').click()
        check('合并控件仍计算跨夜8小时',await page.evaluate('FluffyDebug.state.record.data.hours===8&&FluffyDebug.state.record.data.bedDate<FluffyDebug.state.record.data.wakeDate'))
        await entry(page,'sleep',{'bedtime':'01:00','wakeTime':'07:00','quality':'不错','notes':'睡得好'})
        await page.locator('#confirm-entry').click()
        check('凌晨1到7仍为同日6小时',await page.evaluate('FluffyDebug.state.record.data.hours===6&&FluffyDebug.state.record.data.bedDate===FluffyDebug.state.record.data.wakeDate'))
        await entry(page,'sleep',{})
        await page.locator('#confirm-entry').click()
        check('缺失时间定位小时按钮，不提交空值',await page.evaluate('FluffyDebug.animation.scene==="entry"&&document.activeElement.dataset.key==="bedtime"'))
        await page.get_by_role('combobox',name='入睡小时',exact=True).click()
        await page.evaluate('FluffyDebug.navigate("home")')
        check('离开时关闭时间弹层',await page.locator('#sleep-time-options').is_hidden())

        # 阶段五：估时只回填分钟、不显示黄色面板、不再放入待办；手动修改仍优先。
        await entry(page,'focus',{'task':'阅读绘本20页','durationMinutes':'','notes':'认真看完'})
        check('专注没有稍后开始按钮',await page.get_by_text('放入待办，稍后开始',exact=True).count()==0)
        await page.evaluate('''FluffyDebug.apiTest.setKey("sk-test-only");window.__estimationRequests=[];FluffyDebug.apiTest.request=async(path,body)=>{__estimationRequests.push(body);return {choices:[{finish_reason:"stop",message:{content:JSON.stringify({minutes:30,reason:"测试估时依据，不应显示黄色面板"})}}]}}''')
        await page.get_by_text('让小猫估时',exact=True).click();await page.wait_for_timeout(120)
        check('真实估时调用路径回填30分钟',await page.locator('#field-durationMinutes').input_value()=='30' and await page.evaluate('__estimationRequests.filter(b=>b?.messages).length')==1)
        check('成功估时不出现黄色说明',await page.locator('#draft-note').is_hidden() and await page.locator('#draft-note').inner_text()=='')
        check('估时气泡改为明确自然的两行',await page.locator('#entry-bubble').inner_text()=='时间安排好啦\n我们一起开始')
        check('专注表单无需下滑',(await bounds(page))['scrollHeight']==306)
        await capture(page,'focus')
        await page.evaluate('() => { FluffyDebug.apiTest.request=(path,body)=>body?.messages ? new Promise(resolve=>{window.__resolveEstimate=resolve}) : Promise.resolve({data:[]}); }')
        await page.get_by_text('让小猫估时',exact=True).click()
        await page.locator('#field-durationMinutes').fill('18')
        await page.evaluate('__resolveEstimate({choices:[{finish_reason:"stop",message:{content:JSON.stringify({minutes:40,reason:"迟到测试响应"})}}]})')
        await page.wait_for_timeout(150)
        check('迟到估时不覆盖用户已改分钟数',await page.locator('#field-durationMinutes').input_value()=='18')
        await page.locator('#confirm-entry').click()
        check('点击开始进入真实计时',await page.evaluate('FluffyDebug.animation.scene==="focus"&&FluffyDebug.timer.state==="running"'))
        await page.locator('#timer-pause').click()
        check('专注暂停仍有效',await page.evaluate('FluffyDebug.timer.state==="paused"'))
        await page.locator('#timer-pause').click();await page.locator('#timer-rest').click()
        check('专注休息仍有效',await page.evaluate('FluffyDebug.timer.state==="resting"'))
        await page.locator('#timer-stop').click();await page.get_by_role('button',name='确定',exact=True).click()
        check('完全停止后庆祝且不虚报任务完成',await page.evaluate('FluffyDebug.animation.scene==="celebrate"&&!FluffyDebug.state.record.focus.taskCompleted'))
        check('主要流程无脚本错误',not page.errors)

        # 阶段六：不同视口的边界、气泡与表单高度；使用同一设计坐标避免比例漂移。
        for width,height in [(393,852),(390,844),(375,812),(320,740),(768,1024),(1440,900)]:
            view=await load(browser,width=width,height=height)
            check(f'{width}×{height}无水平页面溢出',await view.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
            for kind in ['food','face','sport','sleep','focus']:
                await entry(view,kind)
                data=await bounds(view)
                if kind=='food': condition=next(x for x in data['fields'] if x['key']=='foods')['bottom']<=298.8
                elif kind=='face': condition=next(x for x in data['fields'] if x['key']=='feeling')['bottom']<=298.8 and next(x for x in data['fields'] if x['key']=='eyeArea')['top']>=305.5
                else: condition=data['scrollHeight']<=data['height']+1
                check(f'{width}×{height} {kind}首屏边界完整',condition)
            check(f'{width}×{height}气泡不裁字且两行',await view.locator('#entry-bubble').evaluate('(n)=>n.scrollWidth<=n.clientWidth&&n.textContent.split("\\n").length===2'))
            check(f'{width}×{height}隐藏滚动条而非禁用滚动',(await bounds(view))['bar']=='none')
            await view.context.close()
        touch=await load(browser,width=393,height=852,touch=True)
        await entry(touch,'sleep')
        await touch.get_by_role('combobox',name='入睡小时',exact=True).tap()
        await touch.get_by_role('option',name='06',exact=True).tap()
        check('触屏选择时间可以提交',await touch.locator('#field-bedtime').input_value()=='06:00')
        check('触屏时间选择后菜单收起',await touch.locator('#sleep-time-options').is_hidden())
        await touch.context.close()
        await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(run())
    finally:
        (OUT/'journal-v6-browser-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
