from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QToolBar,
    QWidget,
    QDialog,
)

from .config import AppConfig, ConfigManager
from .pipeline_runner import PipelineRunner
from .selfcheck import SelfCheck
from .setup_dialog import SetupDialog
from .widgets.log_viewer import LogViewer


@dataclass
class Step:
    id: str
    title: str


STEPS = [
    Step("narration", "Step 1/6: ナレーション生成"),
    Step("subtitles", "Step 2/6: 字幕/タイムライン"),
    Step("plan", "Step 3/6: BGM/SEプラン解析"),
    Step("bgm", "Step 4/6: BGM生成"),
    Step("se", "Step 5/6: SE生成"),
    Step("xml", "Step 6/6: XML書き出し"),
]


class SelfCheckThread(QThread):
    finished = Signal(object)

    def run(self):  # pragma: no cover - UI thread
        result = SelfCheck().run()
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DaVinciAuto GUI")
        self.resize(980, 720)

        self.config_manager = ConfigManager()
        self.config: AppConfig = self.config_manager.load()
        self.runner = PipelineRunner()
        self.runner.log_event.connect(self._on_log_event)
        self.runner.stderr.connect(self._on_stderr)
        self.runner.finished.connect(self._on_finished)

        self._build_ui()
        self._selfcheck_thread: Optional[SelfCheckThread] = None

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self._log_view = LogViewer()
        self._log_view.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        self._steps_list = QListWidget()
        for index, step in enumerate(STEPS):
            item = QListWidgetItem(step.title)
            self._steps_list.addItem(item)
            self._update_step_status(index, "未開始")

        self._badge_selfcheck = QLabel("Self-check: 未実行")
        self._badge_selfcheck.setStyleSheet("color: gray;")
        self._badge_azure = QLabel("Azure Key: 未登録")
        self._badge_eleven = QLabel("ElevenLabs Key: 未登録")
        self._update_key_badges()

        main_layout = QGridLayout()
        main_layout.addWidget(self._badge_selfcheck, 0, 0, 1, 2)
        main_layout.addWidget(self._badge_azure, 0, 2)
        main_layout.addWidget(self._badge_eleven, 0, 3)
        main_layout.addWidget(self._steps_list, 1, 0, 1, 2)
        main_layout.addWidget(self._log_view, 1, 2, 1, 2)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        toolbar = QToolBar("Controls")
        self.addToolBar(toolbar)

        start_action = QAction("開始", self)
        start_action.triggered.connect(self._start_pipeline)
        toolbar.addAction(start_action)

        stop_action = QAction("停止", self)
        stop_action.triggered.connect(self.runner.stop)
        toolbar.addAction(stop_action)

        setup_action = QAction("セットアップ", self)
        setup_action.triggered.connect(self._open_setup)
        toolbar.addAction(setup_action)

        selfcheck_action = QAction("Self-check", self)
        selfcheck_action.triggered.connect(self._run_selfcheck)
        toolbar.addAction(selfcheck_action)

        self.setStatusBar(QStatusBar())

    # ------------------------------------------------------------------
    def _update_key_badges(self) -> None:
        self._badge_azure.setText("Azure Key: 登録済み" if self.config_manager.get_azure_key() else "Azure Key: 未登録")
        self._badge_azure.setStyleSheet("color: green;" if self.config_manager.get_azure_key() else "color: orange;")
        self._badge_eleven.setText("ElevenLabs Key: 登録済み" if self.config_manager.get_eleven_labs_key() else "ElevenLabs Key: 未登録")
        self._badge_eleven.setStyleSheet("color: green;" if self.config_manager.get_eleven_labs_key() else "color: orange;")

    def _update_step_status(self, step_index: int, status: str) -> None:
        item = self._steps_list.item(step_index)
        if item:
            item.setText(f"{STEPS[step_index].title} - {status}")

    # ------------------------------------------------------------------
    def _start_pipeline(self) -> None:
        if self.runner.is_running():
            QMessageBox.information(self, "実行中", "パイプラインは既に実行中です。")
            return
        if not self.config.paths.script or not self.config.paths.output_dir:
            QMessageBox.warning(self, "セットアップ未完了", "台本と保存先をセットアップから指定してください。")
            return
        self.statusBar().showMessage("パイプラインを起動しています…")
        self._log_view.append_text("=== pipeline start ===")
        azure_key = self.config_manager.get_azure_key()
        eleven_key = self.config_manager.get_eleven_labs_key()
        self.runner.start(self.config, azure_key, eleven_key)

    def _on_log_event(self, event: dict) -> None:
        self._log_view.append_event(event)
        code = (event.get("code") or "").lower()
        if "narration" in code or code.endswith("start"):
            self._update_step_status(0, "進行中")
        if "sub" in code:
            self._update_step_status(1, "進行中")
        if "plan" in code:
            self._update_step_status(2, "進行中")
        if "bgm" in code:
            self._update_step_status(3, "進行中")
        if "se" in code:
            self._update_step_status(4, "進行中")
        if "xml" in code:
            self._update_step_status(5, "進行中")

    def _on_stderr(self, text: str) -> None:
        self._log_view.append_text(f"[STDERR] {text}")

    def _on_finished(self, exit_code: int) -> None:
        self.statusBar().showMessage(f"パイプライン終了: exit={exit_code}", 5000)
        self._log_view.append_text(f"=== pipeline finished ({exit_code}) ===")

    # ------------------------------------------------------------------
    def _open_setup(self) -> None:
        dialog = SetupDialog(self.config, self.config_manager, self)
        if dialog.exec() == QDialog.Accepted:
            self.config = self.config_manager.load()
            self._update_key_badges()

    def _run_selfcheck(self) -> None:
        if self._selfcheck_thread and self._selfcheck_thread.isRunning():
            QMessageBox.information(self, "Self-check", "Self-check は実行中です。")
            return
        self._badge_selfcheck.setText("Self-check: 実行中…")
        self._badge_selfcheck.setStyleSheet("color: orange;")
        self._selfcheck_thread = SelfCheckThread()
        self._selfcheck_thread.finished.connect(self._selfcheck_finished)
        self._selfcheck_thread.start()

    def _selfcheck_finished(self, result) -> None:
        if result.ok:
            self._badge_selfcheck.setText("Self-check: OK")
            self._badge_selfcheck.setStyleSheet("color: green;")
        else:
            self._badge_selfcheck.setText("Self-check: 要確認")
            self._badge_selfcheck.setStyleSheet("color: red;")

    # ------------------------------------------------------------------
    def closeEvent(self, event):  # noqa: N802
        if self.runner.is_running():
            self.runner.stop()
        super().closeEvent(event)
