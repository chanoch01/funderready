# Week 2: your pair-build exercises

The pipeline now resolves duplicate sign-ups into people and produces the tables funders'
numbers will come from. Two models are yours to write. Both already build (they return
placeholder values), and each has a dbt unit test that fails until your SQL is right.

```bash
make demo         # build everything on the demo charity
make exercises    # run only your two unit tests
```

When both pass, commit them yourself. You should be able to explain every line.

---

## Exercise 1: `dbt/models/exercises/int_attendance_with_age.sql`

**Why it matters.** One of the charity's funders counts under-16s only. Age has to be
worked out *at the session*, not today: a child who was 15 in February and 16 in May counts
for February.

**What to produce.** One row per `fct_attendance` row, with `age_at_session` and
`age_band` (`under_12`, `12_to_15`, `16_plus` or `unknown`).

**The rule.** We only keep the birth *month* (privacy, see README decision 3), so treat
the birthday as the 1st of that month. A child born in March 2014 is 12 from 1 March 2026.

**Things to think about before you write anything**
- Which join keeps visitors (null `person_id`) in the output?
- Postgres has `age(later_date, earlier_date)` and `date_part('year', interval)`.
  Try `select age(date '2026-03-31', date '2014-04-01')` in psql first.
- The unit test includes the day before a birthday and the day of it. Why are those the
  cases most likely to catch a bug?

**Be ready to answer:** "A child's age can be off by up to a month. When does that change
a funder's number, and how would you tell the funder?"

---

## Exercise 2: `dbt/models/exercises/participants_by_quarter.sql`

**Why it matters.** "Participants" is the word that caused the problem in the first place.
This model shows three different numbers side by side, so nobody can confuse them again.

**What to produce.** One row per programme per calendar quarter with sessions:
`sessions_run`, `attendances`, `unique_participants`, `under_16_participants`.

**The rules**
- `attendances` counts child-sessions and includes visitors.
- `unique_participants` counts distinct children and never includes visitors.
- `under_16_participants` counts a child if they were under 16 at *any* session in that
  quarter.

**Things to think about**
- `count(distinct person_id)` ignores nulls. Is that what you want here? (It is, but say why.)
- Sessions and attendance are different grains. If you join them before aggregating,
  what happens to `sessions_run`? Try it and watch the unit test fail.
- Should a child with an `unknown` age count as under 16? The test doesn't decide this
  for you. Pick a rule, write it in a SQL comment, and be ready to defend it.

**Be ready to answer:** "Why not just count rows in the attendance sheet?"

---

## Exercise 3: explain the threshold (no code)

Run the holdout check and read the output:

```bash
make holdout
```

Then write a short paragraph (5 to 8 sentences) for the README, in your own words:
1. why the match threshold is 14 (look at the sweep: what happens at 12 and at 18?)
2. why it was checked on charities the threshold was *not* chosen on
3. what the two missed duplicates have in common, and why the system cannot catch them
   without storing names (hint: look at what Soundex does to "Lly" and "Lily")

This is the answer to the interview question "how do you know your matching works?",
so practise saying it out loud too.
