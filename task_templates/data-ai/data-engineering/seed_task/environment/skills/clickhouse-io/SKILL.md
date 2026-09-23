# ClickHouse Analytics Patterns

ClickHouse-specific patterns for high-performance analytics and data engineering.

## When to Activate

- Designing ClickHouse table schemas and choosing the right MergeTree variant
- Writing analytical queries with aggregations, window functions, and joins
- Optimizing query performance with partition pruning, projections, and materialized views
- Ingesting large volumes of data with batch inserts or streaming pipelines
- Migrating analytical workloads from PostgreSQL or MySQL into ClickHouse
- Implementing real-time dashboards or time-series analytics

## Overview

ClickHouse is a column-oriented database for online analytical processing. It is optimized for fast analytical queries on large datasets.

Key characteristics:

- Column-oriented storage
- Strong compression
- Parallel query execution
- Distributed query support
- Real-time analytics patterns

## Table Design Patterns

### MergeTree

Use standard `MergeTree` for most analytical time-series tables. Partition by time, order by the most selective filter columns, and avoid unnecessary partitions.

### ReplacingMergeTree

Use `ReplacingMergeTree` when duplicate rows may arrive from multiple sources and deduplication must happen during merges.

### AggregatingMergeTree

Use `AggregatingMergeTree` to maintain pre-aggregated metrics with aggregate states and merge functions such as `sumMerge`, `countMerge`, and `uniqMerge`.

## Query Optimization Patterns

- Filter on indexed and ordered columns early.
- Prefer ClickHouse-native aggregate functions such as `uniq` and `quantile`.
- Use window functions for cumulative metrics and cohort analysis when needed.
- Avoid `SELECT *` in analytical queries.

## Data Insertion Patterns

- Prefer bulk inserts over row-by-row inserts.
- Use streaming inserts only for continuous ingestion.
- Consider materialized views for real-time rollups.

## Performance Monitoring

- Inspect `system.query_log` for slow or expensive queries.
- Inspect `system.parts` for table sizes and modification behavior.
- Monitor merge activity, disk usage, and query latency.

## Best Practices

1. Partition by time, usually month or day.
2. Put frequently filtered columns first in the ordering key.
3. Use the smallest practical data types.
4. Use `LowCardinality` for repeated strings and `Enum` for categorical values when appropriate.
5. Avoid too many joins in hot analytical paths; denormalize if needed.
6. Prefer batched writes and materialized views for real-time aggregates.

Remember: ClickHouse performs best when table design follows query patterns and ingestion is done in efficient batches.
