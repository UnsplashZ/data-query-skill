SELECT
    '对公' AS `来源`,
    T2.payno AS `支付单号`,
    T2.businesscode AS `业务单号`,
    T2.formname AS `单据名称`,
    T2.applicantname AS `申请人`,
    T2.applicantdepartmentname AS `申请部门`,
    T2.createddate AS `创建日期`,
    T2.reimbauditapprovaldate AS `审批通过日期`,
    T2.realpaymentdate AS `付款日期`,
    T2.title AS `申请原因`,
    T2.remark AS `备注`,
    T2.expensetypecategory AS `费用大类`,
    T2.expensetypename AS `费用类型`,
    multiIf(
        T2.categories IN ('大前端','大后端'), '线上业务',
        T2.categories IN ('华彩乐园'), '集团留存',
        T2.categories
    ) AS `组织一级`,
    T2.categories AS `组织二级`,
    multiIf(
        T2.expensetypecategory = '实物采购'
            AND T2.expensetypename IN ('课程随材-采购费','课程随材-快递费'), '随材采购',
        T2.expensetypecategory = '实物采购', '电商采购',
        T2.expensetypecategory = '文旅专项', '文旅采购',
        T2.expensetypecategory IN ('外部合作'), '其他交付成本',
        T2.subject
    ) AS `成本科目`,
    T2.cci2name AS `二级成本中心`,
    T2.cci3name AS `三级成本中心`,
    T2.studio_lv2 AS `工作室类型`,
    T2.lineplanedbcommentepaymentamount AS `金额`
FROM dwd_finance_feikong_crop_prepay_all_d AS T2
WHERE
    T2.paymentlinestatusdesc = '已付款'
    AND ifNull(T2.lineplanedbcommentepaymentamount, 0) != 0
    AND substring(T2.realpaymentdate, 1, 10) BETWEEN '{{start_date}}' AND '{{end_date}}'
    AND T2.cci3name IN ('声乐','钢琴','朗诵','书法','口琴','美妆')

UNION ALL

SELECT
    '报销' AS `来源`,
    T3.payno AS `支付单号`,
    T3.businessCode AS `业务单号`,
    T3.formTypeDesc AS `单据名称`,
    T3.applicantName AS `申请人`,
    T3.applicantDeptName AS `申请部门`,
    T3.createdDate AS `创建日期`,
    T3.reimbApprovalDate AS `审批通过日期`,
    T3.reimbPaymentDate AS `付款日期`,
    T3.reimbRemark AS `申请原因`,
    T3.comment AS `备注`,
    T3.expenseTypeCategory AS `费用大类`,
    T3.expenseType AS `费用类型`,
    multiIf(
        T3.org2name IN ('大前端','大后端'), '线上业务',
        T3.org2name IN ('华彩乐园'), '集团留存',
        T3.org2name
    ) AS `组织一级`,
    T3.org2name AS `组织二级`,
    multiIf(
        T3.expenseTypeCategory = '实物采购'
            AND T3.expenseType IN ('课程随材-采购费','课程随材-快递费'), '随材采购',
        T3.expenseTypeCategory = '实物采购', '电商采购',
        T3.expenseTypeCategory = '文旅专项', '文旅采购',
        T3.expenseTypeCategory IN ('外部合作'), '其他交付成本',
        T3.subject
    ) AS `成本科目`,
    T3.cci2 AS `二级成本中心`,
    T3.cci3 AS `三级成本中心`,
    CAST(NULL, 'Nullable(String)') AS `工作室类型`,
    T3.baseAmount AS `金额`
FROM dwd_finance_feikong_expense_all_d AS T3
WHERE
    T3.reimbStatusDesc = '已付款'
    AND T3.formTypeDesc = '日常报销单'
    AND ifNull(T3.baseAmount, 0) != 0
    AND substring(T3.reimbPaymentDate, 1, 10) BETWEEN '{{start_date}}' AND '{{end_date}}'
    AND T3.cci3 IN ('声乐','钢琴','朗诵','书法','口琴','美妆')
;