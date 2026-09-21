from pathlib import Path
from bs4 import BeautifulSoup
import json,base64
ROOT=Path(__file__).resolve().parents[1]

def test_document(extra_js=''):
    """输入：测试专用依赖代码。输出：内存测试页面。功能：只执行本项目源码，不访问网络或修改浏览器策略。"""
    soup=BeautifulSoup((ROOT/'index.html').read_text(),'html.parser')
    style=soup.new_tag('style');style.string=(ROOT/'css/app.css').read_text();soup.find('link',rel='stylesheet').replace_with(style)
    assets={p.name:'data:'+('image/svg+xml' if p.suffix=='.svg' else 'image/png')+';base64,'+base64.b64encode(p.read_bytes()).decode() for p in (ROOT/'assets').iterdir()}
    soup.find('link',rel='icon')['href']=assets['favicon.svg']
    head=soup.new_tag('script');head.string='window.CAT_ASSETS='+json.dumps(assets)+';\n'+extra_js
    soup.find('script').insert_before(head)
    for script in soup.find_all('script',src=True):
        code=(ROOT/script['src'].split('?')[0]).read_text()
        if script['src'].split('?')[0]=='js/app.js':code=code.replace('if (new URLSearchParams(location.search).has("debug")) {','if (true) {')
        script.attrs={};script.string=code
    for script in list(soup.find_all("script")):
        script.extract();soup.body.append(script)
    return str(soup)
