# Fluffy Cat · v10

基于已部署的v9，仅调整数据回顾的空间利用和六类记录的长按提示。
所有猫咪素材、表单、记录校验、计时、补记、聊天和API设置继续沿用。

## 本版行为

回顾页：小猫、气泡和当天数据卡一起上移44设计像素；近7天卡片从222增至266像素，
100分的最大柱高从79增至135像素。导航、聊天按钮和数据计算不变；情绪保留无高低排序的文字足迹。

未填完整的记录按钮按板块显示：

- 运动：长按和小猫聊运动；饮食：长按告诉小猫吃了啥。
- 情绪：长按和小猫说心情；睡眠：长按和小猫聊睡眠。
- 面部：长按说说今天的状态；专注：长按告诉小猫你的计划。

中文/英文都提供对应短句；填完整后仍恢复“完成并继续”或专注对应动作。
照片不计入填空，可选营养不会变成必填。
记录页长按的波形仍在上方记录模块；回顾页才在底部绿色按钮里显示。

## 运行

目录版不需要构建或安装npm依赖，使用静态服务器：

```sh
python -m http.server 8000
```

生成单文件手动预览：

```sh
python tools/build-standalone.py ../Fluffy-Cat-v10.html
```

图片、CSS和JS均内嵌。语音/模型能力仍需网络、权限和实际Key，Key只保存在页面内存，
不要写入源码或提交仓库。原记录保存在使用者的浏览器中；本地HTML和线上站点不自动同步记录。

## 更新现有网站

完整解压外层更新包，运行 **Update-GitHub-Pages.cmd**，核对仓库名后确认。
更新器基于旧文件SHA检查冲突，保留无关文件，用一次提交更新，再检查原网址上的资源。
不新建仓库、不删除文件、不强推，也不改Pages配置。
不要运行 `site/Publish-GitHub-Pages.cmd`，那是保留的初次创建工具。
本轮GitHub连接写入返回403，下载源码不等于线上网站已经更新。

## 主要实现

- `js/review-layout.js`：Canvas与DOM共用回顾坐标，柱高纯函数。
- `css/review.css`：更高的绘图区、独立刻度/日期空间。
- `js/animation.js`：仅review场景更换平移坐标，不改角色、缩放或动作。
- `js/review.js`：使用共享布局及同比柱高。
- `js/entry-action.js`：分类长按提示，不改变完成度或录音状态。

命名函数头保持“输入、输出、功能”，长函数按阶段注明作用。没有附带字体文件。

## 验证

```sh
npm test
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python tests/refinement_v10_browser_test.py
python tests/interaction_v9_browser_test.py
python tests/review_browser_test.py
python tests/review_extra_test.py
python tests/standalone_v9_smoke.py ../Fluffy-Cat-v10.html
```

脚本支持 `CHROMIUM_BIN`（浏览器路径）、`FLUFFY_RESULTS`（证据输出目录）。
242项单元测试和306项浏览器/交付文件检查通过；65处命名函数/方法注释检查通过。

本环境的localhost浏览器导航被策略阻止，回归使用内存文档中的真实源码和隔离存储。
语音/API场景使用明确替身；真实麦克风、Key、摄像头、iPhone/Safari及Windows更新器没有端到端实测。
完整坐标、测试范围与限制见 [本版说明](docs/v10-recap-spacing-and-prompts.md)。
