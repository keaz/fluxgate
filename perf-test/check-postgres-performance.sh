#!/usr/bin/env bash

# PostgreSQL Performance Check Script
# Verifies optimized configuration and shows cache statistics

set -euo pipefail

CONTAINER="fluxgate-perf-postgres"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   PostgreSQL Performance Check - FluxGate Perf Test   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if container is running
if ! docker ps | grep -q "$CONTAINER"; then
  echo -e "${RED}✗ PostgreSQL container is not running${NC}"
  echo "  Start with: docker-compose -f docker-compose.base.yml up -d postgres"
  exit 1
fi

echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
echo ""

# 1. Configuration Settings
echo -e "${BLUE}━━━ Optimized Configuration Settings ━━━${NC}"
docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT
  name,
  CASE
    WHEN unit = '8kB' THEN pg_size_pretty(setting::bigint * 8192)
    WHEN unit = 'kB' THEN setting || 'kB'
    ELSE setting || COALESCE(' ' || unit, '')
  END AS value,
  short_desc
FROM pg_settings
WHERE name IN (
  'shared_buffers',
  'effective_cache_size',
  'work_mem',
  'random_page_cost',
  'effective_io_concurrency',
  'synchronous_commit',
  'full_page_writes'
)
ORDER BY name;
" | column -t -s '|'

echo ""

# 2. Memory Usage
echo -e "${BLUE}━━━ Memory Usage ━━━${NC}"
docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT
  'Database Size' as metric,
  pg_size_pretty(pg_database_size('feature_toggle')) as value
UNION ALL
SELECT
  'Shared Buffers Used',
  pg_size_pretty(
    (SELECT setting::bigint FROM pg_settings WHERE name = 'shared_buffers') * 8192
  )
UNION ALL
SELECT
  'Active Connections',
  count(*)::text
FROM pg_stat_activity
WHERE state = 'active';
" | column -t -s '|'

echo ""

# 3. Cache Hit Ratio
echo -e "${BLUE}━━━ Cache Performance ━━━${NC}"

cache_stats=$(docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT
  COALESCE(ROUND(100.0 * sum(heap_blks_hit) / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2), 0) AS cache_hit_ratio,
  sum(heap_blks_read) as disk_reads,
  sum(heap_blks_hit) as cache_hits
FROM pg_statio_user_tables;
" | tr -d ' ')

IFS='|' read -r cache_hit_ratio disk_reads cache_hits <<< "$cache_stats"

echo "Cache Hit Ratio:  ${cache_hit_ratio}%"
echo "Disk Reads:       ${disk_reads}"
echo "Cache Hits:       ${cache_hits}"

# Evaluate cache performance
if (( $(echo "$cache_hit_ratio > 90" | bc -l) )); then
  echo -e "${GREEN}✓ Excellent cache performance! (> 90%)${NC}"
elif (( $(echo "$cache_hit_ratio > 80" | bc -l) )); then
  echo -e "${YELLOW}⚠ Good cache performance (80-90%)${NC}"
else
  echo -e "${YELLOW}⚠ Cache may need warming up or more memory (< 80%)${NC}"
  echo -e "  Run some queries to warm the cache"
fi

echo ""

# 4. Table Statistics
echo -e "${BLUE}━━━ Table Statistics ━━━${NC}"
docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT
  schemaname || '.' || tablename as table_name,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
  n_live_tup as rows,
  n_tup_ins as inserts,
  n_tup_upd as updates,
  n_tup_del as deletes
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
" | column -t -s '|'

echo ""

# 5. Index Usage
echo -e "${BLUE}━━━ Top Index Scans ━━━${NC}"
docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT
  schemaname || '.' || tablename as table_name,
  indexname,
  idx_scan as scans,
  idx_tup_read as tuples_read,
  idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE idx_scan > 0
ORDER BY idx_scan DESC
LIMIT 10;
" | column -t -s '|' || echo "No index statistics yet (run some queries first)"

echo ""

# 6. Current Queries
echo -e "${BLUE}━━━ Active Queries ━━━${NC}"
active_count=$(docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%';
" | tr -d ' ')

if [ "$active_count" -gt 0 ]; then
  docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT
  pid,
  usename as user,
  LEFT(query, 60) as query,
  state,
  EXTRACT(EPOCH FROM (now() - query_start))::int as duration_sec
FROM pg_stat_activity
WHERE state = 'active' AND query NOT LIKE '%pg_stat_activity%'
ORDER BY query_start;
" | column -t -s '|'
else
  echo "No active queries"
fi

echo ""

# 7. Recommendations
echo -e "${BLUE}━━━ Recommendations ━━━${NC}"

# Check if cache ratio is low
if (( $(echo "$cache_hit_ratio < 80" | bc -l) )); then
  echo -e "${YELLOW}⚠ Cache hit ratio is low. Recommendations:${NC}"
  echo "  1. Run warm-up queries: SELECT COUNT(*) FROM features;"
  echo "  2. Increase shared_buffers if container has more memory"
  echo "  3. Wait a few minutes for cache to warm up"
  echo ""
fi

# Check synchronous_commit
sync_commit=$(docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT setting FROM pg_settings WHERE name = 'synchronous_commit';
" | tr -d ' ')

if [ "$sync_commit" = "off" ]; then
  echo -e "${YELLOW}⚠ synchronous_commit is OFF${NC}"
  echo "  This is FAST but UNSAFE - only use in test environments"
  echo "  Risk: Recent transactions can be lost on crash"
  echo ""
fi

# Check full_page_writes
fpw=$(docker exec "$CONTAINER" psql -U postgres -t -c "
SELECT setting FROM pg_settings WHERE name = 'full_page_writes';
" | tr -d ' ')

if [ "$fpw" = "off" ]; then
  echo -e "${YELLOW}⚠ full_page_writes is OFF${NC}"
  echo "  This is FAST but UNSAFE - only use in test environments"
  echo "  Risk: Database corruption possible on crash"
  echo ""
fi

echo -e "${GREEN}✓ PostgreSQL is optimized for read-heavy workloads${NC}"
echo ""
echo "For more details, see: POSTGRESQL_OPTIMIZATION.md"
