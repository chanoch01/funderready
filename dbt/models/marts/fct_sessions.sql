-- One row per session that happened: a known date and programme.
-- Sessions with no readable date are left out here and listed in the data-quality inbox.
-- If a coach typed the same session twice, the first row is kept.

with dated as (
    select distinct on (session_id) *
    from {{ ref('stg_sessions') }}
    where session_date is not null
    order by session_id, row_number
),

attendance as (
    select session_id, count(*) as attendances, count(distinct person_id) as unique_attendees
    from {{ ref('fct_attendance') }}
    group by session_id
)

select
    d.session_id,
    d.session_date,
    d.programme,
    d.venue,
    d.coach,
    d.row_number                        as source_row_number,
    coalesce(a.attendances, 0)          as attendances,
    coalesce(a.unique_attendees, 0)     as unique_attendees
from dated as d
left join attendance as a on a.session_id = d.session_id
