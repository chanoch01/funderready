-- Which child is behind each sign-up row.
--
-- Matched pairs are edges in a graph; each connected component is one child. A recursive
-- query walks the edges (so if row 5 matches row 9 and row 9 matches row 30, all three are
-- one child), and `union` rather than `union all` stops it looping forever on cycles.
--
-- person_id comes from the child's earliest sign-up, so it does not change when someone
-- re-sorts the spreadsheet and row numbers move.

with recursive edges as (
    select row_a as from_row, row_b as to_row
    from {{ ref('int_signup_match_scores') }}
    where decision = 'match'
    union all
    select row_b, row_a
    from {{ ref('int_signup_match_scores') }}
    where decision = 'match'
),

reach (start_row, row_number) as (
    select row_number, row_number from {{ ref('stg_signups') }}
    union
    select r.start_row, e.to_row
    from reach as r
    inner join edges as e on e.from_row = r.row_number
),

components as (
    select start_row as row_number, min(row_number) as component
    from reach
    group by start_row
),

firsts as (
    -- the earliest submission in each component names the person
    select distinct on (c.component)
        c.component,
        md5('person|' || s.person_token || '|' || s.submitted_at::text) as person_id,
        s.row_number as first_row_number
    from components as c
    inner join {{ ref('stg_signups') }} as s on s.row_number = c.row_number
    order by c.component, s.submitted_at, s.row_number
)

select
    c.row_number,
    f.person_id,
    f.first_row_number,
    c.row_number = f.first_row_number as is_first_signup
from components as c
inner join firsts as f on f.component = c.component
