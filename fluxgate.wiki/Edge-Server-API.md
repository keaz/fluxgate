# Edge Server API Reference

The FluxGate Edge Server provides a fast, cached evaluation API for checking feature flags in your applications.

## Base URL

The edge server runs on port `8081` by default:
```
http://localhost:8081
```

In production, this would be your edge server's hostname:
```
https://edge.fluxgate.example.com
```

## API Endpoints

### 1. Evaluate Feature

Evaluate a feature flag for a specific user/context.

**Endpoint:** `POST /evaluate`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "flagKey": "string",
  "context": {
    "bucketingKey": "string",
    "environment_id": "string",
    "...any other attributes": "string"
  },
  "client_id": "string (optional)",
  "client_secret": "string (optional)"
}
```

**Required Parameters:**
- `flagKey`: The feature's unique key/identifier
- `context.bucketingKey`: User identifier for consistent bucketing (e.g., userId)
- `context.environment_id`: UUID of the environment (dev, staging, prod)

**Optional Parameters:**
- `context.*`: Any additional user attributes (role, tier, region, etc.)
- `client_id`: Override server's default client ID
- `client_secret`: Override server's default client secret

**Response Format:**
```json
{
  "flagKey": "string",
  "value": any,
  "variant": "string or null",
  "reason": "string",
  "errorCode": "string or null (optional)",
  "metadata": "object (optional)"
}
```

**Response Fields:**
- `flagKey`: The feature key that was evaluated
- `value`: The resolved value (boolean, string, number, or JSON object)
- `variant`: The variant name that was served (null if no variant)
- `reason`: Evaluation reason (`STATIC`, `DISABLED`, `DEFAULT`, `CACHED`, `TARGETED_MATCH`, etc.)
- `errorCode`: Error code if evaluation failed (`FLAG_NOT_FOUND`, `ENVIRONMENT_NOT_FOUND`, etc.)
- `metadata`: Optional additional information about the evaluation

### 2. Health Check

Check if the edge server is healthy and connected to the backend.

**Endpoint:** `GET /health`

**Response:**
```
OK
```
HTTP Status: `200` (if healthy) or `503` (if unavailable)

### 3. API Documentation

Interactive Swagger UI for API exploration.

**Endpoint:** `GET /docs`

Opens interactive API documentation in your browser.

## Request Examples

### Example 1: Simple Boolean Flag

**Scenario:** Check if new checkout flow is enabled for a user.

**Request:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "new_checkout_flow",
    "context": {
      "bucketingKey": "user-12345",
      "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
      "userId": "12345",
      "tier": "premium"
    }
  }'
```

**Response (Feature Enabled):**
```json
{
  "flagKey": "new_checkout_flow",
  "value": true,
  "variant": null,
  "reason": "TARGETED_MATCH"
}
```

**Response (Feature Disabled):**
```json
{
  "flagKey": "new_checkout_flow",
  "value": false,
  "variant": null,
  "reason": "DISABLED"
}
```

**In your code:**
```javascript
if (response.value === true) {
  // Show new checkout flow
} else {
  // Show old checkout flow
}
```

### Example 2: String Variant (Button Text)

**Scenario:** Get button text variant for A/B test.

**Request:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "checkout_button_text",
    "context": {
      "bucketingKey": "user-67890",
      "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
      "userId": "67890",
      "region": "US"
    }
  }'
```

**Response:**
```json
{
  "flagKey": "checkout_button_text",
  "value": "Get Started Today",
  "variant": "variant-a",
  "reason": "TARGETED_MATCH"
}
```

**In your code:**
```javascript
const buttonText = response.value || "Buy Now";
console.log("Showing variant:", response.variant);
```

### Example 3: Number Variant (Pricing)

**Scenario:** Get pricing based on user segment.

**Request:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "subscription_price",
    "context": {
      "bucketingKey": "user-11111",
      "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
      "userId": "11111",
      "tier": "new_user",
      "region": "US"
    }
  }'
```

**Response:**
```json
{
  "flagKey": "subscription_price",
  "value": 7.99,
  "variant": "new-user-discount",
  "reason": "TARGETED_MATCH"
}
```

**In your code:**
```javascript
const price = typeof response.value === 'number' ? response.value : 9.99;
```

### Example 4: JSON Variant (Configuration)

**Scenario:** Get feature configuration based on user region.

**Request:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "api_timeout_config",
    "context": {
      "bucketingKey": "user-22222",
      "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
      "userId": "22222",
      "region": "APAC"
    }
  }'
