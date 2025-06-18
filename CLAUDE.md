# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EZRPA v2.0 is a comprehensive redesign of an RPA (Robotic Process Automation) application implementing Clean Architecture principles. This repository contains a complete implementation with all layers fully developed and functional.

## Current Status (2025-06-18)

**Phase 6: テスト統合・品質保証フェーズ** - **進行中**

### 完了済みフェーズ
- ✅ **Phase 1-2**: Core層、Domain層 - 依存性注入、イベントバス、エンティティ
- ✅ **Phase 3**: Infrastructure層 - リポジトリ実装、暗号化、Windows API統合  
- ✅ **Phase 4**: Application層 - アプリケーションサービス、DTO、ユースケース
- ✅ **Phase 5**: Presentation層 - MVVM パターン、ViewModels、Views、完全なGUI実装

### 現在の作業 (Phase 6)
🔄 **テスト基盤構築** (進行中)
- ✅ pytest設定の最適化とプラグイン統合
- ✅ テストデータ・フィクスチャシステムの構築  
- ✅ モック・ファクトリーパターンの実装
- ✅ テスト環境用DIコンテナの構築
- 🔄 Domain層の単体テスト実装 (進行中)
  - ✅ Recording エンティティテスト
  - ✅ Action エンティティテスト  
  - ✅ Schedule エンティティテスト
  - ✅ Value Objects テスト
- ⏳ Application層の単体テスト実装 (待機中)
- ⏳ Infrastructure層の単体テスト実装 (待機中)
- ⏳ Presentation層の単体テスト実装 (待機中)

## Architecture Design

The project follows Clean Architecture with the following layers:
- **Core Layer**: DI container, event bus, result pattern, threading
- **Domain Layer**: Business entities (Recording, Action, Schedule) and value objects
- **Infrastructure Layer**: Repository implementations, encryption, file services, Windows API
- **Application Layer**: Application services, DTOs, use cases, event handlers
- **Presentation Layer**: MVVM pattern with ViewModels, Views, and GUI components

Key architectural patterns implemented:
- Dependency Injection Container with service registration
- Event Bus for decoupled communication between layers
- Result Pattern for functional error handling
- Repository Pattern for data persistence abstraction
- MVVM Pattern for UI layer separation
- Factory Pattern for test data generation
- Command Pattern for UI actions

## Project Structure

```
src/
├── core/              # DI container, event bus, result pattern, threading
├── domain/            # Business entities, value objects, repository interfaces
├── infrastructure/    # Repository implementations, external services, adapters
├── application/       # Application services, DTOs, use cases, event handlers
├── presentation/      # GUI components, ViewModels, Views (MVVM)
└── shared/           # Common utilities and constants

tests/
├── unit/             # Unit tests for each layer
├── integration/      # Integration tests between layers  
├── e2e/             # End-to-end tests
├── fixtures/        # Test data and fixtures
├── conftest.py      # Pytest configuration and global fixtures
├── factories.py     # Test data factory classes
└── test_container.py # Test-specific DI container
```

## Development Workflow - Updated

実装計画 (8週間):
1. ✅ **Phase 1-2 (4週間)**: アーキテクチャ基盤とコアサービス - **完了**
2. ✅ **Phase 3 (1週間)**: データ層とセキュリティ - **完了**  
3. ✅ **Phase 4 (2週間)**: アプリケーション層統合 - **完了**
4. ✅ **Phase 5 (1週間)**: プレゼンテーション層(MVVM) - **完了**
5. 🔄 **Phase 6 (3週間)**: テスト統合・品質保証 - **進行中**

## Key Technical Requirements

- **Threading**: Safe thread management for background operations
- **IME Support**: Japanese input method integration via Windows API
- **Security**: AES-256 encryption for local data storage
- **UI Framework**: PySide6 with MVVM pattern
- **Testing**: >90% test coverage target with unit/integration/E2E tests

## Implementation Guidelines

- Use dependency injection for all service dependencies
- Implement Result pattern for error handling instead of exceptions
- Follow event-driven architecture for component communication
- Maintain strict layer separation (no circular dependencies)
- All UI operations must be thread-safe using Qt signals/slots
- Data persistence through repository pattern with encryption

## Development Rules

- **Language**: Always respond in Japanese (日本語で回答する)
- **Target Environment**: All code, structure, and libraries must be designed specifically for Windows environment
  - Use Windows-specific paths (e.g., `C:\`, backslashes)
  - Implement Windows API integrations where needed
  - Choose Windows-compatible libraries and dependencies
  - Handle Windows-specific file permissions and security contexts
  - Consider Windows service architecture for background processes

This is currently a planning/design phase repository. Actual implementation should follow the detailed specifications in `outline2.md`.