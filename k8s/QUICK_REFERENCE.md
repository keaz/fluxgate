# Quick Reference: Updated Kustomize Configurations

## Key Changes Summary

### Backend (3 instances with cluster enabled in staging/production)
```yaml
Replicas: 
  - dev: 1 (cluster disabled)
  - staging: 3 (cluster enabled)
  - production: 3 (cluster enabled)

Ports:
  - 8080: HTTP/GraphQL API
  - 50051: gRPC for edge servers
  - 6000: Cluster replication (NEW)

Config (config.toml):
  - JWT secret (NEW)
  - Cluster settings (NEW - enabled in staging/prod)
  - Database-backed peer discovery (NEW)
```

### Edge Server (1 instance, config file-based)
```yaml
Replicas: 1 (all environments)

Port:
  - 8081: HTTP evaluation API

Config (config.toml - NEW format):
  - gRPC connection settings
  - Flush intervals
  - Retry configuration
  - Stream reconnection settings

Migration: Environment variables → config.toml file
```

## Quick Deploy Commands

```bash
# Preview what will be deployed
kubectl kustomize overlays/dev
kubectl kustomize overlays/staging
kubectl kustomize overlays/production

# Deploy to environment
kubectl apply -k overlays/dev
kubectl apply -k overlays/staging       # 3 backend + 1 edge
kubectl apply -k overlays/production    # 3 backend + 1 edge

# Check deployment status
kubectl get pods -n fluxgate
kubectl get svc -n fluxgate

# Follow logs
kubectl logs -f deployment/staging-fluxgate-backend -n fluxgate
kubectl logs -f deployment/staging-fluxgate-edge -n fluxgate
```

## Cluster Verification

```bash
# Check all backend pods are running
kubectl get pods -n fluxgate -l app=fluxgate-backend

# Expected output for staging/production:
# staging-fluxgate-backend-xxxxx   1/1   Running
# staging-fluxgate-backend-xxxxx   1/1   Running
# staging-fluxgate-backend-xxxxx   1/1   Running

# Check cluster port is exposed
kubectl describe svc staging-fluxgate-backend -n fluxgate | grep -A 10 "Port:"

# Check cluster logs
kubectl logs deployment/staging-fluxgate-backend -n fluxgate | grep -i cluster
```

## Configuration Files

### Base
- `base/backend-deployment.yaml` - 3 replicas, cluster port 6000
- `base/backend-service.yaml` - Exposes ports 8080, 50051, 6000
- `base/configmap-backend.yaml` - JWT + cluster config (commented)
- `base/configmap-edge.yaml` - NEW: Full edge config.toml
- `base/edge-deployment.yaml` - 1 replica, uses ConfigMap

### Overlays
- `overlays/dev/` - 1 backend (no cluster), 1 edge
- `overlays/staging/` - 3 backend (cluster ON), 1 edge
- `overlays/production/` - 3 backend (cluster ON), 1 edge

## Before Production Deploy

✅ Update in production overlay:
1. JWT secret in backend config
2. Edge client credentials (client_id, client_secret)
3. Database connection string
4. Consider using external secret management

## Files Modified
- ✅ `base/backend-deployment.yaml`
- ✅ `base/backend-service.yaml`
- ✅ `base/configmap-backend.yaml`
- ✅ `base/configmap-edge.yaml` (NEW)
- ✅ `base/edge-deployment.yaml`
- ✅ `base/kustomization.yaml`
- ✅ `overlays/dev/kustomization.yaml`
- ✅ `overlays/staging/kustomization.yaml`
- ✅ `overlays/production/kustomization.yaml`
