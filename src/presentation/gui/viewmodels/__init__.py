# -*- coding: utf-8 -*-
"""
ViewModels - ビューモデルクラス群

MVVMパターンのViewModelクラス群のエントリーポイントです。
各ViewModelはアプリケーション層との疎結合な連携を実現します。
"""

from .base_viewmodel import (
    BaseViewModel,
    Command,
    AsyncCommand,
    ViewModelError,
    NotificationMessage,
    PropertyChangedEventArgs
)

from .main_viewmodel import MainViewModel
from .recording_viewmodel import RecordingViewModel

__all__ = [
    # Base Components
    "BaseViewModel",
    "Command",
    "AsyncCommand",
    "ViewModelError",
    "NotificationMessage", 
    "PropertyChangedEventArgs",
    
    # ViewModels
    "MainViewModel",
    "RecordingViewModel"
]