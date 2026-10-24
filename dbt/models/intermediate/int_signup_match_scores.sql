-- Score each candidate pair: add up the evidence weights, then decide.
--
--   match_weight >= match_threshold    'match'    merged automatically
--   match_weight >= review_threshold   'review'   a person checks it in the inbox
--   otherwise                          'distinct'
--
-- Thresholds are dbt vars, chosen from the precision/recall sweep in scripts/score_matching.py.
--
-- A person's answer to a review task is recorded in seeds/match_decisions.csv against the
-- two name tokens, not row numbers, so it still applies after the sheet is re-sorted or
-- reloaded. A recorded decision always wins over the score.

with pairs as (
    select * from {{ ref('int_signup_candidate_pairs') }}
),

evidence as (
    select p.row_a, p.row_b, f.feature, f.outcome
    from pairs as p
    cross join lateral (
        values
            ('name_exact', p.name_exact),
            ('name_phonetic', p.name_phonetic),
            ('carer_contact', p.carer_contact),
            ('dob_month', p.dob_month),
            ('postcode_district', p.postcode_district),
            ('programme', p.programme)
    ) as f (feature, outcome)
),

scored as (
    select
        e.row_a,
        e.row_b,
        sum(
            case e.outcome
                when 'agree' then w.agree_weight
                when 'disagree' then w.disagree_weight
                else 0
            end
        ) as match_weight,
        string_agg(e.feature || '=' || e.outcome, ', ' order by e.feature) as evidence
    from evidence as e
    inner join {{ ref('int_match_weights') }} as w on w.feature = e.feature
    group by e.row_a, e.row_b
),

decided as (
    select
        least(person_token_a, person_token_b)       as token_low,
        greatest(person_token_a, person_token_b)    as token_high,
        decision
    from {{ ref('match_decisions') }}
)

select
    s.row_a,
    s.row_b,
    round(s.match_weight, 2) as match_weight,
    case
        when d.decision = 'same' then 'match'
        when d.decision = 'different' then 'distinct'
        when s.match_weight >= {{ var('match_threshold') }} then 'match'
        when s.match_weight >= {{ var('review_threshold') }} then 'review'
        else 'distinct'
    end as decision,
    case when d.decision is not null then 'person' else 'score' end as decided_by,
    s.evidence
from scored as s
inner join pairs as p on p.row_a = s.row_a and p.row_b = s.row_b
left join decided as d
    on d.token_low = least(p.person_token_a, p.person_token_b)
    and d.token_high = greatest(p.person_token_a, p.person_token_b)
