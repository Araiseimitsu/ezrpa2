"""
EZRPA v2.0 ドメイン層デモ

Phase 2で実装したドメイン層の動作確認を行います。
エンティティ、値オブジェクト、ビジネスルールの実装を検証します。
"""

import sys
import os
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_value_objects():
    """値オブジェクトのデモ"""
    print("=== 値オブジェクト デモ ===")
    
    from src.domain import Coordinate, Duration, KeyInput, MouseInput, MouseButton
    from src.shared.constants import WindowsKeys
    
    # 座標オブジェクト
    pos = Coordinate(100, 200)
    scaled_pos = pos.scale(1.5)
    offset_pos = pos.offset(10, 20)
    
    print(f"✓ 基本座標: ({pos.x}, {pos.y})")
    print(f"✓ スケール後: ({scaled_pos.x}, {scaled_pos.y})")
    print(f"✓ オフセット後: ({offset_pos.x}, {offset_pos.y})")
    print(f"✓ 距離計算: {pos.distance_to(scaled_pos):.2f}")
    
    # 時間間隔オブジェクト
    duration = Duration.from_seconds(2.5)
    print(f"✓ 時間間隔: {duration.milliseconds}ms ({duration.seconds}秒)")
    
    # キー入力オブジェクト
    key_a = KeyInput.from_char('A')
    ctrl_c = KeyInput.ctrl_combination(ord('C'))
    
    print(f"✓ キー入力A: {key_a.to_string()}")
    print(f"✓ Ctrl+C: {ctrl_c.to_string()}")
    
    # マウス入力オブジェクト
    mouse_click = MouseInput(MouseButton.LEFT, pos)
    print(f"✓ マウスクリック: {mouse_click.button.name} at ({mouse_click.position.x}, {mouse_click.position.y})")
    
    print()


def demo_actions():
    """アクションエンティティのデモ"""
    print("=== アクション エンティティ デモ ===")
    
    from src.domain import (
        ActionFactory, Coordinate, Duration, MouseButton,
        KeyInput, CommonKeys, CommonDurations
    )
    from src.shared.constants import WindowsKeys
    
    # キーボードアクション
    text_action = ActionFactory.create_text_input("こんにちは、世界！")
    key_action = ActionFactory.create_key_press(CommonKeys.ENTER)
    
    print(f"✓ テキスト入力: {text_action.text}")
    print(f"✓ キー押下: {key_action.key_input.to_string()}")
    print(f"✓ IME必要: {text_action.metadata.get('requires_ime', False)}")
    
    # マウスアクション
    click_action = ActionFactory.create_mouse_click(
        Coordinate(300, 400), 
        MouseButton.LEFT
    )
    
    print(f"✓ マウスクリック: ({click_action.mouse_input.position.x}, {click_action.mouse_input.position.y})")
    
    # 待機アクション
    wait_action = ActionFactory.create_wait(Duration.from_seconds(1))
    print(f"✓ 待機: {wait_action.wait_duration.seconds}秒")
    
    # アクションのバリデーション
    validation = text_action.validate()
    print(f"✓ バリデーション: 有効={validation.is_valid}, エラー数={len(validation.errors)}")
    
    # シリアライゼーション
    action_dict = text_action.to_dict()
    restored_action = text_action.__class__.from_dict(action_dict)
    print(f"✓ シリアライゼーション: {restored_action.text == text_action.text}")
    
    print()


