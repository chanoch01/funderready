-- One row per child, after duplicate resolution.
--
-- Where repeat sign-ups disagree, we take the most recent answer for things that change
-- (postcode, programme, photo consent, which can be withdrawn) and the first known date of
-- birth, which should not change. A child whose sign-ups give two different birth months
-- gets a task in the data-quality inbox.

with signups as (
    select s.*, r.person_id
    from {{ ref('stg_signups') }} as s
    inner join {{ ref('int_signups_resolved') }} as r on r.row_number = s.row_number
)

select
    person_id,
    min(submitted_at)                                                       as first_signed_up_at,
    max(submitted_at)                                                       as last_signed_up_at,
    count(*)                                                                as n_signups,
    (array_agg(dob_month order by submitted_at) filter (where dob_month is not null))[1]
                                                                            as dob_month,
    count(distinct dob_month) > 1                                           as has_dob_conflict,
    (array_agg(postcode_district order by submitted_at desc)
        filter (where postcode_district is not null))[1]                    as postcode_district,
    (array_agg(programme order by submitted_at desc))[1]                    as programme,
    (array_agg(photo_consent order by submitted_at desc))[1]                as photo_consent
from signups
group by person_id
