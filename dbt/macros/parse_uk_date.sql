{#-
  Parse the date formats volunteers type: 2026-03-09, 09/03/2026 and 9 Mar 2026.
  Anything else (including blanks) becomes null, and the data-quality inbox reports it.
  The `like` / `~` checks run first so to_date never sees text it cannot parse.
-#}
{% macro parse_uk_date(column) -%}
    case
        when trim({{ column }}) ~ '^\d{4}-\d{2}-\d{2}( |$)'
            then to_date(left(trim({{ column }}), 10), 'YYYY-MM-DD')
        when trim({{ column }}) ~ '^\d{1,2}/\d{1,2}/\d{4}( |$)'
            then to_date(split_part(trim({{ column }}), ' ', 1), 'DD/MM/YYYY')
        when trim({{ column }}) ~* '^\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{4}$'
            -- "9 March 2026" -> "9 Mar 2026": to_date's Mon pattern wants three letters
            then to_date(
                regexp_replace(trim({{ column }}), '^(\d{1,2}) ([A-Za-z]{3})[A-Za-z]* (\d{4})$', '\1 \2 \3'),
                'DD Mon YYYY'
            )
    end
{%- endmacro %}
