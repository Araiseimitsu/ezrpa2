# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EZRPA v2.0 is a comprehensive redesign of an RPA (Robotic Process Automation) application implementing Clean Architecture principles. This repository contains the architectural planning documentation for a complete rewrite focused on maintainability, testability, and scalability.

## Architecture Design

The project follows Clean Architecture with the following layers:
- **Domain Layer**: Business entities and core logic
- **Application Layer**: Use cases and application services  
- **Infrastructure Layer**: External dependencies (database, file system, APIs)
- **Presentation Layer**: UI components using MVVM pattern

Key architectural patterns implemented:
- Dependency Injection Container
- Event Bus for decoupled communication
- Result Pattern for error handling
- Repository Pattern for data access
- MVVM for UI layer

## Project Structure

```
src/
├── core/              # DI container, event bus, result pattern
├── domain/            # Business entities and domain services
├── infrastructure/    # External services and repositories
├── application/       # Use cases and DTOs  
├── presentation/      # GUI views, viewmodels, components
└── shared/           # Common utilities and constants
```

## Development Workflow

The project follows an 8-week implementation plan:
1. **Phase 1 (2 weeks)**: Architecture foundation and infrastructure
2. **Phase 2 (2 weeks)**: Core recording/playback services
3. **Phase 3 (1 week)**: Data layer and security
4. **Phase 4 (2 weeks)**: UI integration with MVVM
5. **Phase 5 (1 week)**: Testing and optimization

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