```

**Response:**
```json
{
  "flagKey": "api_timeout_config",
  "value": {
    "timeout_ms": 15000,
    "retry_count": 5,
    "cache_ttl": 600
  },
  "variant": "apac-config",
  "reason": "TARGETED_MATCH"
}
```

**In your code:**
```javascript
const config = response.value || {
  timeout_ms: 5000,
  retry_count: 3,
  cache_ttl: 300
};
```

### Example 5: Feature Not Found

**Scenario:** Feature doesn't exist in the system.

**Request:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "nonexistent_feature",
    "context": {
      "bucketingKey": "user-33333",
      "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017"
    }
  }'
```

**Response:**
```json
{
  "flagKey": "nonexistent_feature",
  "value": false,
  "variant": null,
  "reason": "DEFAULT",
  "errorCode": "FLAG_NOT_FOUND"
}
```

### Example 6: Cached Result

**Scenario:** User previously evaluated, result served from cache.

**Request:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "premium_features",
    "context": {
      "bucketingKey": "user-44444",
      "environment_id": "78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017",
      "userId": "44444"
    }
  }'
```

**Response:**
```json
{
  "flagKey": "premium_features",
  "value": true,
  "variant": "premium-enabled",
  "reason": "CACHED"
}
```

## Context Attributes

The `context` object contains attributes about the user or request. Common attributes:

| Attribute | Example | Purpose |
|-----------|---------|---------|
| `bucketingKey` | `"user-12345"` | **Required** - User identifier for consistent bucketing |
| `environment_id` | `"78ccc5d7..."` | **Required** - Environment UUID |
| `userId` | `"12345"` | User's unique ID |
| `email` | `"user@example.com"` | User's email |
| `tier` | `"premium"` | Subscription tier |
| `role` | `"admin"` | User role |
| `region` | `"US"` | Geographic region |
| `country` | `"United States"` | Country name |
| `browser` | `"Chrome"` | Browser type |
| `device` | `"mobile"` | Device type |
| `version` | `"2.1.0"` | App version |
| `custom` | `"any-value"` | Any custom attribute |

**Note:** You can include any attributes that match your targeting rules defined in the FluxGate UI.

## Evaluation Reasons

| Reason | Description |
|--------|-------------|
| `TARGETED_MATCH` | User matched a targeting rule |
| `CACHED` | Result served from cache (user previously evaluated) |
| `STATIC` | Feature globally disabled (kill switch) |
| `DISABLED` | Feature disabled for this environment |
| `DEFAULT` | No matching rule, returning default (false) |

## Error Codes

| Error Code | Description |
|------------|-------------|
| `FLAG_NOT_FOUND` | Feature doesn't exist |
| `ENVIRONMENT_NOT_FOUND` | Environment doesn't exist for this feature |

## Performance

The edge server is optimized for speed:
- **Sub-10ms evaluation** with in-memory caching
- **No database queries** during evaluation
- **Consistent results** via deterministic bucketing
- **Real-time updates** from backend via streaming

## SDK Integration

### JavaScript/Node.js

```javascript
async function evaluateFeature(flagKey, userId, additionalContext = {}) {
  const response = await fetch('http://localhost:8081/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      flagKey: flagKey,
      context: {
        bucketingKey: userId,
        environment_id: process.env.FLUXGATE_ENV_ID,
        userId: userId,
        ...additionalContext
      }
    })
  });
  return response.json();
}

// Usage
const result = await evaluateFeature('new_checkout', 'user-12345', {
  tier: 'premium',
  region: 'US'
});

if (result.value === true) {
  console.log('Feature enabled, variant:', result.variant);
  console.log('Reason:', result.reason);
}
```

### Python

```python
import requests
import os

def evaluate_feature(flag_key, user_id, **context):
    url = "http://localhost:8081/evaluate"
    payload = {
        "flagKey": flag_key,
        "context": {
            "bucketingKey": user_id,
            "environment_id": os.getenv("FLUXGATE_ENV_ID"),
            "userId": user_id,
            **context
        }
    }
    response = requests.post(url, json=payload)
    return response.json()

# Usage
result = evaluate_feature("new_checkout", "user-12345", tier="premium", region="US")
if result["value"] == True:
    print(f"Feature enabled, variant: {result['variant']}")
    print(f"Reason: {result['reason']}")
```

### Java (Spring Boot)

See [Spring Boot Starter](../fluxgate-spring/fluxgate-spring-boot-starter/README.md) for full integration guide.

```java
@Autowired
private FluxGateClient fluxGateClient;

