# -*- coding: utf-8 -*-
"""
Use Cases - ユースケース

ビジネスルールを実装する具体的なユースケースクラスの
エントリーポイントモジュールです。
"""

from .recording_use_cases import (
    StartRecordingUseCase,
    StopRecordingUseCase,
    AddActionUseCase,
    GetRecordingUseCase,
    GetAllRecordingsUseCase,
    DeleteRecordingUseCase,
    UpdateRecordingUseCase,
    SearchRecordingsUseCase
)

from .playback_use_cases import (
    PlayRecordingUseCase,
    PausePlaybackUseCase,
    ResumePlaybackUseCase,
    StopPlaybackUseCase,
    GetPlaybackStatusUseCase,
    ValidateRecordingUseCase
)

from .schedule_use_cases import (
    CreateScheduleUseCase,
    UpdateScheduleUseCase,
    DeleteScheduleUseCase,
    GetScheduleUseCase,
    GetAllSchedulesUseCase,
    ActivateScheduleUseCase,
    DeactivateScheduleUseCase,
    GetScheduleExecutionHistoryUseCase,
    GetNextExecutionTimeUseCase,
    BulkScheduleOperationUseCase
)

__all__ = [
    # Recording Use Cases
    "StartRecordingUseCase",
    "StopRecordingUseCase",
    "AddActionUseCase", 
    "GetRecordingUseCase",
    "GetAllRecordingsUseCase",
    "DeleteRecordingUseCase",
    "UpdateRecordingUseCase",
    "SearchRecordingsUseCase",
    
    # Playback Use Cases
    "PlayRecordingUseCase",
    "PausePlaybackUseCase",
    "ResumePlaybackUseCase",
    "StopPlaybackUseCase",
    "GetPlaybackStatusUseCase",
    "ValidateRecordingUseCase",
    
    # Schedule Use Cases
    "CreateScheduleUseCase",
    "UpdateScheduleUseCase",
    "DeleteScheduleUseCase",
    "GetScheduleUseCase",
    "GetAllSchedulesUseCase",
    "ActivateScheduleUseCase",
    "DeactivateScheduleUseCase",
    "GetScheduleExecutionHistoryUseCase",
    "GetNextExecutionTimeUseCase",
    "BulkScheduleOperationUseCase"
]