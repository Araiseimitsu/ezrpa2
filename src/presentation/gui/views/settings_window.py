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
    QKeySequenceEdit, QScrollArea, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QKeySequence

from src.domain.entities.shortcut_settings import ShortcutSettings, KeyCombination, KeyModifier
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