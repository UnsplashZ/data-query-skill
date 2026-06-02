SELECT
    '对公' AS 来源,
    T2.payno AS 支付单号,
    T2.businesscode AS 业务单号,
    T2.formname AS 单据名称,
    T2.applicantname AS 申请人,
    T2.applicantdepartmentname AS 申请部门,
    T2.createddate AS 创建日期,
    T2.reimbauditapprovaldate AS 审批通过日期,
    T2.realpaymentdate AS 付款日期,
    T2.title AS 申请原因,
    T2.remark AS 备注,
    T2.expensetypecategory AS 费用大类,
    T2.expensetypename AS 费用类型,
    CASE
        WHEN T2.categories IN ('大前端','大后端') THEN '线上业务'
        WHEN T2.categories IN ('华彩乐园') THEN '集团留存'
        ELSE T2.categories
    END AS 组织一级,
    T2.categories AS 组织二级,
    CASE
        WHEN T2.expensetypecategory = '实物采购'
             AND T2.expensetypename IN ('课程随材-采购费','课程随材-快递费') THEN '随材采购'
        WHEN T2.expensetypecategory = '实物采购' THEN '电商采购'
        WHEN T2.expensetypecategory = '文旅专项' THEN '文旅采购'
        WHEN T2.expensetypecategory IN ('外部合作') THEN '其他交付成本'
        ELSE T4.subject
    END AS 成本科目,
    T2.cci2name AS 二级成本中心,
    T2.cci3name AS 三级成本中心,
    T2.studio_lv2 AS 工作室类型,
    T2.lineplanedbcommentepaymentamount AS 金额
FROM dwd_finance_feikong_crop_prepay_all_d T2
LEFT JOIN (
    SELECT DISTINCT subject, subject1
    FROM ods_offline_finance_subject_df
) T4
ON T2.expensetypecategory = T4.subject1
WHERE
    T2.paymentlinestatusdesc = '已付款'
    AND COALESCE(T2.lineplanedbcommentepaymentamount,0) <> 0
    AND SUBSTR(T2.realpaymentdate,1,10) BETWEEN '${start_date}' AND '${end_date}'
    AND T2.cci3name = '声乐'

UNION ALL

SELECT
    '报销' AS 来源,
    T3.payno AS 支付单号,
    T3.businesscode AS 业务单号,
    T3.formtypedesc AS 单据名称,
    T3.applicantname AS 申请人,
    T3.applicantdeptname AS 申请部门,
    T3.createddate AS 创建日期,
    T3.reimbapprovaldate AS 审批通过日期,
    T3.reimbpaymentdate AS 付款日期,
    T3.reimbremark AS 申请原因,
    T3.comment AS 备注,
    T3.expensetypecategory AS 费用大类,
    T3.expensetype AS 费用类型,
    CASE
        WHEN T3.org2name IN ('大前端','大后端') THEN '线上业务'
        WHEN T3.org2name IN ('华彩乐园') THEN '集团留存'
        ELSE T3.org2name
    END AS 组织一级,
    T3.org2name AS 组织二级,
    CASE
        WHEN T3.expensetypecategory = '实物采购'
             AND T3.expensetype IN ('课程随材-采购费','课程随材-快递费') THEN '随材采购'
        WHEN T3.expensetypecategory = '实物采购' THEN '电商采购'
        WHEN T3.expensetypecategory = '文旅专项' THEN '文旅采购'
        WHEN T3.expensetypecategory IN ('外部合作') THEN '其他交付成本'
        ELSE T4.subject
    END AS 成本科目,
    T3.cci2 AS 二级成本中心,
    T3.cci3 AS 三级成本中心,
    NULL AS 工作室类型,
    T3.baseamount AS 金额
FROM dwd_finance_feikong_expense_all_d T3
LEFT JOIN (
    SELECT DISTINCT subject, subject1
    FROM ods_offline_finance_subject_df
) T4
ON T3.expensetypecategory = T4.subject1
WHERE
    T3.reimbstatusdesc = '已付款'
    AND T3.formtypedesc = '日常报销单'
    AND COALESCE(T3.baseamount,0) <> 0
    AND SUBSTR(T3.reimbpaymentdate,1,10) BETWEEN '${start_date}' AND '${end_date}'
    AND T3.cci3 = '声乐'
;