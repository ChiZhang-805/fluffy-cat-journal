"""输入：实际v7代码。输出：补充浏览器证据。功能：检查阅读暂停、键盘、取消、分享释放和只读聊天。"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from review_browser_test import load,SEED,MOCK
import json,os
OUT=Path(os.environ.get('FLUFFY_RESULTS','tests/results/v7-extra'));OUT.mkdir(parents=True,exist_ok=True)
results=[]

def check(name,value):
    """输入：断言名、真值。输出：证据。功能：失败立即退出，禁止报告未执行用例。"""
    results.append({'name':name,'passed':bool(value)}); print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name

def run():
    """输入：无。输出：JSON。功能：使用生产源，只替换测试存储/媒体/模型。"""
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=load(b);page.evaluate(SEED);page.wait_for_timeout(250)
        page.evaluate('''()=>{const r=FluffyDebug.review;r.enqueue([{text:'你已经做得很认真啦。',gesture:'nod'},{text:'想休息就慢慢歇会儿。',gesture:'soft'}]);}''')
        page.locator('#review-bubble').click();page.wait_for_timeout(50);t=page.evaluate('FluffyDebug.review.queueElapsed');page.wait_for_timeout(300)
        check('点气泡可暂停阅读不丢句',page.evaluate('FluffyDebug.review.paused') and page.evaluate('FluffyDebug.review.queueElapsed')==t)
        page.locator('#review-bubble').click();page.wait_for_timeout(140)
        check('再次点击继续阅读',page.evaluate('FluffyDebug.review.queueElapsed')>t)
        page.locator('#review-more').click();page.get_by_role('menuitem',name='评分依据').click()
        t=page.evaluate('FluffyDebug.review.queueElapsed');page.wait_for_timeout(140)
        check('读菜单详情时气泡计时暂停',page.evaluate('FluffyDebug.review.queueElapsed')==t)
        check('依据解释公式且没有底部评分按钮','目标' in page.locator('#sheet-body').inner_text())
        page.locator('#sheet-close').click()
        page.evaluate(MOCK);page.evaluate("()=>{FluffyDebug.review.h.api.setKey('test-not-valid');FluffyDebug.review.h.bailian.clear();FluffyDebug.review.h.api.request=async(path,body)=>{window.textRequest=body;return {choices:[{finish_reason:'stop',message:{content:JSON.stringify({transcript:'模型不该改写的文字',replies:[{text:'先喘口气也很好呀。',gesture:'nod'}]})}}]};};}")
        page.locator('#review-more').click();page.get_by_role('menuitem',name='文字聊聊').click();page.locator('#sheet-body textarea').fill('我其实有点累了');page.get_by_role('button',name='说给小猫',exact=True).click();page.wait_for_timeout(200)
        check('文字聊天调用真实客户端入口而非录入接口',page.evaluate('textRequest.messages.at(-1).content==="我其实有点累了"&&textRequest.tools===undefined'))
        check('文本聊天历史保留用户原话不采信模型另造转写',page.evaluate('FluffyDebug.review.history().at(-2).content==="我其实有点累了"'))
        page.locator('#review-more').click();page.get_by_role('menuitem',name='对话记录').click()
        check('已经消逝的回复在对话记录中可读','先喘口气也很好呀' in page.locator('#sheet-body').inner_text())
        page.locator('#sheet-close').click()
        # 阶段二：分享异步完成时面板已关闭，不重新弹出或生成漏掉的Object URL。
        page.evaluate('''()=>{const r=FluffyDebug.review;window.originalShare=r.makeShare;r.makeShare=()=>new Promise(resolve=>window.resolveShare=resolve);}''')
        page.locator('#review-more').click();page.get_by_role('menuitem',name='分享卡片').click()
        check('分享编码前立即有准备反馈','正在准备' in page.locator('#sheet-body').inner_text())
        page.locator('#sheet-close').click();page.evaluate('resolveShare(new Blob(["test"],{type:"image/png"}))');page.wait_for_timeout(80)
        check('关闭分享后晚到结果不会重新打开页面',page.locator('#sheet-layer').is_hidden() and page.locator('.review-share-preview').count()==0)
        # 阶段三：Space长按/抬键与Esc取消使用同一生命周期。
        page.evaluate(MOCK);page.locator('#review-chat').focus();page.keyboard.down('Space');page.wait_for_timeout(520)
        check('键盘Space长按能启动倾听',page.evaluate('FluffyDebug.review.phase==="listening"'))
        page.keyboard.press('Escape');page.keyboard.up('Space');page.wait_for_timeout(100)
        check('Esc取消收音不发送请求',page.evaluate('requests.length===0&&!FluffyDebug.review.raw.active'))
        page.evaluate("()=>{FluffyDebug.review.raw.supported=()=>false;FluffyDebug.review.enqueue([{text:'这里会陪着你。',gesture:'wave'}]);}")
        page.locator('#review-chat').focus();page.keyboard.down('Space');page.wait_for_timeout(520);page.keyboard.up('Space')
        check('无麦克风能力返回待机而非卡在说话状态',page.evaluate('FluffyDebug.review.phase==="idle"'))
        page.emulate_media(reduced_motion='reduce');page.evaluate('FluffyDebug.animation.reducedMotion=true;FluffyDebug.openReview(testRecords.sleep)');page.wait_for_timeout(100)
        check('减少动态效果时圆环直接显示最终值',page.locator('#review-score').inner_text()=='100')
        check('减少动态效果时柱子不依赖持续动画',page.locator('.review-bar-paint').first.evaluate('(e)=>getComputedStyle(e).animationName')=='none')
        check('补充场景没有脚本异常',not page.errors)
        b.close()

if __name__=='__main__':
    try:run()
    finally:(OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
