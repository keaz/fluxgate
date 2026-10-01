#!/bin/bash

# FluxGate Performance Test Data Cleanup Script

set -e

POSTGRES_CONTAINER="fluxgate-perf-postgres"
DB_USER="postgres"
DB_NAME="feature_toggle"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  FluxGate Performance Test Data Cleanup                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
    echo "❌ Error: PostgreSQL container '${POSTGRES_CONTAINER}' is not running"
    echo "   Start it with: docker-compose -f perf-test/docker-compose.base.yml up -d postgres"
    exit 1
fi

# Show current stats
echo "📊 Current Database State:"
echo "─────────────────────────────────────────────────────────────────"

STATS=$(docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} ${DB_NAME} -t -c "
SELECT
  COUNT(*) as total,
  MIN(CAST(SUBSTRING(key FROM 'feature=([0-9]+)') AS INTEGER)) as min_idx,
  MAX(CAST(SUBSTRING(key FROM 'feature=([0-9]+)') AS INTEGER)) as max_idx,
  (MAX(CAST(SUBSTRING(key FROM 'feature=([0-9]+)') AS INTEGER)) - MIN(CAST(SUBSTRING(key FROM 'feature=([0-9]+)') AS INTEGER)) + 1) - COUNT(*) as gaps
FROM features
WHERE key LIKE 'feature=%';
" 2>/dev/null | tr -d ' ')

IFS='|' read -r TOTAL MIN_IDX MAX_IDX GAPS <<< "$STATS"

echo "  Total Features: $TOTAL"
echo "  Index Range: feature=$MIN_IDX to feature=$MAX_IDX"
echo "  Gaps: $GAPS"
echo ""

# Confirmation
echo "⚠️  WARNING: This will DELETE all performance test features!"
echo ""
read -p "Do you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Operation cancelled"
    exit 0
fi

# Delete features
echo ""
echo "🗑️  Deleting features..."
docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} ${DB_NAME} -c "
DELETE FROM features WHERE key LIKE 'feature=%';
" >/dev/null 2>&1

echo "✅ Deleted $TOTAL features"

# Verify
REMAINING=$(docker exec ${POSTGRES_CONTAINER} psql -U ${DB_USER} ${DB_NAME} -t -c "
SELECT COUNT(*) FROM features WHERE key LIKE 'feature=%';
" 2>/dev/null | tr -d ' ')

echo "✅ Remaining features with 'feature=' pattern: $REMAINING"
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ✓ Cleanup Complete - Ready for Fresh Data Generation        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next step:"
echo "  npm run populate:perf:mt"
echo ""
