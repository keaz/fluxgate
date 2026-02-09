# Welcome to FluxGate

**FluxGate** is a comprehensive feature toggle system that enables teams to safely deploy, manage, and monitor feature flags across multiple environments with powerful analytics, approval workflows, and real-time evaluation.

## Quick Navigation

### Getting Started
- **[Getting Started](Getting-Started)** - System setup, login, and first steps
- **[Features](Features)** - Creating and managing feature flags

### Core Functionality
- **[Criteria](Criteria)** - Targeting rules and audience segmentation
- **[Pipelines](Pipelines)** - Deployment workflows and promotion
- **[Environments](Environments)** - Environment configuration and management
- **[Approvals](Approvals)** - Review and approve feature changes
- **[Approval Policies](Approval-Policies)** - Configure governance rules

### Configuration
- **[Contexts](Contexts)** - Context attributes for targeting
- **[Clients](Clients)** - SDK and API client management
- **[Teams](Teams)** - Team organization and collaboration
- **[Users](Users)** - User management and permissions
- **[Settings](Settings)** - System configuration (JWT, notifications, roles)

### Technical Documentation
- **[Edge Server API](Edge-Server-API)** - Edge server evaluation endpoints
- **[Feature Variants](Feature-Variants)** - Variant types and configuration
- **[Priority Evaluation](Priority-Evaluation)** - Criteria evaluation logic

## Key Features

✅ **Feature Variants**: Support for A/B testing with string, number, boolean, and JSON variant types  
✅ **Priority-Based Criteria**: Ordered evaluation of targeting rules with drag-and-drop UI  
✅ **Kill Switch**: Emergency feature disable with optional auto-rollback scheduling  
✅ **Real-Time Analytics**: Live metrics via WebSocket with evaluation and rollout dashboards  
✅ **Role-Based Access Control**: Requester, Approver, and Team Admin roles with JWT authentication  
✅ **Multi-Environment Support**: Manage features across development, staging, production, and custom environments  
✅ **Approval Workflows**: Configurable approval policies for feature changes  
✅ **Deployment Pipelines**: Automated feature promotion across environments

## Architecture

FluxGate consists of three main components:

- **Backend**: Rust-based API server providing REST and gRPC endpoints
- **Edge Server**: High-performance evaluation service with in-memory caching
- **UI**: React-based web interface for feature flag management

## Support

For questions, issues, or feature requests, please visit the project repository.
