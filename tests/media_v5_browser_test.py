"""麦克风首次授权与相机取消；显式权限和音频源替身。"""
import asyncio, json, os
from playwright.async_api import async_playwright
from journal_v5_browser_test import load, entry, API_MOCK, AUDIO_MOCK, check, RESULTS, OUT

async def run_media():
    """输入：无。输出：媒体边界测试报告。功能：验证晚到授权不能启动录音或上传。"""
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path=os.getenv('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required'])
        # 独立浏览器页，避免软件渲染器多页资源争用。
        q=await load(browser,extra=API_MOCK+AUDIO_MOCK)
        await q.evaluate("FluffyDebug.bailianTest.setKey('sk-test-permission-only');window.__perm='prompt';navigator.permissions.query=async()=>({state:__perm});window.__normalMedia=navigator.mediaDevices.getUserMedia;navigator.mediaDevices.getUserMedia=()=>new Promise(r=>window.__allowFirst=()=>{window.__perm='granted';r({getTracks:()=>[{stop:()=>window.__permissionTrackStopped=true}]})});void 0")
        await entry(q,'mood');b=await q.locator('#confirm-entry').bounding_box();await q.mouse.move(b['x']+b['width']/2,b['y']+b['height']/2);await q.mouse.down();await q.wait_for_function('FluffyDebug.state.phase==="authorizing"');await q.mouse.up()
        await q.evaluate("window.dispatchEvent(new Event('blur'));__allowFirst()")
        await q.wait_for_function('FluffyDebug.state.phase==="idle"')
        check('首次授权弹窗失焦不会误取消许可或偷开录音',await q.evaluate('__permissionTrackStopped===true&&!FluffyDebug.rawAudio.active'))
        check('首次授权不向模型发送音频',await q.evaluate('__apiCalls.length===0'))
        await q.evaluate('navigator.mediaDevices.getUserMedia=__normalMedia;void 0')
        await q.mouse.down();await q.wait_for_function('FluffyDebug.state.phase==="listening"');await q.wait_for_timeout(450);await q.keyboard.press('Escape');await q.mouse.up()
        check('已授权后再次长按直接录音；Escape取消不上传',await q.evaluate('!FluffyDebug.rawAudio.active&&__apiCalls.length===0&&__micTracks.every(t=>t.readyState==="ended")'))
        await entry(q,'face');await q.evaluate("window.__cameraStopped=0;navigator.mediaDevices.getUserMedia=()=>new Promise(r=>window.__allowCamera=()=>r({getTracks:()=>[{stop:()=>__cameraStopped++}]}));void 0")
        await q.get_by_role('button',name='拍照',exact=True).click();await q.wait_for_function('typeof __allowCamera==="function"');await q.locator('#sheet-close').click();await q.evaluate('__allowCamera()');await q.wait_for_timeout(120)
        check('取消相机后晚到的视频轨道立即关闭',await q.evaluate('__cameraStopped>0&&FluffyDebug.photo.stream===null'))
        check('授权与相机异常分支无脚本错误',not q.errors)
        await q.evaluate('Promise.all(__syntheticContexts.map(c=>c.close()))');await q.close()
        await browser.close()
    (OUT/'media-v5-browser-results.json').write_text(json.dumps({'passed':len(RESULTS),'tests':RESULTS,'media':'explicit permission mock and synthetic audio source'},ensure_ascii=False,indent=2))

if __name__=='__main__':asyncio.run(run_media())