def demo_recording():
    """レコーディングエンティティのデモ"""
    print("=== レコーディング エンティティ デモ ===")
    
    from src.domain import (
        Recording, ActionFactory, Coordinate, Duration,
        RecordingStatus, CommonKeys
    )
    
    # レコーディング作成
    recording = Recording(name="デモ記録")
    print(f"✓ 作成: {recording.name} (ID: {recording.recording_id[:8]}...)")
    print(f"✓ 初期状態: {recording.status.value}")
    
    # 記録開始
    start_result = recording.start_recording()
    print(f"✓ 記録開始: {start_result.is_success()}")
    print(f"✓ 記録状態: {recording.status.value}")
    
    # アクション追加
    actions = [
        ActionFactory.create_text_input("サンプルテキスト"),
        ActionFactory.create_key_press(CommonKeys.ENTER),
        ActionFactory.create_mouse_click(Coordinate(150, 250)),
        ActionFactory.create_wait(Duration.from_seconds(0.5))
    ]
    
    for action in actions:
        result = recording.add_action(action)
        if result.is_success():
            print(f"  ✓ アクション追加: {action.action_type.value}")
        else:
            print(f"  ❌ 追加失敗: {result.error}")
    
    print(f"✓ 総アクション数: {recording.action_count}")
    
    # 記録完了
    complete_result = recording.complete_recording()
    print(f"✓ 記録完了: {complete_result.is_success()}")
    print(f"✓ 最終状態: {recording.status.value}")
    print(f"✓ 推定実行時間: {recording.get_estimated_duration().seconds}秒")
    
    # バリデーション
    validation = recording.validate()
    print(f"✓ 全体バリデーション: 有効={validation.is_valid}")
    if validation.warnings:
        print(f"  警告: {len(validation.warnings)}件")
    
    # クローン
    cloned = recording.clone("デモ記録のコピー")
    print(f"✓ クローン作成: {cloned.name} (元と異なるID: {cloned.recording_id != recording.recording_id})")
    
    print()


def demo_schedule():
    """スケジュールエンティティのデモ"""
    print("=== スケジュール エンティティ デモ ===")
    
    from src.domain import (
        ScheduleFactory, TimeCondition, WeekDay, Duration,
        TriggerType, ScheduleStatus
    )
    
    # 毎日実行スケジュール
    daily_schedule = ScheduleFactory.create_daily_schedule(
        recording_id="demo_recording_id",
        execution_time=TimeCondition(9, 30, 0),
        name="毎朝9:30実行"
    )
    
    print(f"✓ 毎日スケジュール: {daily_schedule.name}")
    print(f"✓ トリガータイプ: {daily_schedule.trigger_condition.trigger_type.value}")
    print(f"✓ 実行時刻: {daily_schedule.trigger_condition.execution_time}")
    
    # 週間スケジュール
    weekdays = {WeekDay.MONDAY, WeekDay.WEDNESDAY, WeekDay.FRIDAY}
    weekly_schedule = ScheduleFactory.create_weekly_schedule(
        recording_id="demo_recording_id",
        execution_time=TimeCondition(14, 0, 0),
        weekdays=weekdays,
        name="月水金14:00実行"
    )
    
    print(f"✓ 週間スケジュール: {weekly_schedule.name}")
    print(f"✓ 対象曜日数: {len(weekly_schedule.trigger_condition.weekdays)}")
    
    # ホットキースケジュール
    hotkey_schedule = ScheduleFactory.create_hotkey_schedule(
        recording_id="demo_recording_id",
        hotkey="Ctrl+Alt+F1",
        name="ホットキー実行"
    )
    
    print(f"✓ ホットキー: {hotkey_schedule.trigger_condition.hotkey_combination}")
    
    # スケジュール有効化
    activation_result = daily_schedule.activate()
    print(f"✓ 有効化: {activation_result.is_success()}")
    print(f"✓ 状態: {daily_schedule.status.value}")
    
    # 実行開始シミュレーション
    if daily_schedule.should_execute_now():
        print("✓ 実行タイミング到達")
    else:
        print(f"✓ 次回実行予定: {daily_schedule.next_execution_time}")
    
    # バリデーション
    validation = daily_schedule.validate()
    print(f"✓ スケジュールバリデーション: 有効={validation.is_valid}")
    
    print()


