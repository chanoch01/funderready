select
    _row_number                         as row_number,
    date                                as date_as_typed,
    {{ parse_uk_date('date') }}         as session_date,
    initcap(trim(programme))            as programme,
    person_token,
    name_phonetic
from {{ source('raw', 'attendance') }}
