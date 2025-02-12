import json
import requests  # 使用 requests 库来进行 HTTP 请求


def custom_converter(o):
    """处理非 JSON 可序列化对象"""
    if hasattr(o, "to_dict"):
        return o.to_dict()
    return str(o)


def pretty_print(title, data):
    """格式化打印函数"""
    print(f"\n{'='*10} {title} {'='*10}")
    try:
        print(json.dumps(data, indent=4, ensure_ascii=False, default=custom_converter))
    except Exception as e:
        print("转换为 JSON 出现错误，直接打印：", e)
        print(data)
    print(f"{'='*30}\n")


def main():
    # 本地转发的地址和端口
    base_url = "http://localhost:8888/v1/"  # 通过本地转发访问模型
    api_key = "ollama"  # 必传参数，但实际可能被忽略

    # 创建请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    # 1. 第一个问题：简单的聊天补全
    # 问题：Say this is a test
    chat_payload = {
        "messages": [{"role": "user", "content": "Say this is a test"}],
        "model": "deepseek-r1:70b",
    }
    chat_response = requests.post(
        f"{base_url}chat/completions", json=chat_payload, headers=headers
    )
    chat_completion = chat_response.json()
    pretty_print("Chat Completion 输出 (问题1)", chat_completion)
    print("回答：第一个问题已完成。")

    # 3. 第三个问题：普通文本补全
    # 问题：Say this is a test
    text_payload = {
        "prompt": "Say this is a test",
        "model": "deepseek-r1:70b",
    }
    text_response = requests.post(
        f"{base_url}completions", json=text_payload, headers=headers
    )
    completion = text_response.json()
    pretty_print("Text Completion 输出 (问题3)", completion)
    print("回答：第三个问题已完成。")

    # 4. 第四个问题：列出所有模型
    models_response = requests.get(f"{base_url}models", headers=headers)
    list_models = models_response.json()
    pretty_print("List Models 输出 (问题4)", list_models)
    print("回答：第四个问题已完成。")

    # 5. 第五个问题：检索指定模型的信息
    model_info_response = requests.get(
        f"{base_url}models/deepseek-r1:70b", headers=headers
    )
    model_info = model_info_response.json()
    pretty_print("Retrieve Model 输出 (问题5)", model_info)
    print("回答：第五个问题已完成。")


if __name__ == "__main__":
    main()
