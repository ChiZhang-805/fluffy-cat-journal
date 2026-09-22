# Fluffy Cat · v8 记录日期与双语菜单

393 × 852 的可运行手机交互原型。六类记录、同一只猫的连续动画、记录后回顾，以及基于已确认数据的只读陪伴聊天。

本轮在 v7 基础上增加：六类输入页右上角三点菜单（调整日期／语言切换／数据回顾）；可补记过去日期；记录与回顾页中英界面切换；首页气泡挪近猫咪。已有表单和猫咪素材不重画。

## 使用

点击首页组件进入对应记录页。记录页右上角三点菜单可选择本地过去日期，确认后表单标题和日期标记改变。提交后，记录、周图表和陪聊数据均归到选定日，而非今天创建文件的日期。

语言切换保留输入原文、照片和当前日期；不把用户的中文内容自动翻成英文。菜单“数据回顾”查看已保存记录，没有记录显示空状态，不提前保存草稿。

睡眠以选定日作为醒来日计算跨午夜。专注补记记录过去实际投入的分钟数；今天的新专注仍启动倒计时。手动补记不会假装运行过计时器，不凭空生成计划完成分。

## 更新现有 GitHub Pages

完整解压外层更新包，运行外层的 `Update-GitHub-Pages.cmd`。确认账号/仓库 `ChiZhang-805/fluffy-cat-journal`，按提示输入仓库名。

工具使用你电脑已有的 GitHub CLI 登录，只提交本次改动。不新建仓库、不删除无关文件、不强制覆盖远程的新变更。网页地址和已有 Pages 配置保持原样。它检查新版 HTML、CSS、JavaScript 均已上线后才显示完成。

源码目录里的旧 `Publish-GitHub-Pages.cmd` 是历史新建仓库脚本，不用于本轮更新。不要反复用新建脚本更新现有站点。

本轮 GitHub 集成写入实际返回 403，因此源码包本身不是已经部署的证明。

## 本地开发与单文件

网页无 npm 运行依赖。可以使用已有的静态服务器提供 `site` 根目录，例如 `python -m http.server 8000`。相机和录音还取决于浏览器许可、安全上下文及接口网络。

生成不带测试替身的单文件 HTML：

```sh
python tools/build-standalone.py ../Fluffy-Cat-v8.html
```

单文件用于手动交互预览，API/录音仍需权限与可用网络。模型 Key 通过外部极简设置输入，仅驻留当前页面的客户端实例；不内嵌、不保存到仓库或本地手记。

## AI 与数据

沿用原来的 DeepSeek 文本整理，以及百炼图片/原始音频配置。未配置 Key 时保留手动输入，不拿示例冒充 AI。模型输出仍是可修改草稿；正在请求时更改日期会取消旧请求，迟到的响应不能覆盖用户新输入。

记录存于当前浏览器；本版没有云同步，不同浏览器的数据不自动共享。清理站点存储会影响本机记录。补记结构保留实际 `createdAt` 并新增 `recordDate`，旧记录只读兼容；隐私、图片分析和原始音频边界沿用此前版本。

## 测试

```sh
npm test
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python tests/journal_v8_browser_test.py
python tests/journal_v8_extra_test.py
python tests/review_browser_test.py
python tests/review_extra_test.py
python tools/audit-comments.py
```

浏览器路径通过 `CHROMIUM_BIN` 指定（测试默认 `/usr/bin/chromium`）；结果目录通过 `FLUFFY_RESULTS` 指定。测试在内存文档运行实际交付源码，隔离存储和明确 API 替身，不调用付费服务。

更多字段、日期语义、专注编辑和本轮验证范围见 `docs/v8-record-date-language.md`。新增命名函数与方法使用“输入、输出、功能”注释，复杂方法分阶段说明。没有附带字体文件。
