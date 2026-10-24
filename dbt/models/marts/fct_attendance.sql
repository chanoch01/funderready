-- One row per child per session attended.
--
-- Grain matters for funders: "participants" (unique children) and "attendances"
-- (child-sessions) are different numbers, and both come from this table.
--   * rows that match no session are excluded (they are in the inbox)
--   * a child listed twice for the same session counts once
--   * visitors (no sign-up) are kept with person_id null: they are attendances,
--     but they can never be counted as unique participants

with matched as (
    select
        *,
        row_number() over (
            partition by session_id, coalesce(person_id, 'row-' || row_number)
            order by row_number
        ) as nth_entry
    from {{ ref('int_attendance_matched') }}
    where session_id is not null
)

select
    md5('attendance|' || row_number)    as attendance_id,
    session_id,
    session_date,
    programme,
    person_id,
    person_id is null                   as is_visitor,
    match_method,
    row_number                          as source_row_number
from matched
where nth_entry = 1
