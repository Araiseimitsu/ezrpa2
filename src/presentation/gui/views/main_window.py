"""
Main Window - メインウィンドウView

アプリケーションのメインウィンドウを実装します。
MVVMパターンに基づき、MainViewModelとデータバインディングを行います。
"""

import sys
from typing import Optional
from datetime import datetime

try:
    from PySide6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QSplitter, QStackedWidget, QMenuBar, QMenu, QStatusBar,
        QToolBar, QLabel, QPushButton, QFrame, QScrollArea,
        QGridLayout, QGroupBox, QProgressBar, QTextEdit,
        QListWidget, QListWidgetItem, QSizePolicy
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QThread, pyqtSignal
    from PySide6.QtGui import QAction, QIcon, QFont
    PYSIDE_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtWidgets import (
            QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QSplitter, QStackedWidget, QMenuBar, QMenu, QStatusBar,
            QToolBar, QLabel, QPushButton, QFrame, QScrollArea,
            QGridLayout, QGroupBox, QProgressBar, QTextEdit,
            QListWidget, QListWidgetItem, QSizePolicy
        )
        from PyQt6.QtCore import Qt, QTimer, pyqtSignal as Signal, QThread
        from PyQt6.QtGui import QAction, QIcon, QFont
        PYSIDE_AVAILABLE = False
    except ImportError:
        raise ImportError("PySide6またはPyQt6が必要です")

from ..viewmodels.main_viewmodel import MainViewModel
from ....core.event_bus import EventBus


