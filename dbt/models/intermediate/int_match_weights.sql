-- Fellegi-Sunter match weights, the model behind tools like Splink.
--
--   m = P(feature agrees | same child)       domain assumption, in seeds/match_parameters.csv
--   u = P(feature agrees | different child)  measured here: how often two random sign-ups agree
--
--   agreeing adds    log2(m / u)              (rare coincidence -> strong evidence)
--   disagreeing adds log2((1 - m) / (1 - u))  (usually negative)
--   unknown adds     0
--
-- u is measured over every pair of sign-ups, which includes the few true duplicates; with
-- ~200 sign-ups that inflates u by well under 1%.

with signups as (
    select * from {{ ref('stg_signups') }}
),

all_pairs as (
    select
        a.person_token = b.person_token                               as name_exact,
        a.name_phonetic = b.name_phonetic                             as name_phonetic,
        a.carer_email_token = b.carer_email_token
            or a.carer_phone_token = b.carer_phone_token              as carer_contact,
        a.dob_month = b.dob_month                                     as dob_month,
        a.postcode_district = b.postcode_district                     as postcode_district,
        lower(a.programme) = lower(b.programme)                       as programme
    from signups as a
    inner join signups as b on a.row_number < b.row_number
),

u as (
    -- a floor of 1 in 10,000 stops a feature that never agrees by chance getting log2(m/0)
    select feature, greatest(avg(agrees::int), 0.0001) as u_probability
    from all_pairs
    cross join lateral (
        values
            ('name_exact', name_exact),
            ('name_phonetic', name_phonetic),
            ('carer_contact', carer_contact),
            ('dob_month', dob_month),
            ('postcode_district', postcode_district),
            ('programme', programme)
    ) as f (feature, agrees)
    where agrees is not null
    group by feature
)

select
    p.feature,
    p.m_probability,
    round(u.u_probability, 6)                                             as u_probability,
    round(log(2, (p.m_probability / u.u_probability)::numeric), 3)        as agree_weight,
    round(log(2, ((1 - p.m_probability) / (1 - u.u_probability))::numeric), 3)
        as disagree_weight
from {{ ref('match_parameters') }} as p
inner join u on u.feature = p.feature
