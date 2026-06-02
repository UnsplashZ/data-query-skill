# `/Users/zheng/Desktop/1.sql` follow-up: after `drh_kk_group_team` LEFT JOIN

Session follow-up for the legacy `drh_order` dashboard SQL reconciling April 2026 `书法` GMV.

## Current modified SQL state

The user had already changed the `drh_kk_group_team` joins to `LEFT JOIN` and removed default team filtering from the main GMV path. Rendering the current SQL with:

- `{{sku}}` -> `name='书法'`
- `{{start_time}}` -> `toDate('2026-04-01')`
- `{{end_time}}` -> `toDate('2026-04-30')`
- other optional filters removed

returned:

```text
sku-汇总 / 书法 / 实际gmv = 289,464
```

## Reconciliation of the current SQL

For the current file shape, the stepwise April 2026 `书法` chain was:

```text
书法 + 4月前端支付成功：291,323
+ INNER JOIN drh_channel_emp：289,464
+ INNER JOIN drh_goods：289,464
+ INNER JOIN tock_channel_id_belong：289,464
```

So once `drh_kk_group_team` is no longer restrictive, the remaining `1,859` gap is caused by the `drh_channel_emp` inner join in the GMV branch, not by `drh_kk_group_team`, `drh_goods`, or `tock_channel_id_belong`.

## Recommended fix pattern

In the GMV branch, change:

```sql
inner join (
    select channel_id, emp_name
    from drh_channel_emp final
    where _sign > 0
) a2 on a1.channel_id = a2.channel_id
```

to:

```sql
left join (
    select channel_id, emp_name
    from drh_channel_emp final
    where _sign > 0
) a2 on a1.channel_id = a2.channel_id
```

Apply the same idea to leads branches only if the dashboard should not drop leads when channel ownership is missing. The ad-cost branch using `drh_ad_cost_day.c_id -> drh_channel_emp.id` is a separate attribution path and should be changed only if unattributed ad cost is intentionally included.

## Communication note

In Feishu replies for this user, avoid Markdown tables for this class of debugging summary when the message may be copied/rendered through a card/comment context; Feishu can expose raw Markdown syntax. Prefer plain-text blocks like the chain above or short bullet lists.
