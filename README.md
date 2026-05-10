# 挑战杯提醒

一个本地运行的挑战杯事项提醒工具。启动后会打开浏览器页面，可添加、编辑、完成和删除提醒事项，并在提醒时间到达后触发本机通知。

## 环境要求

本项目只使用 Python 标准库，**不需要额外安装第三方 Python 包**。

你需要准备：

- Python 3.10 或更高版本
- Conda / Miniconda / Miniforge（可选，但推荐）

说明：`forskills` 只是作者电脑上的 Conda 环境名称，不是本项目必须安装的东西。别人使用时可以任选一种方式：

### 方式一：创建同名环境

```bat
conda create -n forskills python=3.11
conda activate forskills
```

这样可以直接使用项目里的 `start.bat`。

### 方式二：使用自己的环境名

例如你想用 `reminder` 作为环境名：

```bat
conda create -n reminder python=3.11
conda activate reminder
```

然后把 `start.bat` 里的：

```bat
call conda activate forskills
```

改成：

```bat
call conda activate reminder
```

### 方式三：不用 Conda

如果电脑已经有可用的 Python，可以直接运行：

```bat
python app.py
```

这种情况下也可以把 `start.bat` 里的 Conda 检查和激活部分删掉，只保留：

```bat
@echo off
cd /d "%~dp0"
python app.py
pause
```

## 使用方法

### 双击启动

1. 确认已安装 Python，并准备好一个可用环境。
2. 如使用 `start.bat`，确认里面的 Conda 环境名与你电脑一致。
3. 双击 `start.bat`。
4. 浏览器会自动打开本地页面，默认地址从 `http://localhost:8787` 开始，如端口占用会自动尝试后续端口。

可以为 `start.bat` 创建桌面快捷方式，方便日常使用：右键 `start.bat` -> 发送到 -> 桌面快捷方式；也可以复制该快捷方式到桌面。

如果双击后提示 `conda` 不可用，请从 Anaconda Prompt 或 Miniforge Prompt 进入项目目录后运行启动命令，或先将 Conda 初始化到当前命令行。如果你没有使用 `forskills` 这个环境名，请同步修改 `start.bat`。

### 命令行启动

```bat
conda activate forskills
python app.py
```

如果你的环境名不是 `forskills`，把第一行换成自己的环境名；如果不用 Conda，可以只运行：

```bat
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

如果你的环境名不是 `forskills`，把第一行换成自己的环境名即可；如果不用 Conda，直接运行第二行。

## 打包成单文件 exe

如果想让别人下载一个 exe 就能使用，可以用 PyInstaller 打包。

### 安装打包工具

```bat
pip install pyinstaller
```

### 执行打包

双击：

```text
build_exe.bat
```

或在命令行运行：

```bat
build_exe.bat
```

打包成功后会生成：

```text
dist/挑战杯提醒.exe
```

把这个 exe 发给别人即可。对方不需要安装 Python 或 Conda。

### exe 版数据位置

源码运行时，数据保存在项目里的：

```text
data/issues.json
```

单文件 exe 运行时，数据会保存在当前 Windows 用户目录下：

```text
%LOCALAPPDATA%/ChallengeCupReminder/data/issues.json
```

这样可以避免 exe 每次启动时因为临时解压目录变化导致数据丢失。

## GitHub 上传提示

提交代码时可以上传启动脚本、README、测试和应用代码，但不要上传本地数据文件：

```text
data/issues.json
```

`.gitignore` 已配置忽略该文件、临时文件和损坏备份文件。
