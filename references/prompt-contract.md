# Prompt Contract

给 Pencil CLI 的 prompt 建议固定为这些段落，减少随意发挥：

## 1. Goal

说明要把哪个页面转换成 Pencil 基线稿，以及本次优先 code-first。

示例：

```text
Recreate the login page into a Pencil baseline from code, not from the current runtime screenshot.
```

## 2. Source Files

显式列出所有页面入口、核心 section、核心 component、关键 hooks。

## 3. Output

- 输出文件路径
- 目标顶层 frame names

## 4. Rules

至少包含：

- Prefer code over current runtime screenshot
- Use actual assets referenced by code
- Ignore items explicitly excluded in this phase
- Treat third-party iframe content as a neutral placeholder
- Add `context/source` notes for key frames

## 5. Deliverables

明确要生成：

- 哪些 frame
- 哪些 derived states
- 哪些资源映射

## 6. Validation Hints

加一句提醒：

```text
The generated .pen must be readable, reviewable, and suitable for further iteration.
```
