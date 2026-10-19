{#- Every organisation gets its own schemas: org_<org>_staging, org_<org>_marts, ... -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    org_{{ var('org') }}_{{ custom_schema_name or 'analytics' }}
{%- endmacro %}
