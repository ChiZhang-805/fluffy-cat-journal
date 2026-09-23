"""输入：交付源码。输出：几何断言、实际画面与JSON。功能：离线内存文档测试，不请求API；不绕过浏览器导航策略。"""
from pathlib import Path
import json, os, sys
from playwright.sync_api import sync_playwright
from browser_helpers_v5 import test_document

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('FLUFFY_V14_OUT',str(ROOT.parent/'verification/v14-browser')));OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
DATA={
 'sport':{'activity':'跑步','durationMinutes':30,'notes':'跑了三公里，感觉挺舒适挺爽的，有一点点酸痛。回家后慢慢拉伸，喝了水，准备早点休息。'},
 'food':{'meal':'午餐','foods':'海鲜意面和蘑菇披萨，还有一杯温水','portion':'意面一盘，披萨半个，与朋友慢慢分享','calories':'860','protein':'38','carbs':'102','fat':'33','notes':'意面口感不错，留了半个披萨，和朋友聊天很开心'},
 'mood':{'mood':'有点失落，但也慢慢放松下来','reason':'准备很久的事情没有达到预期。散步后想通了一点，想给自己一点时间。','notes':'先休息一下，明天再慢慢继续'},
 'sleep':{'bedtime':'23:00','wakeTime':'07:00','quality':'醒来还有一点困，洗漱之后精神好了一些','notes':'中间醒过一次，很快又睡着了'},
 'face':{'feeling':'今天精神还好','eyeArea':'眼周有轻微阴影，右侧受到窗边光线影响','skinAppearance':'脸颊局部泛红，整体比较均匀，额头有少量光泽','notes':'和上次保持了相似的角度和光线'},
 'focus':{'task':'认真阅读论文的方法与实验部分，记下不明白的地方','durationMinutes':30,'notes':'先看清方法，再整理问题，下一次继续复习'}
}

def check(name,value):
    """输入：名称与断言。输出：无。功能：保留逐条测试证据，失败即停止。"""
    RESULTS.append({'name':name,'passed':bool(value)})
    print(('PASS ' if value else 'FAIL ')+name,flush=True)
    assert value,name


def seek(p,t,idle=7):
    """输入：页面、时间。输出：无。功能：测试中定位生产时间轴，不把跳时当完整播放。"""
    p.evaluate('([t,idle])=>{const a=FluffyDebug.animation;a.playing=false;a.time=t;a.idle=idle;a.render()}',[t,idle])


def record(p,id,data=None):
    """输入：类别与人工记录。输出：生产排版。功能：普通记录通过提交生成；专注额外检查其共用笔记投影。"""
    p.evaluate('([id,v])=>{const d=FluffyDebug;d.navigate("home");d.animation.playing=false;d.openEntry(id,v)}',[id,data or DATA[id]])
    if id=='focus':
        p.evaluate('''()=>{const d=FluffyDebug,r={category:'focus',data:d.rawForm(),recordDate:'2026-09-22'};r.displayRows=__fluffyModules['catalog.js'].rows(r);d.state.record=r;d.animation.setRecord(r);d.navigate('record',{transition:false});}''')
    else:
        p.evaluate('FluffyDebug.confirmManual()')
    p.wait_for_function('FluffyDebug.animation.scene==="record"')
    p.evaluate('FluffyDebug.animation.playing=false')
    return p.evaluate('''()=>{const a=FluffyDebug.animation;return {rows:a.rows,layout:a.paperLayout,timeline:a.paperTimeline,lines:a.lines.map(l=>({text:l.text,size:l.size,count:l.rowCount,rules:l.ruleOffsets}))}}''')


