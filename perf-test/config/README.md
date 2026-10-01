# Performance Test Configuration Files

This directory contains configuration files for the FluxGate performance test environment.

## Files

### PostgreSQL Configuration

- **`postgresql.conf`** - PostgreSQL server configuration
  - **Optimized for READ-HEAVY workloads**
  - **Aggressive caching**: 256MB shared_buffers, 512MB effective_cache_size
  - **SSD-optimized**: random_page_cost=1.1, effective_io_concurrency=200
  - **Fast writes** (test-only): synchronous_commit=off, full_page_writes=off
  - **Expected performance**: 10-30x faster feature lookups, 90%+ cache hit ratio
  - **See**: `../POSTGRESQL_OPTIMIZATION.md` for detailed explanation

### Backend Configuration

- **`backend-config.toml`** - Backend server configuration
  - CORS settings
  - HTTP and gRPC bind addresses
  - JWT secret configuration

- **`backend-log4rs.yaml`** - Backend logging configuration
  - Log level: `info`
  - Output: Console only
  - Pattern: `{timestamp} [{level}] [{target}] {message}`

### Edge Server Configuration

- **`edge-config.toml`** - Edge server configuration
  - Client credentials (ID and secret)
  - Backend gRPC connection settings
  - HTTP server configuration
  - Flush intervals for analytics

- **`edge-log4rs.yaml`** - Edge server logging configuration
  - Log level: `info`
  - Output: Console only
  - Pattern: `{timestamp} [{level}] [{target}] {message}`

## Log Configuration Details

### Log4rs Format

Both backend and edge use the same log4rs configuration format:

```yaml
refresh_rate: 30 seconds

appenders:
  stdout:
    kind: console
    encoder:
      pattern: "{d(%Y-%m-%d %H:%M:%S%.3f)} [{l}] [{t}] {m}{n}"

root:
  level: info
  appenders:
    - stdout
```

**Pattern Explanation:**
- `{d(%Y-%m-%d %H:%M:%S%.3f)}` - Timestamp with milliseconds
- `{l}` - Log level (INFO, WARN, ERROR, DEBUG)
- `{t}` - Target module/component
- `{m}` - Log message
- `{n}` - Newline

**Example Output:**
```
2025-11-09 18:27:22.145 [INFO] [feature_edge_server::grpc_client] Stream connection established
2025-11-09 18:27:23.456 [WARN] [feature_edge_server::http] High latency detected: 250ms
```

## Changing Log Levels

### Via Environment Variables

Set `RUST_LOG` environment variable in docker-compose files:

```yaml
environment:
  RUST_LOG: debug  # or info, warn, error
```

### Modifying log4rs Files

Edit the log level in the YAML file:

```yaml
root:
  level: debug  # Change this: trace, debug, info, warn, error
  appenders:
    - stdout
```

## Volume Mounts

These files are mounted as read-only volumes in Docker:

**Backend** (`docker-compose.base.yml`):
```yaml
volumes:
  - ./config/backend-config.toml:/app/config/config.toml:ro
  - ./config/backend-log4rs.yaml:/app/log4rs.yaml:ro
```

**Edge** (`docker-compose.base.yml`):
```yaml
volumes:
  - ./config/edge-config.toml:/app/config/config.toml:ro
  - ./config/edge-log4rs.yaml:/app/log4rs.yaml:ro
```

## Troubleshooting

### Logs Not Appearing

1. Verify the file is mounted correctly:
   ```bash
   docker exec fluxgate-perf-edge ls -la /app/log4rs.yaml
   ```

2. Check the file contents:
   ```bash
   docker exec fluxgate-perf-edge cat /app/log4rs.yaml
   ```

3. Verify RUST_LOG environment variable:
   ```bash
   docker exec fluxgate-perf-edge env | grep RUST_LOG
   ```

### Too Verbose Logs

Reduce log level to `warn` or `error`:

```yaml
root:
  level: warn
```

### Missing Debug Information

Increase log level to `debug` or `trace`:

```yaml
root:
  level: debug
```

Or set environment variable:
```bash
EDGE_LOG_LEVEL=debug docker-compose -f docker-compose.base.yml up
```

## Best Practices

### Performance Testing

For performance tests, use `info` level (default):
- Captures important events
- Minimal performance overhead
- Easy to analyze

### Troubleshooting

Use `debug` level for detailed diagnostics:
- Shows internal operations
- Includes timing information
- Helps identify bottlenecks

### Production-like Testing

Use `warn` or `error` level:
- Mimics production logging
- Reduces log volume
- Focuses on issues

## References

- [log4rs Documentation](https://docs.rs/log4rs/latest/log4rs/)
- [Rust log crate](https://docs.rs/log/latest/log/)
- [FluxGate Main Documentation](../../CLAUDE.md)
