"""输入：可选输出 HTML 路径。输出：可独立打开的 HTML。功能：内嵌本项目 CSS、JS 和原画，不加入测试替身。"""
from pathlib import Path
import base64
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> None:
    """输入：output（输出文件）。输出：无，写入文件。功能：生成离线手动预览；联网功能仍需权限、网络与实际 Key。"""
    # 阶段一：只从已知站点目录读取静态资源。
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    # 第三方SVG许可随单文件一起保留，不要求运行时加载外部文件。
    license_path = ROOT / 'licenses' / 'Lucide-LICENSE.txt'
    if license_path.exists():
        notice = license_path.read_text(encoding='utf-8').replace('--', '—')
        html = html.replace('<head>', '<head>\n<!-- Third-party icon license\n' + notice + '\n-->')
    assets = {}
    for image in (ROOT / 'assets').iterdir():
        if image.suffix not in ('.png', '.svg'):
            continue
        mime = 'image/svg+xml' if image.suffix == '.svg' else 'image/png'
        assets[image.name] = f'data:{mime};base64,' + base64.b64encode(image.read_bytes()).decode('ascii')

    # 阶段二：保留脚本顺序，但放到完整 DOM 之后执行。密钥与用户记录不是构建输入。
    scripts = []
    for src in re.findall(r'<script[^>]*src="([^"]+)"[^>]*></script>', html):
        scripts.append((ROOT / src.split('?')[0]).read_text(encoding='utf-8'))
    html = re.sub(r'<script[^>]*src="[^"]+"[^>]*></script>', '', html)
    for href in re.findall(r'<link[^>]*href="([^"]+\.css[^\"]*)"[^>]*>', html):
        css = (ROOT / href.split('?')[0]).read_text(encoding='utf-8')
        html = re.sub(r'<link[^>]*href="' + re.escape(href) + r'"[^>]*>', lambda _: '<style>\n' + css + '\n</style>', html)
    html = html.replace('assets/favicon.svg', assets['favicon.svg'])
    onboarding = (ROOT / 'onboarding.html').read_text(encoding='utf-8')
    bootstrap = 'window.NAVA_ONBOARDING_HTML=' + json.dumps(onboarding, ensure_ascii=False) + ';\n'
    script = bootstrap + 'window.CAT_ASSETS=' + json.dumps(assets, ensure_ascii=False) + ';\n' + '\n'.join(scripts)
    script = re.sub(r'</script', r'<\\/script', script, flags=re.I)
    html = html.replace('</body>', '<script>\n' + script + '\n</script>\n</body>')
    # 阶段三：只生成实际程序；不会内嵌测试存储、示例响应或真实凭据。
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding='utf-8')
    print(str(output))


if __name__ == '__main__':
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'NAVA-Fluffy-v17.html')