def run():
    """输入：无。输出：所有通过项及截图。功能：检查6类、长文本、实际滚轮/键盘/触摸与保存回归。"""
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        p=browser.new_page(viewport={'width':1100,'height':1000});p.set_default_timeout(12000)
        errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
        p.set_content(test_document(),wait_until='load');p.wait_for_function('window.FluffyDebug?.animation.ready')
        all_layout={}
        for id in DATA:
            info=record(p,id);all_layout[id]=info
            check(id+' 字体不因内容增加而缩小',all(l['size']==25 for l in info['lines']))
            check(id+' 字段数量与内容完整保留',len(info['rows'])=={'food':7,'face':4,'sleep':4}.get(id,3) and all(l['text']==r['value'] for l,r in zip(info['lines'],info['rows'])))
            fields=info['layout']['fields']
            check(id+' 最后横线与下一标题顶部留白恒定',all(abs(b['titleTop']-a['top']-a['lastRule']-30)<1e-6 for a,b in zip(fields,fields[1:])))
            checks=[]
            for part in info['timeline']['segments']:
                seek(p,(part['start']+part['end'])/2)
                checks.append(p.evaluate('''()=>{const a=FluffyDebug.animation,m=a.metrics,r=m.paperRows.find(r=>r.active&&r.canonical);
                    return {title:r?.labelY,visible:r&&r.labelY-14>=m.paperClip[0],sync:!m.penDown||Math.hypot(m.penTip[0]-m.inkTip[0],m.penTip[1]-m.inkTip[1])<1e-7,
                    pen:m.penTip[1]>=438&&m.penTip[1]<=500};}'''))
            check(id+' 每一视觉行标题在当前书写区',all(v['visible'] and abs(v['title']-436)<.001 for v in checks))
            check(id+' 每一视觉行笔尖与新增字迹同步',all(v['sync'] for v in checks))
            check(id+' 长备注不把手臂向下拉长',all(v['pen'] for v in checks))
            check(id+' 书写期间不启用手动滚动',not p.locator('#record-notebook').is_visible())
            movement=p.evaluate('''()=>{const a=FluffyDebug.animation;let worst=0;for(const s of a.paperTimeline.segments)for(const t of [s.start,s.end]){const l=a.activeNib(t-1e-6).tip,r=a.activeNib(t+1e-6).tip;worst=Math.max(worst,Math.hypot(l[0]-r[0],l[1]-r[1]));}return worst}''')
            check(id+' 所有行间和字段边界笔尖连续',movement<.02)
            end=info['timeline']['returnEnd']
            seek(p,end-0.0001)
            p.evaluate('window.__paperBefore=FluffyDebug.animation.ctx.getImageData(84,874,620,520).data')
            seek(p,end)
            diff=p.evaluate('''()=>{const b=window.__paperBefore,a=FluffyDebug.animation.ctx.getImageData(84,874,620,520).data;let sum=0;for(let i=0;i<a.length;i++)sum+=Math.abs(a[i]-b[i]);delete window.__paperBefore;return sum/a.length}''')
            check(id+' 归位前后笔记画面无可见跳变',diff<.1)
            check(id+' 归位后启用有限滚动',p.locator('#record-notebook').is_visible() and p.evaluate('FluffyDebug.animation.metrics.paperMode==="reading"'))
            check(id+' 顶部从第一项开始无旧副本',p.evaluate('''()=>{const a=FluffyDebug.animation;return a.metrics.paperRows[0].index===0&&a.metrics.paperRows[0].labelY===458&&a.metrics.paperRows.every(r=>r.cycle===0)&&a.paperScroll===0;}'''))
            check(id+' 已移除修改记录文本及点击控件',p.locator('#edit-record').count()==0)
            seek(p,info['timeline']['writeEnd']+11)
            p.locator('#phone').screenshot(path=str(OUT/(id+'-top.png')))
            # 实际滚轮，不仅修改内部time/offset变量。
            rect=p.locator('#record-notebook').bounding_box();p.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2)
            p.mouse.wheel(0,5000);p.wait_for_timeout(180)
            check(id+' 实际滚轮到达有限底部',p.evaluate('Math.abs(FluffyDebug.animation.paperScroll-FluffyDebug.animation.paperLayout.maxScroll)<1'))
            check(id+' 最后一条横线完整可见',p.evaluate('''()=>{const a=FluffyDebug.animation;return a.metrics.paperRows.at(-1).index===a.rows.length-1&&a.metrics.paperRows.at(-1).rules.at(-1)<=a.metrics.paperClip[1]-19;}'''))
            p.locator('#phone').screenshot(path=str(OUT/(id+'-bottom.png')))
            p.mouse.wheel(0,5000);p.wait_for_timeout(100)
            check(id+' 到底继续下滑也不回到第一项',p.evaluate('FluffyDebug.animation.paperScroll<=FluffyDebug.animation.paperLayout.maxScroll'))
            before_scroll=p.evaluate('FluffyDebug.animation.paperScroll');seek(p,info['timeline']['writeEnd']+13)
            check(id+' 猫咪继续呼吸不重置手动阅读位置',p.evaluate('FluffyDebug.animation.paperScroll')==before_scroll)
            p.locator('#record-notebook').focus();p.keyboard.press('Home');p.wait_for_timeout(80)
            check(id+' 键盘Home准确回到第一项',p.evaluate('FluffyDebug.animation.paperScroll===0'))
            p.keyboard.press('End');p.wait_for_timeout(80)
            check(id+' 键盘End到达末项且无额外空白',p.evaluate('Math.abs(FluffyDebug.animation.paperScroll-FluffyDebug.animation.paperLayout.maxScroll)<1'))
            check(id+' 阅读面板没有可见滚动条',p.locator('#record-notebook').evaluate('e=>getComputedStyle(e).scrollbarWidth==="none"&&getComputedStyle(e).overflowY==="auto"'))
        # 图中同款运动文本、3~5行备注、单行短笔记。
        for count in [1,2,3,4,5]:
            rows=[{'label':'Activity','value':'Running'},{'label':'Notes','value':'\n'.join(['记录这一小段时间']*count)},{'label':'Time','value':'30 min'}]
            p.evaluate('(rows)=>{const d=FluffyDebug;d.state.record={category:"sport",displayRows:rows};d.animation.setRecord(d.state.record);d.navigate("record",{transition:false});d.animation.playing=false}',rows)
            check(str(count)+'行显式换行保留且不缩字号',p.evaluate('FluffyDebug.animation.lines[1].rowCount')==count and p.evaluate('FluffyDebug.animation.lines.every(l=>l.size===25)'))
            check(str(count)+'行备注后下一标题留白一致',p.evaluate('''()=>{const f=FluffyDebug.animation.paperLayout.fields;return Math.abs(f[2].titleTop-f[1].top-f[1].lastRule-30)<1e-6}'''))
        info=record(p,'sport',{'activity':'跑步','durationMinutes':30,'notes':'很轻松'})
        seek(p,info['timeline']['writeEnd']+11)
        check('三项单行笔记无多余滚动空间',p.evaluate('FluffyDebug.animation.paperLayout.maxScroll===0&&document.getElementById("record-notebook").scrollHeight===290'))
        p.locator('#phone').screenshot(path=str(OUT/'sport-short.png'))
        # 完成、保存、回顾：新阅读层不能遮挡主按钮，用户历史不会因滚动被修改。
        count=p.evaluate('__fluffyModules["journal-store.js"].records().length')
        p.locator('#primary').click();p.wait_for_timeout(180)
        check('阅读后继续实际保存一条并进入庆祝',p.evaluate('FluffyDebug.animation.scene==="celebrate"') and p.evaluate('__fluffyModules["journal-store.js"].records().length')==count+1)
        seek(p,6);p.locator('#primary').click();p.wait_for_timeout(180)
        check('庆祝完成后仍进入运动回顾',p.evaluate('FluffyDebug.animation.scene==="review"'))
        check('离开笔记后滚动层不阻挡回顾',not p.locator('#record-notebook').is_visible())
        # 中文/英文新字段投影；设置语言只做阅读投影不写用户数据。
        p.evaluate('FluffyDebug.changeLanguage("en")');p.wait_for_timeout(100)
        info=record(p,'food',{'meal':'午餐','foods':'Pasta and vegetables','portion':'One plate','calories':'600','protein':'25','carbs':'80','fat':'18','notes':'Shared with a friend'})
        seek(p,info['timeline']['writeEnd']+11)
        check('英文饮食笔记全部标签与内容无中文',p.evaluate('FluffyDebug.animation.rows.every(r=>!/[\u3400-\u9fff]/.test(r.label+r.value))'))
        check('英文长文本不挤压字号',p.evaluate('FluffyDebug.animation.lines.every(l=>l.size===25)'))
        p.locator('#phone').screenshot(path=str(OUT/'food-english.png'))
        # 不同视口只缩放整部手机，滚动范围仍使用设计坐标。
        for w,h in [(1440,1000),(1536,864),(393,852),(375,812),(320,720),(430,932)]:
            p.set_viewport_size({'width':w,'height':h});p.wait_for_timeout(100)
            check(f'{w}×{h} 阅读区与卡片对齐且手机无横向溢出',p.evaluate('''()=>{const s=document.querySelector('#screen').getBoundingClientRect(),n=document.querySelector('#record-notebook').getBoundingClientRect(),c=document.querySelector('#record-card').getBoundingClientRect();return n.left>=c.left&&n.right<=c.right&&n.top>=c.top&&n.bottom<c.bottom&&s.left>=-1&&s.right<=innerWidth+1}'''))
        check('无未处理脚本异常',not errors)
        p.close()
        # 合成触摸拖动通过真实原生滚动；没有真实设备验证的假称。
        ctx=browser.new_context(viewport={'width':393,'height':852},is_mobile=True,has_touch=True,device_scale_factor=2)
        touch=ctx.new_page();touch.set_content(test_document());touch.wait_for_function('window.FluffyDebug?.animation.ready')
        info=record(touch,'food');seek(touch,info['timeline']['writeEnd']+11)
        r=touch.locator('#record-notebook').bounding_box();x=r['x']+r['width']*.5;y=r['y']+r['height']*.85
        cdp=ctx.new_cdp_session(touch)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
        for i in range(1,9):
            cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y-i*20}]});touch.wait_for_timeout(20)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});touch.wait_for_timeout(300)
        check('移动端合成手势确实滚动原生笔记',touch.evaluate('FluffyDebug.animation.paperScroll>30'))
        check('手指滑动不带动整个页面或无限循环',touch.evaluate('scrollY===0&&FluffyDebug.animation.paperScroll<=FluffyDebug.animation.paperLayout.maxScroll'))
        ctx.close();browser.close()
    (OUT/'layouts.json').write_text(json.dumps(all_layout,ensure_ascii=False,indent=2))
    (OUT/'results.json').write_text(json.dumps({'environment':'Chromium production code in an in-memory document. Isolated test storage, no paid API or microphone requests. Time seeking for keyframe geometry; real wheel/keyboard and synthetic touch for native scroll.', 'passed':len(RESULTS),'results':RESULTS},ensure_ascii=False,indent=2))
    print('PASSED',len(RESULTS))

if __name__=='__main__':run()
