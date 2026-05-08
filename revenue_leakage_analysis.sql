create or replace table dm_prod.tb_analise_oportunidade_final as
WITH
churn as 
(
  select distinct
    customerID,
    tenure,
    cast(monthlycharges as numeric) as monthlycharges,
    contract,
    internetservice,
    onlinesecurity,
    techsupport
  from dm_prod.base_clientes
  where 1=1
    and churn = false
),
outliers as 
(
  select 
    customerID,
    tenure,
    monthlycharges,
    contract,
    internetservice,
    onlinesecurity,
    techsupport,
    case
      when (tenure >= 48 and monthlycharges > 80) then 'Platinum'
      when (tenure >= 24 and monthlycharges > 60) then 'Gold'
      when (tenure >= 12 and monthlycharges > 40) then 'Silver'
      else 'Bronze'
    end as tier,
    case
      when monthlycharges > avg(monthlycharges) over(partition by contract,internetservice) * 1.2 then 1
      else 0
    end as pay_above_avg
  from churn
  group by all
),
final as 
(
  select
    o.customerID,
    o.tenure,
    o.monthlycharges,
    o.contract,
    o.internetservice,
    o.onlinesecurity,
    o.techsupport,
    o.tier,
    o.pay_above_avg,
    case
      when 
        o.tier in ("Platinum", "Gold") and 
        p.customerId IS NULL and
        o.internetservice = 'Fiber optic' and
        o.techsupport = 'No' and 
        o.onlinesecurity= 'No'
       then 1
      else 0
    end as `target`
  from outliers o
  left join dm_prod.t_painel_parceiro p
    on o.customerid = p.customerID
)

select
  tier,
  contract,
  count(distinct customerid) as qtd_clientes_ativos,
  countif(`target` = 1) as qtd_clientes_criticos,
  sum(monthlycharges) as total_receita,
  sum
  (
    if(`target` = 1,monthlycharges,0)
  ) as receita_em_risco,
  rank() over(order by sum(if(`target` = 1,monthlycharges,0))desc) as rank_de_risco
from final
group by all
