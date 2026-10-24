-- Sign-ups are never lost or invented by resolution: the people's sign-up counts
-- add up to the number of sign-up rows.
select p.total, s.total
from (select sum(n_signups) as total from {{ ref('dim_people') }}) as p
cross join (select count(*) as total from {{ ref('stg_signups') }}) as s
where p.total <> s.total
