import gradio as gr
import requests
import json
import os
from typing import List, Dict, Optional, Generator
from datetime import datetime

# ==================== 配置部分 ====================
API_KEY = os.getenv("AIMLAPI_KEY", "")  # 留空，由使用者通过环境变量提供；切勿把密钥写进代码
API_BASE_URL = "https://api.edgefn.net/v1/chat/completions"

MODELS = {
    "GLM-5": "GLM-5",
    "DeepSeek-V3.2": "DeepSeek-V3.2"
}

DEFAULT_SYSTEM_PROMPT = "你是一个友好、热情的智能助手，名叫小浩。请用简洁自然的中文回答用户问题。"

# 最大生成长度（可根据需要调整，None 表示使用 API 默认值）
MAX_TOKENS = 8000  # 调大以支持长回复

HISTORY_DIR = "chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

# ==================== 核心功能函数 ====================
def call_llm_api_stream(
    user_message: str,
    model_key: str,
    chat_history: List[Dict],  # 字典列表，格式 [{"role": "user/assistant", "content": "..."}]
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
) -> Generator[str, None, None]:
    """流式调用大模型API，逐块返回回复内容"""
    if not API_KEY:
        yield ('未检测到 API Key：请先设置环境变量 AIMLAPI_KEY'
               '（PowerShell 示例：$env:AIMLAPI_KEY="你的密钥"），或在代码第 9 行填入。')
        return

    # 构建 messages：系统提示 + 历史对话 + 当前用户消息
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)  # 历史已经是字典列表，直接添加
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": MODELS[model_key],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": MAX_TOKENS,   # 使用较大的值
        "top_p": 0.9,
        "stream": True
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            API_BASE_URL,
            headers=headers,
            json=payload,
            stream=True,
            timeout=60  # 延长超时，避免长回复中断
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    except requests.exceptions.RequestException as e:
        yield f"API请求失败: {str(e)}"
    except Exception as e:
        yield f"发生未知错误: {str(e)}"

def save_chat_history(history: List[Dict], filename: Optional[str] = None) -> str:
    """保存对话历史（字典列表）到JSON文件"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_{timestamp}.json"
    filepath = os.path.join(HISTORY_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return filepath

def load_chat_history(filepath: str) -> List[Dict]:
    """从文件加载对话历史（字典列表）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"加载历史失败: {e}")
        return []

def get_saved_history_list() -> List[str]:
    """获取已保存的历史文件列表"""
    files = os.listdir(HISTORY_DIR)
    return [f for f in files if f.endswith(".json")]

def respond_stream(
    message: str,
    history: List[Dict],
    model_choice: str,
    system_prompt: str
) -> Generator[List[Dict], None, None]:
    """流式响应生成器，history 为字典列表，直接更新并返回"""
    if not message.strip():
        yield history
        return

    # 1. 添加用户消息
    history.append({"role": "user", "content": message})
    yield history

    # 2. 添加一个空的 assistant 消息占位，后续逐步填充
    history.append({"role": "assistant", "content": ""})
    yield history

    # 3. 调用流式 API，逐块更新最后一条 assistant 消息
    full_response = ""
    # 传入的 history 是当前（包含刚添加的用户消息，但不包含 assistant 占位）
    # 因为占位消息刚添加，API 调用时不应包含它，所以传入 history[:-1]
    for chunk in call_llm_api_stream(message, model_choice, history[:-2], system_prompt):
        full_response += chunk
        history[-1]["content"] = full_response  # 更新最后一条消息的内容
        yield history

# ==================== 构建界面 ====================
custom_css = """
body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.gradio-container h1 {
    color: white;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    text-align: center;
    font-size: 2.5em;
    margin-bottom: 0.5em;
}
.chatbot-container {
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    background: rgba(255,255,255,0.95);
    height: 500px;
}
.input-box textarea {
    border-radius: 25px;
    border: 2px solid #e0e0e0;
    padding: 15px 20px;
    font-size: 16px;
    transition: all 0.3s;
    resize: none;
}
.input-box textarea:focus {
    border-color: #667eea;
    box-shadow: 0 0 10px rgba(102,126,234,0.3);
    outline: none;
}
button {
    border-radius: 25px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
}
.primary-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    box-shadow: 0 4px 15px rgba(102,126,234,0.4);
}
.primary-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(102,126,234,0.6);
}
.secondary-button {
    background: white;
    color: #667eea;
    border: 2px solid #667eea;
}
.secondary-button:hover {
    background: #667eea;
    color: white;
}
.welcome-text {
    text-align: center;
    color: white;
    font-size: 1.2em;
    margin-bottom: 20px;
    opacity: 0.9;
}
"""

