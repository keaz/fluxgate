# Release Notes

## Version 0.0.14-alpha (December 2025)

This release brings significant enhancements to FluxGate's feature targeting capabilities, approval workflows, and standards compliance.

### 🎯 Advanced Targeting & Rules

**Multi-Variant Weighted Traffic Splits**
- Distribute traffic across multiple feature variants with precise percentage control
- Run multivariate experiments beyond simple A/B tests
- Allocate different weights to each variant for granular traffic distribution

**Compound Rules (AND/OR Logic)**
- Build sophisticated targeting rules using logical operators
- Combine multiple conditions to create complex user segments
- Support for nested rule groups with flexible evaluation logic

**Enhanced Operator Support**
- Expanded set of comparison operators for targeting criteria
- More flexible matching capabilities for user attributes
- Improved precision in audience segmentation

### 📊 Metrics & Analytics

**Metrics Tracking System**
- Track and aggregate evaluation metrics across features
- Monitor feature performance over time
- Gain insights into feature usage patterns and user behavior

**Enhanced Evaluation Events**
- Capture variant values in evaluation events for better analytics
- Improved tracking of which variants are served to users
- Richer data for analysis and reporting

### ✅ Approval Workflows

**Approval Policies**
- Define approval policies with role-based access control
- Configure required approvals for feature deployments
- Manage deployment gates and governance workflows

**Approval Management Interface**
- View and manage approval requests in a centralized dashboard
- Track approval status with detailed request views
- Add comments and collaborate on approval decisions
- Monitor vote tracking and approval progress

**Auto-Approval Scheduler**
- Schedule automatic approvals for time-based deployments
- Reduce manual overhead for pre-approved changes
- Support for scheduled rollouts

**Flexible Authorization**
- Both Requester and Approver roles can execute deployments and rollbacks
- Streamlined permission model for common workflows
- Improved access control flexibility

### 🌐 OpenFeature Standards Compliance

**OFREP-Compliant Edge Server**
- Full implementation of OpenFeature Remote Evaluation Protocol (OFREP)
- New standardized API endpoint: `POST /ofrep/v1/evaluate/flags/{key}`
- Header-based authentication supporting Bearer tokens and API keys
- Proper HTTP status codes (404 for missing flags, 400 for invalid requests)

**Standardized Field Naming**
- Migrated from `bucketingKey` to `targetingKey` following OpenFeature conventions
- Backward compatibility maintained for existing integrations
- Consistent naming across evaluation requests and responses

**OFREP Error Codes & Reasons**
- Evaluation reasons aligned with OFREP specification
- Standardized error codes for better interoperability
- Improved error handling and reporting

**Accurate Cache Behavior**
- Cached evaluations now return original evaluation reasons
- Transparent caching without altering evaluation semantics
- Better debugging and troubleshooting capabilities

### 🎨 User Interface Improvements

**System Overview Dashboard**
- Centralized view of system status and health
- Team-based filtering for multi-tenant environments
- Environment selection scoped to active team

**Enhanced Theme Support**
- Comprehensive light mode implementation
- Gradient support for modern UI aesthetics
- Improved visual consistency across themes
- Better contrast and accessibility

**Improved Component Library**
- Integration of Radix UI Tabs for enhanced navigation
- Clipboard copy functionality for easier data sharing
- Enhanced button styles and interactive elements
- Better user experience across all management interfaces

**Code Quality & Organization**
- Project restructure following industry best practices
- Improved component organization by domain
- Consolidated context providers
- Better maintainability and developer experience

### 🔧 Technical Improvements

**Performance Enhancements**
- Optimized edge server evaluation performance
- Improved query efficiency
- Better resource utilization

**Simplified Data Model**
- Streamlined stage criteria structure
- Removed redundant fields for clearer data models
- Improved API consistency

**Enhanced REST API**
- Updated REST endpoints to support new features
- Improved request/response patterns
- Better validation and error handling

### 🔄 Migration Notes

**For Existing Users:**
- The legacy `/evaluate` endpoint continues to work with `bucketingKey` for backward compatibility
- New integrations should use the OFREP endpoint at `/ofrep/v1/evaluate/flags/{key}` with `targetingKey`
- Review approval policies if using deployment workflows
- Check targeting rules if using multi-variant features

**Breaking Changes:**
- Evaluation contexts should use `targetingKey` instead of `bucketingKey` (backward compatible via alias)
- Some evaluation reasons and error codes have changed to align with OFREP standards
- Cached evaluations now return original evaluation reasons instead of "CACHED"

### 📚 Updated Documentation

- OpenFeature alignment analysis documentation
- Enhanced API documentation with OFREP endpoints
- Updated OpenAPI documentation
- Improved inline code documentation

---

## Version 0.0.13-alpha

Previous release focusing on core feature flag functionality and basic targeting capabilities.

---

## Version 0.0.11-alpha

Earlier release with foundational UI components and basic feature management.

---

**Note**: FluxGate is currently in **beta**. While we strive for stability, breaking changes may occur between alpha releases as we refine the platform based on user feedback.

For detailed implementation notes and development information, see the main [README](../ReadME.md) and [CLAUDE.md](../CLAUDE.md) files.
