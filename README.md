# 小浩 · 智能聊天机器人

基于大模型 API 的智能对话助手，支持流式对话、多模型切换、历史记录持久化。
后端调用 OpenAI 兼容接口（本版本接入 `api.edgefn.net`，可切换 GLM-5 / DeepSeek-V3.2），
界面用 Gradio 搭建。

> **版本说明**：本仓库是**早期 Gradio 单文件版本**，便于阅读与一键运行。
> 另一个基于 PySide6 + QThread 的桌面版（含气泡式聊天窗、头像自定义、百度语音输入）
> 未包含在本仓库中。

## 功能

- **流式对话**：`stream=True` 逐块返回，边生成边渲染，首字延迟低
- **多模型切换**：GLM-5 / DeepSeek-V3.2，下拉框即时切换
- **上下文管理**：系统提示词 + 完整历史消息拼接（`role/content` 结构）
- **历史持久化**：按会话写入 `chat_history/`，重启不丢
- **自定义系统提示词**：可随时改写助手人设

## 快速开始

```bash
pip install -r requirements.txt
```

**先配置 API Key（不要写进代码）**：

```powershell
# Windows PowerShell
$env:AIMLAPI_KEY="你的密钥"
```

```bash
# macOS / Linux
export AIMLAPI_KEY="你的密钥"
```

```bash
python main.py
```

启动后终端会打印本地地址（默认 `http://127.0.0.1:7860`），浏览器打开即可对话。

## 关于密钥

`main.py` 第 9 行读取环境变量，**代码里不含任何密钥**：

```python
API_KEY = os.getenv("AIMLAPI_KEY", "")
```

未配置时界面会给出明确提示。仓库附 `.env.example` 作为模板，`.env` 已被 `.gitignore` 忽略。

> ⚠️ **安全提醒**：本项目早期版本的源码中曾把密钥硬编码在 `API_KEY` 一行。
> 该版本已从仓库历史中移除（本仓库使用全新历史）。如你克隆过旧版本，请到服务商后台
> 作废并重新生成密钥。

## 排查过的真实问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 界面卡住不输出 | 同步阻塞式请求 | 改为 `stream=True` 流式读取并逐块 `yield` |
| 长回复被截断 | `max_tokens` 偏小 | 提到 8000（`MAX_TOKENS` 常量） |
| 换模型后回答风格不对 | 模型名与后端注册名不一致 | 用 `MODELS` 字典做「显示名 → 后端模型名」映射 |
| 重启后历史丢失 | 无持久化 | 增加 `HISTORY_DIR`，按会话落盘 |

## 许可

[MIT](LICENSE)

<!-- repo verified 2026-09-23 -->