# ODPS ↔ ClickHouse Schema KB

- 生成时间：`2026-04-17 18:11:38`
- ODPS：`drh_prod_odps`，表数：`690`
- ClickHouse：`drh`，表数：`1092`
- ODPS 本次刷新：新增 `0` / 变更 `88` / 删除 `0`
- ClickHouse 本次刷新：新增 `0` / 变更 `0` / 删除 `0`

## 使用建议
1. 先查本地知识库定位候选表和字段。
2. 再用实时探表 SQL 校验字段和值。
3. 最后再写正式 SQL，避免按业务口径误猜物理字段。

## 前缀规模
- ODPS：{'dwd': 45, 'dws': 42, 'ods': 64, 'dim': 18, 'ads': 0}
- ClickHouse：{'dwd': 9, 'dws': 3, 'ods': 0, 'dim': 2, 'ads': 0}

## 高优先表落点（前 30）
- `dws_cash_account_indicators_md_pdf` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_dws_cash_account_indicators_md_pdf` (score=0.8357)
- `dwd_order_refund_df` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_dwd_order_refund_df` (score=0.886)
- `ods_feishu_refund_approval_detail_all_d` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_ods_feishu_refund_approval_detail_all_d` (score=0.9437)
- `dwd_order_flow_df` | 匹配：`exact` | ClickHouse同名：`是`
- `dwd_finance_feikong_crop_prepay_all_d` | 匹配：`exact` | ClickHouse同名：`是`
- `ods_offline_finance_subject_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_finance_feikong_expense_all_d` | 匹配：`exact` | ClickHouse同名：`是`
- `dws_netcashflow_gmv_df` | 匹配：`exact` | ClickHouse同名：`是`
- `dws_netcashflow_cost_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dws_pl_cost_md_pdf` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_order_handover_df` | 匹配：`exact` | ClickHouse同名：`是`
- `dwd_ad_pic_zip` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`drh_ad_pic_local` (score=0.5074)
- `dwd_app_active_user_pdi` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_app_tracking_action_pdi` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_dwd_app_tracking_pdi` (score=0.5781)
- `dwd_app_tracking_pdi` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_dwd_app_tracking_pdi` (score=0.7348)
- `dwd_app_user_detail_info_df` | 匹配：`exact` | ClickHouse同名：`是`
- `dwd_applet_main_df` | 匹配：`exact` | ClickHouse同名：`是`
- `dwd_applet_main_repeat_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_applet_main_repeat_pdf` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_applet_originally_channel_cost_df` | 匹配：`exact` | ClickHouse同名：`是`
- `dwd_applet_sale_plan_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_applet_site_day_cost_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_course_info_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_course_study_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_edu_pay_user_df` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_edu_user_study_info_df` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_dwd_edu_user_study_info_df` (score=0.932)
- `dwd_edu_user_study_info_pdi` | 匹配：`candidate` | ClickHouse同名：`否` | 候选：`tock_dwd_edu_user_study_info_df` (score=0.7537)
- `dwd_finance_cash_cost_md_pdf` | 匹配：`exact` | ClickHouse同名：`是`
- `dwd_finance_cci_rate_pdf` | 匹配：`missing` | ClickHouse同名：`否`
- `dwd_finance_cost_prepayment_rate_pdf` | 匹配：`missing` | ClickHouse同名：`否`

