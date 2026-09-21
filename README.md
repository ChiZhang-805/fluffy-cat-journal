# Fluffy Cat · GitHub Pages 版

保留原有 393 × 852 手机界面、同一只小猫、手动填写、长按语音、循环书写、放笔和原地趴睡。
本版只精简 DeepSeek 设置并修复首次麦克风授权被长按取消逻辑打断的问题。

## 在 Windows 上发布

解压整个目录，双击 `Publish-GitHub-Pages.cmd`。

脚本在你的电脑运行。缺少 GitHub CLI 时会先请求安装确认；未登录时打开 GitHub 的官方登录流程。
随后验证登录账号为 `ChiZhang-805`，请你输入 `fluffy-cat-journal` 确认创建公开仓库。
源码和猫咪素材将公开，不会上传 DeepSeek Key、录音、本机运动历史、`.env` 或其他个人目录。
它不需要 Node.js 或 Git 来发布，使用 GitHub CLI 的 REST API 完成上传。

脚本会新建仓库、原子提交源码、设置从默认分支根目录发布 Pages、开启 HTTPS，并查询构建状态。
只有 HTTPS 页面返回 200 且包含本版标识时，才显示“部署成功”并打开 GitHub 实际返回的网页地址。
结果同时写入本地 `deployment-result.json`（不上传仓库）。以后直接访问该网址，不再打开本地 HTML。

同名仓库存在时，脚本会停止，不覆盖任何已有仓库。发布中途失败时，保留错误提示；
如果仓库已经创建并上传，请在该仓库 Settings → Pages 检查发布分支及构建状态，不要反复创建同名仓库。
也可以修改参数使用一个新的仓库名：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\publish.ps1 -RepositoryName fluffy-cat-journal-v2
```

启动器只对本次 PowerShell 进程指定执行策略，不修改系统执行策略，不要求把 GitHub 令牌发给任何人。
发布脚本尚未在用户的真实 GitHub 登录环境中执行，因此本源码包不是“已经上线”的证明。

## 页面设置

右上角点击 DeepSeek，展开一个非模态下拉框，正常状态只有：

- DeepSeek Chat
- API Key 输入框
- 启用 / 清除

没有模型编号、个人原型说明、隐私说明大段文案或额外教程。
输入框为密码类型；启用成功后输入框清空，密钥只存在当前页面的私有客户端实例中。
点击框外或 Escape 可关闭。关闭正在验证的新 Key 不会删除此前有效的 Key。
“清除”取消正在进行的语音/模型工作并清空 Key，但不删除已填写字段。
浏览器仍会保存用户主动点击完成后的运动记录；Key 不会进入这些记录。

## 麦克风：首次授权与录音分开

旧版把 `window.blur` 和 `lostpointercapture` 当作取消录音。浏览器权限弹窗改变焦点时，
这可能使尚未完成的授权失效，用户看到“已取消”，下一次又陷入同样的操作。

新版流程：

1. 第一次长按先查询浏览器权限。如果尚未授权，解除按压捕获，单独申请一次麦克风。
2. 用户点击允许后立即关闭测试音频流，回到待机并提示“可以了，长按开始说话”。此时不转写、不发送音频。
3. 再次长按才正式录音；已经授予权限时不走首次授权分支。松手停止输入，然后整理字段、连续进入书写。
4. 正式录音时离开窗口、隐藏页面、取消或丢失指针捕获仍会停止收音，避免后台监听。
5. 授权请求并发时复用同一 Promise；取消后晚到的音频流仍然立即关闭，不会迟到启动录音。

网页不能绕过或永久授予浏览器权限。HTTPS 的稳定网站地址便于浏览器按站点记住许可。
选择“访问此网站时允许”，而不是只允许一次；无痕模式、主动撤销、浏览器清理、企业策略
或语音识别服务本身的权限仍可能让浏览器再次询问。

## 语音及模型实现

语音仍由浏览器 `SpeechRecognition` / `webkitSpeechRecognition` 转写；
`getUserMedia` + Web Audio 读取实际音量，产生从右向左移动的柱形波。
只有真实语音识别器触发 `onstart` 后，界面才显示“我在听”。
转写文字发送给 DeepSeek 官方 Chat Completions 接口，返回可编辑的四个字段。
音频没有被伪装成 DeepSeek 文本模型的输入，错误时不使用假记录补齐。

界面名称是 DeepSeek Chat。公开配置里的实际模型 ID 沿用本项目当前接口配置，
不在 UI 展示。服务商变更模型时，在 `js/config.js` 更新即可；不要把 Key 写在配置里。
GitHub Pages 只托管静态文件；此原型从浏览器直连官方 API，仍依赖服务商跨域策略和网络可达性。
面向公众的正式产品应将模型密钥和请求鉴权迁到自有后端；这不是本次新增的功能。

## 源码结构和注释

```text
index.html                   手机布局及精简下拉框
css/app.css                  原界面样式、下拉菜单、响应式布局
js/app.js                    表单、语音、设置、动画状态衔接
js/microphone-permission.js   首次授权控制器，不常驻占用麦克风
js/speech.js                 音频输入、音量、真实识别事件
js/gesture.js                短按/长按/松开/取消及授权前 disarm
js/deepseek.js               私有内存 Key、API 校验及结构化整理
js/model.js                  字段校验、编辑保护、循环位置
js/animation.js              原有连续动画时序
js/cat-actor.js               原图纹理、短前爪、尾巴、趴睡
js/handwriting.js            实际记录的笔画
assets/                     原猫图层，不是页面截图轮播
publish.ps1                 Windows 新仓库及 Pages 发布脚本
```

新增函数头说明“输入、输出、功能”；较长逻辑在关键处使用“阶段一 / 阶段二 / 阶段三”注释。

## 验证与限制

运行不需要构建或 npm 依赖。开发时使用任意静态 HTTP 服务器，例如：

```bash
python -m http.server 8000
```

单元测试（Node.js 20+）：

```bash
node --test tests/core.test.cjs
```

浏览器测试（Python）：

```bash
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python tests/browser_test.py
```

本轮通过 7 项单元测试和 26 项浏览器断言，包括授权弹窗失焦、清除/取消、晚到音频、
长按松手只提交一次、短按原流程、六种视口下拉菜单边界。
浏览器测试使用内存文档执行真实项目代码，但麦克风、权限状态和 API 是明确的测试替身。
当前运行环境阻止浏览器访问本地服务器，所以没有把内存文档测试当作线上 URL 测试。
尚未验证真实麦克风、真实 DeepSeek Key、iPhone/Safari、Windows 发布脚本的端到端执行和实际 Pages 上线。

## 官方资料

- 麦克风权限：https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- 权限查询：https://developer.mozilla.org/en-US/docs/Web/API/Permissions/query
- GitHub Pages 发布源：https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- GitHub Pages REST：https://docs.github.com/en/rest/pages/pages
- GitHub CLI 登录：https://cli.github.com/manual/gh_auth_login
- DeepSeek Chat 接口：https://api-docs.deepseek.com/api/create-chat-completion/
