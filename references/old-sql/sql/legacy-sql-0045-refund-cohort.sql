WITH base AS 
(
    SELECT  a1.flow_no
            ,a1.union_id
            ,a1.camp_name AS 营期名称
            ,a1.camp_sku AS 营期sku
            ,a1.main_goods_sku AS 商品sku
            ,a1.main_goods_name AS 商品名称
            ,a1.pay_type_name AS 支付类型
            ,a1.total_original_price AS 商品原价
            ,a1.camp_name AS 前端营期
            ,a1.pay_time AS 支付时间
            ,TO_DATE(a1.pay_time) AS 支付日期
            ,a1.emp_team_name AS 团队
            ,a1.emp_group_name AS 组别
            ,a1.order_emp_name AS 成交人
            ,a1.refund_time AS 退款时间 
            -- 营期阶段（关联 drh_live_camp）
            ,CASE   WHEN a8.is_class = 0 THEN '销转营期'
                    WHEN a8.is_class = 1 AND a8.class_stage = 2 THEN '二阶营期'
                    WHEN a8.is_class = 1 AND a8.class_stage = 3 THEN '三阶营期'
                    WHEN a8.is_class = 1 AND a8.class_stage = 4 THEN '四阶营期'
                    WHEN a8.is_class = 1 AND a8.class_stage = 5 THEN '五阶营期'
                    ELSE '特殊营期'
            END AS 营期阶段 
            -- 二阶承接信息（来自 dwd_order_handover_df，关联 dim_camp_view 过滤教务营期）
            ,a2.order_no AS 二阶订单号
            ,a2.ast_emp_name AS 二阶学管
            ,a2.class_camp_name AS 二阶营期
            ,a2.ast_friend_time AS 加微时间 
            -- 学员状态：从 drh_user_change_camp_record 最新记录判断
            ,a4.change_reason AS 最新变更原因 
            -- 开课日期：从 tock_ast_process_data 按 union_id + camp_id 聚合取 min(class_time)
            ,a3.min_class_time AS 开课日期 
            -- 承接时间
            ,a2.join_group_time AS 加入轨次日期
            ,a2.join_camp_time AS 加入营期日期
            ,CASE   WHEN a2.order_no IS NOT NULL THEN '已承接'
                    ELSE '未承接'
            END AS 承接状态
    FROM    dwd_order_flow_df a1
    LEFT JOIN drh_live_camp a8
    ON      a1.camp_id = a8.id 
    -- 交接承接表（dwd_order_handover_df，关联 dim_camp_view 过滤教务营期）
    LEFT JOIN   (
                    SELECT  h.flow_no AS order_no
                            ,h.ast_emp_name
                            ,h.class_camp_name
                            ,h.ast_friend_time
                            ,h.join_camp_time
                            ,h.join_group_time
                            ,h.class_camp_id
                    FROM    dwd_order_handover_df h
                    LEFT JOIN dim_camp_view v
                    ON      h.class_camp_id = v.camp_id
                    WHERE   v.camp_kind_code_name <> '教务营期'
                    OR      v.camp_kind_code_name IS NULL
                ) a2
    ON      a1.flow_no = a2.order_no 
    -- 从 tock_ast_process_data 按 union_id + camp_id 聚合取 min(class_time)
    LEFT JOIN   (
                    SELECT  union_id
                            ,camp_id
                            ,MIN(class_time) AS min_class_time
                    FROM    tock_ast_process_data
                    GROUP BY union_id
                             ,camp_id
                ) a3
    ON      a1.union_id = a3.union_id
    AND     a2.class_camp_id = a3.camp_id 
    -- 学员状态变更记录（取最新一条，change_reason: 1退费、2休学、7复学）
    LEFT JOIN   (
                    SELECT  order_no
                            ,change_reason
                            ,ROW_NUMBER() OVER (PARTITION BY order_no ORDER BY exe_time DESC ) AS rn
                    FROM    drh_user_change_camp_record
                    WHERE   change_reason IN (1,2,7)
                ) a4
    ON      a1.flow_no = a4.order_no
    AND     a4.rn = 1
    WHERE   a1.main_first_level = '课程'
    AND     a1.pay_type_name IN ('全款','尾款')
    AND     a1.total_original_price >= 1880
    AND     TO_DATE(a1.pay_time) >= '${START_DATE}'
    AND     TO_DATE(a1.pay_time) <= '${END_DATE}'
    AND     (
                a1.main_goods_sku = '声乐'
                OR      a1.main_goods_sku = '钢琴'
    )
    AND     a1.dt >= '${START_DATE}'
    AND     a1.dt <= '${END_DATE}'
)
,flagged AS 
(
    SELECT  union_id
            ,flow_no
            ,营期名称
            ,营期sku
            ,商品sku
            ,支付日期
            ,营期阶段
            ,承接状态
            ,退款时间
            ,二阶学管
            ,二阶营期
            ,最新变更原因
            ,加微时间
            ,开课日期
            ,加入轨次日期
            ,加入营期日期
            ,CASE   WHEN 营期sku <> 商品sku THEN 1
                    ELSE 0
            END AS 是否扩科 
            -- 价格区间：仅销转营期判断
            ,CASE   WHEN 营期阶段 = '销转营期' AND 商品原价 >= 2481 THEN '2980'
                    WHEN 营期阶段 = '销转营期' AND 商品原价 < 2481 THEN '1880'
                    ELSE NULL
            END AS 价格区间 
            -- 退费
            ,CASE   WHEN 退款时间 IS NOT NULL THEN 1
                    ELSE 0
            END AS 是否退费
            ,CASE   WHEN 退款时间 IS NOT NULL AND TO_DATE(退款时间) <= DATEADD(TO_DATE(支付时间),14,'dd') THEN 1
                    ELSE 0
            END AS 是否前端退费
            ,CASE   WHEN 退款时间 IS NOT NULL AND TO_DATE(退款时间) > DATEADD(TO_DATE(支付时间),14,'dd') THEN 1
                    ELSE 0
            END AS 是否后端退费 
            -- 休学：最新变更原因为2（休学），且未退费；或二阶营期含延期/冻课
            ,CASE   WHEN 退款时间 IS NULL
                        AND (最新变更原因 = 2
                        OR NVL(二阶营期,'') LIKE '%延期%'
                        OR NVL(二阶营期,'') LIKE '%冻课%') THEN 1
                    ELSE 0
            END AS 是否休学 
            -- 已承接
            ,CASE   WHEN 承接状态 = '已承接' THEN 1
                    ELSE 0
            END AS 是否已承接 
            -- 已加微
            ,CASE   WHEN 加微时间 IS NOT NULL THEN 1
                    ELSE 0
            END AS 是否已加微 
            -- 已交接：已承接 + 二阶营期非空 + 未退费未休学
            ,CASE   WHEN 承接状态 = '已承接'
                        AND 二阶营期 IS NOT NULL
                        AND 退款时间 IS NULL
                        AND NVL(最新变更原因,0) != 2
                        AND NVL(二阶营期,'') NOT LIKE '%延期%'
                        AND NVL(二阶营期,'') NOT LIKE '%冻课%' THEN 1
                    ELSE 0
            END AS 是否已交接 
            -- 教务待交接：已承接 + 二阶营期为空 + 未退费未休学
            ,CASE   WHEN 承接状态 = '已承接'
                        AND 二阶营期 IS NULL
                        AND 退款时间 IS NULL
                        AND NVL(最新变更原因,0) != 2 THEN 1
                    ELSE 0
            END AS 是否待交接 
            -- 已开课：已交接 + 开课日期 <= 数据截止日期
            ,CASE   WHEN 承接状态 = '已承接'
                        AND 二阶营期 IS NOT NULL
                        AND 退款时间 IS NULL
                        AND NVL(最新变更原因,0) != 2
                        AND NVL(二阶营期,'') NOT LIKE '%延期%'
                        AND NVL(二阶营期,'') NOT LIKE '%冻课%'
                        AND CAST(开课日期 AS DATE) <= DATE '${END_DATE}' THEN 1
                    ELSE 0
            END AS 是否已开课 
            -- 未交接：未承接 + 未退费
            ,CASE   WHEN 承接状态 = '未承接' AND 退款时间 IS NULL THEN 1
                    ELSE 0
            END AS 是否未交接
            -- 首日交接：同已交接逻辑 + 加入轨次日期在支付当天
            ,CASE   WHEN 承接状态 = '已承接'
                        AND 二阶营期 IS NOT NULL
                        AND 退款时间 IS NULL
                        AND NVL(最新变更原因,0) != 2
                        AND NVL(二阶营期,'') NOT LIKE '%延期%'
                        AND NVL(二阶营期,'') NOT LIKE '%冻课%'
                        AND TO_DATE(加入轨次日期) = TO_DATE(支付时间) THEN 1
                    ELSE 0
            END AS 是否首日交接 
            -- 3天内交接：同已交接逻辑 + 加入轨次日期在支付后3天内
            ,CASE   WHEN 承接状态 = '已承接'
                        AND 二阶营期 IS NOT NULL
                        AND 退款时间 IS NULL
                        AND NVL(最新变更原因,0) != 2
                        AND NVL(二阶营期,'') NOT LIKE '%延期%'
                        AND NVL(二阶营期,'') NOT LIKE '%冻课%'
                        AND TO_DATE(加入轨次日期) <= DATEADD(TO_DATE(支付时间),3,'dd') THEN 1
                    ELSE 0
            END AS 是否3天内交接 
            -- 7天内交接：同已交接逻辑 + 加入轨次日期在支付后7天内
            ,CASE   WHEN 承接状态 = '已承接'
                        AND 二阶营期 IS NOT NULL
                        AND 退款时间 IS NULL
                        AND NVL(最新变更原因,0) != 2
                        AND NVL(二阶营期,'') NOT LIKE '%延期%'
                        AND NVL(二阶营期,'') NOT LIKE '%冻课%'
                        AND TO_DATE(加入轨次日期) <= DATEADD(TO_DATE(支付时间),7,'dd') THEN 1
                    ELSE 0
            END AS 是否7天内交接
    FROM    base
) 
SELECT  营期sku AS `营期sku`
        ,商品sku AS `商品sku`
        ,支付日期 AS `支付日期`
        ,营期阶段 AS `营期阶段`
        ,是否扩科 AS `是否扩科`
        ,价格区间 AS `价格区间`
        ,COUNT(*) AS `订单数`
        ,SUM(是否退费) AS `退费订单数`
        ,SUM(是否前端退费) AS `前端退费订单数`
        ,SUM(是否后端退费) AS `后端退费订单数`
        ,SUM(是否休学) AS `休学数`
        ,SUM(是否待交接) AS `教务待交接数`
        ,SUM(是否已交接) AS `已交接数`
        ,SUM(是否已加微) AS `加微数`
        ,SUM(是否已开课) AS `已开课数`
        ,SUM(是否未交接) AS `未交接数`
        ,SUM(是否首日交接) AS `首日交接数`
        ,SUM(是否3天内交接) AS `3天内交接数`
        ,SUM(是否7天内交接) AS `7天内交接数`
FROM    flagged
GROUP BY 营期sku
         ,商品sku
         ,支付日期
         ,营期阶段
         ,是否扩科
         ,价格区间
ORDER BY 支付日期,营期sku,商品sku,营期阶段,价格区间
LIMIT   500000
;
