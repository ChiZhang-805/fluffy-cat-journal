# NAVA · 和小猫记录日常（v17）

这是接入“初见手记”的现有 Fluffy Cat 六类记录应用。保留首页、运动/饮食/情绪/睡眠/面部/专注记录、连续小猫书写、庆祝、回顾图表与陪伴对话。

首次使用先展示欢迎信与七题引导。汇总点击“开启 NAVA 之旅”后进入主应用，再次打开直接进入。偏好和日记分开保存；引导不会生成当天记录或改动已有数据。

## 使用

在既有 GitHub Pages 站点使用 `index.html`。这份更新不改 Pages 域名或发布设置。

本地运行：

```sh
python -m http.server 8000
```

生成单文件（需要 Python）：

```sh
python tools/build-standalone.py ../NAVA-Fluffy-v17.html
```

单文件的交互与网站相同，资源内嵌，无外部字体文件。语音/AI仍需浏览器支持、权限、网络和本人 Key；初见引导完全不需要 API。

## 验证

```sh
npm test
python tests/first_run_v17_browser.py ../NAVA-Fluffy-v17.html
```

浏览器检查需要 `tests/requirements.txt` 中的开发依赖与 Chromium；脚本明确使用隔离存储，不读用户日记。测试数据与替身只在 `tests`，不会打进发行 HTML。

具体改动、架构、数据边界与实机验证范围见 `docs/v17-onboarding.md`。源代码包含必要的函数输入、输出、功能注释。第三方图标许可在 `licenses`，保留原项目的许可证。

当前没有跨设备账户系统。资料与手记保存在当前浏览器；清理网站数据或换设备，不会自动迁移。不要把 API Key 写进源码、GitHub 或问卷资料。
