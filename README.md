# Fluffy Cat · v9

沿用现有手机APP代码原型。本次只调整记录页的底部按钮，以及数据回顾页的「文字聊聊」弹层。

## 本版行为

记录未填满：居中的麦克风 + **长按向小猫倾诉**。
记录填满并有效：普通记录为 **完成并继续**；专注仍为 **开始专注**，编辑/补记保留各自动作。
清空内容会立即回到倾诉提示，照片不计入填空。可选营养等原有提交规则不变，不要求编造未知信息。

记录页长按时仍在上方记录模块显示音量/转写；数据回顾页才在底部绿色聊天按钮里显示波形。

回顾「文字聊聊」标题增加图标，输入与发送按钮间距为14设计像素；发送图标与较大文字一起居中。
支持多行、输入法、Ctrl/Cmd+Enter、空白检查和单次提交；仍然只读既有记录。

## 运行

目录版不需要构建或安装npm依赖，使用静态服务器：

```sh
python -m http.server 8000
```

浏览器打开本机服务器。发布版在既有 GitHub Pages 使用。
单文件预览可由下面命令生成；它内嵌页面资源，但不内嵌API密钥或个人记录：

```sh
python tools/build-standalone.py ../Fluffy-Cat-v9.html
```

语音与模型功能沿用项目现有配置。Key只存页面内存，不要硬编码到本仓库。
用户运动/饮食等记录仍由当前浏览器本机存储管理，单文件与网站属于不同存储环境，不会自动同步。

## 验证

```sh
npm test
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python tests/interaction_v9_browser_test.py
python tests/journal_v8_extra_test.py
python tests/standalone_v9_smoke.py ../Fluffy-Cat-v9.html
```

浏览器脚本可用 `CHROMIUM_BIN` 指定可执行文件，`FLUFFY_RESULTS` 指定证据目录。
测试只注入明确的测试替身，不使用付费服务和真实用户记录。

已完成216个单元测试、113项针对性浏览器/产物检查；更多边界与未验证项见
[`docs/v9-entry-action-and-text-chat.md`](docs/v9-entry-action-and-text-chat.md)。

## 更新现有网站

完整解压外层更新包，运行 **Update-GitHub-Pages.cmd**，核对仓库名后确认。
外层脚本会核验旧文件 SHA、保护并发改动、一次性提交本轮文件，并检查原网址的新版资源。
不新建仓库、不删除无关文件、不强推、不修改Pages配置。

不要运行本目录中的旧 **Publish-GitHub-Pages.cmd**；那是保留的初次创建工具。

## 主要实现

- `js/entry-action.js`：完成度检查和按钮状态映射，纯逻辑可测试。
- `js/app.js`：输入/回填/日期/语言刷新，以及受控的底部面板标题图标。
- `js/review.js`：原回顾聊天链路上的文字输入表单。
- `css/interaction-v9.css`：只作用于本轮改动的布局样式。
- `js/catalog.js`、`js/animation.js` 等原字段/动画模块未改变。

命名函数头保持「输入、输出、功能」，长函数内按阶段注释。没有附带字体文件。
