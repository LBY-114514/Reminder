# 挑战杯提醒

一个本地运行的挑战杯事项提醒工具。启动后会打开浏览器页面，可添加、编辑、完成和删除提醒事项，并在提醒时间到达后触发本机通知。

## 使用方法

### 双击启动

1. 确认已安装 Conda，并存在 `forskills` 环境。
2. 双击 `start.bat`。
3. 程序会切换到项目目录、激活 `forskills` 环境并运行 `python app.py`。
4. 浏览器会自动打开本地页面，默认地址从 `http://localhost:8787` 开始，如端口占用会自动尝试后续端口。

可以为 `start.bat` 创建桌面快捷方式，方便日常使用：右键 `start.bat` -> 发送到 -> 桌面快捷方式；也可以复制该快捷方式到桌面。

如果双击后提示 `conda` 不可用，请从 Anaconda Prompt 或 Miniforge Prompt 进入项目目录后运行启动命令，或先将 Conda 初始化到当前命令行。无论哪种方式，都需要提前创建好 `forskills` 环境。

### 命令行启动

```bat
conda activate forskills
python app.py
```

## 数据位置

提醒事项保存在：

```text
data/issues.json
```

该文件包含本地个人数据，已在 `.gitignore` 中忽略，不会上传到 GitHub。`data/.gitkeep` 仅用于保留空目录。

如果数据文件损坏，程序会备份为类似 `data/issues.json.corrupt-YYYYMMDDHHMMSS` 的文件，并重新创建空数据文件；这些备份文件也不会上传。

## 测试命令

运行测试前先激活虚拟环境：

```bat
conda activate forskills
python -m unittest discover -s tests -v
```

## GitHub 上传提示

提交代码时可以上传启动脚本、README、测试和应用代码，但不要上传本地数据文件：

```text
data/issues.json
```

`.gitignore` 已配置忽略该文件和损坏备份文件。
