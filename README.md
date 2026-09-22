# Fluffy Cat · v11

在现有v10基础上，统一图标、区分新增/修改记录，并补齐整个APP的英文阅读界面。
保留同一只小猫、八个可用拖动位置、表单、语音、书写、趴睡、庆祝、补记和专注计时。

## 本版使用

- 今天该类别还没有记录：点首页卡片进入表单。
- 今天已经有记录：进入今天的回顾。正在计时的专注仍优先回到计时器。
- 回顾三点菜单：「新增记录」再记一次；「修改记录」先选哪一条；「当日记录」查看时间顺序。
- 所有六类都能新增或修改。情绪变化不覆盖之前的心情，面部也能保留不同时间的观察。
- 普通聊天绝不直接改记录。明确要记/纠错时出现独立入口，确认目标后生成可编辑草稿，再由用户保存。
- 已有睡眠多段按真实区间并集合计，防止重叠；其他累计指标从明细重算。

## 图标和英文

主要类别/导航图标使用Lucide，细节、来源和许可证见 `docs/v11-icons.md`。
现有状态栏与猫咪原图不变，未附带任何字体文件。

语言可以从首页菜单、个人页、记录或回顾菜单切换。英文覆盖APP生成的UI、时间单位、
图表、提示、历史和AI短句；中文仍保留原来的混排。
用户原始记录与当前输入值不修改。英文阅读副本与数据分开：常用短语可离线展示，
陌生中文自由文本需要现有已启用API翻译；无Key或失败时显示“Translation unavailable”，
不伪造翻译，也不悄悄把中文原文改成英文。切回中文即可看原表达。

## 运行

纯静态目录，无npm运行依赖：

```sh
python -m http.server 8000
```

访问 `http://localhost:8000`。真实语音和AI功能仍需权限、服务可达和有效Key。
Key仅在当前页面内存，不能写进源码。GitHub Pages不运行自有后端。
用户记录保存在浏览器；本地预览和线上站点的存储相互独立。

生成单文件（仅构建工具需要Python，代码运行不需要）：

```sh
python tools/build-standalone.py ../Fluffy-Cat-v11.html
```

## 更新现有网站

完整解压**外层更新包**，双击 `Update-GitHub-Pages.cmd`，核对
`ChiZhang-805/fluffy-cat-journal` 再确认。无需重建仓库或重设Pages。
更新器核对旧文件SHA，冲突即停；不删除其他文件、不强推，提交后核对线上资源。
不要运行旧的 `site/Publish-GitHub-Pages.cmd`，它只用于最初新建仓库。
本轮GitHub集成写入实际返回403，源码交付不表示网站已经上线。

## 验证与源代码

```sh
npm test
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python tests/v11-browser.py
python tests/media_v5_browser_test.py
python tests/interaction_v9_browser_test.py
python tests/refinement_v10_browser_test.py
python tools/audit-comments.py
```

浏览器默认 `/usr/bin/chromium`，其他环境通过 `CHROMIUM_BIN` 指定实际浏览器。
使用真实源码、隔离存储；API/媒体为明确的fixture，不会花费用户额度。
本轮的实现边界、语言原文保护、跨日意图、多条统计及测试方式详见
`docs/v11-workflow-and-language.md`。外层 `verification` 保留实际结果。

函数头有输入、输出、功能；长函数按阶段组织。真实模型语义准确率、硬件麦克风/摄像头、
iPhone/Safari、Windows更新上线尚未端到端实测，不能用测试替身结果替代。