def create_demo():
    with gr.Blocks(css=custom_css, title="小浩智能聊天机器人") as demo:
        gr.HTML("<h1>🤖 小浩智能聊天机器人</h1>")
        gr.HTML('<div class="welcome-text">👋 你好！我是小浩，支持GLM-5和DeepSeek-V3.2，可以自由切换模型和角色设定！</div>')

        with gr.Row():
            # 左侧控制面板
            with gr.Column(scale=1, min_width=280):
                gr.Markdown("### ⚙️ 模型与角色")
                model_choice = gr.Dropdown(
                    choices=list(MODELS.keys()),
                    value="GLM-5",
                    label="选择模型",
                    info="GLM-5：通用对话；DeepSeek-V3.2：推理能力强"
                )
                system_prompt = gr.Textbox(
                    label="角色设定",
                    value=DEFAULT_SYSTEM_PROMPT,
                    lines=3,
                    placeholder="输入你希望机器人扮演的角色..."
                )

                gr.Markdown("### 📁 历史记录")
                history_files = gr.Dropdown(
                    choices=get_saved_history_list(),
                    label="选择历史文件",
                    interactive=True
                )
                with gr.Row():
                    save_btn = gr.Button("💾 保存当前对话", variant="secondary", elem_classes="secondary-button")
                    load_btn = gr.Button("📂 加载选中历史", variant="secondary", elem_classes="secondary-button")
                    refresh_btn = gr.Button("🔄 刷新列表", variant="secondary", elem_classes="secondary-button")
                save_status = gr.Textbox(label="状态", interactive=False, visible=False)

                gr.Markdown("### 💡 示例问题")
                example_questions = [
                    "你好，介绍一下自己吧",
                    "今天天气怎么样？",
                    "讲个笑话",
                    "怎么学Python？",
                    "什么是人工智能",
                    "推荐一本好书"
                ]
                example_btns = []
                for q in example_questions:
                    btn = gr.Button(q, elem_classes="example-btn")
                    example_btns.append((btn, q))

            # 右侧聊天区域
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="对话历史",
                    height=450,
                    elem_classes="chatbot-container"
                )
                with gr.Row():
                    msg_box = gr.Textbox(
                        show_label=False,
                        placeholder="输入你的问题... (按Enter发送)",
                        container=False,
                        scale=8,
                        elem_classes="input-box"
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=1, min_width=100, elem_classes="primary-button")
                with gr.Row():
                    clear_btn = gr.Button("🗑️ 清空对话", variant="secondary", scale=1, elem_classes="secondary-button")

        # ==================== 事件绑定 ====================
        # 示例问题：点击将文本填入输入框
        for btn, q in example_btns:
            btn.click(
                lambda text=q: text,
                inputs=[],
                outputs=[msg_box]
            )

        # 发送消息（流式）
        def send_message(message, history, model, system):
            if not message.strip():
                yield history
                return
            yield from respond_stream(message, history, model, system)

        send_btn.click(
            send_message,
            inputs=[msg_box, chatbot, model_choice, system_prompt],
            outputs=[chatbot]
        ).then(
            lambda: "",  # 清空输入框
            inputs=None,
            outputs=[msg_box]
        )

        msg_box.submit(
            send_message,
            inputs=[msg_box, chatbot, model_choice, system_prompt],
            outputs=[chatbot]
        ).then(
            lambda: "",
            inputs=None,
            outputs=[msg_box]
        )

        # 清空对话
        clear_btn.click(
            lambda: [],
            outputs=[chatbot]
        )

        # 保存对话
        def save_history(history):
            if not history:
                return "没有对话可保存"
            filepath = save_chat_history(history)
            return f"已保存到 {filepath}"

        save_btn.click(
            save_history,
            inputs=[chatbot],
            outputs=[save_status]
        ).then(
            lambda: gr.Dropdown(choices=get_saved_history_list()),
            inputs=None,
            outputs=[history_files]
        )

        # 加载历史
        def load_history(filename):
            if not filename:
                return []
            filepath = os.path.join(HISTORY_DIR, filename)
            return load_chat_history(filepath)

        load_btn.click(
            load_history,
            inputs=[history_files],
            outputs=[chatbot]
        )

        # 刷新历史文件列表
        refresh_btn.click(
            lambda: gr.Dropdown(choices=get_saved_history_list()),
            inputs=None,
            outputs=[history_files]
        )

    return demo

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    print("=" * 50)
    print("小浩智能聊天机器人 - 最终版启动中...")
    print(f"支持的模型: {', '.join(MODELS.keys())}")
    print(f"最大回复长度: {MAX_TOKENS if MAX_TOKENS else '默认'}")
    print("=" * 50)
    demo = create_demo()
    demo.launch(
        share=True,          # 如需公网分享设为 True
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )