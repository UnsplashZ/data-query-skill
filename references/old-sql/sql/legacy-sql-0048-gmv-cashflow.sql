SELECT *
FROM dws_cash_account_indicators_md_pdf
WHERE mn = '${yyyymm}'
  AND indicators_name IN ('GMV', '渠道收入', '打赏收入')
  AND to_date(p_date) <= '${bizdate}'
