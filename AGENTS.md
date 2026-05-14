

## 语言设置
- 始终使用中文回复

## 输出风格
- 简洁、直接
- 避免不必要的介绍或总结

## 环境配置
- 在终端使用 Python 前，必须先运行 `conda activate forskills` 启动虚拟环境
- 所有 Python 相关命令都应在激活的虚拟环境中执行
## 文件搜索偏好
- 搜索本地文件或文件内容时，优先使用 rg / ripgrep。
- 搜索文件内容：rg <关键词>；按类型搜索：rg <关键词> -g *.py。
- 搜索文件名：rg --files | rg <关键词>；按扩展名列文件：rg --files -g *.py。
- 如果 rg 不可用或不适合，再退回 PowerShell 命令：Get-ChildItem -Recurse、Where-Object、Select-String。

- 对明确要求“全电脑 / 全盘 / 全局”找文件的任务，不要只搜当前目录；优先直接搜所有固定磁盘根目录。
- 找文件名时优先用最短直接命令，避免先 `Get-Command`、复杂 PowerShell 包装或无必要 fallback；例如：`rg --files C:\ D:\ E:\ 2>$null | rg -i '<文件名或正则>'`。
- 在 Git 项目内找仓库文件时优先 `git ls-files | rg -i '<关键词>'`；只有用户要求全盘时才扩大到所有磁盘。
- 搜索前如果用户给的是类似 `ffmpeg.d11` 的疑似拼写，直接同时搜常见变体（如 `d11|dll`），不要额外来回确认。

## 文档阅读
- 阅读 `.docx`、`.xlsx`、`.pdf`、`.pptx` 等文档时，可以使用 `forskills` Conda 环境里的 `markitdown` 工具先转换为 Markdown (`.md`) 文件后再阅读。
- 推荐命令：
  ```powershell
  conda activate forskills
  python -m markitdown "输入文件路径" -o "输出文件路径.md"
  ```

## 用户信息
- GitHub 用户名：LBY-114514
- 邮箱：302688675@qq.com
- 本地代理端口：10090
