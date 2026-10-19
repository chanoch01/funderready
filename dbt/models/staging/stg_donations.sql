with cleaned as (
    select
        _row_number                                         as row_number,
        to_timestamp(created_at, 'YYYY-MM-DD HH24:MI')      as donated_at,
        amount                                              as amount_as_typed,
        replace(replace(trim(amount), '£', ''), ',', '')    as amount_text,
        upper(trim(currency))                               as currency,
        donor_token,
        trim(campaign)                                      as campaign,
        lower(trim(status))                                 as status
    from {{ source('raw', 'donations') }}
)

select
    row_number,
    donated_at,
    amount_as_typed,
    case when amount_text ~ '^\d+(\.\d{1,2})?$' then amount_text::numeric(12, 2) end as amount_gbp,
    currency,
    donor_token,
    campaign,
    status
from cleaned
