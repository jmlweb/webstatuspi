# Task #020: Response Time Percentiles and Standard Deviation

## Metadata
- **Status**: completed
- **Priority**: P2 - Medium
- **Slice**: Core, Database, API
- **Created**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want to see response time percentiles (P50, P95, P99) and standard deviation so that I can better identify performance outliers and understand response time distribution patterns beyond simple averages.

**Acceptance Criteria**:
- [ ] Database queries calculate p50_response_time_24h, p95_response_time_24h, p99_response_time_24h from existing data
- [ ] Database queries calculate stddev_response_time_24h from existing data
- [ ] All new metrics included in UrlStatus model and API responses
- [ ] Dashboard updated to display percentiles where appropriate (optional)
- [ ] Unit tests added for percentile and stddev calculations
- [ ] Performance impact verified on Pi 1B+ (queries should remain < 100ms)

## Implementation Notes

### Derived Metrics (SQL-only, zero capture overhead)
These metrics are calculated from existing `checks` table data using SQL aggregations:
- `p50_response_time_24h`: Median response time (50th percentile) for last 24h
- `p95_response_time_24h`: 95th percentile response time (identifies outliers)
- `p99_response_time_24h`: 99th percentile response time (worst-case scenarios)
- `stddev_response_time_24h`: Standard deviation of response times (measures consistency)

### SQLite Percentile Calculation

SQLite doesn't have built-in percentile functions, but we can calculate them using window functions:

```sql
-- Example approach using ROW_NUMBER and COUNT
WITH ranked AS (
  SELECT 
    response_time_ms,
    ROW_NUMBER() OVER (ORDER BY response_time_ms) as rn,
    COUNT(*) OVER () as total
  FROM checks
  WHERE url_name = ? AND checked_at >= ? AND response_time_ms IS NOT NULL
)
SELECT 
  response_time_ms as p50
FROM ranked
WHERE rn = CAST(total * 0.50 AS INTEGER)
```

**Alternative approach** (more efficient for large datasets):
- Use `ORDER BY response_time_ms LIMIT 1 OFFSET (total * 0.50)` pattern
- Calculate total count first, then fetch specific percentile

### Standard Deviation Calculation

SQLite supports standard deviation via:
```sql
SELECT AVG((response_time_ms - avg_rt) * (response_time_ms - avg_rt)) as variance
-- Then calculate sqrt(variance) in Python or use:
-- Note: SQLite doesn't have STDDEV, but we can calculate it
```

**Simpler approach**: Calculate in Python after fetching data, or use a subquery with AVG.

### Performance Considerations
- Percentiles require sorting, which is O(n log n) - acceptable for 24h window (~1440 checks max at 60s interval)
- Indexes on `checked_at` and `url_name` already exist, so filtering is fast
- Calculations only run when `/status` endpoint is queried (not on every check)
- Estimated query time: +10-30ms per URL (acceptable for < 100ms total target)

### Database Query Strategy

Update `get_latest_status()` and `get_latest_status_by_name()` in `database.py`:

1. Add CTE for percentile calculations:
   ```sql
   percentiles AS (
     SELECT 
       url_name,
       -- Calculate P50, P95, P99 using window functions
   )
   ```

2. Add CTE for standard deviation:
   ```sql
   stddev_stats AS (
     SELECT 
       url_name,
       -- Calculate variance, then sqrt in Python or via subquery
   )
   ```

3. Join with existing CTEs in main query

### API Changes
- Update `UrlStatus` model in `models.py` to include:
  - `p50_response_time_24h: int | None`
  - `p95_response_time_24h: int | None`
  - `p99_response_time_24h: int | None`
  - `stddev_response_time_24h: float | None`
- Update `_url_status_to_dict()` in `api.py` to serialize new fields
- Update `get_latest_status()` query in `database.py` to calculate metrics

### Dashboard Display (Optional)
- Show P95/P99 in tooltip or expanded view (not primary metrics)
- Use P95 as "worst case" indicator alongside max
- Show stddev as "consistency" metric (low = stable, high = variable)

## Files to Modify

- `webstatuspi/models.py` - Add percentile and stddev fields to UrlStatus dataclass
- `webstatuspi/database.py` - Update queries with percentile and stddev CTEs
- `webstatuspi/api.py` - Serialize new metrics in JSON responses
- `webstatuspi/_dashboard.py` - Display percentiles in UI (optional, low priority)
- `tests/test_database.py` - Add tests for percentile and stddev calculations
- `tests/test_api.py` - Verify new fields in API responses

## Dependencies

None - uses existing data and infrastructure (similar to #019)

## Performance Impact Estimate

- **CPU**: +1-3% during queries (only when `/status` is accessed)
- **RAM**: No impact (calculations done in SQLite)
- **Storage**: No impact (no schema changes)
- **Network**: No impact
- **Query time**: +10-30ms per URL (acceptable for < 100ms total target)

**Conclusion**: Acceptable impact for Pi 1B+ given current headroom (22-40% RAM, 15-44% CPU).

## References

- Task #019 (Extended Metrics) - Similar implementation pattern for derived metrics
- [SQLite Window Functions](https://www.sqlite.org/windowfunctions.html)
- [Percentile calculation in SQL](https://www.sqlite.org/lang_aggfunc.html)

## Progress Log

- [2026-01-21] Task created based on metrics analysis

## Learnings

(To be filled during implementation)
