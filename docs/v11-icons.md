# v11 图标规范与来源

## 实际替换范围

首页六类、底部五项导航使用 Lucide 的同一套圆角线性 SVG。
不是图标字体、不是截图、不依赖 CDN。状态栏不随此更换，猫咪素材和绑定不变。
共用 24×24 坐标，界面描边 1.8；类别 25px、导航 23px、中间聊天 37px。
扫描框改为简洁表情；运动改为哑铃；手记为笔记本，待办为勾选清单，减少相似轮廓。
其他小控件沿用并整理本项目的本地几何路径，不宣称全部都是 Lucide 原图。

| 项目 | Lucide 上游文件 |
|---|---|
| 情绪 | icons/face-slightly-smiling.svg |
| 饮食 | icons/utensils.svg |
| 运动 | icons/dumbbell.svg |
| 睡眠 | icons/moon-star.svg |
| 面部 | icons/scan-face.svg |
| 专注 | icons/timer.svg |
| 首页 | icons/house.svg |
| 手记 | icons/notebook-pen.svg |
| 待办 | icons/list-checks.svg |
| 聊天 | icons/message-circle-more.svg |
| 我的 | icons/circle-user-round.svg |

读取来源： https://github.com/lucide-icons/lucide/tree/main/icons ，读取日期 2026-09-22。
许可原文保留在 `licenses/Lucide-LICENSE.txt`，包含 Lucide ISC 与 Feather MIT 的版权说明。
部分共线子路径在本地合并为一个 `path`，轮廓不改变；描边宽度按当前界面校准。
`js/icons.js` 的名称和类名使用白名单，不把模型或用户文字当 SVG 执行。

## 审查

实际手机缩放下检查轮廓、光学大小、行内对齐、白色/蓝色背景和深色聊天按钮。
本项目并非原生 iOS UI，不宣称任何自定义图标等同 Apple 的系统资产。
没有复制或分发系统字体文件。
