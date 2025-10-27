# Kustomize Configuration Update Summary

## Overview
Updated Kustomize configurations to support the new feature-toggle-backend and feature-edge-server configurations with cluster replication and config file-based settings.

## Changes Made

### 1. Backend Deployment (`base/backend-deployment.yaml`)
- **Updated replicas**: Changed from 1 to 3 instances (for cluster support)
- **Added cluster port**: Added containerPort 6000 for cluster replication
- Configuration now mounted from ConfigMap (existing)

### 2. Backend Service (`base/backend-service.yaml`)
- **Added cluster port**: Exposed port 6000 for inter-node cluster communication
- Ports now available:
  - `8080`: HTTP/GraphQL API
  - `50051`: gRPC for edge servers
  - `6000`: Cluster replication

### 3. Backend ConfigMap (`base/configmap-backend.yaml`)
- **Added JWT secret configuration**: For token signing and verification
- **Added cluster configuration section**: 
  - Commented out by default in base
  - Includes cluster settings and discovery configuration
- Configuration structure now matches the Rust backend's config.toml format

### 4. Edge Server ConfigMap (NEW: `base/configmap-edge.yaml`)
- **Created new ConfigMap** for edge server configuration
- Migrated from environment variables to config.toml format
- Includes all new edge server settings:
  - gRPC connection settings (timeouts, keepalive, concurrency)
  - Flush intervals for assignments and evaluations
  - Retry settings with exponential backoff
  - Stream reconnection configuration

### 5. Edge Deployment (`base/edge-deployment.yaml`)
- **Updated to use ConfigMap**: Removed environment variables
- **Changed replicas**: Set to 1 instance (as requested)
- Configuration now mounted from `fluxgate-edge-config` ConfigMap

### 6. Base Kustomization (`base/kustomization.yaml`)
- **Added reference**: to new `configmap-edge.yaml` resource

## Environment-Specific Configurations

### Development Overlay (`overlays/dev/`)
- **Backend**: 1 replica (cluster disabled)
- **Edge**: 1 replica
- **Backend config**: Basic JWT secret for dev
- **Edge config**: Uses test client credentials (`a1b2c3d4-0000-4000-8000-000000000001`)
- Backend references: `dev-fluxgate-backend:50051`

### Staging Overlay (`overlays/staging/`)
- **Backend**: 3 replicas with **cluster enabled**
- **Edge**: 1 replica
- **Backend config**: 
  - Cluster replication enabled
  - JWT secret placeholder (to be changed)
  - Database-backed peer discovery configured
- **Edge config**: Placeholder credentials (to be changed)
- Resource limits: Moderate (256-512Mi memory)
- Backend references: `staging-fluxgate-backend:50051`

### Production Overlay (`overlays/production/`)
- **Backend**: 3 replicas with **cluster enabled**
- **Edge**: 1 replica
- **Backend config**:
  - Cluster replication enabled
  - JWT secret placeholder (use external secret management)
  - Database-backed peer discovery configured
- **Edge config**: Placeholder credentials (use external secret management)
- Resource limits: Production-ready (512Mi-1Gi memory)
- Health checks: Liveness and readiness probes configured
- Image pull policy: `IfNotPresent` for stability
- Backend references: `prod-fluxgate-backend:50051`

## Cluster Replication Settings

When cluster is enabled (staging/production), the backend instances will:
- Listen on port 6000 for cluster communication
- Use database-backed discovery (no external service discovery needed)
- Maintain heartbeat table in PostgreSQL
- Automatically discover and connect to peer nodes
- Handle node failures with configurable timeouts

### Cluster Configuration
```toml
[cluster]
enabled = true
listen_addr = "0.0.0.0:6000"
reconnect_delay_ms = 2000

[cluster.discovery]
heartbeat_interval_secs = 30    # Node heartbeat update frequency
stale_threshold_secs = 90       # When to consider a node dead
cleanup_interval_secs = 60      # Cleanup interval for stale nodes
```

## Edge Server Configuration

The edge server now uses a comprehensive config.toml with:

### gRPC Settings
- Connection and request timeouts
- TCP and HTTP/2 keepalive intervals
- Concurrency limits
- TCP_NODELAY optimization

### Flush Settings
- Assignment flush: 10 seconds
- Evaluation flush: 30 seconds

### Retry Settings
- Exponential backoff (500ms base delay)
- Max 3 attempts for direct calls
- Stream reconnection with progressive delays (1-30 seconds)

## Deployment Instructions

### Preview configurations
```bash
# Development
kubectl kustomize overlays/dev

# Staging (with 3 backend instances and cluster)
kubectl kustomize overlays/staging

# Production (with 3 backend instances and cluster)
kubectl kustomize overlays/production
```

### Deploy to environment
```bash
# Deploy to staging with cluster replication
kubectl apply -k overlays/staging

# Deploy to production with cluster replication
kubectl apply -k overlays/production
```

### Verify cluster communication
```bash
# Check backend pods (should see 3 replicas in staging/production)
kubectl get pods -n fluxgate -l app=fluxgate-backend

# Check logs for cluster connections
kubectl logs -f deployment/staging-fluxgate-backend -n fluxgate | grep cluster

# Check backend service (should expose port 6000)
kubectl describe svc staging-fluxgate-backend -n fluxgate
```

## Security Notes

⚠️ **IMPORTANT**: Before deploying to production:

1. **JWT Secret**: Replace `CHANGE_ME_PRODUCTION_JWT_SECRET_MINIMUM_32_CHARACTERS_LONG` with a secure random string (min 32 chars)
2. **Edge Credentials**: Replace `CHANGE_ME_PRODUCTION_CLIENT_ID` and `CHANGE_ME_PRODUCTION_CLIENT_SECRET` with actual client credentials
3. **Database Password**: Use external secret management (Sealed Secrets, External Secrets Operator, or Vault)
4. **Consider using**: Kubernetes Secrets with RBAC for sensitive values

## Testing Checklist

- [ ] Backend starts successfully with 3 replicas
- [ ] Backend instances discover each other via database
- [ ] Cluster port (6000) is accessible between pods
- [ ] Edge server connects to backend via gRPC
- [ ] Edge server health check (`/health`) responds
- [ ] Backend GraphQL endpoint (`/graphql`) responds
- [ ] Configuration changes trigger pod restarts correctly

## Rollback

To rollback to previous configuration:
```bash
kubectl delete -k overlays/staging
# Then redeploy previous version
```

## Next Steps

1. Update Docker images to latest versions when ready
2. Configure external secret management for production
3. Set up monitoring for cluster health
4. Configure HorizontalPodAutoscaler for edge servers if needed
5. Test cluster failover scenarios
