# -*- coding: utf-8 -*-
"""
Domain Layer - ドメイン層

ビジネスロジックとドメインルールを実装するレイヤーです。
外部依存を持たない純粋なビジネスロジックの実装を提供します。
"""

# エンティティ
from .entities.recording import Recording, RecordingMetadata, PlaybackSettings
from .entities.action import (
    ActionBase, KeyboardAction, MouseAction, WindowAction, WaitAction,
    ActionFactory, ActionTypes
)
from .entities.schedule import (
    Schedule, TriggerCondition, RepeatCondition, ExecutionResult,
    TimeCondition, WeekDay, RepeatUnit, ScheduleFactory
)

# 値オブジェクト
from .value_objects import (
    ActionType, RecordingStatus, PlaybackStatus, ScheduleStatus, TriggerType,
    Coordinate, Rectangle, Duration, 
    KeyInput, MouseInput, MouseButton,
    WindowInfo, FileInfo,
    ValidationResult,
    CommonDurations, CommonKeys
)

# リポジトリインターフェース
from .repositories.recording_repository import IRecordingRepository
from .repositories.schedule_repository import IScheduleRepository
from .repositories.settings_repository import ISettingsRepository

__all__ = [
    'Recording', 'RecordingMetadata', 'PlaybackSettings',
    'ActionBase', 'KeyboardAction', 'MouseAction', 'WindowAction', 'WaitAction',
    'ActionFactory', 'ActionTypes',
    'Schedule', 'TriggerCondition', 'RepeatCondition', 'ExecutionResult',
    'TimeCondition', 'WeekDay', 'RepeatUnit', 'ScheduleFactory',
    'ActionType', 'RecordingStatus', 'PlaybackStatus', 'ScheduleStatus', 'TriggerType',
    'Coordinate', 'Rectangle', 'Duration',
    'KeyInput', 'MouseInput', 'MouseButton',
    'WindowInfo', 'FileInfo',
    'ValidationResult',
    'CommonDurations', 'CommonKeys',
    'IRecordingRepository', 'IScheduleRepository', 'ISettingsRepository',
]