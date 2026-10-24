-- One row per donation in the payment export.
-- is_countable is what every funder total should filter on: paid, not refunded,
-- and an amount we could read.

select
    md5('donation|' || row_number)                          as donation_id,
    donated_at,
    donated_at::date                                        as donation_date,
    amount_gbp,
    campaign,
    donor_token,
    status,
    status = 'paid' and amount_gbp is not null              as is_countable,
    row_number                                              as source_row_number
from {{ ref('stg_donations') }}