## 疑似改名映射（前 30）
- `ods_feishu_refund_approval_detail_all_d` → `tock_ods_feishu_refund_approval_detail_all_d` | score=0.9437 | name=0.8977 | cols=1.0
- `dws_app_tracking_circle_content_d_pdi` → `tock_dws_app_tracking_circle_content_d_pdi` | score=0.9431 | name=0.8966 | cols=1.0
- `ods_odps_xet_bill_detail_plus_rf` → `tock_ods_odps_xet_bill_detail_plus_rf` | score=0.9414 | name=0.8934 | cols=1.0
- `ods_odps_zfb_bill_detail_plus_rf` → `tock_ods_odps_zfb_bill_detail_plus_rf` | score=0.9414 | name=0.8934 | cols=1.0
- `ods_odps_qw_bill_detail_plus_rf` → `tock_ods_odps_qw_bill_detail_plus_rf` | score=0.9409 | name=0.8926 | cols=1.0
- `drh_drh_emp_external_user` → `drh_emp_external_user_local` | score=0.9393 | name=0.8027 | cols=0.9286
- `drh_drh_live_camp_date` → `drh_live_camp_date_local` | score=0.9337 | name=0.7939 | cols=0.9268
- `dws_app_course_tracking_d_pdi` → `tock_dws_app_course_tracking_d_pdi` | score=0.9337 | name=0.8794 | cols=1.0
- `drh_drh_ad_user_pic` → `drh_ad_user_pic_local` | score=0.9331 | name=0.7825 | cols=0.9394
- `dws_app_user_koc_follow_pdf` → `tock_dws_app_user_koc_follow_pdf` | score=0.9326 | name=0.8775 | cols=1.0
- `dws_app_work_tracking_d_pdi` → `tock_dws_app_work_tracking_d_pdi` | score=0.9326 | name=0.8775 | cols=1.0
- `ods_odps_xet_bill_detail_rf` → `tock_ods_odps_xet_bill_detail_rf` | score=0.9326 | name=0.8775 | cols=1.0
- `ods_odps_zfb_bill_detail_rf` → `tock_ods_odps_zfb_bill_detail_rf` | score=0.9326 | name=0.8775 | cols=1.0
- `dwa_app_order_jx_detail_df` → `tock_dwa_app_order_jx_detail_df` | score=0.932 | name=0.8764 | cols=1.0
- `dwd_edu_user_study_info_df` → `tock_dwd_edu_user_study_info_df` | score=0.932 | name=0.8764 | cols=1.0
- `dws_app_ads_tracking_d_pdi` → `tock_dws_app_ads_tracking_d_pdi` | score=0.932 | name=0.8764 | cols=1.0
- `dws_app_agg_tracking_d_pdi` → `tock_dws_app_agg_tracking_d_pdi` | score=0.932 | name=0.8764 | cols=1.0
- `ods_odps_dd_bill_detail_rf` → `tock_ods_odps_dd_bill_detail_rf` | score=0.932 | name=0.8764 | cols=1.0
- `ods_odps_qw_bill_detail_rf` → `tock_ods_odps_qw_bill_detail_rf` | score=0.932 | name=0.8764 | cols=1.0
- `ods_odps_wd_bill_detail_rf` → `tock_ods_odps_wd_bill_detail_rf` | score=0.932 | name=0.8764 | cols=1.0
- `dws_app_order_flow_md_pdf` → `tock_dws_app_order_flow_md_pdf` | score=0.9314 | name=0.8753 | cols=1.0
- `dws_app_tracking_qz_d_pdi` → `tock_dws_app_tracking_qz_d_pdi` | score=0.9314 | name=0.8753 | cols=1.0
- `ods_ots_wx_bill_detail_rf` → `tock_ods_ots_wx_bill_detail_rf` | score=0.9314 | name=0.8753 | cols=1.0
- `ods_ots_dd_bill_plus_rf` → `tock_ods_ots_dd_bill_plus_rf` | score=0.9301 | name=0.8728 | cols=1.0
- `dws_mo_tracking_plus_pdi` → `tock_dws_mo_tracking_plus_pdi` | score=0.9223 | name=0.8586 | cols=1.0
- `dwa_app_user_active_df` → `tock_dwa_app_user_active_df` | score=0.9208 | name=0.856 | cols=1.0
- `dws_app_tracking_d_pdi` → `tock_dws_app_tracking_d_pdi` | score=0.9208 | name=0.856 | cols=1.0
- `temp_dwa_user_live_pdi` → `tock_temp_dwa_user_live_pdi` | score=0.9208 | name=0.856 | cols=1.0
- `dwa_mo_user_active_df` → `tock_dwa_mo_user_active_df` | score=0.9199 | name=0.8544 | cols=1.0
- `drh_drh_living_study_info` → `drh_living_study_info_local` | score=0.9152 | name=0.8027 | cols=0.875

