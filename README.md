# Fluffy Cat · Recap v7

保留原v6记录页。新增六板块的**数据回顾＋上下文陪伴对话**，使用同一只小猫连续动画。
基于线上提交 `000fd77e96441e7220a95d827678f65a97328293`。GitHub连接写入仍为403；本包不是已上线证明。

## 本版怎么体验

记录确认 → 小猫书写/放笔 → Great job! → 点击完成 → 对应板块回顾。
专注实际计时结束后同样进入专注回顾。已有历史记录详情也可“查看回顾”。

回顾一屏内：左上房屋返回首页，右上省略号菜单，原小猫＋短句气泡，当天指标、近7天动态图表，
底部一个“长按和小猫聊两句”按钮。长按时图标和字消失，显示真实音量波形；松手提交。
小猫读取当前类别近7天的确认记录，和当前会话最近六轮，回应你的感受而不是再填一遍表单。

- 原始音频用已有百炼配置；只有DeepSeek时使用浏览器转写＋文本模型。
- 菜单中提供语言切换、分享卡片、评分依据、对话记录和文字聊聊；运动/睡眠另有调整目标。
- 长回复逐句一至两行显示，淡出再出现；点气泡可暂停；回顾保持原位，聊天不修改记录。
- 语言切换范围是回顾界面及后续回复；原记录页和用户原文不变。
- 分享先本地生成图片预览，用户再决定保存/系统分享，不自动对外发布。
- 没有记录的日期留空；没有Key也能看数据，不编造AI回应或历史。

数字采用可查看的确定性规则：运动/专注为目标完成、睡眠为时长目标匹配，饮食/面部为记录完整度。
它们不是医疗/营养健康/疲惫/颜值评分；情绪保留原话而不按好坏打分。
详细公式、接口与限制见 [docs/v7-recap.md](docs/v7-recap.md)。

## 更新原网站

完整解压外层包，在site文件夹外双击 **Update-GitHub-Pages.cmd**。
核对 `ChiZhang-805/fluffy-cat-journal`，按提示输入 `fluffy-cat-journal`。
脚本复用本机GitHub CLI登录，校验远程基线、原子提交更改，保留原网站地址、Pages配置和无关文件。
遇到未知修改就停止，绝不force push。检查到网页及实际CSS/JS内容匹配后才报告上线成功。
不要运行旧的Publish-GitHub-Pages.cmd，那是新建仓库工具。

## 本地和单文件

站点没有构建依赖：

```sh
python -m http.server 8000
```

生成独立预览（不含测试替身、Key、用户数据或字体文件）：

```sh
python tools/build-standalone.py ../Fluffy-Cat-Recap-v7.html
```

语音、模型和系统分享需要相应浏览器能力、许可、网络与有效Key。推荐在已有HTTPS站点实际体验。
Key只在当前页面内存；记录仍保存本浏览器；聊天仅页面内存，不跨设备同步，不是已部署后端。
API继续复用js/config.js中的官方端点与模型配置；本次不改设置菜单和旧表单。

## 检验

```sh
npm test
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
npm run test:browser
python tools/audit-comments.py
```

系统安装Chromium时可设 `CHROMIUM_BIN=/usr/bin/chromium`，原时钟回归使用`CHROMIUM_PATH`。
测试均为真实源代码；存储/权限/音频/API有明确替身。没有付费调用或私人录音样本。
实际通过数量和报告见外层verification，单文件也单独加载核验。
**未完成**真实麦克风/摄像头、个人模型Key、iPhone/Safari、原生分享和Windows在线更新的端到端实测。
本运行环境禁止localhost浏览器导航，检验在内存文档执行，不绕过策略、不冒充真实URL实测。

注释：命名函数/方法头写输入、输出、功能；长流程按阶段说明。
旧docs/v5-validation.md、v6-refinement.md等保留为历史设计；当前回顾路由以v7为准。
