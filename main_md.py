import json
import requests
from sshtunnel import SSHTunnelForwarder
from openai import OpenAI
from datetime import datetime
import os
import sys


# 读取配置文件并解析
def read_config(file_path):
    config = {}
    with open(file_path, "r") as file:
        for line in file:
            # 只处理非空行和非注释行
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


# 使用配置文件
config = read_config("config.txt")

# 获取配置信息
hostname = config.get("hostname")
port = int(config.get("port", 22))  # 默认端口为22
username = config.get("username")
password = config.get("password")
local_port = int(config.get("local_port", 8888))
remote_host = config.get("remote_host")
remote_port = int(config.get("remote_port", 11434))
model = config.get("model")

# 获取当前时间并生成文件名
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_name = f".\\answers\chat_{current_time}.md"


def custom_converter(o):
    """当遇到非 JSON 可序列化对象时，先尝试调用其 to_dict 方法，否则直接将其转换为字符串返回"""
    if hasattr(o, "to_dict"):
        return o.to_dict()
    return str(o)


def pretty_print(title, data):
    """格式化打印函数，使用 custom_converter 处理非序列化对象"""
    print(f"\n{'='*10} {title} {'='*10}")
    try:
        # 尝试将 data 序列化为 JSON 格式
        print(json.dumps(data, indent=4, ensure_ascii=False, default=custom_converter))
    except Exception as e:
        print("转换为 JSON 出现错误，直接打印：", e)
        print(data)
    print(f"{'='*30}\n")


def get_user_input():
    """从终端获取用户输入的问题"""
    user_input = input("请输入您的问题 (按 Enter 键退出): ")
    return user_input if user_input != "" else None


import time  # 引入time模块


def stream_chat_completion(client, messages, user_input):
    """流式获取聊天补全的回复，并将内容写入md文件"""
    response = requests.post(
        f"http://localhost:{local_port}/v1/chat/completions",
        json={"messages": messages, "model": model, "stream": True},
        stream=True,
    )
    # 打开文件进行写入（追加内容）
    with open(file_name, "a", encoding="utf-8") as file:  # 使用 'a' 模式追加内容
        file.write(f"## **DeliXi:** \n")
        file.write(f"{user_input}\n")
        file.write("## **DeepSeek:** \n")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    decoded_line = decoded_line[6:]
                    if decoded_line == "[DONE]":
                        print(f"\n")
                        file.write(f"\n\n")  # 结束对话，插入一个空行
                        sys.stdout.flush()  # 强制刷新标准输出缓冲区
                        file.flush()  # 刷新文件缓冲区，确保写入到磁盘
                        file.seek(0, os.SEEK_END)  # 确保将文件指针移动到末尾
                        os.fsync(file.fileno())  # 确保文件系统也同步
                        break
                    try:
                        data = json.loads(decoded_line)
                        content = data["choices"][0]["delta"].get("content", "")

                        # 处理 <think> 和 </think> 的部分
                        if "<think>" in content:
                            content = content.replace(
                                "<think>", "**Thinking...**\n"
                            )  # 开始积累 think 部分内容
                            print(f"{content}", end="")  # 打印积累的 think 部分内容
                            file.write(f"{content}")  # 写入文件
                            sys.stdout.flush()  # 强制刷新标准输出缓冲区
                            file.flush()  # 刷新文件缓冲区，确保写入到磁盘
                            file.seek(0, os.SEEK_END)  # 确保将文件指针移动到末尾
                            os.fsync(file.fileno())  # 确保文件系统也同步
                        elif "</think>" in content:
                            content = content.replace(
                                "</think>", "\n**End of thinking**\n\n---\n"
                            )
                            print(f"{content}", end="")  # 打印积累的 think 部分内容
                            file.write(f"{content}")  # 写入文件
                            sys.stdout.flush()  # 强制刷新标准输出缓冲区
                            file.flush()  # 刷新文件缓冲区，确保写入到磁盘
                            file.seek(0, os.SEEK_END)  # 确保将文件指针移动到末尾
                            os.fsync(file.fileno())  # 确保文件系统也同步
                        else:
                            print(f"{content}", end="")  # 打印正常回复部分的内容
                            file.write(f"{content}")  # 写入文件
                            sys.stdout.flush()  # 强制刷新标准输出缓冲区
                            file.flush()  # 刷新文件缓冲区，确保写入到磁盘
                            file.seek(0, os.SEEK_END)  # 确保将文件指针移动到末尾
                            os.fsync(file.fileno())  # 确保文件系统也同步

                    except json.JSONDecodeError:
                        continue
        file.write("\n\n")  # 在每次聊天后插入一个空行

    print("\n")  # 确保换行清晰


def main():
    with open(file_name, "w", encoding="utf-8") as file:  # 使用 'w' 模式覆盖文件
        file.write(f"# DeepSeek Qustion-Answering System\n")  # 写入文件

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
                return  # 如果无法访问，提前退出程序
        except Exception as e:
            print(f"Error accessing DeepSeek API via port forwarding: {e}")
            return  # 如果发生连接错误，提前退出程序

        # 连接到OpenAI客户端实例
        client = OpenAI(
            base_url=f"http://localhost:{local_port}/v1/",  # 使用本地端口作为代理
            api_key="ollama",  # 必传参数
        )

        messages = []

        while True:
            # 获取用户输入的问题
            user_input = get_user_input()
            if user_input is None:
                break

            # 添加用户输入到消息列表中
            messages.append({"role": "user", "content": user_input})

            # 发送聊天补全请求
            print(f"Thinking...\n{'='*10} DeepSeek 回复 {'='*10}\n")
            stream_chat_completion(client, messages, user_input)
            print(f"{'='*30}\n")

            # 添加DeepSeek的回复到消息列表中（已经在stream_chat_completion中处理）
            # messages.append({"role": "assistant", "content": assistant_reply})

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # 关闭SSH连接
        server.stop()
        print("SSH connection closed.")


if __name__ == "__main__":
    main()
