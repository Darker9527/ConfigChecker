# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QFileDialog, QTabWidget, QComboBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QSpinBox
)
from sqlmodel import Session, select

from .db import DEFAULT_DB, init_db, get_config, set_config
from .models import Baseline, CheckTask
from .cli import run_check
from .identify import identify_file


class CheckPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.file = QLineEdit()
        btn = QPushButton('选择配置文件')
        btn.clicked.connect(self.pick_file)
        row.addWidget(self.file)
        row.addWidget(btn)
        layout.addLayout(row)

        row = QHBoxLayout()
        self.devtype = QLineEdit('交换机')
        self.brand = QLineEdit('华为')
        self.name = QLineEdit('gui-task')
        self.mode = QComboBox(); self.mode.addItems(['rule', 'hybrid', 'ai'])
        self.format = QLineEdit('html,csv,xlsx,docx,pdf,xml,remediation-xlsx')
        row.addWidget(QLabel('类型')); row.addWidget(self.devtype)
        row.addWidget(QLabel('品牌')); row.addWidget(self.brand)
        row.addWidget(QLabel('任务')); row.addWidget(self.name)
        row.addWidget(QLabel('模式')); row.addWidget(self.mode)
        layout.addLayout(row)
        layout.addWidget(QLabel('报告格式')); layout.addWidget(self.format)

        row = QHBoxLayout()
        auto = QPushButton('自动识别')
        auto.clicked.connect(self.auto_identify)
        run = QPushButton('开始检查')
        run.clicked.connect(self.run_check)
        row.addWidget(auto); row.addWidget(run)
        layout.addLayout(row)
        self.output = QTextEdit(); layout.addWidget(self.output)

    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择配置文件')
        if path: self.file.setText(path)

    def auto_identify(self):
        if not self.file.text(): return
        dev, br, scores = identify_file(self.file.text())
        self.devtype.setText(dev); self.brand.setText(br)
        self.output.append(f'自动识别：{dev}/{br} {scores}')

    def run_check(self):
        try:
            eng = init_db(DEFAULT_DB)
            with Session(eng) as session:
                _, results, reports = run_check(session, Path(self.file.text()), self.devtype.text(), self.brand.text(), self.name.text(), self.mode.currentText(), self.format.text())
            self.output.append(f'完成：{len(results)} 项')
            for r in reports: self.output.append(str(r))
        except Exception as e:
            QMessageBox.critical(self, '错误', repr(e))


class BaselinePage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        btn = QPushButton('刷新基线')
        btn.clicked.connect(self.load)
        layout.addWidget(btn)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['ID', '类型', '品牌', '名称', '风险'])
        layout.addWidget(self.table)
        self.load()

    def load(self):
        eng = init_db(DEFAULT_DB)
        with Session(eng) as session:
            rows = session.exec(select(Baseline).order_by(Baseline.id.desc()).limit(500)).all()
        self.table.setRowCount(len(rows))
        for i, b in enumerate(rows):
            for j, v in enumerate([b.id, b.devtype, b.brand, b.name, b.risk]):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))


class TaskPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        btn = QPushButton('刷新任务')
        btn.clicked.connect(self.load)
        layout.addWidget(btn)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['ID', '时间', '任务', '类型/品牌', '报告'])
        layout.addWidget(self.table)
        self.load()

    def load(self):
        eng = init_db(DEFAULT_DB)
        with Session(eng) as session:
            rows = session.exec(select(CheckTask).order_by(CheckTask.id.desc()).limit(200)).all()
        self.table.setRowCount(len(rows))
        for i, t in enumerate(rows):
            vals = [t.id, t.created_at, t.name, f'{t.devtype}/{t.brand}', t.report_path or '']
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.out_path = QLineEdit()
        self.ai_url = QLineEdit()
        self.ai_model = QLineEdit()
        self.ai_key = QLineEdit()
        self.ai_workers = QSpinBox(); self.ai_workers.setRange(1, 32)
        for label, widget in [('输出目录', self.out_path), ('AI Base URL', self.ai_url), ('AI Model', self.ai_model), ('AI Key', self.ai_key), ('AI并发', self.ai_workers)]:
            layout.addWidget(QLabel(label)); layout.addWidget(widget)
        btn = QPushButton('保存设置'); btn.clicked.connect(self.save)
        layout.addWidget(btn)
        self.load()

    def load(self):
        eng = init_db(DEFAULT_DB)
        with Session(eng) as s:
            self.out_path.setText(get_config(s, 'out_path'))
            self.ai_url.setText(get_config(s, 'ai_base_url'))
            self.ai_model.setText(get_config(s, 'ai_model'))
            self.ai_key.setText(get_config(s, 'ai_api_key'))
            self.ai_workers.setValue(int(get_config(s, 'ai_workers', '1') or '1'))

    def save(self):
        eng = init_db(DEFAULT_DB)
        with Session(eng) as s:
            set_config(s, 'out_path', self.out_path.text())
            set_config(s, 'ai_base_url', self.ai_url.text())
            set_config(s, 'ai_model', self.ai_model.text())
            set_config(s, 'ai_api_key', self.ai_key.text())
            set_config(s, 'ai_workers', str(self.ai_workers.value()))
            s.commit()
        QMessageBox.information(self, '完成', '设置已保存')


class MainWindow(QTabWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ConfigChecker Rebuild')
        self.resize(1100, 760)
        self.addTab(CheckPage(), '配置检查')
        self.addTab(BaselinePage(), '基线库')
        self.addTab(TaskPage(), '任务历史')
        self.addTab(SettingsPage(), '设置')


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
