# FluxGate Kubernetes Kustomize Configuration

This directory contains Kustomize configurations for deploying FluxGate to Kubernetes across different environments.

## Directory Structure

```
k8s/
├── base/                           # Base configurations (common across all environments)
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── edge-deployment.yaml
│   ├── edge-service.yaml
│   ├── ui-deployment.yaml
│   ├── ui-service.yaml
│   ├── configmap-backend.yaml
│   ├── secret-db.yaml
│   └── ingress.yaml
└── overlays/                       # Environment-specific configurations
    ├── dev/
    │   └── kustomization.yaml      # Development environment (1 replica, latest images)
    ├── staging/
    │   └── kustomization.yaml      # Staging environment (2 replicas, versioned images)
    └── production/
        └── kustomization.yaml      # Production environment (3-5 replicas, health checks)
```

## Prerequisites

1. **Install Kustomize**:
   ```bash
   # macOS
   brew install kustomize

   # Linux
   curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash

   # Or use kubectl (built-in kustomize)
   kubectl version  # Kustomize is built into kubectl 1.14+
   ```

2. **Kubernetes Cluster**: Ensure you have access to a Kubernetes cluster
   ```bash
   kubectl cluster-info
   ```

3. **NGINX Ingress Controller**: Install if not already present
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml
   ```

## Quick Start

### Preview Generated Manifests

Before applying, preview what will be deployed:

```bash
# Development
kubectl kustomize overlays/dev

# Staging
kubectl kustomize overlays/staging

# Production
kubectl kustomize overlays/production
```

### Deploy to an Environment

```bash
# Deploy to Development
kubectl apply -k overlays/dev

# Deploy to Staging
kubectl apply -k overlays/staging

# Deploy to Production
kubectl apply -k overlays/production
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n fluxgate

# Check services
kubectl get svc -n fluxgate

# Check ingress
kubectl get ingress -n fluxgate

# Follow logs
kubectl logs -f deployment/fluxgate-backend -n fluxgate
kubectl logs -f deployment/fluxgate-edge -n fluxgate
kubectl logs -f deployment/fluxgate-ui -n fluxgate
```

## Environment Configurations

### Development (dev)

**Characteristics:**
- **Replicas**: 1 for all services (minimal resource usage)
- **Images**: `latest` tag (always pulls newest)
- **Database**: Local/development database
- **Name Prefix**: `dev-`
- **Resource Limits**: None (for faster development)

**Usage:**
```bash
kubectl apply -k overlays/dev
kubectl get pods -n fluxgate -l environment=dev
```

### Staging (staging)

**Characteristics:**
- **Replicas**: 2 for all services
- **Images**: Versioned tags (e.g., `v0.0.8-alpha`)
- **Database**: Staging database
- **Name Prefix**: `staging-`
- **Resource Limits**: Moderate (256-512Mi memory, 100-500m CPU)

**Usage:**
```bash
kubectl apply -k overlays/staging
kubectl get pods -n fluxgate -l environment=staging
```

### Production (production)

**Characteristics:**
- **Replicas**: 3-5 (backend: 3, edge: 5, ui: 3)
- **Images**: Stable versioned tags with `IfNotPresent` pull policy
- **Database**: Production database (external managed service recommended)
- **Name Prefix**: `prod-`
- **Resource Limits**: Production-ready (512Mi-1Gi memory, 250m-1000m CPU)
- **Health Checks**: Liveness and readiness probes configured
- **Monitoring**: Prometheus scrape annotations

**Usage:**
```bash
kubectl apply -k overlays/production
kubectl get pods -n fluxgate -l environment=production
```

## Configuration Customization

### Updating Secrets

**Important**: The database secrets should be managed externally in production (use Sealed Secrets, External Secrets Operator, or HashiCorp Vault).

For development/testing, edit the overlay kustomization:

```yaml
# overlays/dev/kustomization.yaml
secretGenerator:
  - name: fluxgate-db
    behavior: merge
    literals:
      - DATABASE_URL=postgres://user:pass@host:5432/dbname
```

### Updating Image Versions

Edit the overlay kustomization to change image tags:

```yaml
# overlays/production/kustomization.yaml
patches:
  - target:
      kind: Deployment
      name: fluxgate-backend
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/image
        value: keaz/flux-gate-backend:v0.0.9-alpha  # Update version
```

### Updating ConfigMaps

Modify backend configuration in overlays:

```yaml
# overlays/production/kustomization.yaml
configMapGenerator:
  - name: fluxgate-backend-config
    behavior: merge
    literals:
      - config.toml=|
          allowed_origin = "https://your-domain.com"
          http_addr = "0.0.0.0:8080"
          grpc_addr = "0.0.0.0:50051"
```

### Adjusting Replicas

Edit the deployment patch in your overlay:

```yaml
patches:
  - target:
      kind: Deployment
      name: fluxgate-edge
    patch: |-
      - op: replace
        path: /spec/replicas
        value: 10  # Scale to 10 replicas
