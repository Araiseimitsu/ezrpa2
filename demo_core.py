"""
EZRPA v2.0 コア機能デモ

基盤構築Phase 1の動作確認を行います。
"""

import time
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_container():
    """依存性注入コンテナのデモ"""
    print("=== 依存性注入コンテナ デモ ===")
    
    from src.core import get_container
    
    container = get_container()
    
    # テストサービス定義
    class MessageService:
        def __init__(self, message="Hello from DI Container!"):
            self.message = message
        
        def get_message(self):
            return self.message
    
    class CalculatorService:
        def add(self, a, b):
            return a + b
    
    # サービス登録
    container.register(MessageService, lambda: MessageService("Windows環境対応メッセージ"))
    container.register(CalculatorService, lambda: CalculatorService(), singleton=True)
    
    # サービス取得・使用
    message_service = container.get(MessageService)
    calc_service1 = container.get(CalculatorService)
    calc_service2 = container.get(CalculatorService)
    
    print(f"✓ メッセージサービス: {message_service.get_message()}")
    print(f"✓ 計算サービス (5 + 3): {calc_service1.add(5, 3)}")
    print(f"✓ シングルトン確認: {calc_service1 is calc_service2}")
    print()


def demo_result_pattern():
    """Resultパターンのデモ"""
    print("=== Resultパターン デモ ===")
    
    from src.core.result import Ok, Err, try_catch
    
    # 成功ケース
    success_result = Ok("処理成功")
    print(f"✓ 成功判定: {success_result.is_success()}")
    print(f"✓ 値取得: {success_result.unwrap()}")
    
    # 失敗ケース
    error_result = Err("エラーが発生しました")
    print(f"✓ 失敗判定: {error_result.is_failure()}")
    print(f"✓ デフォルト値: {error_result.unwrap_or('デフォルト値')}")
    
    # チェーン操作
    chained = success_result.map(lambda x: f"変換後: {x}")
    print(f"✓ map操作: {chained.unwrap()}")
    
    # 例外キャッチ
    def risky_operation():
        if True:  # わざとエラーを発生
            raise ValueError("テストエラー")
        return "成功"
    
    result = try_catch(risky_operation, "demo_error")
    print(f"✓ 例外キャッチ: {result.is_failure()}")
    print()


def demo_event_bus():
    """イベントバスのデモ"""
    print("=== イベントバス デモ ===")
    
    from src.core import get_event_bus, RecordingStartedEvent, EventPriority
    
    event_bus = get_event_bus()
    received_events = []
    
    # イベントハンドラー定義
    def recording_handler(event):
        received_events.append(f"記録開始: {event.recording_name}")
        print(f"  📡 イベント受信: {event.recording_name}")
    
    def high_priority_handler(event):
        received_events.append("高優先度処理")
        print(f"  🔥 高優先度処理実行")
    
    # ハンドラー登録
    event_bus.subscribe(RecordingStartedEvent, recording_handler)
    event_bus.subscribe(RecordingStartedEvent, high_priority_handler, 
                       priority=EventPriority.HIGH)
    
    # イベント発行
    test_event = RecordingStartedEvent(
        recording_id="demo_001",
        recording_name="デモ記録"
    )
    
    result = event_bus.publish(test_event)
    print(f"✓ イベント発行成功: {result.is_success()}")
    
    # 処理完了待機
    time.sleep(0.2)
    
    print(f"✓ 受信イベント数: {len(received_events)}")
    print()


def demo_thread_manager():
    """スレッドマネージャーのデモ"""
    print("=== スレッドマネージャー デモ ===")
    
    from src.core import get_thread_manager, ThreadPriority
    
    thread_manager = get_thread_manager()
    
    # バックグラウンドタスク定義
    def cpu_intensive_task():
        result = 0
        for i in range(1000000):
            result += i
        return f"計算完了: {result}"
    
    def io_task():
        time.sleep(0.1)  # I/O待機をシミュレート
        return "I/O処理完了"
    
    print("✓ バックグラウンドタスク開始...")
    
    # 並列実行
    future1 = thread_manager.run_in_background(cpu_intensive_task)
    future2 = thread_manager.run_in_background(io_task)
    
    # 結果取得
    result1 = future1.result(timeout=5.0)
    result2 = future2.result(timeout=5.0)
    
    print(f"✓ CPU集約タスク: {result1[:20]}...")
    print(f"✓ I/Oタスク: {result2}")
    
    # コールバック付き実行
    callback_results = []
    
    def callback_task():
        return "コールバックテスト"
    
    def success_callback(result):
        callback_results.append(result)
        print(f"  📞 コールバック実行: {result}")
    
    thread_id = thread_manager.run_with_callback(
        callback_task,
        callback=success_callback
    )
    
    time.sleep(0.2)  # コールバック実行待機
    
    print(f"✓ コールバック結果: {len(callback_results) > 0}")
    print()


def demo_integration():
    """統合デモ - 各コンポーネントを組み合わせた使用例"""
    print("=== 統合デモ ===")
    
    from src.core import (
        get_container, get_event_bus, get_thread_manager,
        RecordingStartedEvent, Ok, Err
    )
    
    # 各コンポーネント取得
    container = get_container()
    event_bus = get_event_bus()
    thread_manager = get_thread_manager()
    
    integration_log = []
    
    # モックサービス定義
    class MockRecordingService:
        def __init__(self):
            self.recordings = {}
        
        def start_recording(self, name):
            recording_id = f"rec_{len(self.recordings) + 1}"
            self.recordings[recording_id] = {"name": name, "status": "recording"}
            
            # イベント発行
            event = RecordingStartedEvent(
                recording_id=recording_id,
                recording_name=name
            )
            event_bus.publish(event)
            
            return Ok(recording_id)
    
    # イベントハンドラー
    def recording_started_handler(event):
        integration_log.append(f"記録開始通知: {event.recording_name}")
    
    # セットアップ
    container.register(MockRecordingService, lambda: MockRecordingService(), singleton=True)
    event_bus.subscribe(RecordingStartedEvent, recording_started_handler)
    
    # バックグラウンドで記録開始
    def start_recording_task():
        service = container.get(MockRecordingService)
        return service.start_recording("統合デモ記録")
    
    future = thread_manager.run_in_background(start_recording_task)
    result = future.result(timeout=2.0)
    
    time.sleep(0.1)  # イベント処理待機
    
    print(f"✓ 記録開始結果: {result.is_success()}")
    print(f"✓ 記録ID: {result.unwrap()}")
    print(f"✓ イベント処理: {len(integration_log) > 0}")
    print(f"✓ ログ内容: {integration_log[0] if integration_log else 'なし'}")
    print()


def main():
    """メインデモ実行"""
    print("🚀 EZRPA v2.0 コア機能デモンストレーション")
    print("=" * 50)
    print()
    
    try:
        # 各機能のデモ実行
        demo_container()
        demo_result_pattern()
        demo_event_bus()
        demo_thread_manager()
        demo_integration()
        
        print("🎉 すべてのデモが正常に完了しました！")
        print()
        print("Phase 1 基盤構築完了:")
        print("✅ 依存性注入コンテナ")
        print("✅ Resultパターン")
        print("✅ イベントバス")
        print("✅ スレッドマネージャー")
        print("✅ Windows環境対応")
        print()
        print("次のフェーズでドメイン層の実装を開始できます。")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())