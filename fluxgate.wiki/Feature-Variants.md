# Feature Variants Guide

Feature Variants allow you to serve different values to different user segments, enabling A/B testing and multivariate experiments without code deployments.

## What are Feature Variants?

Instead of simple true/false flags, variants let you:
- Serve different **values** to different users
- Run **A/B tests** with multiple options
- Deliver **personalized experiences** based on user segments
- Test **configurations** without redeploying

## Supported Value Types

FluxGate supports four variant value types:

### 1. String Variants
Text values for copy testing, UI labels, or content variations.

**Example:**
```json
{
  "control": "Buy Now",
  "variant-a": "Get Started Today",
  "variant-b": "Start Free Trial"
}
```

### 2. Number Variants
Numeric values for pricing, thresholds, or limits.

**Example:**
```json
{
  "control": 9.99,
  "premium": 14.99,
  "enterprise": 29.99
}
```

### 3. Boolean Variants
Traditional on/off behavior.

**Example:**
```json
{
  "control": false,
  "enabled": true
}
```

### 4. JSON Variants
Complex configuration objects.

**Example:**
```json
{
  "control": {
    "color": "blue",
    "size": "medium",
    "animation": false
  },
  "variant-a": {
    "color": "green",
    "size": "large",
    "animation": true
  }
}
```

## Creating Feature Variants

### Step 1: Create the Feature
1. Navigate to **Features** page
2. Click **Create Feature**
3. Enter feature details (key, name, description)
4. Select feature type (Contextual recommended for variants)

### Step 2: Add Variants
1. In the feature creation form, locate **Variants** section
2. Click **Add Variant**
3. Enter variant details:
   - **Control**: Unique identifier (e.g., "control", "variant-a")
   - **Value**: The actual value to serve
   - **Type**: Select the appropriate type (string, number, boolean, json)
   - **Description**: Optional note about this variant

### Step 3: Configure Targeting
1. Add targeting rules (criteria) for each environment
2. For each rule, specify:
   - **Conditions**: User attributes to match (e.g., role=premium)
   - **Rollout %**: Percentage of matching users to receive this variant
   - **Serve**: Which variant to serve when rule matches
   - **Priority**: Order of evaluation (optional)

### Step 4: Deploy
1. Review your configuration
2. Click **Create** or **Save**
3. Feature is deployed to selected environments

## Example Use Cases

### UI Button Test
**Goal**: Test which button text drives more conversions

**Variants:**
- `control`: "Buy Now"
- `variant-a`: "Get Started"
- `variant-b`: "Try Free"

**Targeting:**
- Priority 0: All users → 33% each variant

**In Your App:**
```bash
curl -X POST http://localhost:8081/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "flagKey": "checkout_button_text",
    "context": {
      "bucketingKey": "user-12345",
      "environment_id": "prod-env-id",
      "userId": "12345"
    }
  }'
```

**Response:**
```json
{
  "flagKey": "checkout_button_text",
  "value": "Get Started",
  "variant": "variant-a",
  "reason": "TARGETED_MATCH"
}
```

### Pricing Tier Test
**Goal**: Test price sensitivity across user segments

**Variants:**
- `control`: 9.99
- `premium`: 14.99
- `value`: 7.99

**Targeting:**
- Priority 0: Premium users → serve "premium" (100%)
- Priority 1: New users → serve "value" (50%)
- Priority 2: All others → serve "control" (100%)

### Feature Configuration
**Goal**: Deliver different timeout settings to different regions

**Variants:**
```json
{
  "us-fast": {"timeout_ms": 5000, "retries": 3},
  "eu-standard": {"timeout_ms": 10000, "retries": 5},
  "apac-patient": {"timeout_ms": 15000, "retries": 7}
}
```

**Targeting:**
- Priority 0: region=US → serve "us-fast"
- Priority 1: region=EU → serve "eu-standard"
- Priority 2: region=APAC → serve "apac-patient"

## Best Practices

### 1. Always Have a Control Variant
Create a "control" variant representing your current production behavior. This serves as your baseline for comparison.

### 2. Use Meaningful Identifiers
Choose clear variant identifiers:
- ✅ Good: "control", "variant-a", "high-price", "blue-button"
- ❌ Bad: "v1", "test", "x", "abc"

### 3. Document Your Variants
Use the description field to explain:
- What the variant tests
- Expected impact
- When it was created

### 4. Start Small
Begin with 10-20% rollout, monitor results, then expand.

### 5. Monitor Performance
Use the Analytics dashboard to track:
- Evaluation rates per variant
- Success/failure rates
- Cache performance

### 6. Clean Up Old Variants
Remove variants from completed experiments to keep your feature configuration clean.

## Variant Evaluation Flow

When a user requests feature evaluation:

1. **Context Matching**: System checks targeting rules in priority order
2. **First Match Wins**: Evaluation stops at first matching rule
3. **Variant Lookup**: If rule specifies a variant to serve, that variant's value is returned
4. **Consistent Experience**: Same user always gets same variant (deterministic bucketing)

## Managing Variants in the UI

### Viewing Variants
- Navigate to **Features** page
- Click on a feature
- View all variants in the **Variants** section

### Editing Variants
- Click **Edit** on the feature
- Modify variant values or add new variants
- Click **Save**
- Changes propagate to edge servers within seconds

### Deleting Variants
1. Ensure no targeting rules reference the variant
2. Click **Delete** on the variant
3. Confirm deletion

## Troubleshooting

### Variant Not Returned
**Possible causes:**
- No targeting rule matches user context
- Rule doesn't specify which variant to serve
- Feature is disabled via kill switch

**Solution:** Check targeting rules and ensure at least one rule matches your user context.

### Wrong Variant Returned
**Possible causes:**
- Higher priority rule matched first
- Rollout percentage excludes this user
- User is in control group

**Solution:** Review priority order and rollout percentages in targeting rules.

### Variant Value Type Mismatch
**Possible causes:**
- Client expecting different type than stored
- JSON parsing error

**Solution:** Verify variant type matches your application's expectations.

## Related Topics

- [Priority-Based Targeting](Priority-Evaluation.md) - Control evaluation order
- [Edge Server API](Edge-Server-API.md) - API reference for evaluation
- [Analytics Dashboard](Analytics.md) - Monitor variant performance
