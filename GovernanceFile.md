# GovernanceFile.md

Governance file for the project. Imported and adapted from the prior projects to govern future actions in this repository.

## Workflow Orchestration

### 1. Plan Mode Default
* Enter plan mode when a task meets ANY of these triggers: (a) touches 3+ files, (b) crosses module boundaries, (c) changes a schema / API / contract, or (d) requires an architectural decision. Single-file, single-purpose fixes skip planning.
* If something goes sideways, STOP and re-plan immediately—do not keep pushing blind fixes.
* Use plan mode for verification steps, not just initial building.
* Write detailed specs upfront to reduce ambiguity.

### 2. Subagent Strategy
* Use subagents when ANY of these conditions hold: (a) the work can run in parallel with main-context work, (b) breadth of research would burn more than ~5 grep/read cycles, or (c) a registered subagent type (Explore, Plan, code review) matches the task. Otherwise main-context work is fine — "liberal" is not "default."
* Offload research, deep exploration, and parallel analysis to subagents.
* For complex problems, throw more compute at it via subagents.
* Assign exactly one task per subagent for tightly focused execution.

### 3. Self-Improvement Loop
* After ANY correction from the user: immediately persist the failure pattern. Split by audience: `tasks/lessons.md` for **project-specific** lessons (committed with the code, visible to anyone reading the repo); the harness memory system for **user-preference or cross-project** lessons (private to the harness, not in version control). Rule of thumb: if the lesson is about THIS codebase, file it in `tasks/lessons.md`; if it's about the user's working style or external systems, file it in memory.
* Write rules for yourself that explicitly prevent making the same mistake twice.
* Ruthlessly iterate on these lessons until your systemic mistake rate drops.
* Review existing lessons AND project-relevant memory entries at the start of every session.

### 4. Verification Before Done
* Never mark a task complete without explicitly proving it works.
<!-- Disabled until git is initialized — re-enable when the repo is version-controlled.
* Diff behavior between `main` and your changes whenever relevant.
-->
* Ask yourself: "Would a staff engineer approve this code?"
* Run tests, check system logs, and explicitly demonstrate correctness in the terminal.

### 5. Demand Elegance (Balanced)
* For non-trivial changes: pause and ask "is there a more elegant way to structure this?"
* If a fix feels hacky, stop and prompt: "Knowing everything I know now, implement the truly elegant solution."
* Skip this for simple, completely obvious fixes—do not over-engineer.
* Aggressively challenge your own work before presenting it to the user.

### 6. Autonomous Bug Fixing
* If the bug fix is trivial by rule 1's criteria: just fix it. Do not ask for hand-holding or micro-permissions.
* If the bug fix is non-trivial: write the plan per rule 1, then execute autonomously — do not ask permission for individual steps once the plan is approved.
* Point directly at the logs, errors, or failing tests—then resolve them end-to-end.
* Require zero context switching from the user.
* Go fix failing CI tests autonomously without being explicitly told how.

---

## Task Management
* **Plan First:** Write your engineering plan directly to `tasks/todo.md` with checkable markdown items.
* **Verify Plan:** Check in with the user to get explicit approval before starting implementation.
* **Track Progress:** Mark items complete in real-time as you go.
* **Explain Changes:** Provide a highly concise, high-level summary at each developmental step.
* **Document Results:** Add a thorough review section to `tasks/todo.md` upon completion.
* **Capture Lessons:** Project-specific corrections go in `tasks/lessons.md`; user-preference or cross-project lessons go in the harness memory system. See rule 3 for the split.

---

## Core Principles
* **Simplicity First:** Make every single change as simple as humanly possible. Impact the minimal amount of code necessary.
* **No Laziness:** Track down root causes. Never drop temporary patches or "band-aid" fixes. Maintain rigorous senior developer standards.
* **Minimal Impact:** Changes should only touch what is explicitly required. Avoid scope creep to eliminate regression risks.
