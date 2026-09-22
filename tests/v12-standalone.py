"""输入：单文件路径。输出：验收结果。功能：实际交付HTML的手动交互，网络关闭，无API/语音成功替身。"""
from pathlib import Path
import asyncio,json,os,sys
from playwright.async_api import async_playwright
SOURCE=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'Fluffy-Cat-v12.html'
OUT=Path(os.environ.get('V12_STANDALONE_OUT',Path(__file__).resolve().parents[2]/'verification/standalone'));OUT.mkdir(parents=True,exist_ok=True)
results=[]
def check(name,value):
    """输入：名称/真值。输出：断言记录。功能：只把真实执行通过的项目算进结果。"""
    results.append({'name':name,'passed':bool(value)});print(('PASS ' if value else 'FAIL ')+name,flush=True);assert value,name
async def main():
    """输入：无。输出：JSON和实际截图。功能：不启用FluffyDebug，使用用户能点击的正式界面。"""
    html=SOURCE.read_text()
    check('产物不含测试存储/假AI/自动填写Key',all(x not in html for x in ['window.FLUFFY_TEST=true','window.__mode','sk-fixture','__testStore']))
    check('产物内嵌全部CSS和JS','<script defer="" src=' not in html and '<link href="css/' not in html)
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=await b.new_page(viewport={'width':1050,'height':980});page.set_default_timeout(8000)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.route('**/*',lambda route:route.abort())
        await page.set_content(html)
        await page.locator('.home-widget[data-category=sport]').wait_for(state='visible');await page.wait_for_timeout(400)
        check('正式单文件没有启用调试接口',await page.evaluate('!window.FluffyDebug'))
        check('六入口实际渲染',await page.locator('.home-widget').count()==6)
        await page.locator('.home-widget[data-category=sport]').click()
        await page.locator('#confirm-entry').click();await page.wait_for_timeout(150)
        check('缺项直接由小猫询问','运动项目还空着' in await page.locator('#entry-bubble').inner_text())
        check('缺项没有底部横条',not await page.locator('#phone-toast').is_visible())
        await page.locator('#field-activity').fill('跑步');await page.locator('#field-durationMinutes').fill('30');await page.locator('#field-notes').fill('跑了五公里')
        check('填写后恢复完成并继续','完成并继续' in await page.locator('#confirm-entry').inner_text())
        await page.locator('#confirm-entry').click()
        await page.locator('#primary').wait_for(state='visible');await page.wait_for_timeout(1300)
        check('断网仍能用实际填写内容进入书写',not await page.locator('#entry-form').is_visible() and await page.locator('#primary').is_visible())
        await page.locator('.phone').screenshot(path=str(OUT/'actual-handwriting.png'))
        check('手动流程无脚本异常',not errors)
        await b.close()
        (OUT/'results.json').write_text(json.dumps({'source':str(SOURCE),'api_called':False,'microphone_used':False,'assertions':results,'errors':errors},ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:asyncio.run(main())
    finally:(OUT/'attempt-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
