---
name: File Storage Convention
description: All project-related files stored within the project directory structure
type: feedback
---

**Rule:** All project-related files (plans, memory, documentation) must be stored within `G:\Vibe coding\fantasy-nba-demo`, organized in a consistent directory structure.

**Why:** Centralizing all files within the project directory ensures:
- Easy version control (everything tracked by git)
- Isolated and portable project structure
- No dependency on Claude's user directories
- Clear separation of concerns (project files vs system files)

**How to apply:**

Directory Structure:
```
G:\Vibe coding\fantasy-nba-demo\
├─ memory\          # Project memory files
│  ├─ MEMORY.md
│  ├─ working_directory.md
│  ├─ session_startup_protocol.md
│  ├─ task_progress.md
│  ├─ project_plan.md
│  └─ file_storage_convention.md
├─ claude\
│  └─ plans\        # Implementation plans
│     ├─ enumerated-gathering-spark.md (Task 8)
│     └─ [future plans]
├─ app.py
├─ templates/
├─ data/
├─ cache/
├─ CLAUDE.md
├─ PROGRESS.md
└─ [other project files]
```

**When creating new files:**
1. Plans → `G:\Vibe coding\fantasy-nba-demo\claude\plans\`
2. Memory → `G:\Vibe coding\fantasy-nba-demo\memory\`
3. Documentation → Project root or relevant subdirectory
4. Never use `C:\Users\Shelton\.claude\` for project files (system-wide only)

**Note:** This ensures all project context is portable and version-controlled with git.
