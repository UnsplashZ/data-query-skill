SELECT  flow_no as 订单号
        ,channel_emp_name as 渠道归属人
        ,camp_name as 营期名称
        ,camp_sku as 营期SKU
        ,main_goods_sku as 商品SKU
        ,REGEXP_REPLACE(emp_team_name,'团队$','') as 团队
        ,REGEXP_REPLACE(emp_group_name,'组$','') as 组
        ,REGEXP_REPLACE(REGEXP_REPLACE(order_emp_name,'[0-9]',''),'[\\-\\[（].*$','') as 销售
        ,cci2_name as 利润中心
        ,TO_DATE(refund_time) as 退款日期
        ,MONTH(refund_time) as 退款月份
        ,is_com_name as 当前往期
        ,main_goods_name as 商品名称
        ,case when cci3_name in ('书法','国画') then '书画'
             else cci3_name
       end  as SKU
        ,f_market_belong as 渠道
        ,studio_lv2 as 渠道聚合类型
        ,refund_amount_uhc as 团队退款GMV
        ,refund_amount_hc as 华彩乐园退款GMV
        ,refund_amount as 退款GMV
        ,new_front_end_name as 前后端
        ,main_first_level as 一级分类
FROM    dwd_order_refund_df
WHERE   dt >= '${start_date}'
AND     dt <= '${end_date}'
-- AND     new_front_end_name RLIKE '大前端'
AND     refund_amount > 0