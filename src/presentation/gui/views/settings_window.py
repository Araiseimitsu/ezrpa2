"""
設定画面UI

ショートカットキー設定のユーザーインターフェースを提供します。
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QCheckBox, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QMessageBox, QLineEdit, QFormLayout,
    QDialogButtonBox, QTextEdit, QSplitter, QFrame,
    QKeySequenceEdit, QScrollArea, QFileDialog, QInputDialog,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QToolButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QKeySequence

from src.domain.entities.shortcut_settings import ShortcutSettings, KeyCombination, KeyModifier
from src.domain.entities.custom_shortcut_command import CustomShortcutCommand, CommandType
from src.presentation.gui.viewmodels.settings_viewmodel import SettingsViewModel


class KeyCaptureWidget(QFrame):
    """キー入力キャプチャウィジェット"""
    
    key_captured = Signal(list, str)  # modifiers, key
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(200, 40)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.label = QLabel("キーを押してください...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #666; font-style: italic;")
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.captured_keys = []
        self.captured_key = ""
        
    def keyPressEvent(self, event: QKeyEvent):
        """キー押下イベント"""
        modifiers = []
        
        # 修飾キーを確認
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("Win")
        
        # 通常のキーを取得
        key = event.text().lower() if event.text() and event.text().isprintable() else ""
        if not key:
            # 特殊キーの場合
            key_map = {
                Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3", Qt.Key.Key_F4: "f4",
                Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6", Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8",
                Qt.Key.Key_F9: "f9", Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
                Qt.Key.Key_Space: "space", Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
                Qt.Key.Key_Tab: "tab", Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Delete: "delete",
                Qt.Key.Key_Escape: "esc", Qt.Key.Key_Insert: "insert", Qt.Key.Key_Home: "home",
                Qt.Key.Key_End: "end", Qt.Key.Key_PageUp: "page_up", Qt.Key.Key_PageDown: "page_down",
                Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right"
            }
            key = key_map.get(event.key(), "")
        
        # キー組み合わせが有効な場合のみ処理
        if key and not (event.key() in [Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta]):
            self.captured_keys = modifiers
            self.captured_key = key
            
            # 表示更新
            display_text = "+".join(modifiers + [key.upper()])
            self.label.setText(display_text)
            self.label.setStyleSheet("color: #000; font-weight: bold;")
            
            # シグナル発信
            self.key_captured.emit(modifiers, key)
        
        event.accept()
    
    def clear(self):
        """キャプチャクリア"""
        self.captured_keys = []
        self.captured_key = ""
        self.label.setText("キーを押してください...")
        self.label.setStyleSheet("color: #666; font-style: italic;")
    
    def focusInEvent(self, event):
        """フォーカス取得時"""
        self.setStyleSheet("QFrame { border: 2px solid #0078D4; background-color: #F3F9FF; }")
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        """フォーカス喪失時"""
        self.setStyleSheet("QFrame { border: 1px solid #ccc; background-color: white; }")
        super().focusOutEvent(event)


class SettingsWindow(QDialog):
    """設定画面ウィンドウ"""
    
    settings_applied = Signal(ShortcutSettings)
    
    def __init__(self, shortcut_settings: Optional[ShortcutSettings] = None, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("EZRPA 設定")
        self.setModal(True)
        self.resize(800, 600)
        
        # ViewModelの初期化
        self.viewmodel = SettingsViewModel(shortcut_settings)
        self.viewmodel.error_occurred.connect(self._show_error)
        self.viewmodel.custom_key_added.connect(self._refresh_custom_keys)
        self.viewmodel.custom_key_removed.connect(self._refresh_custom_keys)
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
    
    def _setup_ui(self):
        """UI構築"""
        layout = QVBoxLayout()
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # ショートカットキータブ
        self.shortcuts_tab = self._create_shortcuts_tab()
        self.tab_widget.addTab(self.shortcuts_tab, "🔧 ショートカットキー")
        
        # カスタムショートカットタブ
        self.custom_shortcuts_tab = self._create_custom_shortcuts_tab()
        self.tab_widget.addTab(self.custom_shortcuts_tab, "🚀 カスタムショートカット")
        
        # RPA制御キータブ
        self.rpa_controls_tab = self._create_rpa_controls_tab()
        self.tab_widget.addTab(self.rpa_controls_tab, "⌨️ RPA制御キー")
        
        # 詳細設定タブ
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "⚙️ 詳細設定")
        
        layout.addWidget(self.tab_widget)
        
        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        
        button_box.accepted.connect(self._apply_settings)
        button_box.rejected.connect(self.reject)
        
        # デフォルト復元ボタン
        restore_button = button_box.button(QDialogButtonBox.StandardButton.RestoreDefaults)
        restore_button.setText("デフォルトに戻す")
        restore_button.clicked.connect(self._restore_defaults)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def _create_shortcuts_tab(self) -> QWidget:
        """ショートカットキータブ作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # システムキー除外設定
        system_group = QGroupBox("システムキー除外設定")
        system_layout = QVBoxLayout()
        
        self.exclude_system_keys_cb = QCheckBox("システムキーを除外する")
        self.exclude_system_keys_cb.setToolTip("一般的なWindowsショートカットを記録対象から除外します")
        
        self.exclude_clipboard_keys_cb = QCheckBox("クリップボード操作キー (Ctrl+C/V/X)")
        self.exclude_window_keys_cb = QCheckBox("ウィンドウ操作キー (Alt+F4, Alt+Tab)")
        self.exclude_windows_keys_cb = QCheckBox("Windowsキー組み合わせ (Win+D, Win+R等)")
        self.exclude_app_keys_cb = QCheckBox("アプリケーション操作キー (Ctrl+S/N/O等)")
        
        # インデントをつけて階層表示
        for cb in [self.exclude_clipboard_keys_cb, self.exclude_window_keys_cb, 
                  self.exclude_windows_keys_cb, self.exclude_app_keys_cb]:
            cb.setContentsMargins(20, 0, 0, 0)
        
        system_layout.addWidget(self.exclude_system_keys_cb)
        system_layout.addWidget(self.exclude_clipboard_keys_cb)
        system_layout.addWidget(self.exclude_window_keys_cb)
        system_layout.addWidget(self.exclude_windows_keys_cb)
        system_layout.addWidget(self.exclude_app_keys_cb)
        system_group.setLayout(system_layout)
        
        # カスタム除外キー設定
        custom_group = QGroupBox("カスタム除外キー")
        custom_layout = QVBoxLayout()
        
        # キー一覧
        self.custom_keys_list = QListWidget()
        self.custom_keys_list.setMaximumHeight(150)
        
        # キー追加セクション
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("新しいキー組み合わせ:"))
        
        self.key_capture_widget = KeyCaptureWidget()
        self.key_capture_widget.key_captured.connect(self._on_key_captured)
        add_layout.addWidget(self.key_capture_widget)
        
        self.add_key_btn = QPushButton("追加")
        self.add_key_btn.clicked.connect(self._add_custom_key)
        self.add_key_btn.setEnabled(False)
        add_layout.addWidget(self.add_key_btn)
        
        # キー削除ボタン
        key_controls_layout = QHBoxLayout()
        self.remove_key_btn = QPushButton("削除")
        self.remove_key_btn.clicked.connect(self._remove_custom_key)
        self.remove_key_btn.setEnabled(False)
        key_controls_layout.addWidget(self.remove_key_btn)
        key_controls_layout.addStretch()
        
        custom_layout.addWidget(self.custom_keys_list)
        custom_layout.addLayout(add_layout)
        custom_layout.addLayout(key_controls_layout)
        custom_group.setLayout(custom_layout)
        
        layout.addWidget(system_group)
        layout.addWidget(custom_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _create_rpa_controls_tab(self) -> QWidget:
        """RPA制御キータブ作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # RPA制御キー設定
        rpa_group = QGroupBox("RPA制御ホットキー")
        form_layout = QFormLayout()
        
        # 記録開始/停止キー
        self.start_stop_capture = KeyCaptureWidget()
        self.start_stop_capture.key_captured.connect(
            lambda mods, key: self._set_rpa_control_key("start_stop", mods, key)
        )
        form_layout.addRow("記録開始/停止:", self.start_stop_capture)
        
        # 一時停止/再開キー
        self.pause_resume_capture = KeyCaptureWidget()
        self.pause_resume_capture.key_captured.connect(
            lambda mods, key: self._set_rpa_control_key("pause_resume", mods, key)
        )
        form_layout.addRow("一時停止/再開:", self.pause_resume_capture)
        
        # 緊急停止キー
        self.emergency_stop_capture = KeyCaptureWidget()
        self.emergency_stop_capture.key_captured.connect(
            lambda mods, key: self._set_rpa_control_key("emergency_stop", mods, key)
        )
        form_layout.addRow("緊急停止:", self.emergency_stop_capture)
        
        rpa_group.setLayout(form_layout)
        
        # 説明テキスト
        help_group = QGroupBox("ホットキーについて")
        help_layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(150)
        help_text.setPlainText(
            "• 記録開始/停止: RPA記録の開始と停止を切り替えます\n"
            "• 一時停止/再開: 記録中に一時的に停止・再開できます\n"
            "• 緊急停止: 記録や再生を即座に停止します\n\n"
            "注意: これらのキーは記録中でもシステムに影響を与えます。\n"
            "他のアプリケーションと重複しないキー組み合わせを選択してください。"
        )
        
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        
        layout.addWidget(rpa_group)
        layout.addWidget(help_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _create_custom_shortcuts_tab(self) -> QWidget:
        """カスタムショートカットタブ作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # コマンド一覧テーブル
        commands_group = QGroupBox("カスタムショートカットコマンド")
        commands_layout = QVBoxLayout()
        
        self.commands_table = QTableWidget()
        self.commands_table.setColumnCount(5)
        self.commands_table.setHorizontalHeaderLabels([
            "名前", "キー組み合わせ", "コマンドタイプ", "コマンド", "状態"
        ])
        
        # テーブルの設定
        header = self.commands_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 名前
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # キー組み合わせ
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # コマンドタイプ
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # コマンド
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 状態
        
        self.commands_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.commands_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.commands_table.setAlternatingRowColors(True)
        
        # ボタン群
        button_layout = QHBoxLayout()
        
        self.add_command_btn = QPushButton("➕ 新しいコマンド")
        self.add_command_btn.clicked.connect(self._add_custom_command)
        
        self.edit_command_btn = QPushButton("✏️ 編集")
        self.edit_command_btn.clicked.connect(self._edit_custom_command)
        self.edit_command_btn.setEnabled(False)
        
        self.duplicate_command_btn = QPushButton("📋 複製")
        self.duplicate_command_btn.clicked.connect(self._duplicate_custom_command)
        self.duplicate_command_btn.setEnabled(False)
        
        self.remove_command_btn = QPushButton("🗑️ 削除")
        self.remove_command_btn.clicked.connect(self._remove_custom_command)
        self.remove_command_btn.setEnabled(False)
        
        self.test_command_btn = QPushButton("🧪 テスト実行")
        self.test_command_btn.clicked.connect(self._test_custom_command)
        self.test_command_btn.setEnabled(False)
        
        button_layout.addWidget(self.add_command_btn)
        button_layout.addWidget(self.edit_command_btn)
        button_layout.addWidget(self.duplicate_command_btn)
        button_layout.addWidget(self.remove_command_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.test_command_btn)
        
        # プリセットコマンド
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("プリセット:"))
        
        self.add_preset_btn = QPushButton("📦 プリセットを追加")
        self.add_preset_btn.clicked.connect(self._add_preset_commands)
        preset_layout.addWidget(self.add_preset_btn)
        preset_layout.addStretch()
        
        commands_layout.addWidget(self.commands_table)
        commands_layout.addLayout(button_layout)
        commands_layout.addLayout(preset_layout)
        commands_group.setLayout(commands_layout)
        
        # ヘルプセクション
        help_group = QGroupBox("カスタムショートカットについて")
        help_layout = QVBoxLayout()
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setMaximumHeight(120)
        help_text.setPlainText(
            "カスタムショートカットを使用して、キー組み合わせで様々なコマンドを実行できます。\n\n"
            "• アプリケーション起動: 指定したプログラムを起動\n"
            "• ファイル操作: ファイルやフォルダを開く\n"
            "• システムコマンド: コマンドライン実行\n"
            "• URL開く: ブラウザでWebページを開く\n"
            "• テキスト入力: 定型文をクリップボード経由で入力\n\n"
            "注意: システムキーやRPA制御キーと重複しないキー組み合わせを選択してください。"
        )
        
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        
        layout.addWidget(commands_group)
        layout.addWidget(help_group)
        
        widget.setLayout(layout)
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """詳細設定タブ作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 設定の検証
        validation_group = QGroupBox("設定の検証")
        validation_layout = QVBoxLayout()
        
        self.validate_btn = QPushButton("設定を検証")
        self.validate_btn.clicked.connect(self._validate_settings)
        
        self.validation_result = QTextEdit()
        self.validation_result.setReadOnly(True)
        self.validation_result.setMaximumHeight(100)
        
        validation_layout.addWidget(self.validate_btn)
        validation_layout.addWidget(self.validation_result)
        validation_group.setLayout(validation_layout)
        
        # インポート/エクスポート
        import_export_group = QGroupBox("設定のインポート/エクスポート")
        ie_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("設定をエクスポート")
        self.export_btn.clicked.connect(self._export_settings)
        
        self.import_btn = QPushButton("設定をインポート")
        self.import_btn.clicked.connect(self._import_settings)
        
        ie_layout.addWidget(self.export_btn)
        ie_layout.addWidget(self.import_btn)
        ie_layout.addStretch()
        import_export_group.setLayout(ie_layout)
        
        # 除外されるキー一覧
        excluded_keys_group = QGroupBox("除外されるキー一覧（プレビュー）")
        excluded_layout = QVBoxLayout()
        
        self.excluded_keys_list = QTextEdit()
        self.excluded_keys_list.setReadOnly(True)
        self.excluded_keys_list.setMaximumHeight(200)
        
        self.refresh_preview_btn = QPushButton("プレビュー更新")
        self.refresh_preview_btn.clicked.connect(self._refresh_excluded_keys_preview)
        
        excluded_layout.addWidget(self.excluded_keys_list)
        excluded_layout.addWidget(self.refresh_preview_btn)
        excluded_keys_group.setLayout(excluded_layout)
        
        layout.addWidget(validation_group)
        layout.addWidget(import_export_group)
        layout.addWidget(excluded_keys_group)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def _connect_signals(self):
        """シグナル接続"""
        # システムキー除外設定
        self.exclude_system_keys_cb.toggled.connect(self.viewmodel.set_exclude_system_keys)
        self.exclude_clipboard_keys_cb.toggled.connect(self.viewmodel.set_exclude_clipboard_keys)
        self.exclude_window_keys_cb.toggled.connect(self.viewmodel.set_exclude_window_keys)
        self.exclude_windows_keys_cb.toggled.connect(self.viewmodel.set_exclude_windows_keys)
        self.exclude_app_keys_cb.toggled.connect(self.viewmodel.set_exclude_app_keys)
        
        # カスタムキー一覧
        self.custom_keys_list.itemSelectionChanged.connect(self._on_custom_key_selection_changed)
        
        # カスタムコマンドテーブル
        self.commands_table.itemSelectionChanged.connect(self._on_command_selection_changed)
        
        # システムキー除外の階層制御
        self.exclude_system_keys_cb.toggled.connect(self._update_system_keys_enabled)
    
    def _load_settings(self):
        """設定読み込み"""
        settings = self.viewmodel.get_settings()
        
        # システムキー除外設定
        self.exclude_system_keys_cb.setChecked(settings.exclude_system_keys)
        self.exclude_clipboard_keys_cb.setChecked(settings.exclude_clipboard_keys)
        self.exclude_window_keys_cb.setChecked(settings.exclude_window_keys)
        self.exclude_windows_keys_cb.setChecked(settings.exclude_windows_keys)
        self.exclude_app_keys_cb.setChecked(settings.exclude_app_keys)
        
        # カスタム除外キー
        self._refresh_custom_keys()
        
        # カスタムコマンド
        self._refresh_commands_table()
        
        # RPA制御キー
        self._update_rpa_control_displays()
        
        # システムキー有効/無効状態
        self._update_system_keys_enabled()
        
        # 除外キープレビュー
        self._refresh_excluded_keys_preview()
    
    def _refresh_custom_keys(self):
        """カスタムキー一覧更新"""
        self.custom_keys_list.clear()
        for key_str in self.viewmodel.get_custom_excluded_keys():
            self.custom_keys_list.addItem(key_str)
    
    def _update_rpa_control_displays(self):
        """RPA制御キー表示更新"""
        # 現在の設定を表示に反映
        start_stop_key = self.viewmodel.get_recording_start_stop_key()
        self.start_stop_capture.label.setText(start_stop_key or "設定されていません")
        
        pause_resume_key = self.viewmodel.get_recording_pause_resume_key()
        self.pause_resume_capture.label.setText(pause_resume_key or "設定されていません")
        
        emergency_stop_key = self.viewmodel.get_emergency_stop_key()
        self.emergency_stop_capture.label.setText(emergency_stop_key or "設定されていません")
    
    def _update_system_keys_enabled(self):
        """システムキー詳細設定の有効/無効切り替え"""
        enabled = self.exclude_system_keys_cb.isChecked()
        
        self.exclude_clipboard_keys_cb.setEnabled(enabled)
        self.exclude_window_keys_cb.setEnabled(enabled)
        self.exclude_windows_keys_cb.setEnabled(enabled)
        self.exclude_app_keys_cb.setEnabled(enabled)
    
    def _on_key_captured(self, modifiers: List[str], key: str):
        """カスタムキーキャプチャ時"""
        self.add_key_btn.setEnabled(True)
    
    def _add_custom_key(self):
        """カスタムキー追加"""
        modifiers = self.key_capture_widget.captured_keys
        key = self.key_capture_widget.captured_key
        
        if not key:
            return
        
        # KeyModifierに変換
        modifier_set = set()
        for mod in modifiers:
            if mod.lower() == "ctrl":
                modifier_set.add(KeyModifier.CTRL)
            elif mod.lower() == "alt":
                modifier_set.add(KeyModifier.ALT)
            elif mod.lower() == "shift":
                modifier_set.add(KeyModifier.SHIFT)
            elif mod.lower() == "win":
                modifier_set.add(KeyModifier.WIN)
        
        key_combination = KeyCombination(
            modifiers=modifier_set,
            key=key.lower(),
            description=f"カスタム除外キー"
        )
        
        if self.viewmodel.add_custom_excluded_key(key_combination):
            self.key_capture_widget.clear()
            self.add_key_btn.setEnabled(False)
    
    def _remove_custom_key(self):
        """カスタムキー削除"""
        current_row = self.custom_keys_list.currentRow()
        if current_row >= 0:
            self.viewmodel.remove_custom_excluded_key(current_row)
    
    def _on_custom_key_selection_changed(self):
        """カスタムキー選択変更"""
        self.remove_key_btn.setEnabled(len(self.custom_keys_list.selectedItems()) > 0)
    
    def _set_rpa_control_key(self, key_type: str, modifiers: List[str], key: str):
        """RPA制御キー設定"""
        modifier_set = set()
        for mod in modifiers:
            if mod.lower() == "ctrl":
                modifier_set.add(KeyModifier.CTRL)
            elif mod.lower() == "alt":
                modifier_set.add(KeyModifier.ALT)
            elif mod.lower() == "shift":
                modifier_set.add(KeyModifier.SHIFT)
            elif mod.lower() == "win":
                modifier_set.add(KeyModifier.WIN)
        
        key_combination = KeyCombination(
            modifiers=modifier_set,
            key=key.lower(),
            description=""
        )
        
        if key_type == "start_stop":
            key_combination.description = "記録開始/停止"
            self.viewmodel.set_recording_start_stop_key(key_combination)
        elif key_type == "pause_resume":
            key_combination.description = "記録一時停止/再開"
            self.viewmodel.set_recording_pause_resume_key(key_combination)
        elif key_type == "emergency_stop":
            key_combination.description = "緊急停止"
            self.viewmodel.set_emergency_stop_key(key_combination)
    
    def _validate_settings(self):
        """設定の検証"""
        warnings = self.viewmodel.validate_settings()
        
        if warnings:
            result_text = "⚠️ 以下の警告があります:\n\n" + "\n".join(f"• {warning}" for warning in warnings)
        else:
            result_text = "✅ 設定に問題はありません"
        
        self.validation_result.setPlainText(result_text)
    
    def _export_settings(self):
        """設定エクスポート"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "設定をエクスポート", "ezrpa_shortcuts.json", 
            "JSON ファイル (*.json);;すべてのファイル (*)"
        )
        
        if file_path:
            try:
                settings_dict = self.viewmodel.export_settings_dict()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings_dict, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "エクスポート完了", f"設定をエクスポートしました:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "エクスポートエラー", f"設定のエクスポートに失敗しました:\n{str(e)}")
    
    def _import_settings(self):
        """設定インポート"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "設定をインポート", "", 
            "JSON ファイル (*.json);;すべてのファイル (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings_dict = json.load(f)
                
                if self.viewmodel.import_settings_dict(settings_dict):
                    self._load_settings()  # UI更新
                    QMessageBox.information(self, "インポート完了", f"設定をインポートしました:\n{file_path}")
                else:
                    QMessageBox.warning(self, "インポート失敗", "設定のインポートに失敗しました")
            except Exception as e:
                QMessageBox.critical(self, "インポートエラー", f"設定ファイルの読み込みに失敗しました:\n{str(e)}")
    
    def _refresh_excluded_keys_preview(self):
        """除外キープレビュー更新"""
        settings = self.viewmodel.get_settings()
        excluded_keys = settings.get_all_excluded_keys()
        
        if excluded_keys:
            preview_text = "以下のキー組み合わせが記録から除外されます:\n\n"
            
            # カテゴリ別に整理
            clipboard_keys = []
            window_keys = []
            app_keys = []
            windows_keys = []
            custom_keys = []
            
            for key in excluded_keys:
                key_str = str(key)
                if key in settings.custom_excluded_keys:
                    custom_keys.append(key_str)
                elif KeyModifier.WIN in key.modifiers:
                    windows_keys.append(key_str)
                elif KeyModifier.ALT in key.modifiers:
                    window_keys.append(key_str)
                elif KeyModifier.CTRL in key.modifiers and key.key in ['c', 'v', 'x', 'z', 'y']:
                    clipboard_keys.append(key_str)
                elif KeyModifier.CTRL in key.modifiers:
                    app_keys.append(key_str)
                else:
                    custom_keys.append(key_str)
            
            if clipboard_keys:
                preview_text += "📋 クリップボード操作:\n" + "\n".join(f"  • {key}" for key in clipboard_keys) + "\n\n"
            if window_keys:
                preview_text += "🪟 ウィンドウ操作:\n" + "\n".join(f"  • {key}" for key in window_keys) + "\n\n"
            if windows_keys:
                preview_text += "⊞ Windowsキー:\n" + "\n".join(f"  • {key}" for key in windows_keys) + "\n\n"
            if app_keys:
                preview_text += "📱 アプリケーション操作:\n" + "\n".join(f"  • {key}" for key in app_keys) + "\n\n"
            if custom_keys:
                preview_text += "⚙️ カスタム除外キー:\n" + "\n".join(f"  • {key}" for key in custom_keys) + "\n\n"
            
            preview_text += f"合計: {len(excluded_keys)} 個のキー組み合わせ"
        else:
            preview_text = "除外されるキーはありません（すべてのキーが記録されます）"
        
        self.excluded_keys_list.setPlainText(preview_text)
    
    def _restore_defaults(self):
        """デフォルト設定復元"""
        reply = QMessageBox.question(
            self, "デフォルト復元",
            "設定をデフォルトに戻しますか？\n\n現在の設定は失われます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.viewmodel.restore_default_settings()
            self._load_settings()
    
    def _apply_settings(self):
        """設定適用"""
        # 設定の検証
        warnings = self.viewmodel.validate_settings()
        if warnings:
            reply = QMessageBox.question(
                self, "設定に警告があります",
                f"以下の警告がありますが、設定を適用しますか？\n\n" + 
                "\n".join(f"• {warning}" for warning in warnings),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 設定適用
        settings = self.viewmodel.get_settings()
        self.settings_applied.emit(settings)
        self.accept()
    
    def _show_error(self, message: str):
        """エラー表示"""
        QMessageBox.critical(self, "エラー", message)
    
    # カスタムショートカットコマンド関連メソッド
    def _refresh_commands_table(self):
        """コマンドテーブルを更新"""
        commands = self.viewmodel.get_settings().get_custom_shortcut_commands()
        
        self.commands_table.setRowCount(len(commands))
        
        for row, command in enumerate(commands):
            # 名前
            self.commands_table.setItem(row, 0, QTableWidgetItem(command.name))
            
            # キー組み合わせ
            key_text = str(command.key_combination) if command.key_combination else "未設定"
            self.commands_table.setItem(row, 1, QTableWidgetItem(key_text))
            
            # コマンドタイプ
            type_text = {
                CommandType.APPLICATION: "アプリケーション",
                CommandType.FILE_OPERATION: "ファイル操作",
                CommandType.SYSTEM_COMMAND: "システムコマンド",
                CommandType.SCRIPT_EXECUTION: "スクリプト実行",
                CommandType.URL_OPEN: "URL開く",
                CommandType.TEXT_INPUT: "テキスト入力"
            }.get(command.command_type, "不明")
            self.commands_table.setItem(row, 2, QTableWidgetItem(type_text))
            
            # コマンド（短縮表示）
            cmd_display = command.command
            if len(cmd_display) > 50:
                cmd_display = cmd_display[:47] + "..."
            self.commands_table.setItem(row, 3, QTableWidgetItem(cmd_display))
            
            # 状態
            status_text = "有効" if command.enabled else "無効"
            status_item = QTableWidgetItem(status_text)
            if command.enabled:
                status_item.setBackground(Qt.GlobalColor.green)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
            self.commands_table.setItem(row, 4, status_item)
        
        # テーブル選択状態の更新
        self._on_command_selection_changed()
    
    def _on_command_selection_changed(self):
        """コマンド選択状態変更"""
        has_selection = self.commands_table.currentRow() >= 0
        
        self.edit_command_btn.setEnabled(has_selection)
        self.duplicate_command_btn.setEnabled(has_selection)
        self.remove_command_btn.setEnabled(has_selection)
        self.test_command_btn.setEnabled(has_selection)
    
    def _add_custom_command(self):
        """カスタムコマンド追加"""
        dialog = CustomCommandEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            command = dialog.get_command()
            settings = self.viewmodel.get_settings()
            
            if settings.add_custom_shortcut_command(command):
                self._refresh_commands_table()
                QMessageBox.information(self, "完了", "コマンドが追加されました。")
            else:
                QMessageBox.warning(self, "警告", "キー組み合わせが重複しているか、無効な設定です。")
    
    def _edit_custom_command(self):
        """カスタムコマンド編集"""
        row = self.commands_table.currentRow()
        if row < 0:
            return
        
        commands = self.viewmodel.get_settings().get_custom_shortcut_commands()
        if row >= len(commands):
            return
        
        command = commands[row]
        dialog = CustomCommandEditDialog(command, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_command = dialog.get_command()
            settings = self.viewmodel.get_settings()
            
            if settings.update_custom_shortcut_command(updated_command):
                self._refresh_commands_table()
                QMessageBox.information(self, "完了", "コマンドが更新されました。")
            else:
                QMessageBox.warning(self, "警告", "更新に失敗しました。")
    
    def _duplicate_custom_command(self):
        """カスタムコマンド複製"""
        row = self.commands_table.currentRow()
        if row < 0:
            return
        
        commands = self.viewmodel.get_settings().get_custom_shortcut_commands()
        if row >= len(commands):
            return
        
        original_command = commands[row]
        
        # 複製したコマンドを作成
        new_command = CustomShortcutCommand(
            name=f"{original_command.name} (コピー)",
            description=original_command.description,
            enabled=original_command.enabled,
            key_combination=KeyCombination(),  # キー組み合わせはクリア
            command_type=original_command.command_type,
            command=original_command.command,
            parameters=original_command.parameters.copy(),
            working_directory=original_command.working_directory,
            run_as_admin=original_command.run_as_admin,
            wait_for_completion=original_command.wait_for_completion,
            timeout_seconds=original_command.timeout_seconds,
            active_window_title_pattern=original_command.active_window_title_pattern,
            active_process_name_pattern=original_command.active_process_name_pattern
        )
        
        dialog = CustomCommandEditDialog(new_command, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            command = dialog.get_command()
            settings = self.viewmodel.get_settings()
            
            if settings.add_custom_shortcut_command(command):
                self._refresh_commands_table()
                QMessageBox.information(self, "完了", "コマンドが複製されました。")
            else:
                QMessageBox.warning(self, "警告", "キー組み合わせが重複しているか、無効な設定です。")
    
    def _remove_custom_command(self):
        """カスタムコマンド削除"""
        row = self.commands_table.currentRow()
        if row < 0:
            return
        
        commands = self.viewmodel.get_settings().get_custom_shortcut_commands()
        if row >= len(commands):
            return
        
        command = commands[row]
        
        reply = QMessageBox.question(
            self, "削除確認",
            f"コマンド '{command.name}' を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            settings = self.viewmodel.get_settings()
            if settings.remove_custom_shortcut_command(command.id):
                self._refresh_commands_table()
                QMessageBox.information(self, "完了", "コマンドが削除されました。")
            else:
                QMessageBox.warning(self, "警告", "削除に失敗しました。")
    
    def _test_custom_command(self):
        """カスタムコマンドテスト実行"""
        row = self.commands_table.currentRow()
        if row < 0:
            return
        
        commands = self.viewmodel.get_settings().get_custom_shortcut_commands()
        if row >= len(commands):
            return
        
        command = commands[row]
        
        reply = QMessageBox.question(
            self, "テスト実行",
            f"コマンド '{command.name}' をテスト実行しますか？\n\n"
            f"コマンド: {command.command}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if command.execute():
                    QMessageBox.information(self, "テスト完了", "コマンドが正常に実行されました。")
                else:
                    QMessageBox.warning(self, "テスト失敗", "コマンドの実行に失敗しました。")
            except Exception as e:
                QMessageBox.critical(self, "テストエラー", f"実行中にエラーが発生しました：\n{str(e)}")
    
    def _add_preset_commands(self):
        """プリセットコマンド追加"""
        from src.domain.entities.custom_shortcut_command import create_preset_commands
        
        preset_commands = create_preset_commands()
        settings = self.viewmodel.get_settings()
        
        added_count = 0
        for command in preset_commands:
            if settings.add_custom_shortcut_command(command):
                added_count += 1
        
        if added_count > 0:
            self._refresh_commands_table()
            QMessageBox.information(self, "完了", f"{added_count}個のプリセットコマンドが追加されました。")
        else:
            QMessageBox.information(self, "情報", "プリセットコマンドはすでに追加されているか、キー組み合わせが競合しています。")


class CustomCommandEditDialog(QDialog):
    """カスタムコマンド編集ダイアログ"""
    
    def __init__(self, command: Optional[CustomShortcutCommand] = None, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("カスタムコマンド編集")
        self.setModal(True)
        self.resize(600, 500)
        
        self.command = command or CustomShortcutCommand()
        self._setup_ui()
        self._load_command()
    
    def _setup_ui(self):
        """UI構築"""
        layout = QVBoxLayout()
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # 基本設定タブ
        self.basic_tab = self._create_basic_tab()
        self.tab_widget.addTab(self.basic_tab, "基本設定")
        
        # 詳細設定タブ
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "詳細設定")
        
        layout.addWidget(self.tab_widget)
        
        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def _create_basic_tab(self) -> QWidget:
        """基本設定タブ作成"""
        widget = QWidget()
        layout = QFormLayout()
        
        # 名前
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("コマンドの名前を入力")
        layout.addRow("名前:", self.name_edit)
        
        # 説明
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("コマンドの説明（オプション）")
        layout.addRow("説明:", self.description_edit)
        
        # 有効/無効
        self.enabled_cb = QCheckBox("このコマンドを有効にする")
        layout.addRow("", self.enabled_cb)
        
        # キー組み合わせ
        self.key_capture = KeyCaptureWidget()
        layout.addRow("キー組み合わせ:", self.key_capture)
        
        # コマンドタイプ
        self.command_type_combo = QComboBox()
        self.command_type_combo.addItems([
            "アプリケーション",
            "ファイル操作", 
            "システムコマンド",
            "スクリプト実行",
            "URL開く",
            "テキスト入力"
        ])
        self.command_type_combo.currentTextChanged.connect(self._on_command_type_changed)
        layout.addRow("コマンドタイプ:", self.command_type_combo)
        
        # コマンド
        command_layout = QHBoxLayout()
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText("実行するコマンドまたはパス")
        
        self.browse_btn = QPushButton("参照")
        self.browse_btn.clicked.connect(self._browse_command)
        
        command_layout.addWidget(self.command_edit)
        command_layout.addWidget(self.browse_btn)
        layout.addRow("コマンド:", command_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """詳細設定タブ作成"""
        widget = QWidget()
        layout = QFormLayout()
        
        # 作業ディレクトリ
        work_dir_layout = QHBoxLayout()
        self.working_directory_edit = QLineEdit()
        self.working_directory_edit.setPlaceholderText("作業ディレクトリ（オプション）")
        
        self.browse_workdir_btn = QPushButton("参照")
        self.browse_workdir_btn.clicked.connect(self._browse_working_directory)
        
        work_dir_layout.addWidget(self.working_directory_edit)
        work_dir_layout.addWidget(self.browse_workdir_btn)
        layout.addRow("作業ディレクトリ:", work_dir_layout)
        
        # 実行設定
        self.wait_for_completion_cb = QCheckBox("完了まで待機")
        layout.addRow("実行設定:", self.wait_for_completion_cb)
        
        # タイムアウト
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(1)
        self.timeout_spin.setMaximum(3600)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" 秒")
        layout.addRow("タイムアウト:", self.timeout_spin)
        
        # 条件設定
        self.active_window_pattern_edit = QLineEdit()
        self.active_window_pattern_edit.setPlaceholderText("特定のウィンドウタイトルパターン（オプション）")
        layout.addRow("ウィンドウ条件:", self.active_window_pattern_edit)
        
        self.active_process_pattern_edit = QLineEdit()
        self.active_process_pattern_edit.setPlaceholderText("特定のプロセス名パターン（オプション）")
        layout.addRow("プロセス条件:", self.active_process_pattern_edit)
        
        widget.setLayout(layout)
        return widget
    
    def _load_command(self):
        """コマンド情報を読み込み"""
        self.name_edit.setText(self.command.name)
        self.description_edit.setText(self.command.description)
        self.enabled_cb.setChecked(self.command.enabled)
        
        # キー組み合わせ
        if self.command.key_combination and self.command.key_combination.key:
            modifiers = []
            for mod in self.command.key_combination.modifiers:
                if mod == KeyModifier.CTRL:
                    modifiers.append("Ctrl")
                elif mod == KeyModifier.ALT:
                    modifiers.append("Alt")
                elif mod == KeyModifier.SHIFT:
                    modifiers.append("Shift")
                elif mod == KeyModifier.WIN:
                    modifiers.append("Win")
            
            display_text = "+".join(modifiers + [self.command.key_combination.key.upper()])
            self.key_capture.label.setText(display_text)
            self.key_capture.label.setStyleSheet("color: #000; font-weight: bold;")
        
        # コマンドタイプ
        type_index = {
            CommandType.APPLICATION: 0,
            CommandType.FILE_OPERATION: 1,
            CommandType.SYSTEM_COMMAND: 2,
            CommandType.SCRIPT_EXECUTION: 3,
            CommandType.URL_OPEN: 4,
            CommandType.TEXT_INPUT: 5
        }.get(self.command.command_type, 0)
        self.command_type_combo.setCurrentIndex(type_index)
        
        self.command_edit.setText(self.command.command)
        self.working_directory_edit.setText(self.command.working_directory)
        self.wait_for_completion_cb.setChecked(self.command.wait_for_completion)
        self.timeout_spin.setValue(self.command.timeout_seconds)
        self.active_window_pattern_edit.setText(self.command.active_window_title_pattern)
        self.active_process_pattern_edit.setText(self.command.active_process_name_pattern)
    
    def _on_command_type_changed(self, text: str):
        """コマンドタイプ変更時"""
        if text == "ファイル操作":
            self.command_edit.setPlaceholderText("開くファイルまたはフォルダのパス")
        elif text == "URL開く":
            self.command_edit.setPlaceholderText("https://example.com")
        elif text == "テキスト入力":
            self.command_edit.setPlaceholderText("入力するテキスト")
        else:
            self.command_edit.setPlaceholderText("実行するコマンドまたはパス")
    
    def _browse_command(self):
        """コマンド参照"""
        command_type_text = self.command_type_combo.currentText()
        
        if command_type_text == "アプリケーション":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "実行ファイルを選択", "", "実行ファイル (*.exe);;すべてのファイル (*)")
        elif command_type_text == "ファイル操作":
            file_path = QFileDialog.getExistingDirectory(self, "フォルダを選択")
            if not file_path:
                file_path, _ = QFileDialog.getOpenFileName(self, "ファイルを選択", "", "すべてのファイル (*)")
        elif command_type_text == "スクリプト実行":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "スクリプトファイルを選択", "", 
                "スクリプトファイル (*.py *.bat *.cmd *.ps1);;すべてのファイル (*)")
        else:
            return
        
        if file_path:
            self.command_edit.setText(file_path)
    
    def _browse_working_directory(self):
        """作業ディレクトリ参照"""
        directory = QFileDialog.getExistingDirectory(self, "作業ディレクトリを選択")
        if directory:
            self.working_directory_edit.setText(directory)
    
    def _accept(self):
        """OK時の処理"""
        # 入力検証
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "入力エラー", "名前を入力してください。")
            return
        
        if not self.command_edit.text().strip():
            QMessageBox.warning(self, "入力エラー", "コマンドを入力してください。")
            return
        
        if not hasattr(self.key_capture, 'captured_key') or not self.key_capture.captured_key:
            QMessageBox.warning(self, "入力エラー", "キー組み合わせを設定してください。")
            return
        
        self.accept()
    
    def get_command(self) -> CustomShortcutCommand:
        """設定されたコマンドを取得"""
        # キー組み合わせの変換
        modifiers = set()
        for mod_text in getattr(self.key_capture, 'captured_keys', []):
            if mod_text == "Ctrl":
                modifiers.add(KeyModifier.CTRL)
            elif mod_text == "Alt":
                modifiers.add(KeyModifier.ALT)
            elif mod_text == "Shift":
                modifiers.add(KeyModifier.SHIFT)
            elif mod_text == "Win":
                modifiers.add(KeyModifier.WIN)
        
        key_combination = KeyCombination(
            modifiers=modifiers,
            key=getattr(self.key_capture, 'captured_key', ''),
            description=self.name_edit.text()
        )
        
        # コマンドタイプの変換
        command_type_map = {
            "アプリケーション": CommandType.APPLICATION,
            "ファイル操作": CommandType.FILE_OPERATION,
            "システムコマンド": CommandType.SYSTEM_COMMAND,
            "スクリプト実行": CommandType.SCRIPT_EXECUTION,
            "URL開く": CommandType.URL_OPEN,
            "テキスト入力": CommandType.TEXT_INPUT
        }
        command_type = command_type_map.get(self.command_type_combo.currentText(), CommandType.APPLICATION)
        
        # コマンドを更新
        self.command.name = self.name_edit.text()
        self.command.description = self.description_edit.text()
        self.command.enabled = self.enabled_cb.isChecked()
        self.command.key_combination = key_combination
        self.command.command_type = command_type
        self.command.command = self.command_edit.text()
        self.command.working_directory = self.working_directory_edit.text()
        self.command.wait_for_completion = self.wait_for_completion_cb.isChecked()
        self.command.timeout_seconds = self.timeout_spin.value()
        self.command.active_window_title_pattern = self.active_window_pattern_edit.text()
        self.command.active_process_name_pattern = self.active_process_pattern_edit.text()
        
        return self.command