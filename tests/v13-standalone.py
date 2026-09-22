"""输入：最终HTML路径。输出：单文件饮食验收。功能：装载交付文件正文，不启用调试接口或假模型成功响应。"""
from pathlib import Path
import asyncio, io, json, sys
from PIL import Image
from playwright.async_api import async_playwright
SRC=Path(sys.argv[1]).resolve()
OUT=Path(__file__).resolve().parents[2]/'verification/standalone-food'
OUT.mkdir(parents=True,exist_ok=True)
CHECKS=[]


def check(name,result):
    """输入：名称与真假。输出：断言记录。功能：仅记录实际执行结果。"""
    CHECKS.append({'name':name,'passed':bool(result)})
    print(('PASS ' if result else 'FAIL ')+name,flush=True)
    assert result,name


async def main():
    """输入：无。输出：验证JSON。功能：真实交付HTML的按钮/文件输入操作，外部网络禁止。"""
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=await b.new_page(viewport={'width':1100,'height':1000});page.set_default_timeout(8000)
        errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)))
        async def block(route):
            """输入：外部请求。输出：取消。功能：验收期间不向云服务发送测试照片。"""
            requests.append(route.request.url);await route.abort()
        await page.route('https://**/*',block)
        await page.set_content(SRC.read_text())
        await page.locator('.home-widget[data-category=food]').wait_for(state='visible')
        await page.wait_for_timeout(300)
        await page.locator('.home-widget[data-category=food]').click()
        check('最终文件可从首页进入饮食',await page.locator('#field-foods').count()==1)
        check('最终文件不存在调试接口',await page.evaluate('!window.FluffyDebug'))
        check('最终文件没有分析按钮及营养外框',await page.locator('#analyze-photo,.nutrition-details,.nutrition-fields').count()==0)
        check('四营养字段为真实可编辑控件',await page.evaluate('["calories","protein","carbs","fat"].every(k=>!document.getElementById("field-"+k).disabled)'))
        image=Image.new('RGB',(480,320),'#9ebfaf');buf=io.BytesIO();image.save(buf,format='PNG')
        await page.locator('#photo-library').set_input_files({'name':'fixture.png','mimeType':'image/png','buffer':buf.getvalue()})
        await page.wait_for_function('document.querySelector("#entry-bubble").innerText.includes("百炼")')
        check('没配Key时照片保留在等比例相框',await page.locator('.photo-preview img').is_visible())
        check('没配Key时没有发送任何云请求',not requests)
        check('旧黄色说明与toast均隐藏',not await page.locator('#draft-note').is_visible() and not await page.locator('#phone-toast').is_visible())
        await page.locator('.photo-remove').click()
        check('用户可移除照片恢复空相框',await page.locator('.photo-empty').is_visible())
        check('未配置AI也可继续自己填',await page.locator('#field-foods').is_enabled())
        check('真实交付文件无运行时脚本异常',not errors)
        (OUT/'results.json').write_text(json.dumps({'source':str(SRC),'assertions':CHECKS,'pageErrors':errors,'externalRequests':requests,'mode':'Delivered HTML loaded in memory because file URL navigation is blocked by browser policy; no API success mocks or debug interface.'},ensure_ascii=False,indent=2))
        await b.close()
if __name__=='__main__':asyncio.run(main())
