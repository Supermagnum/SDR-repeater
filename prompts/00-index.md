# Agent prompts for the HT13G-M RFIC work

Each prompt does one job and stands on its own. Paste one into the AI client, or put this folder in the repo as `prompts/` and say "run prompts/0N-….md". Every prompt carries the full set of project rules: no fabrication, the owner decides topologies, the PCB files are read only, nothing is pushed outside this repo, and so on.

| # | Prompt | Job | Writes | Changes design files? |
|---|---|---|---|---|
| 01 | `01-audit-and-verify.md` | What is done; re-run and check the recorded results | `reports/status-*.md` | No |
| 02 | `02-pdk-tool-issues.md` | Known IHP PDK and tool bugs: fixed, worked around or open | `reports/pdk-tool-issues-*.md`, draft upstream issues | No |
| 03 | `03-readme-pdk-links.md` | IHP SG13G2 links section in the main README | `README.md` (that section only) | No |
| 04 | `04-pcb-pinout-check.md` | PCB against the RFIC, backplane and K3 Pico-ITX pinouts | `reports/pcb-pinout-check-*.md` | No (read only) |
| 05 | `05-parts-list.md` | Parts list for the RF module | `PCB/BOM.md`, `PCB/BOM.csv` | No |
| 06 | `06-design-next-step.md` | The next single design item, then stop for review | design files, specs | Yes, one item |

## Suggested order

1. **02, then 01.** A known PDK or tool bug can make a recorded result wrong, and 01 re-runs whatever 02 flags.
2. **03** at any time; it is small.
3. **04, then 05.** The parts list uses the pinout findings.
4. **06**, run again for each step. Each run does one item: right now that is the P2.6 review gate, then (after you accept P2.6) the start-up bypass, the V_tune monitor and the UHF LO floor, one per run. Before each run, check that the newest status report from 01 has no failed or unverified result that the item depends on.

Prompts 01–05 only write reports and documentation. Prompt 06 is the only one that changes the design.
