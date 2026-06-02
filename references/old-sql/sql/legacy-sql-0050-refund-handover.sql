WITH base AS
(
    SELECT
        a1.flow_no AS `flow_no`,
        a1.union_id AS `union_id`,
        a1.nick_name AS `nick_name`,
        a1.camp_name AS `营期名称`,
        a1.camp_group_name AS `营期轨次`,
        a1.start_class_time AS `营期开课日期`,
        a1.end_class_time AS `营期封板日期`,
        a1.camp_sku AS `营期sku`,
        a1.main_goods_sku AS `商品sku`,
        a1.main_goods_name AS `商品名称`,
        a1.pay_type_name AS `支付类型`,
        a1.total_original_price AS `商品原价`,
        a1.camp_name AS `前端营期`,
        a1.pay_time AS `支付时间`,
        toDate(a1.pay_time) AS `支付日期`,
        a1.emp_team_name AS `团队`,
        a1.emp_group_name AS `组别`,
        a1.order_emp_name AS `成交人`,
        nullIf(a1.refund_time, toDateTime('1970-01-01 08:00:00')) AS `退款时间`,
        a1.class_stage_name AS `营期阶段`,
        nullIf(a2.ast_emp_name, '') AS `二阶学管`,
        nullIf(a2.group_camp_name, '') AS `二阶轨次`,
        nullIf(a2.class_camp_name, '') AS `二阶营期`,
        nullIf(a2.ast_friend_time, toDateTime('1970-01-01 08:00:00')) AS `加微时间`,
        nullIf(a3.min_class_time, toDateTime('1970-01-01 08:00:00')) AS `开课日期`,
        nullIf(a4.min_class_time, toDateTime('1970-01-01 08:00:00')) AS `衔接课开课日期`,
        nullIf(a2.join_group_time, toDateTime('1970-01-01 08:00:00')) AS `加入轨次日期`,
        nullIf(a2.join_camp_time, toDateTime('1970-01-01 08:00:00')) AS `加入营期日期`,
        CASE
            WHEN nullIf(a2.order_no, '') IS NOT NULL THEN '已承接'
            ELSE '未承接'
        END AS `承接状态`
    FROM
    (
        SELECT
            T1.order_no AS flow_no,
            coalesce(nullIf(T20.union_id, ''), nullIf(T12.union_id, '')) AS union_id,
            T1.camp_id AS camp_id,
            T7.camp_name AS camp_name,
            T7.camp_group_name AS camp_group_name,
            T7.camp_sku AS camp_sku,
            T3.goods_sku_name AS main_goods_sku,
            T3.goods_name AS main_goods_name,
            CASE
                WHEN T1.pay_type = 1 THEN '首款'
                WHEN T1.pay_type = 2 THEN '尾款'
                WHEN T1.pay_type = 3 THEN '全款'
                ELSE toString(T1.pay_type)
            END AS pay_type_name,
            round(ifNull(T1.total_price, 0) / 100, 4) AS total_original_price,
            toDateTime(T1.pay_time) AS pay_time,
            T4.team_name AS emp_team_name,
            T4.group_name AS emp_group_name,
            T4.emp_name AS order_emp_name,
            parseDateTimeBestEffortOrNull(T2.refund_time) AS refund_time,
            T12.nick_name AS nick_name,
            T0.start_class_time AS start_class_time,
            T0.end_class_time AS end_class_time,
            T0.class_stage_name AS class_stage_name
        FROM
        (
            SELECT
                order_no,
                camp_id,
                goods_id,
                pay_type,
                total_price,
                pay_time,
                emp_num,
                applet_user_id,
                user_id,
                price
            FROM drh_order FINAL
            WHERE _sign > 0
              AND pay_status = 2
              AND (price > 0 OR goods_id = 1710)
        ) T1
        LEFT JOIN
        (
            SELECT
                class_stage_name,
                toDate(start_class_time) AS start_class_time,
                toDate(end_class_time) AS end_class_time,
                camp_id
            FROM dim_camp_df
            WHERE camp_id <> 0
        ) T0
            ON T0.camp_id = T1.camp_id
        LEFT JOIN
        (
            SELECT
                order_no,
                max(end_time) AS refund_time
            FROM tock_ods_feishu_refund_approval_detail_all_d
            WHERE feishu_status = 'APPROVED'
              AND is_delete = 0
            GROUP BY order_no
        ) T2
            ON T2.order_no = T1.order_no
        LEFT JOIN
        (
            SELECT
                gos.id AS goods_id,
                gos.name AS goods_name,
                bl.name AS goods_sku_name,
                CASE
                    WHEN gos.goods_sort = 1 THEN '课程'
                    WHEN gos.goods_sort = 2 THEN '实物'
                    WHEN gos.goods_sort = 3 THEN '服务'
                    ELSE '其他'
                END AS first_level_name
            FROM
            (
                SELECT
                    id,
                    name,
                    category,
                    goods_sort
                FROM drh_goods FINAL
                WHERE _sign > 0
            ) gos
            INNER JOIN
            (
                SELECT
                    category,
                    name
                FROM drh_business_line FINAL
                WHERE _sign > 0 [[AND {{main_goods_sku}}]]
            ) bl
                ON gos.category = bl.category
        ) T3
            ON T1.goods_id = T3.goods_id
        LEFT JOIN
        (
            SELECT
                emp.id AS emp_id,
                emp.name AS emp_name,
                gt.group_name AS group_name,
                gt.team_name AS team_name
            FROM
            (
                SELECT
                    id,
                    name
                FROM drh_kk_emp FINAL
                WHERE _sign > 0
            ) emp
            LEFT JOIN
            (
                SELECT
                    emp_id,
                    group_name,
                    team_name
                FROM drh_kk_group_team FINAL
                WHERE _sign > 0
            ) gt
                ON emp.id = gt.emp_id
        ) T4
            ON T1.emp_num = T4.emp_id
        LEFT JOIN
        (
            SELECT
                camp_id,
                camp_name,
                camp_group_name,
                camp_sku
            FROM dim_camp_df
        ) T7
            ON T1.camp_id = T7.camp_id
        LEFT JOIN
        (
            SELECT
                applet_user_id,
                argMax(union_id, create_time) AS union_id,
                argMax(nick_name, create_time) AS nick_name
            FROM tock_applet_user
            GROUP BY applet_user_id
        ) T12
            ON T1.applet_user_id = T12.applet_user_id
        LEFT JOIN
        (
            SELECT
                id,
                union_id
            FROM drh_live_user FINAL
            WHERE _sign > 0
        ) T20
            ON T1.user_id = T20.id
        WHERE T3.first_level_name = '课程'
          AND T1.pay_type IN (2, 3)
          AND round(ifNull(T1.total_price, 0) / 100, 4) >= {{goods_price}}
          AND toDate(T1.pay_time) >= {{start_date}}
          [[AND toDate(T1.pay_time) <= {{end_date}}]]
    ) a1
    LEFT JOIN
    (
        SELECT
            h.flow_no AS order_no,
            h.ast_emp_name AS ast_emp_name,
            c.camp_name AS class_camp_name,
            c.camp_group_name AS group_camp_name,
            f.ast_friend_time AS ast_friend_time,
            h.join_camp_time AS join_camp_time,
            h.join_group_time AS join_group_time,
            h.class_camp_id AS class_camp_id
        FROM
        (
            SELECT
                order_no AS flow_no,
                argMax(ast_name, id) AS ast_emp_name,
                argMax(union_id, id) AS union_id,
                argMax(ast_id, id) AS ast_id,
                argMax(join_camp_time, id) AS join_camp_time,
                argMax(join_group_time, id) AS join_group_time,
                argMax(
                    if(class_camp_id IS NOT NULL AND class_camp_id != 0, class_camp_id, stop_camp),
                    id
                ) AS class_camp_id
            FROM drh_handover_plus FINAL
            WHERE _sign > 0
            GROUP BY order_no
        ) h
        LEFT JOIN
        (
            SELECT
                camp_id,
                camp_name,
                camp_group_name,
                camp_kind_code_name
            FROM dim_camp_df
            WHERE camp_id <> 0
        ) c
            ON h.class_camp_id = c.camp_id
        LEFT JOIN
        (
            SELECT
                emp_id,
                union_id,
                min(create_time) AS ast_friend_time
            FROM drh_emp_external_user FINAL
            WHERE _sign > 0
            GROUP BY emp_id, union_id
        ) f
            ON h.ast_id = f.emp_id
           AND h.union_id = f.union_id
        WHERE ifNull(c.camp_kind_code_name, '') != '教务营期'
    ) a2
        ON a1.flow_no = a2.order_no
    LEFT JOIN
    (
        SELECT
            union_id,
            camp_id,
            min(class_time) AS min_class_time
        FROM tock_ast_process_data
        WHERE study_time > 0
          AND multiMatchAny(course_name, ['.*月夜.*上', '.*小白杨.*上', '.*鸿雁.*上', '我和你.*上', '红河谷.*第1课', '手指技术专项强化课.*第一节'])
        GROUP BY union_id, camp_id
    ) a3
        ON a1.union_id = a3.union_id
       AND a2.class_camp_id = a3.camp_id
    LEFT JOIN
    (
        SELECT
            union_id,
            camp_id,
            min(class_time) AS min_class_time
        FROM tock_ast_process_data
        WHERE study_time > 0
        GROUP BY union_id, camp_id
    ) a4
        ON a1.union_id = a4.union_id
       AND a2.class_camp_id = a4.camp_id
),

