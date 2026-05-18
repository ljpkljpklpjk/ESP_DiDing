from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget


def make_panel(title=None):
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(18, 16, 18, 18)
    layout.setSpacing(12)
    if title:
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
    return panel, layout


class ValueCard(QFrame):
    def __init__(self, title, value="--", accent=None):
        super().__init__()
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        self.value_label.setWordWrap(True)
        if accent:
            self.value_label.setStyleSheet(f"color: {accent};")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


def add_cards_grid(parent_layout, cards, columns=4):
    grid = QGridLayout()
    grid.setSpacing(12)
    for index, card in enumerate(cards):
        grid.addWidget(card, index // columns, index % columns)
    parent_layout.addLayout(grid)
    return grid


def input_row(label, line_edit, button_text=None, callback=None, primary=False):
    row = QHBoxLayout()
    row.setSpacing(10)
    text = QLabel(label)
    text.setMinimumWidth(105)
    row.addWidget(text)
    row.addWidget(line_edit, 1)
    button = None
    if button_text:
        button = QPushButton(button_text)
        if primary:
            button.setObjectName("primaryButton")
        if callback:
            button.clicked.connect(callback)
        row.addWidget(button)
    return row, button


def make_line_edit(value="", password=False):
    edit = QLineEdit(str(value))
    if password:
        edit.setEchoMode(QLineEdit.Password)
    return edit


def make_button(text, callback=None, primary=False, danger=False):
    button = QPushButton(text)
    if primary:
        button.setObjectName("primaryButton")
    if danger:
        button.setObjectName("dangerButton")
    if callback:
        button.clicked.connect(callback)
    return button


def make_log():
    log = QTextEdit()
    log.setReadOnly(True)
    log.setMinimumHeight(150)
    return log


def append_log(log, text, max_lines=500):
    log.append(str(text))
    document = log.document()
    extra = document.blockCount() - max_lines
    if extra > 0:
        cursor = log.textCursor()
        cursor.movePosition(cursor.Start)
        for _ in range(extra):
            cursor.select(cursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
    log.verticalScrollBar().setValue(log.verticalScrollBar().maximum())


def page_widget():
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(14)
    return page, layout
