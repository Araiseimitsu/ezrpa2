"""
暗号化サービス - データ暗号化・復号化機能

AES-256暗号化によるデータの安全な暗号化・復号化を提供します。
Windows環境でのキー管理とセキュリティ機能を実装します。
"""

import base64
import hashlib
import os
import secrets
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from ...core.result import Result, Ok, Err, ErrorInfo
from ...shared.constants import SecurityConstants, WindowsPaths


class EncryptionService:
    """暗号化サービス実装"""
    
    def __init__(self, master_password: Optional[str] = None):
        self._lock = threading.RLock()
        self._master_password = master_password
        self._derived_keys: Dict[str, bytes] = {}
        self._backend = default_backend()
        
        # Windows環境でのキーストレージパス
        self._key_storage_path = WindowsPaths.get_app_data_dir() / "keys"
        self._key_storage_path.mkdir(parents=True, exist_ok=True)
        
        # RSA キーペアの初期化
        self._rsa_private_key: Optional[rsa.RSAPrivateKey] = None
        self._rsa_public_key: Optional[rsa.RSAPublicKey] = None
        
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """暗号化システムの初期化"""
        try:
            # RSAキーペアの読み込みまたは生成
            self._load_or_generate_rsa_keys()
            
            # マスターパスワードが設定されている場合、派生キーを生成
            if self._master_password:
                self._generate_derived_key("default", self._master_password)
                
        except Exception as e:
            # 初期化エラーは警告レベルでログ出力（サービス自体は動作可能）
            pass
    
    def set_master_password(self, password: str, key_id: str = "default") -> Result[None, str]:
        """マスターパスワードを設定"""
        try:
            with self._lock:
                return self._generate_derived_key(key_id, password)
        except Exception as e:
            return Err(f"マスターパスワード設定エラー: {str(e)}")
    
    def encrypt_data(self, data: str, key_id: str = "default") -> Result[str, str]:
        """データを暗号化"""
        try:
            with self._lock:
                if key_id not in self._derived_keys:
                    return Err(f"キー '{key_id}' が設定されていません")
                
                # バイト変換
                data_bytes = data.encode('utf-8')
                
                # ランダムなIVを生成
                iv = secrets.token_bytes(SecurityConstants.IV_SIZE)
                
                # AES-256-CBC暗号化
                cipher = Cipher(
                    algorithms.AES(self._derived_keys[key_id]),
                    modes.CBC(iv),
                    backend=self._backend
                )
                
                encryptor = cipher.encryptor()
                
                # PKCS7パディング
                padded_data = self._add_pkcs7_padding(data_bytes)
                
                # 暗号化実行
                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
                
                # IV + 暗号化データを結合してBase64エンコード
                combined_data = iv + encrypted_data
                encoded_data = base64.b64encode(combined_data).decode('ascii')
                
                return Ok(encoded_data)
                
        except Exception as e:
            return Err(f"暗号化エラー: {str(e)}")
    
    def decrypt_data(self, encrypted_data: str, key_id: str = "default") -> Result[str, str]:
        """データを復号化"""
        try:
            with self._lock:
                if key_id not in self._derived_keys:
                    return Err(f"キー '{key_id}' が設定されていません")
                
                # Base64デコード
                try:
                    combined_data = base64.b64decode(encrypted_data.encode('ascii'))
                except Exception:
                    return Err("無効な暗号化データ形式です")
                
                if len(combined_data) < SecurityConstants.IV_SIZE:
                    return Err("暗号化データが短すぎます")
                
                # IVと暗号化データを分離
                iv = combined_data[:SecurityConstants.IV_SIZE]
                encrypted_bytes = combined_data[SecurityConstants.IV_SIZE:]
                
                # AES-256-CBC復号化
                cipher = Cipher(
                    algorithms.AES(self._derived_keys[key_id]),
                    modes.CBC(iv),
                    backend=self._backend
                )
                
                decryptor = cipher.decryptor()
                
                # 復号化実行
                padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
                
                # PKCS7パディング除去
                data_bytes = self._remove_pkcs7_padding(padded_data)
                
                # UTF-8デコード
                decrypted_data = data_bytes.decode('utf-8')
                
                return Ok(decrypted_data)
                
        except Exception as e:
            return Err(f"復号化エラー: {str(e)}")
    
    def encrypt_file(self, file_path: Path, output_path: Optional[Path] = None, 
                    key_id: str = "default") -> Result[Path, str]:
        """ファイルを暗号化"""
        try:
            with self._lock:
                if not file_path.exists():
                    return Err(f"ファイルが存在しません: {file_path}")
                
                if key_id not in self._derived_keys:
                    return Err(f"キー '{key_id}' が設定されていません")
                
                # 出力パスの決定
                if output_path is None:
                    output_path = file_path.with_suffix(file_path.suffix + '.enc')
                
                # ファイル読み込み
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # 暗号化
                iv = secrets.token_bytes(SecurityConstants.IV_SIZE)
                cipher = Cipher(
                    algorithms.AES(self._derived_keys[key_id]),
                    modes.CBC(iv),
                    backend=self._backend
                )
                
                encryptor = cipher.encryptor()
                padded_data = self._add_pkcs7_padding(file_data)
                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
                
                # 暗号化ファイル書き込み
                with open(output_path, 'wb') as f:
                    f.write(iv)  # IVを先頭に書き込み
                    f.write(encrypted_data)
                
                return Ok(output_path)
                
        except Exception as e:
            return Err(f"ファイル暗号化エラー: {str(e)}")
    
    def decrypt_file(self, encrypted_file_path: Path, output_path: Optional[Path] = None,
                    key_id: str = "default") -> Result[Path, str]:
        """ファイルを復号化"""
        try:
            with self._lock:
                if not encrypted_file_path.exists():
                    return Err(f"暗号化ファイルが存在しません: {encrypted_file_path}")
                
                if key_id not in self._derived_keys:
                    return Err(f"キー '{key_id}' が設定されていません")
                
                # 出力パスの決定
                if output_path is None:
                    if encrypted_file_path.suffix == '.enc':
                        output_path = encrypted_file_path.with_suffix('')
                    else:
                        output_path = encrypted_file_path.with_suffix('.dec')
                
                # 暗号化ファイル読み込み
                with open(encrypted_file_path, 'rb') as f:
                    encrypted_data = f.read()
                
                if len(encrypted_data) < SecurityConstants.IV_SIZE:
                    return Err("暗号化ファイルが短すぎます")
                
                # IVと暗号化データを分離
                iv = encrypted_data[:SecurityConstants.IV_SIZE]
                encrypted_bytes = encrypted_data[SecurityConstants.IV_SIZE:]
                
                # 復号化
                cipher = Cipher(
                    algorithms.AES(self._derived_keys[key_id]),
                    modes.CBC(iv),
                    backend=self._backend
                )
                
                decryptor = cipher.decryptor()
                padded_data = decryptor.update(encrypted_bytes) + decryptor.finalize()
                decrypted_data = self._remove_pkcs7_padding(padded_data)
                
                # 復号化ファイル書き込み
                with open(output_path, 'wb') as f:
                    f.write(decrypted_data)
                
                return Ok(output_path)
                
        except Exception as e:
            return Err(f"ファイル復号化エラー: {str(e)}")
    
    def generate_secure_token(self, length: int = 32) -> str:
        """セキュアなランダムトークンを生成"""
        return secrets.token_urlsafe(length)
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Result[Dict[str, str], str]:
        """パスワードをハッシュ化"""
        try:
            if salt is None:
                salt = secrets.token_bytes(SecurityConstants.SALT_SIZE)
            
            # PBKDF2によるハッシュ化
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=SecurityConstants.PBKDF2_ITERATIONS,
                backend=self._backend
            )
            
            hashed = kdf.derive(password.encode('utf-8'))
            
            return Ok({
                'hash': base64.b64encode(hashed).decode('ascii'),
                'salt': base64.b64encode(salt).decode('ascii'),
                'iterations': str(SecurityConstants.PBKDF2_ITERATIONS)
            })
            
        except Exception as e:
            return Err(f"パスワードハッシュ化エラー: {str(e)}")
    
    def verify_password(self, password: str, stored_hash: str, salt: str, 
                       iterations: int = SecurityConstants.PBKDF2_ITERATIONS) -> bool:
        """パスワードを検証"""
        try:
            salt_bytes = base64.b64decode(salt.encode('ascii'))
            stored_hash_bytes = base64.b64decode(stored_hash.encode('ascii'))
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=iterations,
                backend=self._backend
            )
            
            # パスワードから同じハッシュが生成されるかチェック
            try:
                kdf.verify(password.encode('utf-8'), stored_hash_bytes)
                return True
            except Exception:
                return False
                
        except Exception:
            return False
    
    def encrypt_with_rsa(self, data: str) -> Result[str, str]:
        """RSA公開キーでデータを暗号化"""
        try:
            if not self._rsa_public_key:
                return Err("RSA公開キーが設定されていません")
            
            data_bytes = data.encode('utf-8')
            
            # RSA-OAEPパディングで暗号化
            encrypted = self._rsa_public_key.encrypt(
                data_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return Ok(base64.b64encode(encrypted).decode('ascii'))
            
        except Exception as e:
            return Err(f"RSA暗号化エラー: {str(e)}")
    
    def decrypt_with_rsa(self, encrypted_data: str) -> Result[str, str]:
        """RSA秘密キーでデータを復号化"""
        try:
            if not self._rsa_private_key:
                return Err("RSA秘密キーが設定されていません")
            
            encrypted_bytes = base64.b64decode(encrypted_data.encode('ascii'))
            
            # RSA-OAEPパディングで復号化
            decrypted = self._rsa_private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return Ok(decrypted.decode('utf-8'))
            
        except Exception as e:
            return Err(f"RSA復号化エラー: {str(e)}")
    
    def is_encryption_available(self, key_id: str = "default") -> bool:
        """暗号化が使用可能かチェック"""
        return key_id in self._derived_keys
    
    def clear_keys(self):
        """メモリ内のキーをクリア"""
        with self._lock:
            self._derived_keys.clear()
            self._master_password = None
    
    # プライベートメソッド
    def _generate_derived_key(self, key_id: str, password: str) -> Result[None, str]:
        """パスワードから派生キーを生成"""
        try:
            # ソルトの生成または読み込み
            salt_file = self._key_storage_path / f"{key_id}_salt.key"
            
            if salt_file.exists():
                with open(salt_file, 'rb') as f:
                    salt = f.read()
            else:
                salt = secrets.token_bytes(SecurityConstants.SALT_SIZE)
                with open(salt_file, 'wb') as f:
                    f.write(salt)
                
                # Windowsファイル属性で隠しファイルに設定
                try:
                    import subprocess
                    subprocess.run(['attrib', '+H', str(salt_file)], 
                                 capture_output=True, check=False)
                except Exception:
                    pass
            
            # PBKDF2でキー派生
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=SecurityConstants.AES_KEY_SIZE // 8,  # 256bit = 32bytes
                salt=salt,
                iterations=SecurityConstants.PBKDF2_ITERATIONS,
                backend=self._backend
            )
            
            derived_key = kdf.derive(password.encode('utf-8'))
            self._derived_keys[key_id] = derived_key
            
            return Ok(None)
            
        except Exception as e:
            return Err(f"派生キー生成エラー: {str(e)}")
    
    def _load_or_generate_rsa_keys(self):
        """RSAキーペアの読み込みまたは生成"""
        private_key_file = self._key_storage_path / "rsa_private.pem"
        public_key_file = self._key_storage_path / "rsa_public.pem"
        
        try:
            if private_key_file.exists() and public_key_file.exists():
                # 既存キーの読み込み
                with open(private_key_file, 'rb') as f:
                    self._rsa_private_key = serialization.load_pem_private_key(
                        f.read(), password=None, backend=self._backend
                    )
                
                with open(public_key_file, 'rb') as f:
                    self._rsa_public_key = serialization.load_pem_public_key(
                        f.read(), backend=self._backend
                    )
            else:
                # 新規キーペア生成
                self._rsa_private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=self._backend
                )
                self._rsa_public_key = self._rsa_private_key.public_key()
                
                # キーファイル保存
                with open(private_key_file, 'wb') as f:
                    f.write(self._rsa_private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))
                
                with open(public_key_file, 'wb') as f:
                    f.write(self._rsa_public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ))
                
                # Windowsファイル属性設定
                try:
                    import subprocess
                    subprocess.run(['attrib', '+H', str(private_key_file)], 
                                 capture_output=True, check=False)
                    subprocess.run(['attrib', '+H', str(public_key_file)], 
                                 capture_output=True, check=False)
                except Exception:
                    pass
                    
        except Exception as e:
            # キー生成失敗時は警告のみ（暗号化機能は制限される）
            self._rsa_private_key = None
            self._rsa_public_key = None
    
    def _add_pkcs7_padding(self, data: bytes) -> bytes:
        """PKCS7パディングを追加"""
        block_size = SecurityConstants.AES_BLOCK_SIZE
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    def _remove_pkcs7_padding(self, padded_data: bytes) -> bytes:
        """PKCS7パディングを除去"""
        if not padded_data:
            raise ValueError("パディングされたデータが空です")
        
        padding_length = padded_data[-1]
        
        # パディング長の妥当性チェック
        if padding_length > SecurityConstants.AES_BLOCK_SIZE or padding_length == 0:
            raise ValueError("無効なパディング長です")
        
        # パディングバイトの整合性チェック
        for i in range(padding_length):
            if padded_data[-(i + 1)] != padding_length:
                raise ValueError("パディングが不正です")
        
        return padded_data[:-padding_length]