class DashboardWidget(QWidget):
    """ダッシュボードウィジェット"""
    
    def __init__(self, main_viewmodel: MainViewModel, parent=None):
        super().__init__(parent)
        self._viewmodel = main_viewmodel
        self._setup_ui()
        self._connect_viewmodel()
    
    def _setup_ui(self):
        """UIの設定"""
        layout = QVBoxLayout(self)
        
        # ウェルカムセクション
        welcome_frame = QFrame()
        welcome_frame.setFrameStyle(QFrame.Shape.Box)
        welcome_layout = QVBoxLayout(welcome_frame)
        
        welcome_label = QLabel("EZRPA v2.0 へようこそ")
        welcome_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(welcome_label)
        
        status_label = QLabel("Ready")
        status_label.setObjectName("statusLabel")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(status_label)
        
        layout.addWidget(welcome_frame)
        
        # 統計情報セクション
        stats_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 記録統計
        recording_stats_group = QGroupBox("記録統計")
        recording_stats_layout = QGridLayout(recording_stats_group)
        
        self._total_recordings_label = QLabel("0")
        self._total_actions_label = QLabel("0")
        self._avg_actions_label = QLabel("0.0")
        
        recording_stats_layout.addWidget(QLabel("総記録数:"), 0, 0)
        recording_stats_layout.addWidget(self._total_recordings_label, 0, 1)
        recording_stats_layout.addWidget(QLabel("総アクション数:"), 1, 0)
        recording_stats_layout.addWidget(self._total_actions_label, 1, 1)
        recording_stats_layout.addWidget(QLabel("平均アクション数:"), 2, 0)
        recording_stats_layout.addWidget(self._avg_actions_label, 2, 1)
        
        stats_splitter.addWidget(recording_stats_group)
        
        # 再生統計
        playback_stats_group = QGroupBox("再生統計")
        playback_stats_layout = QGridLayout(playback_stats_group)
        
        self._total_playbacks_label = QLabel("0")
        self._successful_playbacks_label = QLabel("0")
        self._failed_playbacks_label = QLabel("0")
        
        playback_stats_layout.addWidget(QLabel("総再生回数:"), 0, 0)
        playback_stats_layout.addWidget(self._total_playbacks_label, 0, 1)
        playback_stats_layout.addWidget(QLabel("成功回数:"), 1, 0)
        playback_stats_layout.addWidget(self._successful_playbacks_label, 1, 1)
        playback_stats_layout.addWidget(QLabel("失敗回数:"), 2, 0)
        playback_stats_layout.addWidget(self._failed_playbacks_label, 2, 1)
        
        stats_splitter.addWidget(playback_stats_group)
        
        # スケジュール統計
        schedule_stats_group = QGroupBox("スケジュール統計")
        schedule_stats_layout = QGridLayout(schedule_stats_group)
        
        self._total_schedules_label = QLabel("0")
        self._active_schedules_label = QLabel("0")
        self._total_executions_label = QLabel("0")
        
        schedule_stats_layout.addWidget(QLabel("総スケジュール数:"), 0, 0)
        schedule_stats_layout.addWidget(self._total_schedules_label, 0, 1)
        schedule_stats_layout.addWidget(QLabel("アクティブ:"), 1, 0)
        schedule_stats_layout.addWidget(self._active_schedules_label, 1, 1)
        schedule_stats_layout.addWidget(QLabel("総実行回数:"), 2, 0)
        schedule_stats_layout.addWidget(self._total_executions_label, 2, 1)
        
        stats_splitter.addWidget(schedule_stats_group)
        
        layout.addWidget(stats_splitter)
        
        # 最近のアクティビティ
        recent_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 最近の記録
        recent_recordings_group = QGroupBox("最近の記録")
        recent_recordings_layout = QVBoxLayout(recent_recordings_group)
        
        self._recent_recordings_list = QListWidget()
        self._recent_recordings_list.setMaximumHeight(150)
        recent_recordings_layout.addWidget(self._recent_recordings_list)
        
        recent_splitter.addWidget(recent_recordings_group)
        
        # アクティブなスケジュール
        active_schedules_group = QGroupBox("アクティブなスケジュール")
        active_schedules_layout = QVBoxLayout(active_schedules_group)
        
        self._active_schedules_list = QListWidget()
        self._active_schedules_list.setMaximumHeight(150)
        active_schedules_layout.addWidget(self._active_schedules_list)
        
        recent_splitter.addWidget(active_schedules_group)
        
        layout.addWidget(recent_splitter)
        
        # クイックアクション
        quick_actions_group = QGroupBox("クイックアクション")
        quick_actions_layout = QHBoxLayout(quick_actions_group)
        
        self._quick_record_btn = QPushButton("クイック記録")
        self._quick_record_btn.clicked.connect(self._on_quick_record_clicked)
        quick_actions_layout.addWidget(self._quick_record_btn)
        
        self._view_recordings_btn = QPushButton("記録一覧")
        self._view_recordings_btn.clicked.connect(self._on_view_recordings_clicked)
        quick_actions_layout.addWidget(self._view_recordings_btn)
        
        self._view_schedules_btn = QPushButton("スケジュール")
        self._view_schedules_btn.clicked.connect(self._on_view_schedules_clicked)
        quick_actions_layout.addWidget(self._view_schedules_btn)
        
        layout.addWidget(quick_actions_group)
        
        layout.addStretch()
    
    def _connect_viewmodel(self):
        """ViewModelとの接続"""
        self._viewmodel.add_property_changed_handler(self._on_property_changed)
        
        # 初期値の設定
        self._update_status()
        self._update_statistics()
        self._update_recent_data()
    
    def _on_property_changed(self, args):
        """プロパティ変更イベントハンドラー"""
        if args.property_name == 'app_status':
            self._update_status()
        elif args.property_name in ['recording_stats', 'playback_stats', 'schedule_stats']:
            self._update_statistics()
        elif args.property_name in ['recent_recordings', 'active_schedules']:
            self._update_recent_data()
        elif args.property_name == 'is_busy':
            self._update_ui_state()
    
    def _update_status(self):
        """ステータス表示を更新"""
        status_label = self.findChild(QLabel, "statusLabel")
        if status_label:
            status_label.setText(self._viewmodel.app_status)
    
    def _update_statistics(self):
        """統計情報を更新"""
        # 記録統計
        if self._viewmodel.recording_stats:
            stats = self._viewmodel.recording_stats
            self._total_recordings_label.setText(str(stats.total_recordings))
            self._total_actions_label.setText(str(stats.total_actions))
            self._avg_actions_label.setText(f"{stats.avg_actions_per_recording:.1f}")
        
        # 再生統計
        if self._viewmodel.playback_stats:
            stats = self._viewmodel.playback_stats
            self._total_playbacks_label.setText(str(stats.get('total_playbacks', 0)))
            self._successful_playbacks_label.setText(str(stats.get('successful_playbacks', 0)))
            self._failed_playbacks_label.setText(str(stats.get('failed_playbacks', 0)))
        
        # スケジュール統計
        if self._viewmodel.schedule_stats:
            stats = self._viewmodel.schedule_stats
            self._total_schedules_label.setText(str(stats.total_schedules))
            self._active_schedules_label.setText(str(stats.active_schedules))
            self._total_executions_label.setText(str(stats.total_executions))
    
    def _update_recent_data(self):
        """最近のデータを更新"""
        # 最近の記録
        self._recent_recordings_list.clear()
        for recording in self._viewmodel.recent_recordings:
            item_text = f"{recording['name']} ({recording['action_count']}アクション)"
            item = QListWidgetItem(item_text)
            self._recent_recordings_list.addItem(item)
        
        # アクティブなスケジュール
        self._active_schedules_list.clear()
        for schedule in self._viewmodel.active_schedules:
            next_exec = schedule.get('next_execution', 'N/A')
            item_text = f"{schedule['name']} (次回: {next_exec})"
            item = QListWidgetItem(item_text)
            self._active_schedules_list.addItem(item)
    
    def _update_ui_state(self):
        """UI状態を更新"""
        is_busy = self._viewmodel.is_busy
        self._quick_record_btn.setEnabled(not is_busy and self._viewmodel.is_recording_available)
    
    def _on_quick_record_clicked(self):
        """クイック記録ボタンクリック"""
        command = self._viewmodel.get_command('quick_record')
        if command and command.can_execute():
            import asyncio
            asyncio.create_task(command.execute_async())
    
    def _on_view_recordings_clicked(self):
        """記録一覧ボタンクリック"""
        command = self._viewmodel.get_command('navigate_to_recording')
        if command and command.can_execute():
            command.execute()
    
    def _on_view_schedules_clicked(self):
        """スケジュールボタンクリック"""
        command = self._viewmodel.get_command('navigate_to_schedule')
        if command and command.can_execute():
            command.execute()


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    # シグナル定義
    window_closing = Signal()
    
    def __init__(self, main_viewmodel: MainViewModel, parent=None):
        super().__init__(parent)
        self._viewmodel = main_viewmodel
        self._dashboard_widget = None
        self._notification_timer = QTimer()
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_viewmodel()
        
        # 初期化
        import asyncio
        asyncio.create_task(self._initialize_async())
    
    def _setup_ui(self):
        """UIの初期設定"""
        self.setWindowTitle("EZRPA v2.0")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        main_layout = QHBoxLayout(central_widget)
        
        # サイドバー
        self._sidebar = self._create_sidebar()
        main_layout.addWidget(self._sidebar)
        
        # メインコンテンツエリア
        self._content_stack = QStackedWidget()
        main_layout.addWidget(self._content_stack)
        
        # ダッシュボードウィジェット
        self._dashboard_widget = DashboardWidget(self._viewmodel)
        self._content_stack.addWidget(self._dashboard_widget)
        
        # 他のビューウィジェット（後で追加）
        # recording_widget = RecordingWidget(recording_viewmodel)
        # playback_widget = PlaybackWidget(playback_viewmodel)
        # schedule_widget = ScheduleWidget(schedule_viewmodel)
        # settings_widget = SettingsWidget(settings_viewmodel)
        
        # レイアウト比率の設定
        main_layout.setStretch(0, 0)  # サイドバー
        main_layout.setStretch(1, 1)  # コンテンツ
    
    def _create_sidebar(self) -> QWidget:
        """サイドバーを作成"""
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border-right: 1px solid #ccc;
            }
            QPushButton {
                text-align: left;
                padding: 10px;
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ナビゲーションボタン
        self._nav_buttons = {}
        
        nav_items = [
            ("dashboard", "🏠 ダッシュボード"),
            ("recording", "🔴 記録"),
            ("playback", "▶️ 再生"),
            ("schedule", "📅 スケジュール"),
            ("settings", "⚙️ 設定")
        ]
        
        for view_name, button_text in nav_items:
            btn = QPushButton(button_text)
            btn.clicked.connect(lambda checked, view=view_name: self._navigate_to_view(view))
            layout.addWidget(btn)
            self._nav_buttons[view_name] = btn
        
        layout.addStretch()
        
        # サイドバー切り替えボタン
        toggle_btn = QPushButton("<<<")
        toggle_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(toggle_btn)
        
        return sidebar
    
    def _setup_menus(self):
        """メニューバーの設定"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu("ファイル(&F)")
        
        new_action = QAction("新しい記録(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_recording)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self._on_exit)
        file_menu.addAction(exit_action)
        
        # 表示メニュー
        view_menu = menubar.addMenu("表示(&V)")
        
        refresh_action = QAction("更新(&R)", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._on_refresh)
        view_menu.addAction(refresh_action)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu("ヘルプ(&H)")
        
        about_action = QAction("バージョン情報(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """ツールバーの設定"""
        toolbar = self.addToolBar("メイン")
        
        # クイック記録
        quick_record_action = QAction("クイック記録", self)
        quick_record_action.triggered.connect(self._on_quick_record)
        toolbar.addAction(quick_record_action)
        
        toolbar.addSeparator()
        
        # 停止
        stop_action = QAction("全停止", self)
        stop_action.triggered.connect(self._on_stop_all)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        # 更新
        refresh_action = QAction("更新", self)
        refresh_action.triggered.connect(self._on_refresh)
        toolbar.addAction(refresh_action)
    
    def _setup_statusbar(self):
        """ステータスバーの設定"""
        statusbar = self.statusBar()
        
        # ステータスラベル
        self._status_label = QLabel("Ready")
        statusbar.addWidget(self._status_label)
        
        statusbar.addPermanentWidget(QLabel("|"))
        
        # プログレスバー
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        statusbar.addPermanentWidget(self._progress_bar)
        
        statusbar.addPermanentWidget(QLabel("|"))
        
        # バージョン表示
        version_label = QLabel(f"v{self._viewmodel.app_version}")
        statusbar.addPermanentWidget(version_label)
    
    def _connect_viewmodel(self):
        """ViewModelとの接続"""
        self._viewmodel.add_property_changed_handler(self._on_property_changed)
        
        # 通知タイマーの設定
        self._notification_timer.timeout.connect(self._update_notifications)
        self._notification_timer.start(1000)  # 1秒間隔
    
    def _on_property_changed(self, args):
        """プロパティ変更イベントハンドラー"""
        if args.property_name == 'current_view':
            self._update_current_view()
        elif args.property_name == 'app_status':
            self._update_status()
        elif args.property_name == 'is_busy':
            self._update_busy_state()
        elif args.property_name == 'sidebar_expanded':
            self._update_sidebar_visibility()
    
    def _update_current_view(self):
        """現在のビューを更新"""
        current_view = self._viewmodel.current_view
        
        # ナビゲーションボタンの状態を更新
        for view_name, btn in self._nav_buttons.items():
            btn.setStyleSheet("background-color: #d0d0d0;" if view_name == current_view else "")
        
        # コンテンツスタックの切り替え
        if current_view == "dashboard":
            self._content_stack.setCurrentWidget(self._dashboard_widget)
        # 他のビューは後で実装
    
    def _update_status(self):
        """ステータス表示を更新"""
        self._status_label.setText(self._viewmodel.app_status)
    
    def _update_busy_state(self):
        """ビジー状態を更新"""
        is_busy = self._viewmodel.is_busy
        busy_message = self._viewmodel.busy_message
        
        if is_busy:
            self._progress_bar.setVisible(True)
            self._status_label.setText(busy_message)
        else:
            self._progress_bar.setVisible(False)
            self._status_label.setText(self._viewmodel.app_status)
    
    def _update_sidebar_visibility(self):
        """サイドバーの表示状態を更新"""
        self._sidebar.setVisible(self._viewmodel.sidebar_expanded)
    
    def _update_notifications(self):
        """通知を更新"""
        notifications = self._viewmodel.notifications
        
        # 最新の通知をステータスバーに表示（簡易実装）
        if notifications:
            latest = notifications[-1]
            if not latest.is_persistent:
                # 一定時間後に通知を削除
                elapsed = (datetime.now(timezone.utc) - latest.timestamp).total_seconds() * 1000
                if elapsed > latest.duration_ms:
                    self._viewmodel.remove_notification(latest.message_id)
    
    def _navigate_to_view(self, view_name: str):
        """ビューに遷移"""
        command = self._viewmodel.get_command(f'navigate_to_{view_name}')
        if command and command.can_execute():
            command.execute()
    
    def _toggle_sidebar(self):
        """サイドバーの表示切り替え"""
        command = self._viewmodel.get_command('toggle_sidebar')
        if command and command.can_execute():
            command.execute()
    
    # メニューアクションハンドラー
    def _on_new_recording(self):
        """新しい記録メニュー"""
        self._navigate_to_view('recording')
    
    def _on_quick_record(self):
        """クイック記録"""
        command = self._viewmodel.get_command('quick_record')
        if command and command.can_execute():
            import asyncio
            asyncio.create_task(command.execute_async())
    
    def _on_stop_all(self):
        """全停止"""
        command = self._viewmodel.get_command('stop_all_operations')
        if command and command.can_execute():
            import asyncio
            asyncio.create_task(command.execute_async())
    
    def _on_refresh(self):
        """更新"""
        command = self._viewmodel.get_command('refresh')
        if command and command.can_execute():
            import asyncio
            asyncio.create_task(command.execute_async())
    
    def _on_about(self):
        """バージョン情報"""
        command = self._viewmodel.get_command('show_about')
        if command and command.can_execute():
            command.execute()
    
    def _on_exit(self):
        """終了"""
        command = self._viewmodel.get_command('exit_application')
        if command and command.can_execute():
            import asyncio
            asyncio.create_task(command.execute_async())
    
    async def _initialize_async(self):
        """非同期初期化"""
        await self._viewmodel.initialize_async()
    
    def closeEvent(self, event):
        """ウィンドウクローズイベント"""
        self.window_closing.emit()
        
        # ViewModelのリソースを破棄
        self._viewmodel.dispose()
        
        event.accept()