from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from .config import AppConfig, ConfigManager


class SetupDialog(QDialog):
    def __init__(self, config: AppConfig, config_manager: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("セットアップ")
        self.resize(640, 520)
        self._config_manager = config_manager
        self._config = config

        self._steps = QListWidget()
        self._steps.addItems([
            "1. 保存先",
            "2. 入力ファイル",
            "3. API キー",
            "4. 声の割り当てプレビュー",
        ])
        self._steps.setCurrentRow(0)
        self._steps.currentRowChanged.connect(self._on_step_changed)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_output_page())
        self._stack.addWidget(self._build_files_page())
        self._stack.addWidget(self._build_keys_page())
        self._stack.addWidget(self._build_roles_page())

        self._next_button = QPushButton("次へ")
        self._next_button.clicked.connect(self._next)
        self._back_button = QPushButton("戻る")
        self._back_button.clicked.connect(self._back)
        self._finish_button = QPushButton("完了")
        self._finish_button.clicked.connect(self._finish)

        buttons = QHBoxLayout()
        buttons.addWidget(self._back_button)
        buttons.addWidget(self._next_button)
        buttons.addStretch(1)
        buttons.addWidget(self._finish_button)

        layout = QHBoxLayout()
        layout.addWidget(self._steps, 0)
        layout.addWidget(self._stack, 1)

        wrapper = QVBoxLayout(self)
        wrapper.addLayout(layout)
        wrapper.addLayout(buttons)

        self._update_buttons()

    # ------------------------------------------------------------------
    def _build_output_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)

        self._output_edit = QLineEdit(self._config.paths.output_dir or "")
        select_btn = QPushButton("フォルダを選択")
        select_btn.clicked.connect(self._choose_output)
        row = QHBoxLayout()
        row.addWidget(self._output_edit)
        row.addWidget(select_btn)
        layout.addRow("保存先フォルダ", row)

        self._fake_tts_checkbox = QCheckBox("ナレーション生成をスキップ（静音ファイル）")
        self._fake_tts_checkbox.setChecked(self._config.fake_tts)
        layout.addRow("", self._fake_tts_checkbox)
        return page

    def _build_files_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        def file_row(edit: QLineEdit, caption: str, mode: str = "file", filter_: str = "*"):
            button = QPushButton("選択")
            def choose():
                if mode == "directory":
                    path = QFileDialog.getExistingDirectory(self, caption)
                else:
                    path, _ = QFileDialog.getOpenFileName(self, caption, filter=filter_)
                if path:
                    edit.setText(path)
            button.clicked.connect(choose)
            row = QHBoxLayout()
            row.addWidget(edit)
            row.addWidget(button)
            return row

        self._script_edit = QLineEdit(self._config.paths.script or "")
        form.addRow("台本 (必須)", file_row(self._script_edit, "台本ファイルを選択", filter_="Text (*.txt *.md *.json);;All (*)"))

        self._srt_edit = QLineEdit(self._config.paths.subtitle_srt or "")
        form.addRow("字幕 SRT", file_row(self._srt_edit, "SRT を選択", filter_="SubRip (*.srt);;All (*)"))

        self._scene_edit = QLineEdit(self._config.paths.scene_plan or "")
        form.addRow("シーン構成 (Markdown)", file_row(self._scene_edit, "Markdown を選択", filter_="Markdown (*.md);;All (*)"))

        self._bgm_edit = QLineEdit(self._config.paths.bgm_plan or "")
        form.addRow("BGM/SE プラン JSON", file_row(self._bgm_edit, "BGM プランを選択", filter_="JSON (*.json);;All (*)"))
        return page

    def _build_keys_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self._azure_key_edit = QLineEdit()
        azure_key = self._config_manager.get_azure_key()
        if azure_key:
            self._azure_key_edit.setPlaceholderText("***保存済み***")
        form.addRow("Azure Speech APIキー", self._azure_key_edit)

        self._eleven_key_edit = QLineEdit()
        eleven_key = self._config_manager.get_eleven_labs_key()
        if eleven_key:
            self._eleven_key_edit.setPlaceholderText("***保存済み***")
        form.addRow("ElevenLabs APIキー", self._eleven_key_edit)
        return page

    def _build_roles_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel("声の割り当てプレビュー (台本/セリフ CSVから抽出予定)")
        label.setWordWrap(True)
        self._roles_preview = QTextEdit()
        self._roles_preview.setReadOnly(True)
        self._roles_preview.setPlainText("役割プレビューは v0.1 ではスタブ表示です。")
        layout.addWidget(label)
        layout.addWidget(self._roles_preview)
        return page

    # ------------------------------------------------------------------
    def _choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "保存先フォルダ")
        if path:
            self._output_edit.setText(path)

    def _on_step_changed(self, row: int) -> None:
        self._stack.setCurrentIndex(row)
        self._update_buttons()

    def _update_buttons(self) -> None:
        index = self._stack.currentIndex()
        self._back_button.setEnabled(index > 0)
        self._next_button.setEnabled(index < self._stack.count() - 1)
        self._finish_button.setEnabled(index == self._stack.count() - 1)

    def _next(self) -> None:
        index = self._stack.currentIndex()
        if index < self._stack.count() - 1:
            self._steps.setCurrentRow(index + 1)

    def _back(self) -> None:
        index = self._stack.currentIndex()
        if index > 0:
            self._steps.setCurrentRow(index - 1)

    def _finish(self) -> None:
        if not self._validate():
            return
        paths = self._config.paths
        paths.output_dir = self._output_edit.text().strip() or None
        paths.script = self._script_edit.text().strip() or None
        paths.subtitle_srt = self._srt_edit.text().strip() or None
        paths.scene_plan = self._scene_edit.text().strip() or None
        paths.bgm_plan = self._bgm_edit.text().strip() or None
        self._config.paths = paths
        self._config.fake_tts = self._fake_tts_checkbox.isChecked()
        self._config_manager.save(self._config)

        if key := self._azure_key_edit.text().strip():
            self._config_manager.set_azure_key(key)
        if key := self._eleven_key_edit.text().strip():
            self._config_manager.set_eleven_labs_key(key)
        self.accept()

    def _validate(self) -> bool:
        output_dir = self._output_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "入力エラー", "保存先フォルダを指定してください。")
            return False
        script_path = self._script_edit.text().strip()
        if not script_path:
            QMessageBox.warning(self, "入力エラー", "台本ファイルを指定してください。")
            return False
        return True
