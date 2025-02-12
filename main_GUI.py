import json
import requests
from sshtunnel import SSHTunnelForwarder
from openai import OpenAI
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
)
from PyQt5.QtGui import QFont, QColor, QTextCharFormat
from PyQt5.QtCore import Qt, pyqtSignal, QThread
import threading


# 读取配置文件并解析
def read_config(file_path):
    config = {}
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


# 使用配置文件
config = read_config("config.txt")

# 获取配置信息
hostname = config.get("hostname")
port = int(config.get("port", 22))
username = config.get("username")
password = config.get("password")
local_port = int(config.get("local_port", 8888))
remote_host = config.get("remote_host")
remote_port = int(config.get("remote_port", 11434))


def custom_converter(o):
    if hasattr(o, "to_dict"):
        return o.to_dict()
    return str(o)


def pretty_print(title, data):
    print(f"\n{'='*10} {title} {'='*10}")
    try:
        print(json.dumps(data, indent=4, ensure_ascii=False, default=custom_converter))
    except Exception as e:
        print("Error converting to JSON:", e)
        print(data)
    print(f"{'='*30}\n")


class DeepSeekChat(QMainWindow):
    update_signal = pyqtSignal(str)  # 定义一个信号传递字符串

    def __init__(self):
        super().__init__()
        self.initUI()
        self.messages = []
        self.update_signal.connect(self.append_to_text_widget)  # 连接信号到槽
        self.content_accumulator = ""  # 初始化一个空字符串用于累积内容

    def initUI(self):
        self.setWindowTitle("DeepSeek Chat")
        self.setGeometry(100, 100, 1400, 1000)

        # 创建主窗口部件
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        # 创建垂直布局
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # 创建输出区域
        self.text_widget = QTextEdit(self)
        self.text_widget.setReadOnly(True)
        self.text_widget.setFont(QFont("Arial", 14))
        self.layout.addWidget(self.text_widget)

        # 定义不同角色的颜色
        self.user_char_format = QTextCharFormat()
        self.user_char_format.setForeground(QColor("blue"))
        self.deepseek_char_format = QTextCharFormat()
        self.deepseek_char_format.setForeground(QColor("green"))
        self.default_char_format = QTextCharFormat()
        self.default_char_format.setForeground(QColor("black"))

        # 创建输入区域
        self.input_frame = QWidget(self)
        self.input_layout = QHBoxLayout()
        self.input_frame.setLayout(self.input_layout)

        self.entry = QLineEdit(self)
        self.entry.setFont(QFont("Arial", 14))
        self.entry.returnPressed.connect(self.on_send)
        self.input_layout.addWidget(self.entry)

        self.send_button = QPushButton("发送", self)
        self.send_button.setFont(QFont("Arial", 14))
        self.send_button.clicked.connect(self.on_send)
        self.input_layout.addWidget(self.send_button)

        self.exit_button = QPushButton("退出", self)
        self.exit_button.setFont(QFont("Arial", 14))
        self.exit_button.clicked.connect(self.on_exit)
        self.input_layout.addWidget(self.exit_button)

        self.layout.addWidget(self.input_frame)

    def on_send(self):
        user_input = self.entry.text().strip()
        if not user_input:
            return

        self.messages.append({"role": "user", "content": user_input})

        # 显示用户输入的消息，并加上“我：”前缀
        self.text_widget.setCurrentCharFormat(self.user_char_format)
        self.text_widget.append(f"我: {user_input}\n")

        # 清空输入框
        self.entry.clear()

        # 立即显示 Deepseek 提示
        self.text_widget.setCurrentCharFormat(self.deepseek_char_format)
        self.text_widget.append("Deepseek:\n")
        self.text_widget.setCurrentCharFormat(self.default_char_format)

        # 发送聊天补全请求
        print(f"Thinking...\n{'='*10} DeepSeek 回复 {'='*10}\n")
        threading.Thread(
            target=self.stream_chat_completion,
            args=(client, self.messages),
        ).start()

    def on_exit(self):
        self.close()

    def stream_chat_completion(self, client, messages):
        """流式获取聊天补全的回复"""
        response = requests.post(
            f"http://localhost:{local_port}/v1/chat/completions",
            json={"messages": messages, "model": "deepseek-r1:70b", "stream": True},
            stream=True,
        )
        think_part = ""  # 用于存储 think 部分的内容
        normal_part = ""  # 用于存储正常回复内容
        is_think = True
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    decoded_line = decoded_line[6:]
                    if decoded_line == "[DONE]":
                        self.update_signal.emit(f"{normal_part}")  # 输出正常部分
                    try:
                        data = json.loads(decoded_line)
                        delta_content = data["choices"][0]["delta"].get("content", "")

                        # 如果是think部分，累积think内容

                        if "<think>" in delta_content:
                            is_think = True
                            # self.update_signal.emit(f"<think>")
                        if is_think:
                            if "\n" in delta_content:
                                None
                            else:
                                think_part += delta_content  # 累积 think 部分
                        else:
                            if "\n" in delta_content:
                                None
                            else:
                                normal_part += delta_content  # 累积正常回复部分
                        if "</think>" in delta_content:
                            is_think = False
                            self.update_signal.emit(
                                f"{think_part}"
                            )  # 输出带think标签的内容
                            # self.update_signal.emit(f"</think>")  # 输出think标签
                            think_part = ""  # 清空think部分

                        # 如果正常回复部分包含换行符，或者think部分结束了，就输出正常回复
                        if "\n" in delta_content and is_think:
                            self.update_signal.emit(
                                f"{think_part}"
                            )  # 输出带think标签的内容
                            think_part = ""  # 清空think部分
                        if "\n" in delta_content and not is_think:
                            self.update_signal.emit(f"{normal_part}")  # 输出正常部分
                            normal_part = ""  # 清空正常部分

                    except json.JSONDecodeError:
                        continue
        # print("\n")  # 打印换行符以确保格式正确

    def append_to_text_widget(self, content):
        """更新 QTextEdit 内容的方法，在主线程中执行"""
        self.text_widget.setCurrentCharFormat(self.default_char_format)

        # 将新的内容追加到已有内容后
        self.text_widget.append(content)
        self.text_widget.ensureCursorVisible()


def main():
    # 设置SSH隧道转发
    server = SSHTunnelForwarder(
        (hostname, port),
        ssh_username=username,
        ssh_password=password,
        remote_bind_address=(remote_host, remote_port),
        local_bind_address=("localhost", local_port),
    )

    try:
        # 连接到SSH服务器并启动隧道
        server.start()
        print("SSH connection established!")

        # 检查端口转发是否正常工作
        try:
            print(
                f"Checking port forwarding by accessing localhost:{local_port}/v1/models"
            )
            response = requests.get(f"http://localhost:{local_port}/v1/models")
            if response.status_code == 200:
                print("Port forwarding is working, and DeepSeek API is accessible.")
            else:
                print(
                    f"Failed to access DeepSeek API via port forwarding, Status code: {response.status_code}"
                )
                return
        except Exception as e:
            print(f"Error accessing DeepSeek API via port forwarding: {e}")
            return

        # 连接到OpenAI客户端实例
        global client
        client = OpenAI(
            base_url=f"http://localhost:{local_port}/v1/",  # 使用本地端口作为代理
            api_key="ollama",  # 必传参数
        )

        app = QApplication([])
        chat = DeepSeekChat()
        chat.show()
        app.exec_()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 关闭SSH连接
        server.stop()
        print("SSH connection closed.")


if __name__ == "__main__":
    main()
