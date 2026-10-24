-- Attendance rows linked to a session and to a resolved person.
--
-- The attendance sheet only has a typed name, so we match in two steps:
--   1. 'exact'     the normalised name belongs to exactly one person
--   2. 'phonetic'  the Soundex name belongs to exactly one person *in that programme*
-- Anything else stays unmatched (a visitor, or a child who never signed up) and goes to
-- the inbox. Ambiguous matches are left unmatched on purpose: a wrong link is worse than
-- none, because it silently counts one child's attendance as another's.

with people as (
    select distinct
        s.person_token,
        s.name_phonetic,
        lower(s.programme) as programme,
        r.person_id
    from {{ ref('stg_signups') }} as s
    inner join {{ ref('int_signups_resolved') }} as r on r.row_number = s.row_number
),

by_name as (
    select person_token, min(person_id) as person_id
    from people
    group by person_token
    having count(distinct person_id) = 1
),

by_sound as (
    select name_phonetic, programme, min(person_id) as person_id
    from people
    group by name_phonetic, programme
    having count(distinct person_id) = 1
)

select
    a.row_number,
    a.session_date,
    a.programme,
    s.session_id,
    coalesce(n.person_id, p.person_id)                  as person_id,
    case
        when n.person_id is not null then 'exact'
        when p.person_id is not null then 'phonetic'
        else 'unmatched'
    end                                                 as match_method
from {{ ref('stg_attendance') }} as a
left join {{ ref('stg_sessions') }} as s
    on s.session_date = a.session_date and s.programme = a.programme
left join by_name as n
    on n.person_token = a.person_token
left join by_sound as p
    on p.name_phonetic = a.name_phonetic and p.programme = lower(a.programme)
