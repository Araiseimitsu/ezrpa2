"""
コア機能統合テスト

クリーンアーキテクチャ基盤の動作確認を行います。
"""

import time
import threading
from typing import Any

import pytest

# Core機能のインポート
from src.core import (
    get_container, get_event_bus, get_thread_manager,
    Result, Ok, Err, 
    RecordingStartedEvent, EventPriority,
    ThreadPriority
)


class TestCoreIntegration:
    """コア機能統合テスト"""
    
    def test_container_basic_functionality(self):
        """依存性注入コンテナの基本機能テスト"""
        container = get_container()
        
        # サービス登録
        class TestService:
            def get_message(self):
                return "Hello from TestService"
        
        container.register(TestService, lambda: TestService())
        
        # サービス取得
        service = container.get(TestService)
        assert service.get_message() == "Hello from TestService"
        
        # 別インスタンスが返されることを確認（transient）
        service2 = container.get(TestService)
        assert service is not service2
    
    def test_container_singleton(self):
        """シングルトンサービステスト"""
        container = get_container()
        
        class SingletonService:
            def __init__(self):
                self.value = time.time()
        
        container.register(SingletonService, lambda: SingletonService(), singleton=True)
        
        # 同じインスタンスが返されることを確認
        service1 = container.get(SingletonService)
        service2 = container.get(SingletonService)
        assert service1 is service2
        assert service1.value == service2.value
    
    def test_result_pattern_success(self):
        """Resultパターン成功ケーステスト"""
        result = Ok("成功値")
        
        assert result.is_success()
        assert not result.is_failure()
        assert result.unwrap() == "成功値"
        assert result.unwrap_or("デフォルト") == "成功値"
        
        # map操作
        mapped = result.map(lambda x: f"変換: {x}")
        assert mapped.unwrap() == "変換: 成功値"
    
    def test_result_pattern_failure(self):
        """Resultパターン失敗ケーステスト"""
        result = Err("エラーメッセージ")
        
        assert not result.is_success()
        assert result.is_failure()
        assert result.unwrap_or("デフォルト") == "デフォルト"
        
        # unwrapは例外を発生させる
        with pytest.raises(RuntimeError):
            result.unwrap()
    
    def test_event_bus_basic(self):
        """イベントバス基本機能テスト"""
        event_bus = get_event_bus()
        received_events = []
        
        def event_handler(event):
            received_events.append(event)
        
        # イベント購読
        subscription_id = event_bus.subscribe(RecordingStartedEvent, event_handler)
        
        # イベント発行
        test_event = RecordingStartedEvent(
            recording_id="test_123",
            recording_name="テスト記録"
        )
        
        result = event_bus.publish(test_event)
        assert result.is_success()
        
        # イベント処理の完了を待機
        time.sleep(0.1)
        
        # イベントが受信されたことを確認
        assert len(received_events) == 1
        assert received_events[0].recording_id == "test_123"
        assert received_events[0].recording_name == "テスト記録"
        
        # 購読解除
        assert event_bus.unsubscribe(subscription_id)
    
    def test_event_bus_priority(self):
        """イベントバス優先度テスト"""
        event_bus = get_event_bus()
        execution_order = []
        
        def high_priority_handler(event):
            execution_order.append("high")
        
        def low_priority_handler(event):
            execution_order.append("low")
        
        # 優先度の異なるハンドラーを登録
        event_bus.subscribe(RecordingStartedEvent, low_priority_handler, 
                          priority=EventPriority.LOW)
        event_bus.subscribe(RecordingStartedEvent, high_priority_handler, 
                          priority=EventPriority.HIGH)
        
        # イベント発行
        test_event = RecordingStartedEvent()
        event_bus.publish(test_event)
        
        # 処理完了を待機
        time.sleep(0.1)
        
        # 高優先度ハンドラーが先に実行されることを確認
        assert execution_order == ["high", "low"]
    
    def test_thread_manager_basic(self):
        """スレッドマネージャー基本機能テスト"""
        thread_manager = get_thread_manager()
        
        def test_task():
            time.sleep(0.1)
            return "タスク完了"
        
        # バックグラウンドタスク実行
        future = thread_manager.run_in_background(test_task)
        result = future.result(timeout=1.0)
        
        assert result == "タスク完了"
    
    def test_thread_manager_with_callback(self):
        """コールバック付きスレッド実行テスト"""
        thread_manager = get_thread_manager()
        results = []
        
        def test_task():
            return "コールバックテスト"
        
        def success_callback(result):
            results.append(f"成功: {result}")
        
        # コールバック付き実行
        thread_id = thread_manager.run_with_callback(
            test_task, 
            callback=success_callback
        )
        
        # スレッド完了を待機
        time.sleep(0.2)
        
        # 結果確認
        status = thread_manager.get_thread_status(thread_id)
        assert status is not None
        assert status.result == "コールバックテスト"
    
    def test_integration_workflow(self):
        """統合ワークフローテスト"""
        # 各コンポーネントを組み合わせた実際の使用例
        container = get_container()
        event_bus = get_event_bus()
        thread_manager = get_thread_manager()
        
        workflow_events = []
        
        # ワークフロー監視ハンドラー
        def workflow_handler(event):
            workflow_events.append(type(event).__name__)
        
        event_bus.subscribe(RecordingStartedEvent, workflow_handler)
        
        # サービス定義
        class MockRecordingService:
            def start_recording(self, name: str) -> Result[str, str]:
                # イベント発行
                event = RecordingStartedEvent(
                    recording_id="workflow_test",
                    recording_name=name
                )
                event_bus.publish(event)
                return Ok("workflow_test")
        
        # サービス登録
        container.register(MockRecordingService, lambda: MockRecordingService())
        
        # バックグラウンドでサービス実行
        def recording_task():
            service = container.get(MockRecordingService)
            return service.start_recording("統合テスト")
        
        future = thread_manager.run_in_background(recording_task)
        result = future.result(timeout=1.0)
        
        # 結果確認
        assert result.is_success()
        assert result.unwrap() == "workflow_test"
        
        # イベント処理完了を待機
        time.sleep(0.1)
        
        # イベントが発行されたことを確認
        assert "RecordingStartedEvent" in workflow_events
    
    def test_error_handling_integration(self):
        """エラーハンドリング統合テスト"""
        thread_manager = get_thread_manager()
        
        def failing_task():
            raise ValueError("テストエラー")
        
        # エラーが適切にキャッチされることを確認
        future = thread_manager.run_in_background(failing_task)
        
        with pytest.raises(ValueError):
            future.result(timeout=1.0)
    
    @pytest.fixture(autouse=True)
    def cleanup(self):
        """テスト後のクリーンアップ"""
        yield
        
        # イベントバスの購読をクリア
        event_bus = get_event_bus()
        event_bus.clear_subscriptions()


def test_basic_imports():
    """基本インポートテスト"""
    # インポートエラーがないことを確認
    from src.core import (
        Container, get_container,
        EventBus, get_event_bus, 
        ThreadManager, get_thread_manager,
        Result, Ok, Err
    )
    
    assert Container is not None
    assert EventBus is not None
    assert ThreadManager is not None
    assert Result is not None


if __name__ == "__main__":
    # 基本的な動作確認
    print("EZRPA v2.0 コア機能統合テスト")
    
    # 基本機能テスト
    container = get_container()
    event_bus = get_event_bus()
    thread_manager = get_thread_manager()
    
    print(f"✓ 依存性注入コンテナ: {type(container).__name__}")
    print(f"✓ イベントバス: {type(event_bus).__name__}")
    print(f"✓ スレッドマネージャー: {type(thread_manager).__name__}")
    
    # Resultパターンテスト
    success_result = Ok("成功")
    error_result = Err("エラー")
    
    print(f"✓ 成功Result: {success_result.is_success()}")
    print(f"✓ エラーResult: {error_result.is_failure()}")
    
    print("\n🎉 基盤構築Phase 1完了！")
    print("次のフェーズでドメイン層の実装を開始できます。")