## 高频字段 → 优先表（前 40）
- `dt`: `dwd_app_active_user_pdi`, `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_app_user_detail_info_df`, `dwd_applet_main_repeat_pdf`, `dwd_edu_pay_user_df`, `dwd_edu_user_study_info_df`, `dwd_edu_user_study_info_pdi` ... (+41)
- `union_id`: `dwd_app_active_user_pdi`, `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_app_user_detail_info_df`, `dwd_applet_main_df`, `dwd_applet_main_repeat_df`, `dwd_applet_main_repeat_pdf`, `dwd_course_study_df` ... (+36)
- `camp_id`: `dwd_applet_main_df`, `dwd_applet_originally_channel_cost_df`, `dwd_applet_sale_plan_df`, `dwd_applet_site_day_cost_df`, `dwd_course_study_df`, `dwd_edu_pay_user_df`, `dwd_edu_user_study_info_df`, `dwd_edu_user_study_info_pdi` ... (+27)
- `studio_lv2`: `dwd_applet_main_df`, `dwd_applet_originally_channel_cost_df`, `dwd_finance_cash_cost_md_pdf`, `dwd_finance_cci_rate_pdf`, `dwd_finance_cost_prepayment_rate_pdf`, `dwd_finance_feikong_crop_prepay_all_d`, `dwd_finance_feikong_crop_prepay_df`, `dwd_order_common_df` ... (+19)
- `camp_name`: `dwd_ad_pic_zip`, `dwd_applet_main_df`, `dwd_applet_originally_channel_cost_df`, `dwd_applet_site_day_cost_df`, `dwd_course_study_df`, `dwd_edu_pay_user_df`, `dwd_edu_user_study_info_df`, `dwd_edu_user_study_info_pdi` ... (+18)
- `org_name2`: `dwd_applet_originally_channel_cost_df`, `dwd_finance_cash_cost_md_pdf`, `dwd_finance_cci_rate_pdf`, `dwd_money_class_user_agg_df`, `dwd_order_common_df`, `dwd_order_handover_df`, `dwd_order_receipt_refund_md_pdf`, `dws_cash_account_debt_df` ... (+17)
- `cci2_name`: `dwd_applet_originally_channel_cost_df`, `dwd_finance_cash_cost_md_pdf`, `dwd_finance_cci_rate_pdf`, `dwd_money_class_user_agg_df`, `dwd_order_common_df`, `dwd_order_flow_df`, `dwd_order_handover_df`, `dwd_order_receipt_refund_md_pdf` ... (+11)
- `cci3_name`: `dwd_applet_originally_channel_cost_df`, `dwd_finance_cci_rate_pdf`, `dwd_money_class_user_agg_df`, `dwd_order_flow_df`, `dwd_order_handover_df`, `dwd_order_receipt_refund_md_pdf`, `dwd_order_refund_df`, `dws_netcashflow_cost_df` ... (+9)
- `user_id`: `dwd_order_common_df`, `dwd_ots_test_user_order_all_df`, `dwd_ots_test_user_tip_all_df`, `dwd_ots_user_order_all_df`, `dwd_ots_user_tip_all_df`, `dwd_test_ots_user_order_all_df`, `dwd_user_course_all_d`, `dwd_user_order_all_df` ... (+7)
- `live_user_id`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_applet_main_df`, `dwd_course_study_df`, `dwd_edu_pay_user_df`, `dwd_edu_user_study_info_df`, `dwd_edu_user_study_info_pdi`, `dwd_handover_plus_pdf` ... (+6)
- `mn`: `dwd_finance_cash_cost_md_pdf`, `dwd_order_receipt_refund_md_pdf`, `dws_app_order_flow_md_pdf`, `dws_cash_account_debt_md_pdi`, `dws_cash_account_indicators_md_pdf`, `dws_cash_account_md_pdf`, `dws_cash_account_md_pdf_test`, `dws_netcashflow_core_indicators_md_pdf` ... (+8)
- `create_time`: `dwd_ad_pic_zip`, `dwd_applet_main_df`, `dwd_applet_main_repeat_df`, `dwd_applet_main_repeat_pdf`, `dwd_applet_site_day_cost_df`, `dwd_course_info_df`, `dwd_handover_plus_pdf`, `dwd_order_common_df` ... (+5)
- `emp_id`: `dwd_ad_pic_zip`, `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_course_info_df`, `dwd_edu_pay_user_df`, `dwd_h5_app_user_emp_pdf`, `dwd_handover_plus_pdf`, `dwd_ots_channel_data` ... (+5)
- `study_time`: `dwd_course_study_df`, `dwd_user_course_all_d`, `dws_applet_detail_df`, `dws_camp_all_df`, `dws_ots_camp_all_df`, `dws_ots_test_camp_all_df`, `dws_ots_test_user_camp_all_df`, `dws_ots_test_user_live_all_df` ... (+5)
- `pay_time`: `dwd_edu_pay_user_df`, `dwd_handover_plus_pdf`, `dwd_order_common_df`, `dwd_order_flow_df`, `dwd_order_h5_df`, `dwd_order_handover_df`, `dwd_order_refund_df`, `dwd_ots_test_user_tip_all_df` ... (+4)
- `sku`: `dwd_app_user_detail_info_df`, `dwd_course_study_df`, `dwd_edu_pay_user_df`, `dwd_mo_tracking_pdi`, `dwd_mo_tracking_pdi_bak`, `dwd_order_handover_df`, `dwd_ots_test_user_order_all_df`, `dwd_ots_user_order_all_df` ... (+4)
- `sku_id`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_applet_main_df`, `dwd_applet_main_repeat_df`, `dwd_applet_main_repeat_pdf`, `dwd_applet_sale_plan_df`, `dwd_edu_pay_user_df`, `dwd_mo_tracking_pdi` ... (+4)
- `arrive_rate`: `dws_app_ads_tracking_d_pdi`, `dws_app_agg_tracking_d_pdi`, `dws_app_course_tracking_d_pdi`, `dws_app_work_tracking_d_pdi`, `dws_camp_all_df`, `dws_ots_camp_all_df`, `dws_ots_test_camp_all_df`, `dws_ots_test_user_camp_all_df` ... (+4)
- `applet_user_id`: `dwd_applet_main_df`, `dwd_applet_main_repeat_df`, `dwd_applet_main_repeat_pdf`, `dwd_course_study_df`, `dwd_order_common_df`, `dwd_order_flow_df`, `dwd_order_h5_df`, `dwd_order_handover_df` ... (+3)
- `org_name1`: `dwd_finance_cash_cost_md_pdf`, `dwd_finance_cci_rate_pdf`, `dws_netcashflow_core_indicators_md_pdf`, `dws_netcashflow_cost_df`, `dws_netcashflow_cost_df_test`, `dws_netcashflow_cost_pdf`, `dws_netcashflow_gmv_df`, `dws_netcashflow_order_gmv_df` ... (+3)
- `sku_name`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_applet_main_df`, `dwd_applet_main_repeat_df`, `dwd_applet_main_repeat_pdf`, `dwd_applet_sale_plan_df`, `dwd_mo_tracking_plus_pdi`, `dwd_order_common_df` ... (+3)
- `p_date`: `dwd_money_class_user_agg_df`, `dws_cash_account_indicators_md_pdf`, `dws_cash_account_md_pdf`, `dws_cash_account_md_pdf_test`, `dws_netcashflow_core_indicators_md_pdf`, `dws_netcashflow_core_indicators_md_pdf_test`, `dws_pl_core_indicators_md_pdf`, `dws_pl_cost_md_pdf` ... (+3)
- `channel_id`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_mo_tracking_pdi`, `dwd_mo_tracking_pdi_bak`, `dwd_order_flow_df`, `dwd_order_h5_df`, `dwd_order_handover_df`, `dwd_order_receipt_refund_md_pdf` ... (+2)
- `update_time`: `dwd_ad_pic_zip`, `dwd_applet_main_df`, `dwd_applet_site_day_cost_df`, `dwd_handover_plus_pdf`, `dwd_order_common_df`, `dwd_order_flow_df`, `dwd_order_handover_df`, `dwd_order_receipt_refund_md_pdf` ... (+2)
- `goods_id`: `dwd_edu_pay_user_df`, `dwd_handover_plus_pdf`, `dwd_order_common_df`, `dwd_order_h5_df`, `dwd_order_handover_df`, `dwd_ots_channel_data`, `dwd_ots_test_user_order_all_df`, `dwd_ots_user_order_all_df` ... (+2)
- `position`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_mo_tracking_pdi`, `dwd_mo_tracking_pdi_bak`, `dws_app_ads_tracking_d_pdi`, `dws_app_agg_tracking_d_pdi`, `dws_app_course_tracking_d_pdi`, `dws_app_tracking_d_pdi` ... (+2)
- `indicators_name`: `dws_cash_account_indicators_md_pdf`, `dws_netcashflow_core_indicators_md_pdf`, `dws_netcashflow_core_indicators_md_pdf_test`, `dws_netcashflow_cost_df`, `dws_netcashflow_cost_df_test`, `dws_netcashflow_cost_pdf`, `dws_pl_core_indicators_md_pdf`, `dws_pl_cost_md_pdf` ... (+1)
- `collect_order_no`: `dwd_course_study_df`, `dwd_edu_pay_user_df`, `dwd_handover_plus_pdf`, `dwd_order_flow_df`, `dwd_order_handover_df`, `dwd_order_receipt_refund_md_pdf`, `dwd_order_refund_df`, `dwd_ots_test_user_order_all_df` ... (+1)
- `camp_sku`: `dwd_applet_main_df`, `dwd_applet_site_day_cost_df`, `dwd_edu_pay_user_df`, `dwd_order_common_df`, `dwd_order_flow_df`, `dwd_order_receipt_refund_md_pdf`, `dwd_order_refund_df`, `dws_app_order_flow_md_pdf` ... (+1)
- `camp_date_id`: `dwd_ad_pic_zip`, `dwd_applet_main_df`, `dwd_applet_originally_channel_cost_df`, `dwd_applet_sale_plan_df`, `dwd_applet_site_day_cost_df`, `dwd_order_common_df`, `dwd_ots_channel_data`, `dwd_user_basic_detail_all_d` ... (+1)
- `live_id`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_edu_user_study_info_df`, `dwd_edu_user_study_info_pdi`, `dwd_order_common_df`, `dwd_ots_test_user_tip_all_df`, `dwd_ots_user_tip_all_df`, `dwd_user_live_source_pdi` ... (+1)
- `pay_amount`: `dwd_finance_cash_cost_md_pdf`, `dwd_order_flow_df`, `dwd_order_refund_df`, `dws_cash_account_debt_md_pdi`, `dws_netcashflow_gmv_df`, `dws_netcashflow_order_gmv_df`, `dws_pl_kpi_md_pdf`, `dws_pl_kpi_mtd_pdf`
- `sale_emp_id`: `dwd_applet_main_df`, `dwd_applet_originally_channel_cost_df`, `dwd_applet_sale_plan_df`, `dwd_course_study_df`, `dws_applet_detail_df`, `dws_pl_kpi_md_pdf`, `dws_pl_kpi_md_pdf_1`, `dws_pl_kpi_mtd_pdf`
- `friend_cnt`: `dwd_applet_originally_channel_cost_df`, `dws_app_ads_tracking_d_pdi`, `dws_app_agg_tracking_d_pdi`, `dws_app_course_tracking_d_pdi`, `dws_app_tracking_d_pdi`, `dws_app_work_tracking_d_pdi`, `dws_pl_kpi_md_pdf`, `dws_pl_kpi_mtd_pdf`
- `goods_name`: `dwd_order_common_df`, `dwd_ots_channel_data`, `dwd_ots_test_user_order_all_df`, `dwd_ots_test_user_tip_all_df`, `dwd_ots_user_order_all_df`, `dwd_ots_user_tip_all_df`, `dwd_test_ots_user_order_all_df`, `dwd_user_order_all_df`
- `finish_rate`: `dws_camp_all_df`, `dws_ots_camp_all_df`, `dws_ots_test_camp_all_df`, `dws_ots_test_user_camp_all_df`, `dws_ots_test_user_live_all_df`, `dws_ots_user_camp_all_df`, `dws_ots_user_live_all_df`, `dws_user_camp_all_df`
- `msg_times`: `dws_camp_all_df`, `dws_ots_camp_all_df`, `dws_ots_test_camp_all_df`, `dws_ots_test_user_camp_all_df`, `dws_ots_test_user_live_all_df`, `dws_ots_user_camp_all_df`, `dws_ots_user_live_all_df`, `dws_user_camp_all_df`
- `works_submit_rate`: `dws_camp_all_df`, `dws_ots_camp_all_df`, `dws_ots_test_camp_all_df`, `dws_ots_test_user_camp_all_df`, `dws_ots_test_user_live_all_df`, `dws_ots_user_camp_all_df`, `dws_ots_user_live_all_df`, `dws_user_camp_all_df`
- `refund_amount`: `dwd_order_flow_df`, `dwd_order_refund_df`, `dws_netcashflow_gmv_df`, `dws_netcashflow_refund_order_gmv_df`, `dws_pl_kpi_md_pdf`, `dws_pl_kpi_mtd_pdf`, `ods_feishu_refund_approval_detail_all_d`
- `user_type_name`: `dwd_app_tracking_action_pdi`, `dwd_app_tracking_pdi`, `dwd_order_flow_df`, `dws_app_ads_tracking_d_pdi`, `dws_app_agg_tracking_d_pdi`, `dws_app_course_tracking_d_pdi`, `dws_app_work_tracking_d_pdi`

## 输出文件
- 统一索引：`${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/unified_schema_index.json`
- 字段倒排：`${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/field_to_tables.json`
- 表映射：`${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/table_mapping.json`
- 刷新摘要：`${HERMES_HOME:-~/.hermes}/cleaned/projects/sql-metadata-index/index/refresh_summary.json`