public void checkFeature() {
    Map<String, String> context = Map.of(
        "userId", "12345",
        "tier", "premium",
        "region", "US"
    );
    
    boolean enabled = fluxGateClient.evaluateFeature(
        "new_checkout",
        environmentId,
        context
    );
}
```

### Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

type EvaluateRequest struct {
    FlagKey string                 `json:"flagKey"`
    Context map[string]interface{} `json:"context"`
}

type EvaluateResponse struct {
    FlagKey   string      `json:"flagKey"`
    Value     interface{} `json:"value"`
    Variant   *string     `json:"variant"`
    Reason    string      `json:"reason"`
    ErrorCode *string     `json:"errorCode,omitempty"`
}

func evaluateFeature(flagKey, userID string, attrs map[string]string) (*EvaluateResponse, error) {
    context := map[string]interface{}{
        "bucketingKey":   userID,
        "environment_id": os.Getenv("FLUXGATE_ENV_ID"),
        "userId":         userID,
    }
    for k, v := range attrs {
        context[k] = v
    }
    
    reqBody, _ := json.Marshal(EvaluateRequest{
        FlagKey: flagKey,
        Context: context,
    })
    
    resp, err := http.Post("http://localhost:8081/evaluate", "application/json", bytes.NewBuffer(reqBody))
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result EvaluateResponse
    json.NewDecoder(resp.Body).Decode(&result)
    return &result, nil
}

// Usage
result, _ := evaluateFeature("new_checkout", "user-12345", map[string]string{
    "tier": "premium",
    "region": "US",
})
```

## Best Practices

### 1. Cache Edge URL
Store your edge server URL in environment configuration:
```bash
FLUXGATE_EDGE_URL=https://edge.fluxgate.example.com
FLUXGATE_ENV_ID=78ccc5d7-e1bb-4e41-b6ef-02adf5c0d017
```

### 2. Handle Errors Gracefully
Always provide fallback behavior if evaluation fails:
```javascript
try {
  const result = await evaluateFeature('new_feature', userId);
  return result.value;
} catch (error) {
  console.error('Feature evaluation failed:', error);
  return false; // Safe default
}
```

### 3. Use Consistent Bucketing Keys
Always use the same bucketing key for the same user:
- ✅ Good: Always use `userId` or `sessionId`
- ❌ Bad: Using different keys for the same user

### 4. Include Relevant Context
Only send context attributes used in targeting rules:
```javascript
// ✅ Good - only relevant attributes
{
  bucketingKey: "user-123",
  environment_id: "env-uuid",
  tier: "premium",
  region: "US"
}

// ❌ Bad - unnecessary sensitive data
{
  bucketingKey: "user-123",
  environment_id: "env-uuid",
  password: "...",
  ssn: "...",
  credit_card: "..."
}
```

### 5. Monitor Performance
Track evaluation latency in your application:
```javascript
const start = Date.now();
const result = await evaluateFeature('feature_key', userId);
const duration = Date.now() - start;
// Log or report duration
console.log(`Evaluation took ${duration}ms, reason: ${result.reason}`);
```

### 6. Check Evaluation Reason
Use the `reason` field for debugging and monitoring:
```javascript
const result = await evaluateFeature('feature_key', userId);
if (result.reason === 'CACHED') {
  // Fast path - served from cache
} else if (result.reason === 'TARGETED_MATCH') {
  // Evaluated against targeting rules
} else if (result.errorCode) {
  // Handle error
  console.error(`Error: ${result.errorCode}`);
}
```

## Troubleshooting

### Issue: Getting `FLAG_NOT_FOUND`
**Solution:** Verify the feature exists and the `flagKey` is correct.

### Issue: Getting `ENVIRONMENT_NOT_FOUND`
**Solution:** Check that the `environment_id` is correct and the feature is configured for that environment.

### Issue: Always getting `false`
**Possible causes:**
- Feature is disabled for the environment
- Kill switch is enabled (`reason: "STATIC"`)
- User doesn't match any targeting rules

**Solution:** Check feature configuration in FluxGate UI.

### Issue: Inconsistent results for same user
**Possible cause:** Using different `bucketingKey` values for the same user.

**Solution:** Always use the same bucketing key for the same user.

## Related Topics

- [Feature Variants](Feature-Variants.md) - Using variants in your application
- [Priority-Based Targeting](Priority-Evaluation.md) - How rules are evaluated
- [Spring Boot Integration](../fluxgate-spring/fluxgate-spring-boot-starter/README.md) - Java SDK
