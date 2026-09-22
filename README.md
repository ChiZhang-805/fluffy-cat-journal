# Fluffy Cat · 六入口陪伴手记

可运行的 393 × 852 竖屏交互代码原型。基于已确认的小猫原图图层和旧版书写动画，新增浅蓝空间首页、六类记录、照片草稿和真实专注计时。不是图片轮播，也不是 iOS 原生安装包。

**构建标识：`fluffy-home-20260922-v4`。** 默认首页没有示例记录、虚构健康分数或预填任务。顶栏使用实际本地记录统计。

## 直接操作

- 点击六张卡片：进入运动、饮食、情绪、睡眠、面部或专注。
- 长按约 0.43 秒后松开：打开该组件的快捷菜单；保持按住并拖动：调整组件顺序。位置保存在当前浏览器。
- 键盘：Tab 到卡片，Enter 进入；Shift+F10 打开菜单；Alt+方向键排序；Escape 取消。
- 点击小猫：招呼回应。长按小猫或点击中央聊天按钮：打开对话入口，选择类别后整理文字，或者进入该类的长按语音记录。
- 底部五个入口：主页、手记、交流、待办、我的。都是真实交互，不是无效图标。

小猫用同一原画、独立前爪/尾巴/头部参数连续渲染；首页不是重复播放庆祝动作。没有走路/跳跃流程。减少动态效果可在“我的”设置。

## 六类记录

| 类别 | 输入与行为 |
|---|---|
| 运动 | 项目、公里数、分钟数、备注。保留整数和小数。 |
| 饮食 | 餐次、食物、份量、备注；拍照/选图，点击分析后生成可编辑营养估算。热量、蛋白质、碳水、脂肪、维生素单独展开。 |
| 情绪 | 用户自己选择情绪、强度、事件与备注。不让模型从照片判断心情。 |
| 睡眠 | 带日期的入睡/起床时间、主观感受、备注，正确计算跨午夜时长。 |
| 面部 | 用户自评、可见眼周/皮肤外观、备注，支持照片。只记观察，不打颜值分、不判断身份、疾病或真实疲劳程度。 |
| 专注 | 任务、预计分钟、目标；可让 AI 给出可修改的估时，也可放入待办再开始。 |

### 普通记录

输入或 AI 草稿 → **用户确认** → 小猫实际书写 → 放稳铅笔 → 点击继续 → Great job → 回到首页。

书写内容来自确认记录；三组“标题、笔迹、横线”一起循环，正在写的标题留在笔尖附近；最终回到完整摘要。较详细营养数据在“手记”保留，而不是全挤在猫爪旁边。写完等待时小猫原地趴睡。

### 专注

确认任务和时间 → 真实倒计时 → 到时/主动完全停止 → 按实际用时保存 → Great job。

暂停、休息、继续、重置、停止都有操作。重置和停止需要确认。暂停与休息不计为专注时间，休息另行累计。使用绝对截止时间而不是减少动画帧计数，刷新会恢复未结束会话。在首页点击正在计时的“专注”卡片直接回到计时器。

“计时结束”不自动代表“任务完成”。待办完成状态由用户自己勾选。网页被系统终止时不能保证准时响铃/推送，本版没有声称实现原生后台闹钟；恢复网页后会按截止时间结算。

## DeepSeek 与媒体

外部右上角下拉菜单仅包含 DeepSeek Chat、API Key、启用/清除。Key 只保存在本次页面的客户端私有内存，不写入 localStorage、源码、历史记录、URL 或 GitHub。启用操作读取官方模型列表验证访问权限；无 Key 不假装 AI 成功，手动记录不受影响。

公开模型 ID 在 `js/config.js`。按 2026-09-22 查询到的 DeepSeek 官方文档，`deepseek-flash` 接受文本和图片；本版用 Chat Completions 的 `image_url` 内容块发送重新编码的内存 JPEG。UI 保持名称 DeepSeek Chat。语音转写仍由浏览器 SpeechRecognition 提供，不把音频当成文本模型输入。

首次长按先走独立麦克风授权，允许后再长按收音。松开后停止，整理成可编辑草稿，确认后才写。未授权、无语音支持、离线、无效响应、超时会提示，不填入演示数据。

饮食/面部可以调用摄像头或选择照片；**选择照片后不自动上传**，用户再点“让小猫看看”才发送给模型。图片限制 15 MB、长边重编码至 1280px，并去除原始位置/EXIF 元数据。拍下、取消、切页或迟到授权都会关闭相机轨道。照片只在当前页面中处理，不写入历史或 GitHub。

