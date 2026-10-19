-- Fails if any column in this organisation's raw schema looks like a direct identifier.
-- Pseudonymisation happens before loading; this test makes sure it stays that way.
select table_name, column_name
from information_schema.columns
where table_schema = 'org_{{ var("org") }}_raw'
  and column_name ~* '(first_name|last_name|full_name|attendee|email$|phone$|postcode$|date_of_birth)'
