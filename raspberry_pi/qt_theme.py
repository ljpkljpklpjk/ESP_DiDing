from PySide6.QtCore import Qt


LIGHT_THEME = """
QMainWindow, QWidget {
    background: #f3f6fb;
    color: #0f172a;
    font-family: "Microsoft YaHei", "Noto Sans CJK SC", "Arial";
    font-size: 15px;
}
QTabWidget::pane {
    border: 0;
    background: #f3f6fb;
}
QTabBar::tab {
    background: #e5edf7;
    color: #334155;
    padding: 13px 26px;
    margin-right: 8px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    font-size: 17px;
    font-weight: 700;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0f4ea3;
}
QLabel#titleLabel {
    color: #0f172a;
    font-size: 26px;
    font-weight: 800;
}
QLabel#sectionTitle {
    color: #0f172a;
    font-size: 18px;
    font-weight: 800;
}
QLabel#cardTitle {
    color: #64748b;
    font-size: 14px;
    font-weight: 700;
}
QLabel#cardValue {
    color: #0f172a;
    font-size: 28px;
    font-weight: 900;
}
QFrame#card, QFrame#panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
}
QFrame#topBar {
    background: #ffffff;
    border: 1px solid #dbe7f5;
    border-radius: 20px;
}
QLineEdit {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 10px 12px;
    min-height: 26px;
    selection-background-color: #2563eb;
}
QLineEdit:focus {
    border: 2px solid #2563eb;
}
QPushButton {
    background: #e8eef8;
    color: #0f172a;
    border: 0;
    border-radius: 13px;
    padding: 12px 16px;
    min-height: 26px;
    font-weight: 700;
}
QPushButton:hover {
    background: #dbeafe;
}
QPushButton:pressed {
    background: #bfdbfe;
}
QPushButton:disabled {
    background: #e5e7eb;
    color: #94a3b8;
}
QPushButton#primaryButton {
    background: #2563eb;
    color: #ffffff;
}
QPushButton#primaryButton:hover {
    background: #1d4ed8;
}
QPushButton#dangerButton {
    background: #dc2626;
    color: #ffffff;
    font-size: 18px;
    min-height: 38px;
}
QPushButton#dangerButton:hover {
    background: #b91c1c;
}
QTextEdit {
    background: #0f172a;
    color: #dbeafe;
    border: 0;
    border-radius: 16px;
    padding: 12px;
    font-family: "Consolas", "Courier New";
    font-size: 13px;
}
QProgressBar {
    background: #e2e8f0;
    border: 0;
    border-radius: 9px;
    min-height: 18px;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 9px;
}
"""


def apply_theme(app):
    app.setStyleSheet(LIGHT_THEME)
    app.setLayoutDirection(Qt.LeftToRight)
