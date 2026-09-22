"""输入：单文件HTML路径。输出：产物级断言。功能：检查真正的内嵌文件，不用源码版本代替交付文件。"""
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os,json,sys
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'Fluffy-Cat-v9.html'
OUT=Path(os.environ.get('FLUFFY_RESULTS',ROOT/'tests/results/v9-standalone'));OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]

def check(name,value):
    """输入：检查名称与真值。输出：断言结果。功能：只记录真实产物上的运行状态。"""
    RESULTS.append({'name':name,'passed':bool(value)});print(('PASS 'if value else 'FAIL ')+name,flush=True);assert value,name

def run():
    """输入：无。输出：产物检查。功能：仅在测试副本注入隔离存储，正式HTML不包含替身。"""
    original=SOURCE.read_text();soup=BeautifulSoup(original,'html.parser')
    check('产物没有外部脚本或样式依赖',not soup.find('script',src=True)and not soup.find('link',rel='stylesheet'))
    check('产物没有注入测试存储、示例Key或API替身','__testStore'not in original and 'test-only-'not in original and 'finishDelayed'not in original)
    setup='<script>window.FLUFFY_TEST=true;window.__testStore=new Map();Object.defineProperty(window,"localStorage",{value:{getItem:k=>__testStore.get(k)||null,setItem:(k,v)=>__testStore.set(k,String(v)),removeItem:k=>__testStore.delete(k)}});</script>'
    doc=original.replace('<head>','<head>'+setup,1)
    with sync_playwright()as p:
        b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1000,'height':1000});page.set_default_timeout(6000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.set_content(doc);page.wait_for_function('window.FluffyDebug?.animation.ready')
        check('单文件启动是现有猫咪首页',page.evaluate("FluffyDebug.animation.scene==='home'"))
        for id in ['sport','food','mood','sleep','face','focus']:
            page.evaluate('(id)=>FluffyDebug.openEntry(id,{})',id);check(id+'单文件空表单使用长按提示',page.locator('#confirm-label').inner_text()=='长按向小猫倾诉');page.locator('#entry-more').click();check(id+'单文件有三项菜单',page.locator('#entry-menu button').count()==3);page.keyboard.press('Escape')
        page.evaluate("FluffyDebug.openEntry('sport',{activity:'跑步',durationMinutes:12,notes:'沿河慢跑'})")
        check('单文件填写完整后恢复继续',page.locator('#confirm-label').inner_text()=='完成并继续');page.locator('#entry-more').click();page.locator('[data-action=date]').click();page.locator('[data-date]:not(:disabled)').nth(6).click();date=page.evaluate('FluffyDebug.entryMenu.candidate');page.locator('.date-save').click();page.locator('#confirm-entry').click()
        check('单文件补记后进入连续书写',page.evaluate("FluffyDebug.animation.scene==='record'"))
        page.evaluate('FluffyDebug.animation.time=FluffyDebug.animation.writeEnd+10;FluffyDebug.animation.render()');page.locator('#primary').click();page.evaluate('FluffyDebug.animation.time=6;FluffyDebug.animation.render()');page.locator('#primary').click()
        check('单文件完成后回顾日期等于选择日期',page.evaluate('FluffyDebug.review.view.date')==date)
        check('单文件记录只保存一次',page.evaluate("__fluffyModules['journal-store.js'].records().length===1"))
        page.evaluate('FluffyDebug.review.textSheet()');page.locator('#sheet').evaluate('(e)=>Promise.all(e.getAnimations().map(a=>a.finished))');check('单文件聊天标题和发送按钮均有图标',page.locator('#sheet-title .icon').count()==1 and page.locator('.review-text-submit .icon').count()==1);check('单文件聊天保留独立间距',page.evaluate('parseFloat(getComputedStyle(document.querySelector(".review-text-compose")).gap)===14'));check('单文件无脚本错误',not errors);page.close();b.close()

if __name__=='__main__':
    try:run()
    finally:(OUT/'results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2))
