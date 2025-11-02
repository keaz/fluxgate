# TLS Certificate Setup for FluxGate

This document describes the TLS certificate configuration for FluxGate Kubernetes deployment.

## Overview

FluxGate uses TLS certificates to enable HTTPS access, which is required for:
- Secure communication between components
- Browser APIs like `navigator.clipboard` that require secure contexts
- WebSocket Secure (WSS) connections for GraphQL subscriptions

## Certificate Files

### Base Configuration
- **TLS Secret**: `base/tls-secret.yaml`
  - Contains the TLS certificate and private key
  - Automatically included in all overlays (dev, staging, production)

### Generated Files (Local Development)
- `fluxgate-tls.crt` - Self-signed certificate (not committed to git)
- `fluxgate-tls.key` - Private key (not committed to git)

## Domains Covered

The self-signed certificate covers the following domains:
- `fluxgate.example.com` - UI
- `api.fluxgate.example.com` - GraphQL API
- `edge.fluxgate.example.com` - Edge evaluation server
- `*.fluxgate.example.com` - Wildcard for any subdomain

## Environment Configuration

### Development (overlays/dev/)
- **Protocol**: HTTPS (port 443)
- **WebSocket**: WSS
- **CORS Origin**: `https://fluxgate.example.com`
- **Replicas**: 1 per component

### Staging (overlays/staging/)
- **Protocol**: HTTPS (port 443)
- **WebSocket**: WSS
- **CORS Origin**: `https://staging.fluxgate.example.com`
- **Replicas**: Backend: 3, Edge: 1, UI: 2
- **Note**: Requires separate certificate for staging subdomain in production

### Production (overlays/production/)
- **Protocol**: HTTPS (port 443)
- **WebSocket**: WSS
- **CORS Origin**: `https://fluxgate.example.com`
- **Replicas**: Backend: 3, Edge: 1, UI: 3
- **Note**: Replace with valid CA-signed certificate

## Regenerating Certificates (Local Development)

If you need to regenerate the certificate (e.g., adding new domains):

```bash
# Generate new certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout fluxgate-tls.key \
  -out fluxgate-tls.crt \
  -subj "/CN=fluxgate.example.com/O=FluxGate" \
  -addext "subjectAltName = DNS:fluxgate.example.com,DNS:api.fluxgate.example.com,DNS:edge.fluxgate.example.com,DNS:*.fluxgate.example.com"

# Create Kubernetes secret manifest
kubectl create secret tls fluxgate-tls \
  --cert=fluxgate-tls.crt \
  --key=fluxgate-tls.key \
  -n fluxgate \
  --dry-run=client -o yaml > base/tls-secret.yaml

# Apply the updated configuration
kubectl apply -k overlays/dev/
```

## Trusting the Self-Signed Certificate

For local development, you must trust the self-signed certificate in your browser/system:

### macOS
```bash
# Add to system keychain
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain fluxgate-tls.crt

# Or manually: Double-click fluxgate-tls.crt and mark as "Always Trust"
```

### Linux
```bash
# Chrome/Chromium
sudo cp fluxgate-tls.crt /usr/local/share/ca-certificates/fluxgate.crt
sudo update-ca-certificates

# Firefox: Settings → Privacy & Security → Certificates → View Certificates → Import
```

### Windows
```powershell
# Run as Administrator
certutil -addstore -f "ROOT" fluxgate-tls.crt
```

## Production Considerations

### Using Let's Encrypt with cert-manager

For production, use cert-manager to automatically provision and renew certificates:

```yaml
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

### Update Ingress for cert-manager

Add annotations to the ingress:

```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
  cert-manager.io/acme-challenge-type: http01
```

### Using Cloud Provider Certificates

For AWS, GCP, or Azure, use their managed certificate services:
- **AWS**: ACM (AWS Certificate Manager) with ALB Ingress Controller
- **GCP**: Google-managed SSL certificates
- **Azure**: Application Gateway with Azure Key Vault certificates

## Verification

After applying the configuration, verify TLS is working:

```bash
# Check ingress
kubectl get ingress -n fluxgate

# Verify TLS secret exists
kubectl get secret fluxgate-tls -n fluxgate

# Test HTTPS endpoint
curl -k https://fluxgate.example.com
curl -k https://api.fluxgate.example.com/graphql
curl -k https://edge.fluxgate.example.com/health
```

## Troubleshooting

### Mixed Content Errors
If you see "(blocked:mixed-content)" errors:
- Verify UI environment variables use `https` and `wss`
- Check backend CORS origin uses `https://`
- Ensure ingress TLS is properly configured

### Certificate Not Trusted
If browser shows "Not Secure":
- Ensure certificate is added to system trust store
- Restart browser after trusting certificate
- Check certificate domains match the URL

### WebSocket Connection Failed
If WSS connections fail:
- Verify `WS_PROTOCOL=wss` in UI deployment
- Check ingress WebSocket annotations
- Ensure port 443 is accessible

## Security Notes

⚠️ **IMPORTANT**:
- Self-signed certificates are for **local development only**
- Never use self-signed certificates in production
- Keep private keys secure and never commit them to version control
- Rotate certificates regularly
- Use proper secret management (Sealed Secrets, Vault, etc.) for production
