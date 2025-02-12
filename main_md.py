import json
import requests
from sshtunnel import SSHTunnelForwarder
from openai import OpenAI


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


def stream_chat_completion(client, messages):
    """流式获取聊天补全的回复，并将内容写入md文件"""
    response = requests.post(
        f"http://localhost:{local_port}/v1/chat/completions",
        json={"messages": messages, "model": "deepseek-r1:70b", "stream": True},
        stream=True,
    )
    is_think = True
    think_content = ""  # 用来积累 think 部分的内容
    normal_content = ""  # 用来积累正常回复部分的内容

    # 打开文件进行写入
    with open("output.md", "a", encoding="utf-8") as file:
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    decoded_line = decoded_line[6:]
                    if decoded_line == "[DONE]":
                        print(f"{normal_content}\n")
                        file.write(f"{normal_content}\n\n")  # 结束对话，插入一个空行
                        break
                    try:
                        data = json.loads(decoded_line)
                        content = data["choices"][0]["delta"].get("content", "")

                        # 处理 <think> 和 </think> 的部分
                        if "<think>" in content:
                            is_think = True
                            think_content += content.replace(
                                "<think>",
                                "<details>\n<summary>**Thinking...**</summary>",
                            )  # 开始积累 think 部分内容
                            print(f"{think_content}")  # 打印积累的 think 部分内容
                            file.write(f"{think_content}")  # 写入文件，
                            think_content = ""  # 清空积累 think 部分的内容
                        if is_think:
                            if "\n" in content:
                                None  # 忽略换行
                            else:
                                think_content += content  # 继续积累 think 部分的内容
                        else:
                            if "\n" in content:
                                None  # 忽略换行
                            else:
                                normal_content += content  # 继续积累正常回复部分的内容
                        if "</think>" in content:
                            is_think = False
                            think_content += content.replace(
                                "</think>", "</details>"
                            )  # 结束积累 think 部分内容，插入 HTML 标签
                            print(f"{think_content}")  # 打印积累的 think 部分内容
                            file.write(f"{think_content}")  # 写入文件，
                            think_content = ""  # 清空积累 think 部分的内容
                        if "\n" in content and is_think:
                            print(f"{think_content}")  # 打印积累的 think 部分内容
                            file.write(f"{think_content}")  # 写入文件
                            think_content = ""  # 清空积累 think 部分的内容
                        if "\n" in content and not is_think:
                            print(f"{normal_content}")
                            file.write(f"{normal_content}")  # 结束对话，插入一个空行
                            normal_content = ""  # 清空积累正常回复部分的内容

                    except json.JSONDecodeError:
                        continue
        file.write("\n\n")  # 在每次聊天后插入一个空行

    print("\n")  # 确保换行清晰


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
            stream_chat_completion(client, messages)
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