营养为估计；重量、油量和不可见配料无法确认时要求补充。维生素不强行输出没有依据的精确数值。面部输出仅作外观观察，不能作为疲惫测量或医疗结论。

**生产环境建议：** GitHub Pages 是静态前端。本原型依赖服务商 CORS、浏览器媒体支持及网络；正式多人 APP 应将模型密钥与鉴权移至自有后端（可另接 Supabase 等服务）。本版没有声称已经部署 AI 后端、云同步、账号系统或医学验证。

## 数据

- 六类记录：`fluffy-six-journal-v1`。
- 待办：`fluffy-six-tasks-v1`。
- 排序：`fluffy-home-order-v1`。
- 当前计时会话：`fluffy-active-focus-v1`。
- 首次无新记录时，读取旧版 `fluffy-cat-minimal-records-v1` 兼容运动历史，不修改旧数据。
- 重播不重复增加记录；从历史修改保留原 ID。“我的”可导出 JSON 或确认清除本机记录。
- 这些数据是当前浏览器本地数据，不会在电脑与手机间自动同步。

## 更新既有 GitHub Pages

使用更新包外层的 **`Update-GitHub-Pages.cmd`**，不要再运行旧的 `Publish-GitHub-Pages.cmd` 创建仓库。

更新器只处理清单中的已验证文本文件，保留现有原图和其他文件；先核对远程文件是否还是基线版本，再创建一个原子提交，非强制推进 main。遇到后续修改会停止，不覆盖。成功后轮询原 Pages URL 和新 CSS/JS 的内容 SHA，不重新配置 Pages 或更换域名。

可在 Windows PowerShell 执行只读检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\update-existing.ps1 -CheckOnly
```

本次助手实际尝试创建功能分支，GitHub 集成返回 **403 Resource not accessible by integration**，未创建分支/提交，未更改线上网站。更新包需要在你自己的 GitHub CLI 登录环境执行。没有向你索取 GitHub 令牌或 DeepSeek Key。

## 开发

不依赖 npm 包/CDN，不需要构建。使用任意静态 HTTP 服务器，例如：

```bash
python -m http.server 8000
```

打开 localhost:8000。HTTPS/localhost 更适合媒体权限测试。可用 `?debug=1` 显式开放时间轴调试对象；默认没有调试控件。单文件手动预览可运行：

```bash
python tools/build-standalone.py ../Fluffy-Cat-Home.html
```

本地文件 URL 的权限/跨域行为不等同于 HTTPS 线上页面，语音与照片 API 以部署后的网页为准。

## 代码组织与注释

```text
index.html                  页面、状态栏、动态卡片及导航容器
css/home.css                浅蓝空间、错落卡片、计时、照片和内部面板
js/home-board.js            点击/长按/拖拽/键盘排序
js/catalog.js               六类字段、校验、摘要、书写行
js/journal-store.js         本地记录/待办、旧数据兼容
js/focus-timer.js           绝对时钟、暂停、恢复、结束
js/photo-input.js           图像重编码和相机生命周期
js/ai-journal.js            文本/视觉草稿、估时、字段白名单
js/app.js                   路由、表单、AI确认、历史与计时的衔接
js/animation.js             首页待机、原连续书写与庆祝
js/cat-actor.js             原图纹理、头、短前爪、尾巴及趴睡
js/status-bar.js            设备本地时间
```

函数头写明输入、输出、功能；较长流程在内部标注阶段。所有上传的 UI 文本经 textContent/表单值处理；模型生成结果不作为 HTML 注入。

## 测试与边界

```bash
npm test
python -m pip install -r tests/requirements.txt
python tests/home_browser_test.py
```

浏览器测试的 `CHROMIUM_BIN` 可指定本机 Chromium 路径。测试文档明确注入存储、网络等替身，不调用付费模型，也不请求真实设备的麦克风或摄像头。测试结果另见更新包 `validation/`；旧 `browser_test.py`/`refinement_test.py` 属于以前的运动专用布局，不应当作本版主页端到端测试。

已进行 Chromium 内存文档的实际 DOM/Canvas 操作、计时恢复与模块接口回归。**尚未完成真实麦克风/摄像头、个人 Key、iPhone/Safari、Windows 更新器以及实际线上部署的端到端验证。** 状态栏时间是真实的，信号和电池仍是装饰；不声称原生状态栏逐像素一致。

## 官方接口参考

核对日期：2026-09-22。

- DeepSeek 图像输入：https://api-docs.deepseek.com/zh-cn/guides/vision/
- DeepSeek 思考开关：https://api-docs.deepseek.com/guides/thinking_mode/
- 摄像头与麦克风：https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- 浏览器语音识别：https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition
- Pages 发布源：https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
