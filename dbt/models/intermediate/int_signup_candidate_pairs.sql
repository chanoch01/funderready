-- Every pair of sign-ups that could be the same child, with the evidence for and against.
--
-- Comparing all pairs is n^2, so pairs are "blocked": we only compare sign-ups that share
--   a phonetic name, OR a carer email or phone, OR both month of birth and postcode district.
-- A pair outside every block is assumed distinct, so blocking sets the ceiling on recall.
-- The third rule catches a typo that changes the Soundex code ("Lily" L400, "Lly" L000)
-- on a form filled in by the other parent.
-- Each feature is 'agree', 'disagree' or 'unknown' (a value is missing on one side).

with signups as (
    select * from {{ ref('stg_signups') }}
),

pairs as (
    select distinct a.row_number as row_a, b.row_number as row_b
    from signups as a
    inner join signups as b
        on a.row_number < b.row_number
        and (
            a.name_phonetic = b.name_phonetic
            or a.carer_email_token = b.carer_email_token
            or a.carer_phone_token = b.carer_phone_token
            or (a.dob_month = b.dob_month and a.postcode_district = b.postcode_district)
        )
)

select
    p.row_a,
    p.row_b,
    a.person_token as person_token_a,
    b.person_token as person_token_b,
    case when a.person_token = b.person_token then 'agree' else 'disagree' end
        as name_exact,
    case when a.name_phonetic = b.name_phonetic then 'agree' else 'disagree' end
        as name_phonetic,
    case
        when a.carer_email_token = b.carer_email_token
            or a.carer_phone_token = b.carer_phone_token then 'agree'
        when coalesce(a.carer_email_token, a.carer_phone_token) is null
            or coalesce(b.carer_email_token, b.carer_phone_token) is null then 'unknown'
        else 'disagree'
    end as carer_contact,
    case
        when a.dob_month is null or b.dob_month is null then 'unknown'
        when a.dob_month = b.dob_month then 'agree'
        else 'disagree'
    end as dob_month,
    case
        when a.postcode_district is null or b.postcode_district is null then 'unknown'
        when a.postcode_district = b.postcode_district then 'agree'
        else 'disagree'
    end as postcode_district,
    case when lower(a.programme) = lower(b.programme) then 'agree' else 'disagree' end
        as programme
from pairs as p
inner join signups as a on a.row_number = p.row_a
inner join signups as b on b.row_number = p.row_b
