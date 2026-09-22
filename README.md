# Fluffy Cat v13 · 选图即分析的饮食记录

此包可直接从已发布的 v11 更新到 v13，包含 v12 的全部语言路由、听写恢复和气泡反馈修复。
先完整解压，再双击外层 `Update-GitHub-Pages.cmd`。不要运行 `site/Publish-GitHub-Pages.cmd`。
更新继续使用 `ChiZhang-805/fluffy-cat-journal`，不创建仓库、不更改 Pages 地址。

## 本版饮食页

- 用户选择或拍摄照片并返回记录页后，自动请求一次百炼视觉分析；没有“让小猫看看”按钮。
- 删除黄色说明区的显示。热量、蛋白质、碳水化合物、脂肪直接平铺为四个全宽输入框，无营养折叠模块。
- 小猫在气泡中表现思考、完成和失败；照片和表单始终可见，录音的原有上方波形不变。
- 份量与营养根据清楚的食物和用户补充作大致计算。正常图片不再因为缺少称重信息一概返回空值；真正缺少可用依据时仍留空，不伪造数字。
- 常驻界面不显示“估算”说明。内部 `estimated` 保留来源语义；数值不是实测结果。
- 新图自动取代旧图的未修改AI字段，上传前或等待期间的手动填写不覆盖；取消和迟到回复受同一页面/日期/条目标识保护。
- 无Key时先保留图片，用户启用百炼后处理当前等待中的照片。失败后点小猫可重试，不无限自动重发。
- 面部页保持原来的手动分析按钮；此次改变范围是饮食页。没有调整小猫、首页、回顾或专注计时。

## 服务分工

DeepSeek 处理所有文字整理、回顾聊天、翻译和估时。浏览器负责语音转写。
百炼仅处理照片，保留北京端点与 `qwen3-vl-plus` 配置。Key 只存在本次页面内存，不写入源码、照片元数据或本地记录。
自动分析仅源于用户新选图/拍摄；渲染、语言切换、打开历史或普通输入不会自行上传图片。

## 本地运行和测试

```sh
python -m http.server 8000
npm test
python tests/v13-browser.py
python tests/v12-browser.py
python tools/build-standalone.py ../Fluffy-Cat-v13.html
python tests/v12-standalone.py ../Fluffy-Cat-v13.html
```

浏览器测试需要 `tests/requirements.txt` 中的依赖和 Chromium；默认查找 `/usr/bin/chromium`。
测试源图、摄像头视频流和上游回复均为明确的人工测试输入，不调用收费 API。
独立 HTML 手动流程测试禁止网络、不启用测试接口。

## 文档

- `docs/v13-food-auto-analysis.md`：请求生命周期、字段所有权和已知边界。
- `docs/v12-ai-and-feedback.md`：语言路由、语音与气泡错误反馈。
- 其余 `docs/v*.md`：此前版本的实现与历史验证说明。
- `licenses/Lucide-LICENSE.txt`：保留的图标许可。

真实个人 API Key、真实食物识别准确度、实体摄像头、iPhone/Safari、Windows 在线发布未在本轮实测。
网页不是已部署的证明。仓库写入被 GitHub 集成权限拒绝，需本机更新脚本完成提交。
