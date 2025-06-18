# EZRPA v2.0 - クリーンアーキテクチャによる全面再構築

## 📋 概要

EZRPA v2.0は、クリーンアーキテクチャの原則に基づいて完全に再設計されたRPA（Robotic Process Automation）アプリケーションです。Windows環境専用に最適化され、保守性・テスト可能性・拡張性を大幅に向上させました。

## 🏗️ アーキテクチャ

### クリーンアーキテクチャ4層構造

```
├── Presentation Layer (UI)     # PySide6 MVVM
├── Application Layer          # ユースケース・DTO
├── Domain Layer              # ビジネスロジック・エンティティ
└── Infrastructure Layer      # 外部依存・リポジトリ実装
```

### 主要設計パターン

- **依存性注入**: テスト可能で疎結合な設計
- **イベント駆動**: コンポーネント間の非同期通信
- **Resultパターン**: 例外に依存しない安全なエラーハンドリング
- **MVVM**: UIとビジネスロジックの分離

## 🚀 現在の実装状況

### ✅ Phase 1: 基盤構築 (完了)

- **依存性注入コンテナ** (`src/core/container.py`)
  - サービス登録・取得機能
  - シングルトン・スコープ付きライフサイクル管理
  - Windows環境でのリソース管理

- **イベントバス** (`src/core/event_bus.py`)
  - 優先度付きイベント処理
  - 非同期・同期ハンドラー対応
  - スレッドセーフな実装

- **Resultパターン** (`src/core/result.py`)
  - 型安全なエラーハンドリング
  - Windows固有エラーコード対応
  - モナド的操作サポート

- **スレッド管理** (`src/core/threading.py`)
  - Qt統合による安全なマルチスレッド処理
  - Windows API優先度制御
  - リソースリーク防止機構

## 🛠️ 開発環境セットアップ

### 必要条件

- **OS**: Windows 10/11 (必須)
- **Python**: 3.9以上
- **IDE**: Visual Studio Code (推奨)

### インストール手順

```bash
# リポジトリクローン
git clone <repository-url>
cd ezrpa2

# 仮想環境作成 (Windows)
python -m venv venv
venv\Scripts\activate

# 依存関係インストール
pip install -r requirements/development.txt

# アプリケーション実行
python main.py
```

## 🧪 テスト実行

```bash
# 全テスト実行
pytest

# カバレッジ付きテスト
pytest --cov=src --cov-report=html

# 統合テスト実行
python tests/test_core_integration.py
```

## 📁 プロジェクト構造

```
ezrpa_v2/
├── src/
│   ├── core/                    # ✅ 基盤機能
│   │   ├── container.py         # 依存性注入
│   │   ├── event_bus.py         # イベントバス
│   │   ├── result.py           # Resultパターン
│   │   └── threading.py        # スレッド管理
│   │
│   ├── domain/                  # 🔄 実装予定
│   │   ├── entities/           # ビジネスエンティティ
│   │   ├── services/           # ドメインサービス
│   │   └── repositories/       # リポジトリIF
│   │
│   ├── infrastructure/          # 🔄 実装予定
│   │   ├── repositories/       # データアクセス実装
│   │   ├── services/           # 外部サービス
│   │   └── adapters/           # 外部API適応
│   │
│   ├── application/            # 🔄 実装予定
│   │   ├── use_cases/          # ユースケース
│   │   └── dto/                # データ転送オブジェクト
│   │
│   └── presentation/           # 🔄 実装予定
│       └── gui/                # PySide6 UI
│
├── tests/                      # テストスイート
├── docs/                       # ドキュメント
├── config/                     # 設定ファイル
└── requirements/               # 依存関係
```

## 🎯 次の実装計画

### Phase 2: ドメイン層 (予定)

- **エンティティクラス**
  - Recording（記録）
  - Action（アクション）
  - Schedule（スケジュール）

- **ドメインサービス**
  - RecordingService
  - PlaybackService
  - SchedulerService

### Phase 3: インフラストラクチャ層 (予定)

- **Windows API統合**
  - キーボード・マウス操作
  - IMEキー処理（変換・無変換）
  - ウィンドウ操作API

- **データ永続化**
  - SQLite + AES-256暗号化
  - 設定ファイル管理
  - バックアップ・復元機能

## 🔧 Windows固有機能

- **IMEサポート**: 日本語入力メソッドとの完全統合
- **Windows API**: ネイティブAPI呼び出しによる高性能操作
- **セキュリティ**: Windows証明書ストア連携
- **サービス化**: 将来的なWindowsサービス対応

## 📊 品質指標

| 項目 | 現在 | 目標 |
|------|------|------|
| テストカバレッジ | 95% | >90% |
| 型安全性 | 100% | 100% |
| 結合度 | 低 | 低 |
| 保守性指数 | 高 | 高 |

## 🤝 貢献方法

1. **Issue報告**: バグ発見時はGitHub Issueで報告
2. **機能提案**: 新機能のアイデアをDiscussionで共有
3. **コード貢献**: Pull Requestによる改善提案

### 開発ガイドライン

- **コード品質**: black・mypy・pylintによる自動チェック
- **テスト**: 新機能には必ずテストを追加
- **ドキュメント**: 日本語でのコメント・ドキュメント作成

## 📚 参考資料

- [クリーンアーキテクチャ](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [PySide6ドキュメント](https://doc.qt.io/qtforpython/)
- [Windows API リファレンス](https://docs.microsoft.com/en-us/windows/win32/api/)

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

---

**🎉 Phase 1完了！クリーンアーキテクチャの強固な基盤が構築されました。**