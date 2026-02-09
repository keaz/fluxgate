# Priority-Based Targeting

Priority-based targeting gives you precise control over the order in which targeting rules are evaluated, ensuring the right users get the right experience.

## What is Priority-Based Targeting?

Targeting rules (criteria) are evaluated in order based on their **priority value**:
- **Lower priority numbers** are evaluated **first**
- **First matching rule** determines the outcome
- Enables complex targeting scenarios with predictable results

## Why Order Matters

Without priority control, rule evaluation order is unpredictable. With priorities, you can ensure:
- Premium users always get premium features
- Regional rules override global defaults
- Specific segments get targeted experiences before falling back to defaults

### Example Scenario

**Without Priority:**
```
Rule A: Beta users → enabled (100%)
Rule B: Premium users → variant-premium
```
Problem: Premium users who are also beta users might match either rule randomly.

**With Priority:**
```
Priority 0: Premium users → variant-premium (100%)
Priority 1: Beta users → enabled (100%)
```
Result: Premium users always match first, even if they're also in beta program.

## How to Use Priorities

### Setting Priorities in the UI

#### Visual Drag-and-Drop
1. Navigate to your feature
2. Go to the environment's targeting rules
3. **Drag and drop** rules to reorder them
4. Rules at the **top** have **lower priority** (evaluated first)
5. Rules at the **bottom** have **higher priority** (evaluated last)

#### Manual Priority Assignment
1. Click **Edit** on a targeting rule
2. Set the **Priority** field (0, 1, 2, etc.)
3. Lower numbers = higher priority (evaluated first)
4. Click **Save**

### Default Behavior
- New rules automatically get the next available priority number
- Existing rules maintain their relative order when adding new ones

## Common Priority Patterns

### 1. Layered Targeting

Serve different variants to overlapping user segments.

```
Priority 0: Enterprise customers → premium-features (100%)
Priority 1: Team plan users → standard-features (100%)
Priority 2: Individual users → basic-features (50%)
Priority 3: Everyone else → disabled
```

**Why it works**: Enterprise customers get premium features even if they also match "Team plan" criteria.

### 2. Geographic Rollout

Roll out features by region with fallback.

```
Priority 0: region=US → enabled (100%)
Priority 1: region=EU → enabled (75%)
Priority 2: region=APAC → enabled (50%)
Priority 3: All others → enabled (10%)
```

**Why it works**: US users always get the feature, other regions have gradual rollouts.

### 3. VIP Treatment

Ensure VIPs always get special treatment.

```
Priority 0: userId in VIP_LIST → variant-vip (100%)
Priority 1: tier=premium → variant-premium (100%)
Priority 2: tier=standard → variant-standard (50%)
Priority 3: Everyone else → control (10%)
```

**Why it works**: VIP users get special variant regardless of their tier.

### 4. Feature Gates with Override

Allow manual overrides for specific users.

```
Priority 0: userId in BETA_TESTERS → enabled (100%)
Priority 1: tier=enterprise → enabled (50%)
Priority 2: All others → disabled
```

**Why it works**: Beta testers always get access, even if they don't have enterprise tier.

### 5. A/B Test with Control Group

Run experiments while excluding certain users.

```
Priority 0: userId in EXCLUSION_LIST → disabled
Priority 1: region=US → variant-a (33%), variant-b (33%), control (34%)
Priority 2: All others → disabled
```

**Why it works**: Excluded users never participate in the test.

## Best Practices

### 1. Start with Specific, End with General
Place most specific rules at **lower priority numbers** (top), general rules at **higher numbers** (bottom).

```
✅ Good:
Priority 0: userId=specific-user → variant-a
Priority 1: tier=premium → variant-b
Priority 2: All users → control

❌ Bad:
Priority 0: All users → control
Priority 1: tier=premium → variant-b  // Never evaluated!
Priority 2: userId=specific-user → variant-a  // Never evaluated!
```

### 2. Use Priority Gaps
Leave gaps between priority numbers for future insertions.

```
✅ Good: 0, 10, 20, 30 (can insert 15 between 10 and 20)
❌ OK but limiting: 0, 1, 2, 3
```

### 3. Document Rule Purpose
Add clear descriptions to each rule explaining why it has that priority.

### 4. Test Priority Changes
After reordering rules, test with sample user contexts to verify expected behavior.

### 5. Review Regularly
Periodically review priority order to ensure it still matches your business logic.

## Visual Priority Management

FluxGate's UI makes priority management intuitive:

### Drag-and-Drop Interface
- **Grab** the handle icon on the left of each rule
- **Drag** up or down to reorder
- **Drop** in the desired position
- Priority numbers **update automatically**

### Visual Indicators
- Rules are displayed in evaluation order (top to bottom)
- Priority numbers are shown for reference
- First matching rule is highlighted during simulation

### Real-Time Updates
- Changes propagate to edge servers immediately
- No deployment required
- Users see updated behavior within seconds

## Evaluation Flow

When evaluating a feature for a user:

1. **Sort Rules**: All targeting rules sorted by priority (ascending)
2. **Iterate**: Check each rule in order
3. **Match Test**: Does user's context match rule conditions?
4. **First Match**: If yes, return the result (variant or boolean)
5. **Stop**: Evaluation stops, remaining rules ignored
6. **No Match**: If no rules match, feature is disabled

## Troubleshooting

### Rule Never Matches
**Symptom**: Rule appears correct but never returns expected result.

**Possible causes:**
- Higher priority rule matches first
- User context doesn't actually match conditions
- Rollout percentage excludes this user

**Solution:**
1. Check rules with lower priority numbers
2. Verify user context values
3. Test with 100% rollout to eliminate percentage issues

### Wrong Variant Served
**Symptom**: User gets unexpected variant.

**Possible causes:**
- Higher priority rule specifies different variant
- Multiple rules match, first one wins

**Solution:**
1. Review all rules with priority < current rule
2. Ensure only intended rule matches user
3. Adjust priorities if needed

### Can't Reorder Rules
**Symptom**: Drag-and-drop doesn't work.

**Solution:**
- Ensure you're in edit mode
- Check browser console for errors
- Refresh page and try again
- Use manual priority field as fallback

## Advanced Scenarios

### Gradual Migration

Migrate users from old to new experience gradually.

```
Priority 0: rollout_group=early_adopters → new_experience (100%)
Priority 1: Random 25% → new_experience (25%)
Priority 2: Everyone else → old_experience
```

Over time, increase Priority 1 rollout: 25% → 50% → 75% → 100%

### Canary Release by Region

Test in one region before expanding.

```
Week 1:
Priority 0: region=US-WEST → new_version (10%)
Priority 1: All others → old_version

Week 2:
Priority 0: region=US-WEST → new_version (50%)
Priority 1: region=US-EAST → new_version (10%)
Priority 2: All others → old_version
```

### Persona-Based Variants

Serve different experiences to different user personas.

```
Priority 0: persona=developer → dev_focused_ui
Priority 1: persona=designer → design_focused_ui
Priority 2: persona=manager → analytics_focused_ui
Priority 3: Everyone else → default_ui
```

## Related Topics

- [Feature Variants](Feature-Variants.md) - Using variants with priorities
- [Edge Server API](Edge-Server-API.md) - How evaluation works
- [Analytics Dashboard](Analytics.md) - Monitor rule performance
