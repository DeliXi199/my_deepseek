import paramiko

# 配置连接信息
hostname = "159.226.208.68"  # 服务器的 IP 地址
port = 61288  # 自定义端口
username = "yihaoxu"  # 用户名
password = "3477630483ZZYe"  # SSH 密码，如果需要的话

# 创建 SSH 客户端对象
ssh = paramiko.SSHClient()

# 自动加载本地的 SSH 公钥文件
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    # 连接到现有节点（主节点）
    ssh.connect(hostname, port=port, username=username, password=password)
    print("SSH connection established!")

    # 获取 Transport 对象
    transport = ssh.get_transport()

    # 本地端口
    local_port = 8888
    # 目标节点的 IP 地址和端口
    remote_host = "172.16.8.24"
    remote_port = 11434

    # 设置端口转发
    # 通过 'open_channel' 来转发本地端口到远程节点的指定端口
    local_channel = transport.open_channel(
        "direct-tcpip",  # 使用 direct-tcpip 类型来进行端口转发
        (remote_host, remote_port),  # 目标远程节点的 IP 和端口
        ("localhost", local_port),  # 本地端口，通常设为 localhost 和本地端口
    )

    print(
        f"Port forwarding established on localhost:{local_port} to {remote_host}:{remote_port}"
    )

    # 保持连接活跃，直到手动停止程序
    input("Press Enter to stop port forwarding and close the connection...")

finally:
    # 关闭 SSH 连接
    ssh.close()
    print("SSH connection closed.")
