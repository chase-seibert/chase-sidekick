# Epic Status Change Recommendations

Generated: 2026-06-24

Heuristic used: recommend `Done` when all direct children are Done/Cancelled, recommend `In Progress` when any direct child is in an active status, and recommend `Delayed` when no direct child work has started. I only used `Delayed`, not `Canceled`, where there was no explicit child-status evidence of cancellation.

## Simplify Sharing

### Recommended: Delayed

| Epic | Summary | Current status | Why |
| --- | --- | --- | --- |
| [SHARE-8428](https://dropbox.atlassian.net/browse/SHARE-8428) | Inband Email Consolidation | Triage | No direct child issues were returned by `parent = SHARE-8428`, so there is no child-status evidence that work has started. |
| [SHARE-8439](https://dropbox.atlassian.net/browse/SHARE-8439) | Inband Performance Improvements for Folders | Triage | No direct child issues were returned by `parent = SHARE-8439`, so there is no child-status evidence that work has started. |
| [SHARE-8449](https://dropbox.atlassian.net/browse/SHARE-8449) | Mobile web on mobile app spike | Triage | No direct child issues were returned by `parent = SHARE-8449`, so there is no child-status evidence that work has started. |
| [SHARE-8706](https://dropbox.atlassian.net/browse/SHARE-8706) | [Web] SM26 Create Folder Flow | Product Review | No direct child issues were returned by `parent = SHARE-8706`; child-status evidence does not support Product Review. |
| [SHARE-9138](https://dropbox.atlassian.net/browse/SHARE-9138) | [iOS] SM26 Modernize In Band Flows Rollout | To Do | No direct child issues were returned by `parent = SHARE-9138`, so there is no child-status evidence that work has started. |
| [SHARE-9149](https://dropbox.atlassian.net/browse/SHARE-9149) | [Android] SM26 MVP GA Rollout | Product Review | No direct child issues were returned by `parent = SHARE-9149`; child-status evidence does not support Product Review. |

## Team Expansion

### Recommended: Done

| Epic | Summary | Current status | Why |
| --- | --- | --- | --- |
| [TEXP-3403](https://dropbox.atlassian.net/browse/TEXP-3403) | Everyone Group Exclusion | Product Review | `parent = TEXP-3403 AND statusCategory != Done` returned no issues; moved children found were Done or Cancelled. |

### Recommended: Delayed

| Epic | Summary | Current status | Why |
| --- | --- | --- | --- |
| [TEXP-4075](https://dropbox.atlassian.net/browse/TEXP-4075) | Unification FSS MPE [IMM M5] | Triage | No direct child issues were returned by `parent = TEXP-4075`, so there is no child-status evidence that work has started. |
| [TEXP-4076](https://dropbox.atlassian.net/browse/TEXP-4076) | Unification FSS MPE [R2J] | Triage | No direct child issues were returned by `parent = TEXP-4076`, so there is no child-status evidence that work has started. |
| [TEXP-4281](https://dropbox.atlassian.net/browse/TEXP-4281) | [Foundation] MLM v1 deprecation [M2 Q3] | Triage | No direct child issues were returned by `parent = TEXP-4281`, so there is no child-status evidence that work has started. |
| [TEXP-4301](https://dropbox.atlassian.net/browse/TEXP-4301) | Unification FSS MPE Q3 | Triage | No direct child issues were returned by `parent = TEXP-4301`, so there is no child-status evidence that work has started. |
| [TEXP-4398](https://dropbox.atlassian.net/browse/TEXP-4398) | [Foundation] Growthbook/Stormcrow/Kiev Clean up for Q3 | Triage | Direct children were present, but the returned children were still To Do/Triage; no child had moved out of To Do. |
| [TEXP-4409](https://dropbox.atlassian.net/browse/TEXP-4409) | [Q3/M1][Foundation]Improve Code Test Coverage | Triage | Direct children `TEXP-4167` and `TEXP-4502` are both Triage; no child had moved out of To Do. |
| [TEXP-4542](https://dropbox.atlassian.net/browse/TEXP-4542) | [KTLO] Team Expansion KTLO [2026-Q3-Block-6] | Triage | No direct child issues were returned by `parent = TEXP-4542`, so there is no child-status evidence that work has started. |

## Team Formation

### Recommended: In Progress

| Epic | Summary | Current status | Why |
| --- | --- | --- | --- |
| [TFM-1327](https://dropbox.atlassian.net/browse/TFM-1327) | Team Formation Cleanup Dead Routes 2026 Q2 | At Risk | Direct children include one active child (`TFM-1745` In Progress) and several Open children (`TFM-1743`, `TFM-1744`, `TFM-1746`); child statuses support In Progress rather than At Risk. |

### Recommended: Delayed

| Epic | Summary | Current status | Why |
| --- | --- | --- | --- |
| [TFM-1328](https://dropbox.atlassian.net/browse/TFM-1328) | TFM Q3: Improve Production Debugging by Completing Self Identified Projects to Address Team Pain Points | Open | No direct child issues were returned by `parent = TFM-1328`, so there is no child-status evidence that work has started. |
| [TFM-1544](https://dropbox.atlassian.net/browse/TFM-1544) | Limit Password Sharing: Enforcement M3.5 | On Hold | No direct child issues were returned by `parent = TFM-1544`; with no started child work, Delayed is the clearer status. |
