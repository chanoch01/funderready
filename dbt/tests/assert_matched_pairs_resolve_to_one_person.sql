-- Every pair scored 'match' must end up as the same person after clustering.
-- Returns the pairs that did not (a clustering bug).
select m.row_a, m.row_b
from {{ ref('int_signup_match_scores') }} as m
inner join {{ ref('int_signups_resolved') }} as a on a.row_number = m.row_a
inner join {{ ref('int_signups_resolved') }} as b on b.row_number = m.row_b
where m.decision = 'match' and a.person_id <> b.person_id
