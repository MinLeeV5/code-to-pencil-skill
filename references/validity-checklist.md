# Validity Checklist

一份 `code-to-pencil` 产出，至少满足以下条件才算有效：

## Source Validity

- 顶层 frame 能回溯到页面入口文件
- 关键资源能回溯到 import 路径
- 关键状态能回溯到 step / loading / error / expired / countdown 等代码分支

## Pen Validity

- `.pen` 可被 JSON 解析
- 顶层 frame 名称完整且不重复
- 顶层 frame 带 `context` 或等价说明
- 引用的相对资源路径真实存在

## UX Validity

- 主路径 affordance 清晰
- 省略区域已显式说明
- 第三方内容未被错误固化为真实用户态

## Review Validity

- 至少做过一次 Pencil `get_screenshot`
- 如果走过 interactive / headless 修补链路，已经显式执行过 `save()`
- 结论依据代码或结构事实，而不是主观感觉
