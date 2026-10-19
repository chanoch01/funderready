-- Attendance rows linked to a session and to a sign-up.
-- People are matched on the exact name token first, then on the phonetic token
-- ("Jon" vs "John"). Week 2 replaces this with scored duplicate resolution.

with people as (
    select distinct on (person_token)
        person_token, name_phonetic, dob_month, postcode_district
    from {{ ref('stg_signups') }}
    order by person_token, submitted_at
),

phonetic as (
    -- only use a phonetic match when it points at exactly one sign-up
    select name_phonetic, min(person_token) as person_token
    from people
    group by name_phonetic
    having count(*) = 1
)

select
    a.row_number,
    a.session_date,
    a.programme,
    s.session_id,
    coalesce(exact.person_token, phon.person_token)     as matched_person_token,
    case
        when exact.person_token is not null then 'exact'
        when phon.person_token is not null then 'phonetic'
        else 'unmatched'
    end                                                 as match_method
from {{ ref('stg_attendance') }} as a
left join {{ ref('stg_sessions') }} as s
    on s.session_date = a.session_date and s.programme = a.programme
left join people as exact
    on exact.person_token = a.person_token
left join phonetic as phon
    on phon.name_phonetic = a.name_phonetic
