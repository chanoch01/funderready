-- A child appears at most once per session, however many times the sheet lists them.
select session_id, person_id, count(*) as n
from {{ ref('fct_attendance') }}
where person_id is not null
group by session_id, person_id
having count(*) > 1