def demo_business_rules():
    """ビジネスルールのデモ"""
    print("=== ビジネスルール デモ ===")
    
    from src.domain import Recording, ActionFactory, Coordinate
    from src.shared.constants import ValidationConstants
    
    # 制限テスト
    recording = Recording(name="制限テスト")
    recording.start_recording()
    
    # アクション数制限のテスト
    print(f"✓ 最大アクション数: {ValidationConstants.MAX_ACTIONS_PER_RECORDING}")
    
    # 無効なアクション追加の試行
    invalid_action = ActionFactory.create_mouse_click(Coordinate(-1, -1))
    validation = invalid_action.validate()
    
    if not validation.is_valid:
        print(f"✓ 無効アクション検出: {validation.errors[0]}")
    
    # 名前長制限テスト
    long_name = "x" * (ValidationConstants.MAX_RECORDING_NAME_LENGTH + 1)
    long_recording = Recording(name=long_name)
    validation = long_recording.validate()
    
    if not validation.is_valid:
        print(f"✓ 名前長制限検出: バリデーションエラー")
    
    # 状態変遷ルールテスト
    recording.complete_recording()
    
    # 完了後のアクション追加は失敗する
    action = ActionFactory.create_text_input("追加テスト")
    result = recording.add_action(action)
    
    if result.is_failure():
        print(f"✓ 状態変遷ルール: {result.error[:30]}...")
    
    print()


def demo_integration():
    """統合デモ - エンティティ間の連携"""
    print("=== 統合デモ ===")
    
    from src.domain import (
        Recording, Schedule, ActionFactory, 
        TimeCondition, Coordinate, CommonKeys
    )
    
    # 完全なワークフロー
    print("完全なRPAワークフローの作成:")
    
    # 1. レコーディング作成
    recording = Recording(name="統合デモワークフロー")
    recording.start_recording()
    
    # 2. 複数アクションの追加
    workflow_actions = [
        ActionFactory.create_text_input("統合テスト実行中"),
        ActionFactory.create_key_press(CommonKeys.TAB),
        ActionFactory.create_mouse_click(Coordinate(200, 300)),
        ActionFactory.create_key_press(CommonKeys.CTRL_S),
    ]
    
    for action in workflow_actions:
        recording.add_action(action)
    
    recording.complete_recording()
    print(f"  ✓ レコーディング完成: {recording.action_count}アクション")
    
    # 3. スケジュール作成
    from src.domain import ScheduleFactory
    schedule = ScheduleFactory.create_daily_schedule(
        recording_id=recording.recording_id,
        execution_time=TimeCondition(10, 0, 0),
        name="毎日10時実行"
    )
    
    schedule.activate()
    print(f"  ✓ スケジュール作成: {schedule.name}")
    
    # 4. 実行可能性チェック
    print(f"  ✓ 実行可能: {recording.can_be_executed}")
    print(f"  ✓ 編集可能: {recording.can_be_edited}")
    print(f"  ✓ スケジュール有効: {schedule.is_active}")
    
    # 5. メタデータと統計
    recording.metadata.author = "EZRPA Demo"
    recording.metadata.category = "demo"
    recording.metadata.tags = ["統合テスト", "デモ"]
    
    print(f"  ✓ 作成者: {recording.metadata.author}")
    print(f"  ✓ カテゴリ: {recording.metadata.category}")
    print(f"  ✓ タグ数: {len(recording.metadata.tags)}")
    
    print()


def main():
    """メインデモ実行"""
    print("🚀 EZRPA v2.0 ドメイン層デモンストレーション")
    print("=" * 50)
    print()
    
    try:
        # 各機能のデモ実行
        demo_value_objects()
        demo_actions()
        demo_recording()
        demo_schedule()
        demo_business_rules()
        demo_integration()
        
        print("🎉 すべてのドメイン層デモが正常に完了しました！")
        print()
        print("Phase 2 ドメイン層実装完了:")
        print("✅ 値オブジェクト（座標、時間、入力等）")
        print("✅ Actionエンティティ（キーボード・マウス・ウィンドウ・待機）")
        print("✅ Recordingエンティティ（集約ルート）")
        print("✅ Scheduleエンティティ（自動実行管理）")
        print("✅ ビジネスルール（バリデーション・制約）")
        print("✅ リポジトリインターフェース（永続化抽象化）")
        print("✅ Windows環境対応（IME・DPI・API統合）")
        print()
        print("次のフェーズでインフラストラクチャ層の実装を開始できます。")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())