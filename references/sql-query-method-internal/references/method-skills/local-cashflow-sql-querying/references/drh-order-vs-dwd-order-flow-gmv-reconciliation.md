# drh_order dashboard SQL vs dwd_order_flow_df GMV reconciliation

Session-specific finding from reconciling `/Users/zheng/Desktop/1.sql` for 2026-04-01 through 2026-04-30 calligraphy/书法 SKU.

## Symptom

A dashboard-style SQL based on `drh_order` returned `实际gmv = 182,920`, while a `dwd_order_flow_df` check for the same month and front-end calligraphy SKU returned `291,323`.

## Key source SQL pattern

The dashboard SQL GMV comes from `drh_order FINAL`:

```sql
WHERE _sign > 0
  AND price > 0
  AND front_end = 1
  AND pay_status = 2
```

SKU is mapped through:

```text
drh_order.camp_id -> drh_live_camp.category -> drh_business_line.name = '书法'
```

Then the SQL uses several `INNER JOIN`s, including:

- `drh_channel_emp`
- `drh_goods` with `goods_sort = 1`
- `tock_channel_id_belong`
- `drh_kk_group_team` on `drh_order.emp_num = drh_kk_group_team.emp_id`

## Verified reconciliation numbers

For April 2026 calligraphy / front-end scope:

| Step | GMV |
|---|---:|
| `drh_order` + live-camp/business-line SKU mapping to `书法` | 291,323 |
| after `drh_channel_emp` inner join | 289,464 |
| after `drh_goods goods_sort=1` inner join | 267,420 |
| after `tock_channel_id_belong` inner join | 267,420 |
| after `drh_kk_group_team` inner join | 182,920 |

The largest reduction was the team join:

```text
267,420 - 182,920 = 84,500
```

Top missing `emp_num` examples observed after the team join requirement:

| emp_num | orders | GMV |
|---:|---:|---:|
| 4930 | 22 | 34,880 |
| 4981 | 17 | 26,880 |
| 5128 | 4 | 10,320 |
| 5005 | 3 | 4,140 |
| 4949 | 3 | 2,940 |

## `dwd_order_flow_df` matching checks

The reported `291,323` matched this broader order-flow scope:

```sql
SELECT count(), round(sum(pay_amount), 2)
FROM dwd_order_flow_df
WHERE pay_time >= toDateTime('2026-04-01 00:00:00')
  AND pay_time <  toDateTime('2026-05-01 00:00:00')
  AND pay_status_name = '支付成功'
  AND new_front_end_name LIKE '%前端%'
  AND camp_sku = '书法'
```

Breakdown:

| main_first_level | camp_sku | orders | GMV |
|---|---|---:|---:|
| 课程 | 书法 | 169 | 268,880 |
| 电商 | 书法 | 58 | 22,443 |

Useful alternate checks:

| Scope | Orders | GMV |
|---|---:|---:|
| front-end, `main_goods_sku='书法'`, all categories | 283 | 308,067 |
| front-end, `main_goods_sku='书法'`, `main_first_level='课程'` | 225 | 285,624 |
| front-end, `camp_sku='书法'`, all categories | 227 | 291,323 |
| front-end, `camp_sku='书法'`, `main_first_level='课程'` | 169 | 268,880 |

## Reusable explanation rule

When a legacy dashboard SQL based on `drh_order` disagrees with `dwd_order_flow_df` GMV:

1. First identify whether SKU is `camp_sku`, `main_goods_sku`, or business-line category mapped through camp category.
2. Check whether the `dwd_order_flow_df` comparison includes `main_first_level='课程'` or also includes `电商`.
3. Decompose the legacy SQL one join at a time, especially inner joins to dimension/ownership tables.
4. Treat `drh_kk_group_team` inner joins as potentially restrictive; they can remove valid paid orders whose `emp_num` is missing from the active team table.
5. If the dashboard should show total GMV rather than team-attributed GMV, use `LEFT JOIN` for team enrichment and only filter team when the user explicitly selects a team.
