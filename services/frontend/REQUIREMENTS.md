# WatchIt requirements after integration #34

Source review against the owner's list (items 2–22). This records code coverage, not a claim that the stopped local deployment is updated. Follow-up #35 restores the missing date controls and removes the unapproved Entra layout.

| Item | Behavior | Source / verification |
|---|---|---|
| 2 | No tagline below the brand | `AppShell.tsx` |
| 3 | Watchit brand | `AppShell.tsx` |
| 4 | Queue filters fold below level tabs | `QueueFilters.tsx`; queue tests |
| 5 | Column chart; 24h, 7d, 30d and custom dates | `QueuePage.tsx`, `TrendStrip.tsx`; custom range integration test |
| 6 | Public reports disabled and removed from UI | `test_watchit.py` public-report 404 checks |
| 7 | Fixed 21 Nov 2026 20:50 Warsaw launch; no future selection | `config.py`, `date_bounds.py`, `dates.ts`; exact launch and boundary tests |
| 8 | Criterion definitions on hover/focus | Criterion components and case tests |
| 9 | Polish user-facing terminology | UI source review; Analiza URL, Uzasadnienie, Tok rozumowania |
| 10 | AI recommendation and plain justification | `DebateBlock.tsx` |
| 11 | Reasoning disclosure closed initially | `DebateBlock.tsx`; native details |
| 12 | Source label Adres URL | `SourcesBlock.tsx`, `EvidenceDrawer.tsx` |
| 13 | UKNF remit gating | `test_watchit.py` out-of-remit list/statistics check; v4 scope preserved |
| 14 | Audit filters collapse | `AuditPage.tsx`; auth integration test |
| 15 | Ascending/descending queue and audit sorting | QueueTable and AuditPage; queue domain tests |
| 16 | Entra-inspired redesign requires separate approval | Deferred; #35 uses ordinary fields and full-width register details |
| 17 | Case ID, review start and elapsed processing time | `QueueTable.tsx`; workflow clock tests |
| 18 | Analiza URL; all three modules automatically | `ScanDialog.tsx`; scan integration tests |
| 19 | Alternating white/grey rows | queue and audit table styles |
| 20 | Calibration notifications per user | `test_watchit.py` private persistent notification checks |
| 21 | Optional AI verdict behind a button | `VerdictBlock.tsx`; case tests |
| 22 | No calibration link on queue card | `QueuePage.tsx` source review |

The footer release marker is `2026.11.22.2`. This follow-up is pushed for review only; no merge or Docker operations are authorized by the latest instruction.
