with parsed as (
    select
        _row_number                              as row_number,
        date                                     as date_as_typed,
        {{ parse_uk_date('date') }}              as session_date,
        initcap(trim(programme))                 as programme,
        trim(venue)                              as venue,
        upper(trim(coach))                       as coach
    from {{ source('raw', 'sessions') }}
)

select
    md5(coalesce(session_date::text, 'row-' || row_number) || '|' || programme) as session_id,
    *
from parsed
