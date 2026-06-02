SELECT  dt as 日期
        ,org_name2 as 前后端
        ,cci2_name as 利润中心
        ,case when cci3_name in ('书法','国画') then '书画'
             else cci3_name
       end  as SKU
        ,studio_lv2 as 渠道聚合类型
        ,pay_amount as GMV
        ,refund_amount as 退款GMV
        ,net_income as 收入
        ,order_sc_user_cnt as 正价课学员数
        ,order_tc_user_cnt as 期课学员数
        ,refund_sc_user_cnt as 退费正价课学员数
        ,refund_tc_user_cnt as 退费期课学员数
        ,freeze_sc_user_cnt as 冻课正价课学员数
        ,freeze_tc_user_cnt as 冻课期课学员数
        ,restore_sc_user_cnt as 解冻正价课学员数
        ,restore_tc_user_cnt as 解冻期课学员数
        ,h5_price as 渠道收入
        ,common_price as 打赏收入
        ,org_name1
FROM    dws_netcashflow_gmv_df
WHERE   dt >= '${start_date}'
AND     dt <= '${end_date}'
-- AND     org_name2 = '大前端'
;