export_base AS
(
    SELECT
        `flow_no`,
        `union_id`,
        `nick_name`,
        `营期名称`,
        `营期轨次`,
        `营期开课日期`,
        `营期封板日期`,
        `营期sku`,
        `商品sku`,
        `商品名称`,
        `支付类型`,
        `商品原价`,
        toString(`支付时间`) AS `支付时间`,
        toString(`支付日期`) AS `支付日期`,
        `团队`,
        `组别`,
        `成交人`,
        if(isNull(`退款时间`), CAST(NULL, 'Nullable(String)'), toString(`退款时间`)) AS `退款时间`,
        `营期阶段`,
        `二阶学管`,
        `二阶轨次`,
        `二阶营期`,
        if(isNull(`加微时间`), CAST(NULL, 'Nullable(String)'), toString(`加微时间`)) AS `加微时间`,
        if(isNull(`开课日期`), CAST(NULL, 'Nullable(String)'), toString(`开课日期`)) AS `开课日期`,
        if(isNull(`衔接课开课日期`), CAST(NULL, 'Nullable(String)'), toString(`衔接课开课日期`)) AS `衔接课开课日期`,
        if(isNull(`加入轨次日期`), CAST(NULL, 'Nullable(String)'), toString(`加入轨次日期`)) AS `加入轨次日期`,
        if(isNull(`加入营期日期`), CAST(NULL, 'Nullable(String)'), toString(`加入营期日期`)) AS `加入营期日期`,
        if(`承接状态` = '已承接' AND `二阶学管` <> '', '已选期', '未选期') AS `选期状态`,
        if(`承接状态` = '已承接' AND `二阶学管` <> '' AND `加微时间` <> '', '已加微', '未加微') AS `加微状态`,
        if(`承接状态` = '已承接' AND `二阶学管` <> '' AND `加微时间` <> '' AND `开课日期` <> '' AND toString(today()) >= `开课日期`, '已开课', '未开课') AS `开课状态`,
        if(`承接状态` = '已承接' AND `二阶学管` <> '' AND `加微时间` <> '' AND `衔接课开课日期` <> '' AND toString(today()) >= `衔接课开课日期`, '已开课', '未开课') AS `衔接课开课状态`
    FROM base
)

SELECT *
FROM export_base
WHERE 1 = 1
[[AND `营期阶段` = {{stage}}]]
[[AND `选期状态` = {{status}}]]
[[AND `加微状态` = {{status2}}]]
[[AND multiMatchAny(`union_id`, [replace({{union_id}}, ',', '|')])]]
ORDER BY `支付时间` DESC
