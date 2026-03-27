# Pencil CLI Prompt Workflow

## Goal

把页面代码转换成一份稳定的 Pencil 基线稿，避免依赖当前运行态截图。

## Recommended Flow

1. 选定 page entry、section、component、hook、resource files
2. 用 `scripts/build_pencil_prompt.py` 生成结构化 prompt
3. 用 `pencil --workspace --out --prompt` 生成 `.pen`
4. 用 `scripts/validate_pen.py` 做结构校验
5. 用 Pencil screenshot 做轻量复审

## Why Prefer `--prompt`

- 不依赖当前桌面端 / Web 是否正停在目标状态
- 可以明确写入 source files、忽略项、第三方占位规则
- 更适合批量化生成多个页面的基线稿

## Required CLI Shape

```bash
pencil \
  --workspace /absolute/path/to/repo \
  --out /absolute/path/to/repo/uidesign/<page>.pen \
  --prompt "$(cat /tmp/<page>-pencil-prompt.txt)"
```

说明：

- 优先把最终产物交给 `--out`，避免只在交互会话里改了内存态却没有真正写文件
- 官方 CLI 文档明确说明 interactive/headless 模式不会自动保存；如果后续进入交互修补，必须显式执行 `save()`

## Interactive Fallback

如果 prompt mode 结果需要局部修补，再进入：

```bash
pencil interactive -i <input.pen> -o <output.pen>
```

然后：

- `get_editor_state({ include_schema: false })`
- `get_screenshot({ nodeId: "frameId" })`
- 修完以后执行 `save()`

## Do Not Use Runtime As The Only Source

以下场景默认跳过 screenshot-first：

- 鉴权态受本地缓存影响
- 页面需要清 token / 清 session / 清本地状态才能进入
- 第三方 iframe 内容不可控
- 目标态依赖复杂远程数据
