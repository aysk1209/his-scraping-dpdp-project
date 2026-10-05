<!-- Written by scripts/check_ui_update.py: layout v1 against v2 of the fixture portal. -->

### HIS update check — screens of 2026-10-05 against 2026-10-05

**Modules**

- Patient Registration is now Front Office (/m/registration/ -> /app/front-office/).
- Clinical Records is now Patient Chart (/m/clinical/ -> /app/chart/).
- Departmental Orders is now Diagnostics (/m/departments/ -> /app/diagnostics/).
- Billing & Accounts is now split: Accounts (/app/accounts/) and Insurance & Payers (/app/payers/).
- Audit Log is now System Activity (/m/integration/ -> /app/activity/).

**Fields**

- The "MRN" column is now headed "UHID".
- The "full name" column is now headed "Patient Name".
- The "date of birth" column is now headed "DOB".
- Ward is no longer found on any Patient Administration page.
- Primary diagnosis is now on the record page of Patient Chart (was the list page).
- The "attending clinician" column is now headed "Consultant".
- Invoice id moved: Billing & Accounts, list page -> Accounts, list page.
- The "amount" column is now headed "Amount (INR)".
- Amount (INR) moved: Billing & Accounts, list page -> Accounts, list page.
- The "policy number" column is now headed "Policy No.".
- Policy No. moved: Billing & Accounts, record page -> Insurance & Payers, record page.
- Payer moved: Billing & Accounts, list page -> Insurance & Payers, list page.

**Buttons**

- "New patient" is now "Add registration" (Front Office, list page).
- "Edit details" is now "Update demographics" (Front Office, record page).
- "Mark arrived" is now "Check-in" (Front Office, record page).
- "Book appointment" is now "New appointment" (Front Office, record page).
- "Reschedule" is now "Change appointment" (Front Office, record page).
- "Cancel appointment" is now "Cancel booking" (Front Office, record page).
- "Allocate bed" is now "Assign bed" (Front Office, record page).
- "Transfer" is now "Transfer ward" (Front Office, record page).
- "Discharge" (Patient Registration, record page) is gone: no button for it was recognised.
- "Ward census" is now "Occupancy report" (Front Office, list page).
- "Record consent withdrawal" is now "Withdraw consent" (Front Office, record page).
- "Log privacy request" is now "Data protection request" (Front Office, list page).
- "Record dose given" is now "Administer" (Patient Chart, record page).
- "Add allergy" is now "New allergy" (Patient Chart, record page).
- "Ready for discharge" is now "Mark fit for discharge" (Patient Chart, record page).
- "New lab request" is now "Order test" (Diagnostics, list page).
- "Record observation" is now "Add vitals" (Diagnostics, record page).
- "Open account" is now "New account", on Accounts, list page.
- "Check eligibility" is now "Verify coverage", on Insurance & Payers, list page.
- "Post charge" is now "Add charge", on Accounts, record page.
- "Generate invoice" is now "Create bill", on Accounts, record page.
- "Record settlement" is now "Mark settled", on Accounts, record page.

**Not understood -- needs a person to confirm**

- A column headed "Unit" on Front Office (record page) is not in the field aliases -- most likely ward, which disappeared in the same update. Confirm "Unit" = admission_ward to restore it.
- A button "Close episode" on Front Office (record page) is not one I recognise -- most likely "Discharge", which disappeared in the same update. Confirm "Close episode" = discharge to restore it.

| Role | Tasks | Unchanged | Re-worded | Withheld |
|---|---|---|---|---|
| reception | 11 | 0 | 11 | 0 |
| nurse | 10 | 0 | 10 | 0 |
| administrator | 16 | 0 | 12 | 4 |

**Withheld until confirmed**

- allocate a bed: ward could not be found on any Patient Administration page
- transfer a patient to another ward: ward could not be found on any Patient Administration page
- discharge a patient and release the bed: no button for "Discharge" was found on any Patient Administration page; and ward could not be found on any Patient Administration page
- run a ward census: ward could not be found on any Patient Administration page; the step before it could not be placed

**After the two proposals were confirmed**


| Role | Tasks | Unchanged | Re-worded | Withheld |
|---|---|---|---|---|
| reception | 11 | 0 | 11 | 0 |
| nurse | 10 | 0 | 10 | 0 |
| administrator | 16 | 0 | 16 | 0 |
