# User Seeding Runbook for Admin Staff

This checklist explains how to prepare the bulk user spreadsheet and load the
accounts into the Quote Tool container. Follow the steps in order, then return
the completed CSV to the engineering or operations contact who will seed it if
you do not have console access yourself.

---

## Quick reference

1. **Copy the template** found at `users_seed_template.csv`.
2. **Fill in a row per person** using the column notes below.
3. **Double-check the data** (unique emails, strong passwords, correct roles).
4. **Save the CSV** and hand it off for review or upload it to the shared
   location agreed with engineering.
5. **Run the seeding script** (or request it) to import the users into the
   running container.

---

## Step 1 – Make your working copy of the template

1. Locate `users_seed_template.csv` in the repository root or the shared drive.
2. Create a copy named with the date you collected the data, for example
   `users_2024-05-15.csv`.
3. Open the copy in Excel, Numbers, Google Sheets, or another CSV-friendly
   editor. Avoid reordering or renaming the headers.

## Step 2 – Collect information for each person

Each row represents one account. Fill in as many columns as possible; blank
cells are allowed for the optional fields. The table below describes every
column and how administrators should use it.

| Column | Required? | What to enter |
| --- | --- | --- |
| `email` | ✅ | Work email address in lowercase. This must be unique for every account. |
| `name` | ⚪️ | Full display name. Leave blank if you are providing both `first_name` and `last_name`; the system will join them. |
| `first_name` / `last_name` | ⚪️ | Personal name split into two fields. Helpful when the user prefers a nickname in the interface. |
| `phone` | ⚪️ | Direct-dial phone number. Use digits and separators (e.g., `555-555-0100`). |
| `company_name` | ⚪️ | Company or division the user belongs to. |
| `company_phone` | ⚪️ | Main company phone number. Same formatting rules as `phone`. |
| `password` | ✅ | A strong temporary password to deliver to the user on first login. Use at least 12 characters with upper/lower case, numbers, and a symbol. If engineering supplied a pre-hashed password, paste it here instead. |
| `role` | ✅ (defaults to `customer`) | Choose one: `customer`, `employee`, or `super_admin`. Super admins have full dashboard access. |
| `is_admin` | ⚪️ | Use `TRUE` for super admins. Leaving it blank or `FALSE` keeps the account at the role level specified above. |
| `employee_approved` | ⚪️ | Set to `TRUE` only when the user is an FSI employee who should immediately access internal tools. |
| `is_active` | ⚪️ | Leave `TRUE` (the default) unless the account should start disabled. |

> **Password tip:** If you would rather not share plain-text passwords through
> email, request a password hash from engineering. They can generate one with
> `werkzeug.security.generate_password_hash(...)` and you paste the resulting
> string into the `password` column.

## Step 3 – Add additional people

- Insert a new row beneath the existing data for each additional person.
- Copy the formatting from the example row if your spreadsheet software does
  not automatically apply CSV formatting.
- Keep the header row untouched—this ensures the import script recognizes every
  column.

## Step 4 – Quality check before handoff

Use this short checklist before you save the file:

- [ ] Every `email` cell is filled in, unique, and spelled correctly.
- [ ] Passwords meet the strength rules or contain a pre-generated hash.
- [ ] `role`, `is_admin`, and `employee_approved` make sense together (for
      example, super admins should have `is_admin=TRUE`).
- [ ] Optional phone fields contain dialable numbers or are left blank.
- [ ] The file is still in CSV format (no formulas or additional sheets).

When everything looks good, save the CSV and send it to the person responsible
for running the import. Store the file in the approved secure location if you
are not emailing it.

## Step 5 – (Optional) Validate the file yourself

If you have command-line access, you can preview the import without writing to
the database. Place the CSV alongside the project files and run:

```bash
python scripts/seed_users.py --file users_2024-05-15.csv --dry-run
```

The script prints a summary of how many rows would be created or updated and
lists any validation errors it discovers.

## Step 6 – Seed the users inside the container

The Quote Tool container stores its application files in `/app`. Replace
`users_2024-05-15.csv` and `quote_tool` with the actual file name and container
name used in your environment.

1. Copy the CSV into the running container (skip this step if the file already
   lives in the container volume):

   ```bash
   docker cp users_2024-05-15.csv quote_tool:/app/users_2024-05-15.csv
   ```

2. Run a dry run inside the container to catch mistakes:

   ```bash
   docker exec quote_tool python scripts/seed_users.py \
     --file /app/users_2024-05-15.csv --dry-run
   ```

3. When the dry run succeeds, import the users for real. Include
   `--update-existing` if you want to refresh existing accounts rather than
   skipping them.

   ```bash
   docker exec quote_tool python scripts/seed_users.py \
     --file /app/users_2024-05-15.csv --update-existing
   ```

4. Confirm the script reports the expected number of created/updated rows. If
   you added sensitive temporary passwords, delete the CSV from the container
   after import:

   ```bash
   docker exec quote_tool rm /app/users_2024-05-15.csv
   ```

5. Let the requestor know the seeding is complete and share any warnings the
   script printed so they can correct the spreadsheet for the next run.

---

## Need help?

If you encounter validation errors you cannot resolve, send the CSV and the
exact error message to the engineering support channel. They can advise on
formatting issues or generate password hashes for you.
