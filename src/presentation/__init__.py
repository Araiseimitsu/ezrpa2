# -*- coding: utf-8 -*-
"""
Presentation Layer - プレゼンテーション層

MVVMパターンによるユーザーインターフェースとViewModelクラス群の
エントリーポイントモジュールです。
"""

from .gui.viewmodels.base_viewmodel import (
    BaseViewModel,
    Command,
    AsyncCommand,
    ViewModelError,
    NotificationMessage,
    PropertyChangedEventArgs
)

from .gui.viewmodels.main_viewmodel import MainViewModel
from .gui.viewmodels.recording_viewmodel import RecordingViewModel

from .gui.views.main_window import MainWindow, DashboardWidget

__all__ = [
    # Base ViewModel Components
    "BaseViewModel",
    "Command", 
    "AsyncCommand",
    "ViewModelError",
    "NotificationMessage",
    "PropertyChangedEventArgs",
    
    # ViewModels
    "MainViewModel",
    "RecordingViewModel",
    
    # Views
    "MainWindow",
    "DashboardWidget"
]