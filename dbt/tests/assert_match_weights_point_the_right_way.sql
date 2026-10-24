-- Agreeing on a feature must be evidence FOR a match and disagreeing evidence AGAINST.
-- If m <= u for a feature, the parameters in seeds/match_parameters.csv are wrong.
select feature, agree_weight, disagree_weight
from {{ ref('int_match_weights') }}
where agree_weight <= 0 or disagree_weight >= 0
