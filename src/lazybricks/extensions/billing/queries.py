"""SQL queries for billing data.

These queries are executed via the Statement Execution API against
Databricks system tables (system.billing.usage, system.billing.list_prices).

Parameters are passed as named parameters (:param_name format).
"""

# Quick access check - validates user has billing table access
ACCESS_CHECK_QUERY = """
SELECT 1 FROM system.billing.usage LIMIT 1
"""

# SKU-level cost summary with effective pricing
SKU_COST_QUERY = """
WITH prices AS (
  SELECT
    account_id,
    sku_name,
    cloud,
    usage_unit,
    price_start_time,
    COALESCE(price_end_time, TIMESTAMP '2999-12-31') AS price_end_time,
    pricing.effective_list.default  AS unit_price_effective,
    pricing.default                 AS unit_price_list,
    pricing.promotional.default     AS unit_price_promo
  FROM system.billing.list_prices
  WHERE usage_unit = 'DBU'
),
usage AS (
  SELECT
    account_id,
    sku_name,
    cloud,
    usage_unit,
    usage_type,
    billing_origin_product,
    usage_start_time,
    usage_quantity
  FROM system.billing.usage
  WHERE usage_unit = 'DBU'
    AND usage_date >= DATE(:window_start)
    AND usage_date < DATE(:window_end)
)
SELECT
  u.sku_name,
  u.usage_type,
  u.billing_origin_product,
  SUM(u.usage_quantity) AS total_dbu,
  MAX(p.unit_price_effective) AS unit_price_effective,
  SUM(u.usage_quantity) * MAX(p.unit_price_effective) AS estimated_cost,
  MAX(p.unit_price_list) AS unit_price_list,
  MAX(p.unit_price_promo) AS unit_price_promo,
  CASE
    WHEN MAX(p.unit_price_list) IS NULL OR MAX(p.unit_price_list) = 0 THEN NULL
    ELSE 1 - (MAX(p.unit_price_effective) / MAX(p.unit_price_list))
  END AS discount_pct
FROM usage u
LEFT JOIN prices p
  ON  u.account_id = p.account_id
  AND u.sku_name   = p.sku_name
  AND u.cloud      = p.cloud
  AND u.usage_unit = p.usage_unit
  AND u.usage_start_time >= p.price_start_time
  AND u.usage_start_time <  p.price_end_time
GROUP BY u.sku_name, u.usage_type, u.billing_origin_product
ORDER BY estimated_cost DESC NULLS LAST
LIMIT 50
"""

# Breakdown by compute target for a selected SKU
BREAKDOWN_QUERY = """
WITH prices AS (
  SELECT
    account_id, sku_name, cloud, usage_unit,
    price_start_time,
    COALESCE(price_end_time, TIMESTAMP '2999-12-31') AS price_end_time,
    pricing.effective_list.default AS unit_price_effective
  FROM system.billing.list_prices
  WHERE usage_unit = 'DBU'
),
usage AS (
  SELECT
    account_id,
    workspace_id,
    sku_name,
    cloud,
    usage_unit,
    usage_start_time,
    usage_quantity,
    usage_metadata.cluster_id   AS cluster_id,
    usage_metadata.warehouse_id AS warehouse_id,
    usage_metadata.job_id       AS job_id,
    usage_metadata.job_run_id   AS job_run_id,
    custom_tags.x_Creator       AS creator,
    custom_tags.x_ResourceClass AS resource_class
  FROM system.billing.usage
  WHERE usage_unit = 'DBU'
    AND sku_name = :sku_name
    AND usage_date >= DATE(:window_start)
    AND usage_date < DATE(:window_end)
)
SELECT
  workspace_id,
  cluster_id,
  warehouse_id,
  job_id,
  job_run_id,
  creator,
  resource_class,
  SUM(usage_quantity) AS total_dbu,
  MAX(p.unit_price_effective) AS unit_price_effective,
  SUM(usage_quantity) * MAX(p.unit_price_effective) AS estimated_cost
FROM usage u
LEFT JOIN prices p
  ON  u.account_id = p.account_id
  AND u.sku_name   = p.sku_name
  AND u.cloud      = p.cloud
  AND u.usage_unit = p.usage_unit
  AND u.usage_start_time >= p.price_start_time
  AND u.usage_start_time <  p.price_end_time
GROUP BY workspace_id, cluster_id, warehouse_id, job_id, job_run_id, creator, resource_class
ORDER BY estimated_cost DESC NULLS LAST
LIMIT 200
"""

# Total cost for time window (used for home screen widget)
TOTAL_COST_QUERY = """
WITH prices AS (
  SELECT
    account_id, sku_name, cloud, usage_unit,
    price_start_time,
    COALESCE(price_end_time, TIMESTAMP '2999-12-31') AS price_end_time,
    pricing.effective_list.default AS unit_price_effective
  FROM system.billing.list_prices
  WHERE usage_unit = 'DBU'
),
usage AS (
  SELECT
    account_id, sku_name, cloud, usage_unit,
    usage_start_time, usage_quantity
  FROM system.billing.usage
  WHERE usage_unit = 'DBU'
    AND usage_date >= DATE(:window_start)
    AND usage_date < DATE(:window_end)
)
SELECT
  SUM(u.usage_quantity * p.unit_price_effective) AS total_cost
FROM usage u
LEFT JOIN prices p
  ON  u.account_id = p.account_id
  AND u.sku_name   = p.sku_name
  AND u.cloud      = p.cloud
  AND u.usage_unit = p.usage_unit
  AND u.usage_start_time >= p.price_start_time
  AND u.usage_start_time <  p.price_end_time
"""
