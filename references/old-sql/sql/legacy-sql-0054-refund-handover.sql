
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
      live_user AS (
        SELECT union_id, anyLast(nick_name) AS nick_name, anyLast(phone) AS phone
        FROM drh_live_user FINAL
        WHERE _sign > 0 AND union_id!=''
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
      complaint_user AS (
        SELECT union_id, max(msgtime) AS latest_complaint_time, count() AS complaint_msg_cnt
        FROM tock_qw_message_res
        WHERE union_id!='' AND match(content, '投诉|客诉|举报|315|消协|黑猫|律师|法院|起诉|报警')
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
      ),
      current_friend AS (
        SELECT union_id, emp_id, anyLast(emp_name) AS emp_name, anyLast(company) AS company,
               anyLast(belong_name) AS belong_name, anyLast(external_user_id) AS external_user_id,
               min(add_time) AS first_add_time, max(add_time) AS latest_add_time,
               max(qw_tag_name) AS qw_tag_name, max(emp_remark) AS emp_remark
        FROM tock_emp_external_user
        WHERE union_id!='' AND emp_id!=0 AND (del_time IS NULL OR del_time <= toDateTime('1971-01-01 00:00:00'))
        GROUP BY union_id, emp_id
      ),
      all_friend AS (
        SELECT union_id, emp_id, anyLast(emp_name) AS emp_name, anyLast(company) AS company,
               anyLast(belong_name) AS belong_name, anyLast(external_user_id) AS external_user_id,
               min(add_time) AS first_add_time, max(add_time) AS latest_add_time,
               max(qw_tag_name) AS qw_tag_name, max(emp_remark) AS emp_remark,
               minIf(del_time, del_time > toDateTime('1971-01-01 00:00:00')) AS first_del_time,
               max(del_time IS NULL OR del_time <= toDateTime('1971-01-01 00:00:00')) AS is_current_friend
        FROM tock_emp_external_user
        WHERE union_id!='' AND emp_id!=0
        GROUP BY union_id, emp_id
      ),
      msg_30 AS (
        SELECT union_id, emp_id, count() AS recent_qw_msg_cnt, max(msgtime) AS latest_qw_msg_time
        FROM tock_qw_message_res
        WHERE union_id!='' AND emp_id!=0 AND msgtime >= toDateTime('2026-05-19 00:00:00') - INTERVAL 30 DAY
        GROUP BY union_id, emp_id
      ),
      msg_30_user AS (
        SELECT m.union_id, count() AS recent_msg_friend_cnt
        FROM msg_30 m INNER JOIN current_friend cf ON m.union_id=cf.union_id AND m.emp_id=cf.emp_id
        GROUP BY m.union_id
      ),
      eligible_user AS (
        SELECT gu.union_id AS eligible_union_id,
               1 AS eligible_flag,
               if(ifNull(mu.recent_msg_friend_cnt,0)>0,1,0) AS has_recent_friend_interaction
        FROM gt880_user gu
        LEFT JOIN study_30 st ON gu.union_id=st.union_id
        LEFT JOIN msg_30_user mu ON gu.union_id=mu.union_id
        LEFT JOIN complaint_user cu ON gu.union_id=cu.union_id
        WHERE cu.union_id='' AND (ifNull(st.recent_study_record_cnt,0)>0 OR ifNull(mu.recent_msg_friend_cnt,0)>0)
      )
    SELECT ou.union_id AS union_id, lu.nick_name, lu.phone, ou.paid_order_cnt, round(ou.paid_amount,2) AS paid_amount,
           round(ou.refund_amount,2) AS refund_amount, ou.latest_refund_time, ou.latest_pay_time,
           arrayStringConcat(ou.paid_skus, ',') AS paid_skus, ou.has_official_order, round(ou.official_paid_amount,2) AS official_paid_amount,
           ifNull(st.recent_study_record_cnt,0) AS recent_study_record_cnt, st.latest_study_time, round(ifNull(st.recent_study_minutes,0),2) AS recent_study_minutes,
           ifNull(st.all_started_class_cnt,0) AS all_started_class_cnt, st.first_started_class_time,
           ifNull(si.is_served,0) AS is_served, si.latest_service_stage, si.latest_service_camp_name, si.latest_service_emp_name, si.latest_service_group_name,
           if(ifNull(st.recent_study_record_cnt,0)>0,1,0) AS has_recent_study, ifNull(eu.has_recent_friend_interaction,0) AS has_recent_friend_interaction,
           if(ifNull(ru.union_id, '') != '', 1, 0) AS is_refund_user, if(ifNull(fu.union_id, '') != '', 1, 0) AS is_first_lt1000_user, ifNull(eu.eligible_flag, 0) AS is_gt880_eligible_user
    FROM order_user ou
    LEFT JOIN live_user lu ON ou.union_id=lu.union_id
    LEFT JOIN study_30 st ON ou.union_id=st.union_id
    LEFT JOIN service_info si ON ou.union_id=si.union_id
    LEFT JOIN refund_user ru ON ou.union_id=ru.union_id
    LEFT JOIN first_lt1000_user fu ON ou.union_id=fu.union_id
    LEFT JOIN eligible_user eu ON ou.union_id=eu.eligible_union_id
    WHERE ifNull(ru.union_id, '') != '' OR ifNull(fu.union_id, '') != '' OR ifNull(eu.eligible_flag, 0) = 1
    