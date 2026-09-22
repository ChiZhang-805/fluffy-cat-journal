"""输入：可选JSON输出路径。输出：函数头注释检查。功能：检查本轮修改模块的命名函数与类方法，不把行内回调计入。"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = ['entry-action.js', 'review-layout.js', 'animation.js', 'review.js']
DECL = re.compile(r'^([ \t]*)(?:(?:async|static|get|set)\s+)*(?:function\s+)?([A-Za-z_$][\w$]*)\s*\([^\n]*\)\s*\{', re.M)
EXCLUDED = {'if','for','while','switch','catch','with'}


def audit():
    """输入：源码列表。输出：检查条目数组。功能：确认每个命名函数前紧邻的块注释含输入、输出、功能。"""
    results=[]
    # 阶段一：声明位置来自源码行，区分方法定义与普通控制语句。
    for name in FILES:
        text=(ROOT/'js'/name).read_text(encoding='utf-8')
        for m in DECL.finditer(text):
            if m.group(2) in EXCLUDED or '=>' in m.group(0):
                continue
            before=text[:m.start()].rstrip()
            comment=''
            if before.endswith('*/'):
                start=before.rfind('/**')
                if start>=0:
                    comment=before[start:]
            # 阶段二：保留所有声明的检查结果，不只记录通过项。
            results.append({'file':'js/'+name,'name':m.group(2),'line':text.count('\n',0,m.start())+1,'passed':all(word in comment for word in ['输入','输出','功能'])})
    return results


if __name__=='__main__':
    items=audit()
    payload={'scope':'Named declarations and class methods in four changed modules; inline event callbacks excluded','count':len(items),'results':items}
    output=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'tests/results/comment-v10-audit.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[item for item in items if not item['passed']]
    print(json.dumps({'count':len(items),'failures':failures},ensure_ascii=False,indent=2))
    sys.exit(bool(failures))
