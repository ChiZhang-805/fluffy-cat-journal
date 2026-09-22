"""输入：交付源码。输出：v10的布局/文案/动画检查。功能：在内存文档执行真实代码，隔离存储，不调用API。"""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright
from browser_helpers_v5 import test_document
from interaction_v9_browser_test import FULL
from review_browser_test import SEED

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('FLUFFY_RESULTS',ROOT/'tests/results/v10'))
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]
ZH={'sport':'长按和小猫聊运动','food':'长按告诉小猫吃了啥','mood':'长按和小猫说心情','sleep':'长按和小猫聊睡眠','face':'长按说说今天的状态','focus':'长按告诉小猫你的计划'}
EN={'sport':'Hold to log your workout','food':'Hold to share your meal','mood':'Hold to share how you feel','sleep':'Hold to talk about sleep','face':'Hold to share your skin notes','focus':'Hold to tell me your plan'}


def check(name, value):
    """输入：断言名、真值。输出：证据或异常。功能：仅记录实际执行的测试。"""
    RESULTS.append({'name':name,'passed':bool(value)})
    print(('PASS ' if value else 'FAIL ')+name,flush=True)
    assert value,name


def run():
    """输入：无。输出：测试证据与截图。功能：依次检查几何、同比柱高、两种语言、填空状态与跨尺寸回顾。"""
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        page=b.new_page(viewport={'width':1080,'height':1000})
        page.set_default_timeout(8000)
        errors=[];network=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('https://**/*',lambda r:(network.append(r.request.url),r.abort()))
        page.set_content(test_document())
        page.wait_for_function('window.FluffyDebug?.animation.ready')
        # 阶段一：真实记录模型生成六类快照；用户数据不参与。
        page.evaluate(SEED)
        for category in FULL:
            page.evaluate('(id)=>FluffyDebug.openReview(testRecords[id])',category)
            g=page.evaluate('''()=>{const $=s=>document.querySelector(s),b=$('#review-bubble'),s=$('#review-summary'),w=$('#review-week'),d=$('#review-date').getBoundingClientRect(),r=b.getBoundingClientRect();return{
                bubble:b.offsetTop,summary:s.offsetTop,summaryHeight:s.offsetHeight,week:w.offsetTop,weekHeight:w.offsetHeight,
                bottom:w.offsetTop+w.offsetHeight,chat:$('#review-chat').offsetTop,pet:$('#review-pet').offsetTop,
                dateClear:d.bottom<r.top,scroll:$('#review-page').scrollHeight===852&&$('#review-page').scrollWidth===393,
                graphHeight:$(".review-bars,.review-mood-week").offsetHeight};}''')
            check(category+'猫咪与卡片同步向上，周卡增高但不挤占聊天按钮',g=={'bubble':137,'summary':264,'summaryHeight':166,'week':444,'weekHeight':266,'bottom':710,'chat':744,'pet':120,'dateClear':True,'scroll':True,'graphHeight':176})
            check(category+'原只读记录仍归属当前板块',page.evaluate('(id)=>FluffyDebug.review.view.records.every(r=>r.category===id)',category))
        # 阶段二：用明确的渲染夹具验证100/50/0分、空缺与同一基线，不改评分算法。
        page.evaluate('''()=>{FluffyDebug.openReview(testRecords.sport);const r=FluffyDebug.review;const scores=[0,25,50,null,75,100,95];r.view.week.forEach((d,i)=>{d.score=scores[i];d.count=scores[i]===null?0:1});r.renderWeek();window.recordSnapshot=JSON.stringify(__fluffyModules['journal-store.js'].records())}''')
        page.wait_for_timeout(160)
        early=page.locator('.review-bar-paint').last.evaluate('(e)=>new DOMMatrix(getComputedStyle(e).transform).m22')
        page.wait_for_timeout(1200)
        late=page.locator('.review-bar-paint').last.evaluate('(e)=>new DOMMatrix(getComputedStyle(e).transform).m22')
        check('柱子仍逐根升起而不是静态换图',early<.95 and abs(late-1)<.001)
        paints=page.locator('.review-bar:not(.missing)').evaluate_all('(buttons)=>buttons.map(b=>({label:b.querySelector(".review-bar-number").textContent,height:parseFloat(b.querySelector(".review-bar-paint").style.height)}))')
        check('100分135px且其他分数按相同比例放大',paints==[{'label':str(x),'height':x/100*135} for x in [0,25,50,75,100,95]])
        check('无记录日不生成柱子，已知0分不变成未知',page.locator('.review-bar.missing .review-bar-paint').count()==0 and page.locator('.review-bar.missing .review-bar-number').inner_text()=='—' and page.locator('.review-bar-number').first.inner_text()=='0')
        check('分数标签在标题下方且在对应柱子上方，日期在底部',page.evaluate('''()=>{const heading=document.querySelector('.review-week-heading').getBoundingClientRect();return [...document.querySelectorAll('.review-bar:not(.missing)')].every(b=>{const p=b.querySelector('.review-bar-paint').getBoundingClientRect(),n=b.querySelector('.review-bar-number').getBoundingClientRect(),d=b.querySelector('.review-bar-day').getBoundingClientRect();return n.top>=heading.bottom&&n.bottom<=p.top+1&&p.bottom<=d.top;})}'''))
        check('各柱使用同一个零点且真实绘图区135px',page.evaluate('''()=>{const bars=[...document.querySelectorAll('.review-bar-paint')].map(e=>e.getBoundingClientRect().bottom);return Math.max(...bars)-Math.min(...bars)<.1&&document.querySelector('.review-bar-slot').offsetHeight===135;}'''))
        page.locator('.review-bar.missing').click()
        check('空白日可点击且摘要正确',page.locator('#review-week-detail').inner_text()=='这一天还没有记录')
        page.locator('.review-bar').nth(5).click()
        check('选日和图表扩容不会改动已保存数据',page.evaluate("JSON.stringify(__fluffyModules['journal-store.js'].records())===recordSnapshot"))
        page.emulate_media(reduced_motion='reduce');page.evaluate('FluffyDebug.review.renderWeek()')
        check('减少动态效果时柱子直接显示最终高度',page.locator('.review-bar-paint').last.evaluate('(e)=>getComputedStyle(e).transform')=='none')
        page.emulate_media(reduced_motion='no-preference')
        # 阶段三：六类文案不同，完成度、语言切换和录音状态规则仍各司其职。
        for category,data in FULL.items():
            page.evaluate('(id)=>{FluffyDebug.changeLanguage("zh");FluffyDebug.openEntry(id,{})}',category)
            check(category+'初始邀请按板块显示且图标文字居中',page.locator('#confirm-label').inner_text()==ZH[category] and page.evaluate('()=>{const a=document.querySelector(".entry-action-content").getBoundingClientRect(),b=document.querySelector("#confirm-entry").getBoundingClientRect();return Math.abs(a.left+a.width/2-b.left-b.width/2)<1}'))
            page.evaluate('(d)=>FluffyDebug.fillForm(d)',data)
            check(category+'填完整后恢复原继续动作',page.locator('#confirm-label').inner_text()==('开始专注' if category=='focus' else '完成并继续'))
            page.locator('#field-notes').fill('')
            check(category+'再次清空恢复对应邀请而非通用倾诉',page.locator('#confirm-label').inner_text()==ZH[category])
            before=page.locator('#entry-form').evaluate('(f)=>[...f.querySelectorAll("input,textarea")].map(e=>e.value)')
            page.evaluate('FluffyDebug.changeLanguage("en")')
            check(category+'切换英文保留输入并显示对应邀请',page.locator('#confirm-label').inner_text()==EN[category] and before==page.locator('#entry-form').evaluate('(f)=>[...f.querySelectorAll("input,textarea")].map(e=>e.value)'))
        # 阶段四：在统一手机设计坐标下检查缩放后的按钮文案和回顾页的完整一屏。
        for width,height in [(375,812),(393,852),(430,932),(650,900),(1080,1000),(1440,1000)]:
            page.set_viewport_size({'width':width,'height':height})
            for lang,words in [('zh',ZH),('en',EN)]:
                for category in FULL:
                    page.evaluate('([id,lang])=>{FluffyDebug.openEntry(id,{});FluffyDebug.changeLanguage(lang)}',[category,lang])
                    check(f'{width}-{lang}-{category}邀请单行无裁切',page.locator('#confirm-label').inner_text()==words[category] and page.evaluate('''()=>{const g=document.querySelector('.entry-action-content'),l=document.querySelector('#confirm-label'),m=g.querySelector('.mic-icon'),b=document.querySelector('#confirm-entry').getBoundingClientRect(),r=l.getBoundingClientRect(),a=m.getBoundingClientRect();return g.scrollWidth<=g.clientWidth+1&&a.right<r.left&&r.right<b.right-8&&l.offsetHeight<=parseFloat(getComputedStyle(l).fontSize)*1.7&&document.querySelector('#screen').scrollWidth===393}'''))
                page.evaluate('FluffyDebug.openReview(testRecords.sleep)')
                check(f'{width}-{lang}回顾卡片与按钮不相交且日期不受影响',page.evaluate('''()=>{const w=document.querySelector('#review-week').getBoundingClientRect(),s=document.querySelector('#review-summary').getBoundingClientRect(),c=document.querySelector('#review-chat').getBoundingClientRect(),h=document.querySelector('#home-indicator').getBoundingClientRect(),d=document.querySelector('#review-date').getBoundingClientRect(),b=document.querySelector('#review-bubble').getBoundingClientRect();return s.bottom<w.top&&w.bottom<c.top&&c.bottom<h.top&&b.top>d.bottom&&document.querySelector('#review-page').scrollHeight===852;}'''))
        check('所有检查没有脚本异常',not errors)
        check('所有检查没有请求付费模型服务',not network)
        b.close()

if __name__=='__main__':
    try:run()
    finally:(OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
