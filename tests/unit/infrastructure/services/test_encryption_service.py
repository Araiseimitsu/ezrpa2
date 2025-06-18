"""
Encryption Service Unit Tests - 暗号化サービスのテスト

AES-256暗号化サービスの機能をテストします。
"""

import pytest
import tempfile
import secrets
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.infrastructure.services.encryption_service import EncryptionService
from src.core.result import Result, Ok, Err, ErrorInfo


class TestEncryptionService:
    """暗号化サービスのテストクラス"""
    
    @pytest.fixture
    def temp_key_dir(self):
        """一時キーストレージディレクトリ"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def encryption_service(self, temp_key_dir):
        """テスト対象の暗号化サービス"""
        with patch('src.infrastructure.services.encryption_service.WindowsPaths') as mock_paths:
            mock_paths.get_app_data_dir.return_value = temp_key_dir
            return EncryptionService(master_password="test_password_123")
    
    @pytest.fixture
    def service_without_password(self, temp_key_dir):
        """パスワードなしの暗号化サービス"""
        with patch('src.infrastructure.services.encryption_service.WindowsPaths') as mock_paths:
            mock_paths.get_app_data_dir.return_value = temp_key_dir
            return EncryptionService()
    
    # ========================
    # 初期化・設定テスト
    # ========================
    
    def test_service_initialization_with_password(self, encryption_service):
        """パスワード付き初期化のテスト"""
        # Assert
        assert encryption_service._master_password == "test_password_123"
        assert encryption_service._key_storage_path.exists()
        assert encryption_service._rsa_private_key is not None
        assert encryption_service._rsa_public_key is not None
    
    def test_service_initialization_without_password(self, service_without_password):
        """パスワードなし初期化のテスト"""
        # Assert
        assert service_without_password._master_password is None
        assert service_without_password._key_storage_path.exists()
        assert service_without_password._rsa_private_key is not None
        assert service_without_password._rsa_public_key is not None
    
    def test_rsa_key_generation(self, encryption_service):
        """RSAキー生成のテスト"""
        # Assert - RSAキーが適切に生成されている
        private_key = encryption_service._rsa_private_key
        public_key = encryption_service._rsa_public_key
        
        assert private_key is not None
        assert public_key is not None
        assert private_key.key_size == 2048  # 適切なキーサイズ
        
        # 公開鍵と秘密鍵の対応確認
        assert private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ) == public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def test_key_storage_directory_creation(self, temp_key_dir):
        """キーストレージディレクトリ作成のテスト"""
        # Arrange
        key_dir = temp_key_dir / "test_keys"
        
        with patch('src.infrastructure.services.encryption_service.WindowsPaths') as mock_paths:
            mock_paths.get_app_data_dir.return_value = key_dir
            
            # Act
            service = EncryptionService()
            
            # Assert
            assert key_dir.exists()
            assert service._key_storage_path == key_dir
    
    # ========================
    # AES暗号化・復号化テスト
    # ========================
    
    def test_encrypt_decrypt_string_success(self, encryption_service):
        """文字列の暗号化・復号化成功のテスト"""
        # Arrange
        original_text = "テスト用の日本語テキストです。This is a test text."
        
        # Act - 暗号化
        encrypt_result = encryption_service.encrypt(original_text)
        
        # Assert - 暗号化成功
        assert encrypt_result.is_success()
        encrypted_data = encrypt_result.value
        assert isinstance(encrypted_data, bytes)
        assert encrypted_data != original_text.encode()
        
        # Act - 復号化
        decrypt_result = encryption_service.decrypt(encrypted_data)
        
        # Assert - 復号化成功
        assert decrypt_result.is_success()
        decrypted_text = decrypt_result.value
        assert decrypted_text == original_text
    
    def test_encrypt_decrypt_bytes_success(self, encryption_service):
        """バイト列の暗号化・復号化成功のテスト"""
        # Arrange
        original_bytes = b"Binary data \x00\x01\x02\xff"
        
        # Act
        encrypt_result = encryption_service.encrypt(original_bytes)
        assert encrypt_result.is_success()
        
        decrypt_result = encryption_service.decrypt(encrypt_result.value)
        
        # Assert
        assert decrypt_result.is_success()
        assert decrypt_result.value == original_bytes
    
    def test_encrypt_large_data(self, encryption_service):
        """大きなデータの暗号化テスト"""
        # Arrange
        large_data = "A" * 10000  # 10KB のデータ
        
        # Act
        encrypt_result = encryption_service.encrypt(large_data)
        
        # Assert
        assert encrypt_result.is_success()
        
        decrypt_result = encryption_service.decrypt(encrypt_result.value)
        assert decrypt_result.is_success()
        assert decrypt_result.value == large_data
    
    def test_encrypt_empty_data(self, encryption_service):
        """空データの暗号化テスト"""
        # Act
        encrypt_result = encryption_service.encrypt("")
        
        # Assert
        assert encrypt_result.is_success()
        
        decrypt_result = encryption_service.decrypt(encrypt_result.value)
        assert decrypt_result.is_success()
        assert decrypt_result.value == ""
    
    def test_encrypt_unicode_data(self, encryption_service):
        """Unicode文字の暗号化テスト"""
        # Arrange
        unicode_text = "🎌日本語テスト🔒暗号化🔑復号化✅"
        
        # Act
        encrypt_result = encryption_service.encrypt(unicode_text)
        decrypt_result = encryption_service.decrypt(encrypt_result.value)
        
        # Assert
        assert encrypt_result.is_success()
        assert decrypt_result.is_success()
        assert decrypt_result.value == unicode_text
    
    # ========================
    # キー管理テスト
    # ========================
    
    def test_generate_key_success(self, encryption_service):
        """キー生成成功のテスト"""
        # Act
        result = encryption_service.generate_key("test_context")
        
        # Assert
        assert result.is_success()
        key = result.value
        assert isinstance(key, bytes)
        assert len(key) == 32  # AES-256キーは32バイト
    
    def test_derive_key_from_password(self, encryption_service):
        """パスワードからのキー派生テスト"""
        # Arrange
        password = "secure_password_123"
        context = "test_context"
        
        # Act
        result = encryption_service.derive_key(password, context)
        
        # Assert
        assert result.is_success()
        derived_key = result.value
        assert isinstance(derived_key, bytes)
        assert len(derived_key) == 32
        
        # 同じ入力から同じキーが生成される
        result2 = encryption_service.derive_key(password, context)
        assert result2.is_success()
        assert result2.value == derived_key
    
    def test_derive_key_different_contexts(self, encryption_service):
        """異なるコンテキストでのキー派生テスト"""
        # Arrange
        password = "same_password"
        
        # Act
        key1_result = encryption_service.derive_key(password, "context1")
        key2_result = encryption_service.derive_key(password, "context2")
        
        # Assert
        assert key1_result.is_success()
        assert key2_result.is_success()
        assert key1_result.value != key2_result.value  # 異なるコンテキストで異なるキー
    
    def test_store_and_load_key(self, encryption_service):
        """キーの保存・読み込みテスト"""
        # Arrange
        key_name = "test_key"
        original_key = secrets.token_bytes(32)
        
        # Act - キー保存
        store_result = encryption_service.store_key(key_name, original_key)
        assert store_result.is_success()
        
        # Act - キー読み込み
        load_result = encryption_service.load_key(key_name)
        
        # Assert
        assert load_result.is_success()
        loaded_key = load_result.value
        assert loaded_key == original_key
    
    def test_load_nonexistent_key(self, encryption_service):
        """存在しないキーの読み込みテスト"""
        # Act
        result = encryption_service.load_key("nonexistent_key")
        
        # Assert
        assert result.is_failure()
        assert "KEY_NOT_FOUND" in result.error.code
    
    # ========================
    # RSA暗号化テスト
    # ========================
    
    def test_rsa_encrypt_decrypt_success(self, encryption_service):
        """RSA暗号化・復号化成功のテスト"""
        # Arrange
        original_data = "RSAで暗号化するテストデータ"
        
        # Act
        encrypt_result = encryption_service.rsa_encrypt(original_data)
        
        # Assert
        assert encrypt_result.is_success()
        encrypted_data = encrypt_result.value
        assert isinstance(encrypted_data, bytes)
        
        # Act - 復号化
        decrypt_result = encryption_service.rsa_decrypt(encrypted_data)
        
        # Assert
        assert decrypt_result.is_success()
        assert decrypt_result.value == original_data
    
    def test_rsa_encrypt_large_data_failure(self, encryption_service):
        """RSA暗号化での大きなデータ処理失敗テスト"""
        # Arrange - RSAの最大サイズを超えるデータ
        large_data = "A" * 500  # RSA-2048では約245バイトが上限
        
        # Act
        result = encryption_service.rsa_encrypt(large_data)
        
        # Assert
        assert result.is_failure()
        assert "RSA_DATA_TOO_LARGE" in result.error.code or "ENCRYPTION_ERROR" in result.error.code
    
    # ========================
    # ハッシュ化テスト
    # ========================
    
    def test_hash_data_success(self, encryption_service):
        """データハッシュ化成功のテスト"""
        # Arrange
        data = "ハッシュ化するテストデータ"
        
        # Act
        result = encryption_service.hash_data(data)
        
        # Assert
        assert result.is_success()
        hash_value = result.value
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA-256は64文字の16進文字列
        
        # 同じデータから同じハッシュが生成される
        result2 = encryption_service.hash_data(data)
        assert result2.is_success()
        assert result2.value == hash_value
    
    def test_hash_different_data(self, encryption_service):
        """異なるデータのハッシュ化テスト"""
        # Act
        hash1_result = encryption_service.hash_data("data1")
        hash2_result = encryption_service.hash_data("data2")
        
        # Assert
        assert hash1_result.is_success()
        assert hash2_result.is_success()
        assert hash1_result.value != hash2_result.value
    
    def test_verify_hash_success(self, encryption_service):
        """ハッシュ検証成功のテスト"""
        # Arrange
        original_data = "検証するデータ"
        hash_result = encryption_service.hash_data(original_data)
        hash_value = hash_result.value
        
        # Act
        verify_result = encryption_service.verify_hash(original_data, hash_value)
        
        # Assert
        assert verify_result.is_success()
        assert verify_result.value is True
    
    def test_verify_hash_failure(self, encryption_service):
        """ハッシュ検証失敗のテスト"""
        # Arrange
        original_data = "元のデータ"
        tampered_data = "改ざんされたデータ"
        hash_result = encryption_service.hash_data(original_data)
        hash_value = hash_result.value
        
        # Act
        verify_result = encryption_service.verify_hash(tampered_data, hash_value)
        
        # Assert
        assert verify_result.is_success()
        assert verify_result.value is False
    
    # ========================
    # セキュリティテスト
    # ========================
    
    def test_encryption_randomness(self, encryption_service):
        """暗号化のランダム性テスト"""
        # Arrange
        data = "同じデータ"
        
        # Act - 同じデータを複数回暗号化
        encrypt1 = encryption_service.encrypt(data)
        encrypt2 = encryption_service.encrypt(data)
        
        # Assert - 毎回異なる暗号化結果が得られる（IVによる）
        assert encrypt1.is_success()
        assert encrypt2.is_success()
        assert encrypt1.value != encrypt2.value
        
        # 両方とも正しく復号化される
        decrypt1 = encryption_service.decrypt(encrypt1.value)
        decrypt2 = encryption_service.decrypt(encrypt2.value)
        assert decrypt1.is_success()
        assert decrypt2.is_success()
        assert decrypt1.value == data
        assert decrypt2.value == data
    
    def test_key_derivation_salt(self, encryption_service):
        """キー派生のソルト使用テスト"""
        # Arrange
        password = "test_password"
        context = "test_context"
        
        # Act - 内部実装によるソルトの効果確認
        # 実際のテストでは、saltが適切に使用されていることを確認
        key1 = encryption_service.derive_key(password, context)
        key2 = encryption_service.derive_key(password, context)
        
        # Assert - 同じ入力から同じキーが生成される（確定的）
        assert key1.is_success()
        assert key2.is_success()
        assert key1.value == key2.value
    
    def test_secure_key_storage(self, encryption_service):
        """安全なキー保存のテスト"""
        # Arrange
        key_name = "secure_test_key"
        sensitive_key = secrets.token_bytes(32)
        
        # Act
        store_result = encryption_service.store_key(key_name, sensitive_key)
        
        # Assert
        assert store_result.is_success()
        
        # ファイルシステムでキーファイルの存在確認
        key_file_path = encryption_service._key_storage_path / f"{key_name}.key"
        assert key_file_path.exists()
        
        # ファイル内容が暗号化されている（平文でない）
        with open(key_file_path, 'rb') as f:
            file_content = f.read()
        assert file_content != sensitive_key  # 平文で保存されていない
    
    # ========================
    # エラーハンドリングテスト
    # ========================
    
    def test_decrypt_invalid_data(self, encryption_service):
        """無効なデータの復号化テスト"""
        # Arrange
        invalid_data = b"invalid_encrypted_data"
        
        # Act
        result = encryption_service.decrypt(invalid_data)
        
        # Assert
        assert result.is_failure()
        assert "DECRYPTION_ERROR" in result.error.code
    
    def test_decrypt_corrupted_data(self, encryption_service):
        """破損したデータの復号化テスト"""
        # Arrange
        original_data = "テストデータ"
        encrypt_result = encryption_service.encrypt(original_data)
        encrypted_data = bytearray(encrypt_result.value)
        
        # データを破損させる
        encrypted_data[10] = encrypted_data[10] ^ 0xFF  # 1バイト変更
        
        # Act
        result = encryption_service.decrypt(bytes(encrypted_data))
        
        # Assert
        assert result.is_failure()
        assert "DECRYPTION_ERROR" in result.error.code
    
    def test_service_without_master_password(self, service_without_password):
        """マスターパスワードなしでの操作テスト"""
        # Arrange
        data = "パスワードなしでの暗号化"
        
        # Act
        encrypt_result = service_without_password.encrypt(data)
        
        # Assert - パスワードなしでも基本的な暗号化は動作する
        assert encrypt_result.is_success()
        
        decrypt_result = service_without_password.decrypt(encrypt_result.value)
        assert decrypt_result.is_success()
        assert decrypt_result.value == data
    
    # ========================
    # パフォーマンステスト
    # ========================
    
    def test_encryption_performance(self, encryption_service):
        """暗号化パフォーマンステスト"""
        # Arrange
        large_data = "A" * 100000  # 100KB のデータ
        
        # Act
        import time
        start_time = time.time()
        
        encrypt_result = encryption_service.encrypt(large_data)
        assert encrypt_result.is_success()
        
        decrypt_result = encryption_service.decrypt(encrypt_result.value)
        assert decrypt_result.is_success()
        
        end_time = time.time()
        
        # Assert - パフォーマンス要件: 100KBの暗号化・復号化が1秒以内
        assert (end_time - start_time) < 1.0
        assert decrypt_result.value == large_data
    
    # ========================
    # スレッドセーフティテスト
    # ========================
    
    def test_concurrent_encryption(self, encryption_service):
        """並行暗号化のテスト"""
        import threading
        import time
        
        results = []
        errors = []
        
        def encrypt_data(data_id):
            try:
                data = f"concurrent_test_data_{data_id}"
                result = encryption_service.encrypt(data)
                if result.is_success():
                    decrypt_result = encryption_service.decrypt(result.value)
                    if decrypt_result.is_success() and decrypt_result.value == data:
                        results.append(data_id)
                    else:
                        errors.append(f"Decrypt failed for {data_id}")
                else:
                    errors.append(f"Encrypt failed for {data_id}")
            except Exception as e:
                errors.append(f"Exception for {data_id}: {e}")
        
        # Act - 複数スレッドで並行処理
        threads = []
        for i in range(10):
            thread = threading.Thread(target=encrypt_data, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Assert
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"