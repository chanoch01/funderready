select donation_id, amount_gbp
from {{ ref('fct_donations') }}
where amount_gbp <= 0
