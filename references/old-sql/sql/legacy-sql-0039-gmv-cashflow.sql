SELECT  flow_no as 订单号
        ,channel_emp_name as 渠道归属人
        ,camp_name as 营期名称
        ,camp_sku as 营期SKU
        ,main_goods_sku as 商品SKU
        ,regexp_replace(emp_team_name,'团队$','') AS 团队
        ,REGEXP_REPLACE(emp_group_name,'组$','') AS 组
        ,REGEXP_REPLACE(REGEXP_REPLACE(order_emp_name,'[0-9]',''),'[\\-\\[（].*$','') AS 销售
        ,cci2_name as 利润中心
        ,TO_DATE(pay_time) AS 支付日期
        ,MONTH(pay_time) AS 支付月份
        ,is_com_name as 当前往期
        ,main_goods_name as 商品名称
        ,case when cci3_name in ('书法','国画') then '书画'
              else cci3_name
        end  as SKU
        ,f_market_belong as 渠道
        ,studio_lv2 as 渠道聚合类型
        ,net_income as 收入
        ,pay_amount_uhc as 团队GMV
        ,pay_amount_hc as 华彩乐园GMV
        ,pay_amount as GMV
        ,new_front_end_name as 前后端
        ,main_first_level as 一级分类
      --   ,case 
      --   when a8.is_class = 0 then '销转营期'
      --   when a8.is_class = 1 and a8.class_stage = 2 then '二阶营期'
      --   when a8.is_class = 1 and a8.class_stage = 3 then '三阶营期'
      --   when a8.is_class = 1 and a8.class_stage = 4 then '四阶营期'
      --   when a8.is_class = 1 and a8.class_stage = 5 then '五阶营期'
      --       else '特殊营期'
      --   end 营期阶段
FROM    dwd_order_flow_df a1 
-- left join (
--       select id, name, category, is_class, class_stage from drh_live_camp
-- ) a8 on a1.camp_id = a8.id 
-- WHERE   new_front_end_name RLIKE '大前端'
where     dt >= '${start_date}'
AND     dt <= '${end_date}'
AND     pay_amount > 0