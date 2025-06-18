# -*- coding: utf-8 -*-
"""
Application Layer - アプリケーション層

ユースケース、DTO、アプリケーションサービス、イベントハンドラーの
エントリーポイントモジュールです。
"""

# ユースケース
from .use_cases.recording_use_cases import (
    StartRecordingUseCase,
    StopRecordingUseCase,
    AddActionUseCase,
    GetRecordingUseCase,
    GetAllRecordingsUseCase,
    DeleteRecordingUseCase,
    SearchRecordingsUseCase,
    GetRecordingsByStatusUseCase
)

from .use_cases.playback_use_cases import (
    PlayRecordingUseCase,
    PausePlaybackUseCase,
    ResumePlaybackUseCase,
    StopPlaybackUseCase,
    GetPlaybackStatusUseCase,
    ValidateRecordingUseCase
)

from .use_cases.schedule_use_cases import (
    CreateScheduleUseCase,
    UpdateScheduleUseCase,
    DeleteScheduleUseCase,
    GetScheduleUseCase,
    GetAllSchedulesUseCase,
    ActivateScheduleUseCase,
    DeactivateScheduleUseCase,
    GetScheduleExecutionHistoryUseCase,
    GetNextExecutionTimeUseCase
)

# DTO
from .dto.recording_dto import (
    RecordingDTO,
    CreateRecordingDTO,
    UpdateRecordingDTO,
    RecordingListDTO,
    RecordingSearchDTO,
    RecordingStatsDTO,
    RecordingExportDTO
)

from .dto.playback_dto import (
    PlaybackConfigDTO,
    PlaybackStatusDTO,
    PlaybackResultDTO,
    PlaybackHistoryDTO,
    PlaybackValidationDTO,
    PlaybackQueueDTO
)

from .dto.schedule_dto import (
    ScheduleDTO,
    CreateScheduleDTO,
    UpdateScheduleDTO,
    ScheduleListDTO,
    TriggerConditionDTO,
    RepeatConditionDTO,
    ScheduleStatsDTO,
    ExecutionResultDTO,
    ScheduleExecutionHistoryDTO,
    ScheduleValidationDTO
)

# アプリケーションサービス
from .services.recording_application_service import RecordingApplicationService
from .services.playback_application_service import PlaybackApplicationService
from .services.schedule_application_service import ScheduleApplicationService

# イベントハンドラー
from .handlers.recording_event_handler import RecordingEventHandler
from .handlers.playback_event_handler import PlaybackEventHandler
from .handlers.schedule_event_handler import ScheduleEventHandler

__all__ = [
    # ユースケース
    "StartRecordingUseCase",
    "StopRecordingUseCase", 
    "AddActionUseCase",
    "GetRecordingUseCase",
    "GetAllRecordingsUseCase",
    "DeleteRecordingUseCase",
    "SearchRecordingsUseCase",
    "GetRecordingsByStatusUseCase",
    "PlayRecordingUseCase",
    "PausePlaybackUseCase",
    "ResumePlaybackUseCase", 
    "StopPlaybackUseCase",
    "GetPlaybackStatusUseCase",
    "ValidateRecordingUseCase",
    "CreateScheduleUseCase",
    "UpdateScheduleUseCase",
    "DeleteScheduleUseCase",
    "GetScheduleUseCase",
    "GetAllSchedulesUseCase",
    "ActivateScheduleUseCase",
    "DeactivateScheduleUseCase",
    "GetScheduleExecutionHistoryUseCase",
    "GetNextExecutionTimeUseCase",
    
    # DTO
    "RecordingDTO",
    "CreateRecordingDTO",
    "UpdateRecordingDTO",
    "RecordingListDTO", 
    "RecordingSearchDTO",
    "RecordingStatsDTO",
    "RecordingExportDTO",
    "PlaybackConfigDTO",
    "PlaybackStatusDTO",
    "PlaybackResultDTO",
    "PlaybackHistoryDTO",
    "PlaybackValidationDTO",
    "PlaybackQueueDTO",
    "ScheduleDTO",
    "CreateScheduleDTO",
    "UpdateScheduleDTO",
    "ScheduleListDTO",
    "TriggerConditionDTO",
    "RepeatConditionDTO",
    "ScheduleStatsDTO",
    "ExecutionResultDTO",
    "ScheduleExecutionHistoryDTO",
    "ScheduleValidationDTO",
    
    # アプリケーションサービス
    "RecordingApplicationService",
    "PlaybackApplicationService",
    "ScheduleApplicationService",
    
    # イベントハンドラー
    "RecordingEventHandler",
    "PlaybackEventHandler",
    "ScheduleEventHandler"
]