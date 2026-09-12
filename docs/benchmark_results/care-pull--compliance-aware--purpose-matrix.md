### Purpose matrix — `care-pull--compliance-aware`

_The same records, the same manifest, the same seven rules: 1.000 under 'care_coordination', 0.857 under 'billing_settlement'. Nothing about the extraction changed -- only what it was for. Compliance is a property of the pull and its purpose together, not of the pull alone._

One extraction (50 records; categories `administrative`, `clinical`, `direct_identifier`, `quasi_identifier`; 30d retention declared), scored against every purpose in the policy with the same rule set.

For any purpose other than the declared one, the privacy notice is treated as not covering it — the notice given to the Data Principal named the declared purpose. That is a consequence of changing the purpose, not an adjustment made to produce a result.

| Purpose | Declared | Compliance | Rules passed | Verdict |
|---|---|---|---|---|
| `care_coordination` | yes | 1.000 | 7/7 | lawful for this purpose |
| `billing_settlement` | no | 0.857 | 5/7 | out of scope: clinical, quasi_identifier |
| `patient_registration` | no | 0.893 | 5/7 | out of scope: clinical |