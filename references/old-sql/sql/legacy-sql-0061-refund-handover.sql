
    WITH
      tail_pay AS (
        SELECT relate_flow_no FROM dwd_order_flow_df
        WHERE pay_status_name='支付成功' AND pay_type_code=2 AND relate_flow_no!=''
        GROUP BY relate_flow_no
      ),
      order_user AS (
        SELECT union_id,
               count() AS paid_order_cnt,
               sum(pay_amount) AS paid_amount,
               sum(refund_amount) AS refund_amount,
               max(refund_time) AS latest_refund_time,
               max(pay_time) AS latest_pay_time,
               groupUniqArray(camp_sku) AS paid_skus,
               max(is_official) AS has_official_order,
               sumIf(pay_amount, is_official=1) AS official_paid_amount
        FROM dwd_order_flow_df
        WHERE pay_status_name='支付成功' AND main_first_level='课程'
          AND union_id!='' AND pay_time >= toDateTime('2026-01-01 00:00:00')
        GROUP BY union_id
      ),
      refund_user AS (
        SELECT DISTINCT union_id FROM dwd_order_flow_df
        WHERE pay_status_name='支付成功' AND main_first_level='课程'
          AND union_id!='' AND pay_time >= toDateTime('2026-01-01 00:00:00') AND refund_amount>0
      ),
      first_lt1000_user AS (
        SELECT DISTINCT f.union_id
        FROM dwd_order_flow_df f LEFT JOIN tail_pay t ON f.flow_no=t.relate_flow_no
        WHERE f.pay_status_name='支付成功' AND f.main_first_level='课程'
          AND f.union_id!='' AND f.pay_time >= toDateTime('2026-01-01 00:00:00')
          AND f.pay_type_code=1 AND f.pay_amount < 1000 AND f.refund_amount<=0 AND t.relate_flow_no=''
      ),
      gt880_user AS (
        SELECT DISTINCT union_id FROM dwd_order_flow_df
        WHERE pay_status_name='支付成功' AND main_first_level='课程'
          AND union_id!='' AND pay_time >= toDateTime('2026-01-01 00:00:00') AND pay_amount>880 AND refund_amount<=0
      ),
      study_30 AS (
        SELECT union_id,
               countIf(class_time >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY AND (study_time>0 OR zb_study_time>0 OR submit_cnt>0 OR e_time_cnt>0 OR message_cnt>0)) AS recent_study_record_cnt,
               maxIf(class_time, class_time >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY AND (study_time>0 OR zb_study_time>0 OR submit_cnt>0 OR e_time_cnt>0 OR message_cnt>0)) AS latest_study_time,
               sumIf(study_time + zb_study_time, class_time >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY AND (study_time>0 OR zb_study_time>0 OR submit_cnt>0 OR e_time_cnt>0 OR message_cnt>0)) AS recent_study_minutes,
               countIf(class_time > toDateTime('1971-01-01 00:00:00') AND study_time > 0) AS all_started_class_cnt,
               minIf(class_time, class_time > toDateTime('1971-01-01 00:00:00') AND study_time > 0) AS first_started_class_time
        FROM tock_ast_process_data
        WHERE union_id!=''
        GROUP BY union_id
      ),
      service_info AS (
        SELECT union_id,
               max(service_camp_name!='') AS is_served,
               argMax(service_camp_stage, pay_time) AS latest_service_stage,
               argMax(service_camp_name, pay_time) AS latest_service_camp_name,
               argMax(service_emp_name, pay_time) AS latest_service_emp_name,
               argMax(service_emp_group_name, pay_time) AS latest_service_group_name
        FROM tock_handover_plus
        WHERE union_id!='' AND pay_time >= toDateTime('2026-01-01 00:00:00')
        GROUP BY union_id
      )
    SELECT ou.union_id AS union_id, ou.paid_order_cnt, round(ou.paid_amount,2) AS paid_amount,
           round(ou.refund_amount,2) AS refund_amount, ou.latest_refund_time, ou.latest_pay_time,
           arrayStringConcat(ou.paid_skus, ',') AS paid_skus, ou.has_official_order, round(ou.official_paid_amount,2) AS official_paid_amount,
           ifNull(st.recent_study_record_cnt,0) AS recent_study_record_cnt, st.latest_study_time, round(ifNull(st.recent_study_minutes,0),2) AS recent_study_minutes,
           ifNull(st.all_started_class_cnt,0) AS all_started_class_cnt, st.first_started_class_time,
           ifNull(si.is_served,0) AS is_served, si.latest_service_stage, si.latest_service_camp_name, si.latest_service_emp_name, si.latest_service_group_name,
           if(ifNull(st.recent_study_record_cnt,0)>0,1,0) AS has_recent_study,
           if(ifNull(ru.union_id, '') != '', 1, 0) AS is_refund_user,
           if(ifNull(fu.union_id, '') != '', 1, 0) AS is_first_lt1000_user,
           if(ifNull(gu.union_id, '') != '', 1, 0) AS is_gt880_noref_user,
           ou.paid_order_cnt AS paid_order_cnt
    FROM order_user ou
    LEFT JOIN study_30 st ON ou.union_id=st.union_id
    LEFT JOIN service_info si ON ou.union_id=si.union_id
    LEFT JOIN refund_user ru ON ou.union_id=ru.union_id
    LEFT JOIN first_lt1000_user fu ON ou.union_id=fu.union_id
    LEFT JOIN gt880_user gu ON ou.union_id=gu.union_id
    WHERE ifNull(ru.union_id, '') != '' OR ifNull(fu.union_id, '') != '' OR ifNull(gu.union_id, '') != ''
    