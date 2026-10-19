select
    _row_number                                         as row_number,
    to_timestamp(submitted_at, 'DD/MM/YYYY HH24:MI:SS') as submitted_at,
    person_token,
    name_phonetic,
    case when dob_month ~ '^\d{4}-\d{2}$'
        then to_date(dob_month || '-01', 'YYYY-MM-DD') end as dob_month,
    dob_provided,
    postcode_district,
    trim(programme)                                     as programme,
    carer_email_token,
    carer_phone_token,
    lower(left(trim(photo_consent), 1)) = 'y'           as photo_consent
from {{ source('raw', 'signups') }}
