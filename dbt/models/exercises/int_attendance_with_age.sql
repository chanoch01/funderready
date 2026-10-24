-- EXERCISE 1 (yours to write): how old was each child at each session?
-- Brief: exercises/WEEK2.md. Check your answer with:  make exercises
--
-- Output: one row per row of fct_attendance, with
--   attendance_id, session_id, session_date, programme, person_id   (passed through)
--   age_at_session   whole years between the child's birth month and the session date,
--                    treating the birthday as the 1st of the birth month; null if unknown
--   age_band         'under_12', '12_to_15', '16_plus' or 'unknown'
--
-- Inputs: ref('fct_attendance') and ref('dim_people') (which has dob_month).
-- Visitors have a null person_id, so they must come out as 'unknown'.

select
    a.attendance_id,
    a.session_id,
    a.session_date,
    a.programme,
    a.person_id,
    null::int       as age_at_session,  -- TODO
    'TODO'          as age_band         -- TODO
from {{ ref('fct_attendance') }} as a
