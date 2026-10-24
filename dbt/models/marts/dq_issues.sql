-- The data-quality inbox: every problem as a plain-English task a volunteer can fix,
-- pointing at the sheet and row to open.

with issues as (

    select 'Sign-ups' as sheet, row_number, 'missing_dob' as issue_type,
           'Date of birth missing' as message
    from {{ ref('stg_signups') }}
    where not dob_provided

    union all
    select 'Sign-ups', row_number, 'unreadable_dob',
           'Date of birth could not be read; use DD/MM/YYYY'
    from {{ ref('stg_signups') }}
    where dob_provided and dob_month is null

    union all
    select 'Sign-ups', row_number, 'possible_duplicate',
           'Repeat sign-up of row ' || first_row_number || ', merged automatically'
    from {{ ref('int_signups_resolved') }}
    where not is_first_signup

    union all
    select 'Sign-ups', row_b, 'check_duplicate',
           'Same child as row ' || row_a || '? Some details match (' ||
           case
               when evidence like '%name_phonetic=disagree%' then 'different name, '
               else 'similar name, '
           end ||
           case
               when evidence like '%carer_contact=agree%' then 'same carer contact'
               else 'different carer contact'
           end ||
           case when evidence like '%dob_month=agree%' then ', same birth month' else '' end ||
           '). Twins, or a repeat sign-up? Record the answer in match_decisions.csv'
    from {{ ref('int_signup_match_scores') }}
    where decision = 'review'

    union all
    select 'Sign-ups', s.row_number, 'dob_conflict',
           'This child''s sign-ups give different dates of birth'
    from {{ ref('dim_people') }} as p
    inner join {{ ref('int_signups_resolved') }} as s
        on s.person_id = p.person_id and s.is_first_signup
    where p.has_dob_conflict

    union all
    select 'Sessions', row_number, 'session_no_date',
           case when coalesce(trim(date_as_typed), '') = '' then 'Date missing'
                else 'Date "' || date_as_typed || '" could not be read' end
    from {{ ref('stg_sessions') }}
    where session_date is null

    union all
    select 'Attendance', row_number, 'no_matching_session',
           'No ' || programme || ' session on ' || coalesce(session_date::text, 'that date')
    from {{ ref('int_attendance_matched') }}
    where session_id is null

    union all
    select 'Attendance', row_number,
           case match_method when 'phonetic' then 'attendee_spelling' else 'attendee_unknown' end,
           case match_method
               when 'phonetic' then 'Name spelt differently from the sign-up form'
               else 'Attendee not found in sign-ups'
           end
    from {{ ref('int_attendance_matched') }}
    where match_method <> 'exact'

    union all
    select 'Donations', row_number, 'amount_unreadable',
           'Amount "' || amount_as_typed || '" is not a number'
    from {{ ref('stg_donations') }}
    where amount_gbp is null
)

select
    md5(sheet || '|' || row_number || '|' || issue_type || '|' || message) as issue_id,
    sheet,
    row_number,
    issue_type,
    sheet || ' sheet, row ' || row_number || ': ' || message as task
from issues
