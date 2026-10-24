-- EXERCISE 2 (yours to write): the first funder numbers.
-- Brief: exercises/WEEK2.md. Check your answer with:  make exercises
--
-- Output: one row per programme per calendar quarter that had at least one session:
--   programme, quarter_start (date, e.g. 2026-04-01)
--   sessions_run            sessions in fct_sessions that quarter
--   attendances             child-sessions, visitors included
--   unique_participants     distinct children, visitors NOT included
--   under_16_participants   distinct children aged under 16 at any session that quarter
--
-- Inputs: ref('fct_sessions') and ref('int_attendance_with_age') (exercise 1).

select
    programme,
    date_trunc('quarter', session_date)::date   as quarter_start,
    count(*)                                    as sessions_run,
    0                                           as attendances,           -- TODO
    0                                           as unique_participants,   -- TODO
    0                                           as under_16_participants  -- TODO
from {{ ref('fct_sessions') }}
group by 1, 2
