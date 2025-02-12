import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QPushButton,
    QFrame,
)


class CollapsibleWidget(QWidget):
    def __init__(self, title, content_widget):
        super().__init__()

        # 外层布局
        self.layout = QVBoxLayout(self)

        # 创建折叠按钮
        self.toggle_button = QPushButton(title, self)
        self.toggle_button.setCheckable(True)  # 设置按钮为可选状态

        # 创建内容区域
        self.content_widget = content_widget

        # 添加折叠按钮和内容区域
        self.layout.addWidget(self.toggle_button)
        self.layout.addWidget(self.content_widget)

        # 设置初始状态（折叠）
        self.content_widget.setVisible(False)

        # 连接按钮的点击信号
        self.toggle_button.toggled.connect(self.toggle_content)

    def toggle_content(self, checked):
        # 根据按钮的状态控制内容区域的显示与隐藏
        if checked:
            self.content_widget.setVisible(True)
        else:
            self.content_widget.setVisible(False)


class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        # 设置窗口标题和大小
        self.setWindowTitle("折叠功能示例")
        self.resize(400, 300)

        # 创建标签作为内容
        content_label = QLabel("这是折叠内容区域\n可以包含任意控件", self)
        content_label.setWordWrap(True)  # 使标签内容换行

        # 创建CollapsibleWidget，传入标题和内容区域
        collapsible = CollapsibleWidget("点击折叠/展开", content_label)

        # 设置布局
        layout = QVBoxLayout()
        layout.addWidget(collapsible)
        self.setLayout(layout)


# 主程序
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
