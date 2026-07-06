🎬 B站视频智能总结助手
输入 B站 BV 号，自动下载视频，通过语音识别 + 画面理解生成结构化学习笔记

✨ 功能特性
📥 获取分P列表：输入BV号，自动获取视频所有分P

⬇️ 选择性下载：勾选需要处理的分P，调用 BBDown 下载

🎙️ 语音转写：Whisper 模型，GPU 加速

🖼️ 画面描述：BLIP 模型，理解视频画面内容

🔗 多模态融合：音画时间轴对齐，生成融合上下文

📝 AI 总结：调用 Agnes API 生成结构化笔记

🔄 反思机制：生成 → 自评 → 修正，闭环优化

🔧 工具调用：Wikipedia 检索，增强事实准确性

⚡ 快速模式：跳过画面描述 + 关闭反思，速度提升 3~5 倍

💬 多轮对话：基于笔记内容与 AI 对话修改

📚 历史管理：笔记持久化存储，支持删除（可选同时删视频）

🛠️ 技术栈
类别	技术
后端框架	FastAPI + Uvicorn
AI 模型	Whisper (语音) + BLIP (图像)
大语言模型	Agnes API / DeepSeek
视频处理	FFmpeg、BBDown
前端	HTML + CSS + JavaScript (无框架)
数据库	SQLite
📦 前置条件
项目	说明	下载地址
Python 3.10+	必须安装	https://www.python.org/downloads/
FFmpeg	音视频处理	https://ffmpeg.org/download.html
BBDown	B站视频下载	https://github.com/nilaoda/BBDown/releases
Whisper-small	语音识别模型 (~500MB)	https://huggingface.co/openai/whisper-small
BLIP	图像描述模型 (~1GB)	https://huggingface.co/Salesforce/blip-image-captioning-base
Agnes API 密钥	大模型调用	https://apihub.agnes-ai.com/
🚀 快速开始
1️⃣ 克隆项目
bash
git clone https://github.com/你的用户名/项目名.git
cd 项目名
2️⃣ 下载外部工具
将以下文件放入项目根目录：

ffmpeg.exe

BBDown.exe

whisper-small/ 文件夹

blip-model/ 文件夹

3️⃣ 配置 API 密钥
bash
# 将 .env.example 重命名为 .env
# 打开 .env，填入你的密钥
AGNES_API_KEY=sk-你的密钥
4️⃣ 安装依赖 & 启动
bash
# 双击 start.bat（自动安装依赖并启动后端）
# 或手动执行：
pip install -r requirements.txt
python -m uvicorn backend:app --host 127.0.0.1 --port 8000
5️⃣ 打开前端
双击 index.html，或浏览器访问 http://127.0.0.1:8000

6️⃣ 首次使用：B站账号登录
bash
.\BBDown.exe login   # 终端扫码登录，只需一次
📁 目录结构
text
bili/
├── modules/                 # 核心功能模块
│   ├── audio.py            # FFmpeg 提取音频
│   ├── frames.py           # FFmpeg 抽取关键帧
│   ├── transcribe.py       # Whisper 语音转文字
│   ├── vision.py           # BLIP 画面描述
│   ├── fusion.py           # 音画时间轴融合
│   └── summarize.py        # AI 总结 + 反思 + 工具调用
├── backend.py              # FastAPI 后端
├── orchestrator.py         # 核心流水线调度
├── database.py             # SQLite 数据库操作
├── decision.py             # 参数自主决策
├── utils.py                # 工具函数
├── index.html              # 前端界面
├── start.bat               # 一键启动
├── requirements.txt        # Python 依赖
├── .env.example            # 密钥配置模板
└── .gitignore              # Git 忽略配置
⚙️ 配置说明
API 切换 (Agnes / DeepSeek)
在 utils.py 中修改：

python
USE_API = "agnes"  # 可选 "agnes" 或 "deepseek"
快速模式
前端勾选 “⚡ 快速模式”，自动：

跳过 BLIP 画面描述

关闭反思机制

关闭工具调用

自定义提示词
在配置面板输入额外指令，例如：

text
请重点分析案例，用通俗语言解释
❓ 常见问题
Q1: 启动时提示“未找到 .env 文件”
创建 .env 文件，填入 AGNES_API_KEY=你的密钥

Q2: 下载时提示“BBDown.exe 未找到”
确保 BBDown.exe 已放入项目根目录

Q3: 解析时报错“ffmpeg 不是内部命令”
确保 ffmpeg.exe 已放入项目根目录

Q4: 模型加载时卡住不动
首次加载约 1~2 分钟，请耐心等待

检查 whisper-small/ 和 blip-model/ 文件夹是否完整

Q5: 历史记录里为什么有两条相同的笔记？
旧版本可能产生无效记录，访问 http://127.0.0.1:8000/cleanup 可自动清理

📄 License
MIT License © 2026

🙏 致谢
FFmpeg — 音视频处理

BBDown — B站视频下载

Whisper — OpenAI 语音识别

BLIP — Salesforce 图像描述

Agnes API — 大语言模型

FastAPI — Web 框架

开始使用吧 🎉