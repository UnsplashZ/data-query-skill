select p_date as 日期,
       org_name2 as 前后端,
       cci2_name as 利润中心,
       case when cci3_name in ('书法','国画') then '书画'
             else cci3_name
       end  as SKU,
       studio_lv2 as 渠道聚合类型,
       indicators_name as 成本项,
       sum(cost_amount) as 成本金额,
       org_name1
from dws_pl_cost_md_pdf
where mn >= substring(replace('${start_date}','-',''),1,6)
and mn <= substring(replace('${end_date}','-',''),1,6)
group by p_date,
         org_name2,
         cci2_name,
         case when cci3_name in ('书法','国画') then '书画'
             else cci3_name
       end ,
         studio_lv2,
         indicators_name
         ,org_name1
;