```

Apply the changes:
```bash
kubectl apply -k overlays/production
```

## Common Operations

### Scale Deployments

```bash
# Using kubectl directly
kubectl scale deployment/prod-fluxgate-edge -n fluxgate --replicas=10

# Or update kustomization and reapply
kubectl apply -k overlays/production
```

### Update Configuration

1. Edit the overlay kustomization file
2. Apply changes:
   ```bash
   kubectl apply -k overlays/production
   ```
3. Restart pods if needed:
   ```bash
   kubectl rollout restart deployment/prod-fluxgate-backend -n fluxgate
   ```

### View Differences

```bash
# Compare current state with what would be applied
kubectl diff -k overlays/production
```

### Delete Environment

```bash
# Delete all resources in an overlay
kubectl delete -k overlays/dev

# Delete only the namespace (cascades to all resources)
kubectl delete namespace fluxgate
```

## Environment Variables

### Backend
- `DATABASE_URL`: PostgreSQL connection string (from secret)

### Edge Server
- `EDGE_BACKEND_GRPC`: Backend gRPC endpoint
- `EDGE_HTTP_ADDR`: HTTP server bind address
- `EDGE_CLIENT_ID`: Client ID for authentication (update in base or overlay)
- `EDGE_CLIENT_SECRET`: Client secret (update in base or overlay)
- `EDGE_ASSIGNMENT_FLUSH_SECS`: Flush interval for sticky assignments
- `EDGE_EVALUATION_FLUSH_SECS`: Flush interval for evaluation events

### UI
- `BACKEND_HOST`: Backend API hostname
- `BACKEND_PORT`: Backend API port
- `BACKEND_PROTOCOL`: http or https
- `WS_PROTOCOL`: ws or wss (for GraphQL subscriptions)

## Ingress Configuration

The default ingress configuration exposes three hosts:

- **fluxgate.example.com**: UI
- **api.fluxgate.example.com**: Backend GraphQL API
- **edge.fluxgate.example.com**: Edge evaluation service

Update hosts in `base/ingress.yaml` or create overlay patches:

```yaml
# overlays/production/ingress-patch.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fluxgate
  namespace: fluxgate
spec:
  rules:
    - host: fluxgate.yourdomain.com
      # ... rest of config
```

Then reference in kustomization:
```yaml
patchesStrategicMerge:
  - ingress-patch.yaml
```

## Monitoring and Health Checks

Production overlay includes health probes:

### Backend
- **Liveness**: `GET /graphql` on port 8080
- **Readiness**: `GET /graphql` on port 8080

### Edge Server
- **Liveness**: `GET /health` on port 8081
- **Readiness**: `GET /health` on port 8081

### UI
- No health checks configured (static content)

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n fluxgate

# Describe pod for events
kubectl describe pod <pod-name> -n fluxgate

# Check logs
kubectl logs <pod-name> -n fluxgate
```

### ConfigMap/Secret Not Updated

Pods need to be restarted after ConfigMap/Secret changes:

```bash
kubectl rollout restart deployment/prod-fluxgate-backend -n fluxgate
```

### Ingress Not Working

```bash
# Check ingress
kubectl describe ingress fluxgate -n fluxgate

# Check nginx controller logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller
```

## Best Practices

1. **Version Control**: Commit all kustomization changes to Git
2. **Secret Management**: Use external secret management in production (Sealed Secrets, Vault, etc.)
3. **Image Tags**: Use specific version tags in staging/production, avoid `latest`
4. **Resource Limits**: Always set resource requests/limits in production
5. **Health Checks**: Configure liveness and readiness probes
6. **GitOps**: Consider using ArgoCD or Flux for automated deployments
7. **Validation**: Always run `kubectl kustomize` before applying to validate syntax

## CI/CD Integration

### GitLab CI Example

```yaml
deploy:
  stage: deploy
  script:
    - kubectl apply -k k8s/overlays/$ENVIRONMENT
  only:
    - main
```

### GitHub Actions Example

```yaml
- name: Deploy to Kubernetes
  run: |
    kubectl apply -k k8s/overlays/${{ env.ENVIRONMENT }}
```

## Additional Resources

- [Kustomize Documentation](https://kustomize.io/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [FluxGate Project README](../README.md)
- [FluxGate Product Guide](../FluxGate-Product-Guide.md)

## Migration from Plain YAML

The original YAML files are preserved in the `k8s/` directory. The kustomize structure provides:

- **DRY principle**: Base configurations shared across environments
- **Environment isolation**: Clear separation of dev/staging/production configs
- **Patch-based customization**: Override specific fields without duplicating entire files
- **Built-in transformations**: Common labels, name prefixes, namespace management
- **GitOps-friendly**: Easy to track and review configuration changes

To migrate back to plain YAML if needed:
```bash
kubectl kustomize overlays/production > fluxgate-production.yaml
```
