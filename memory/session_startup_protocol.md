---
name: Session Startup Protocol
description: Greet user and provide task status summary at the beginning of each session
type: feedback
---

**Rule:** At the start of each session, actively greet the user and provide a task status summary

**Why:** The user wants to maintain awareness of project progress and pending tasks without having to manually request updates. This improves workflow efficiency and keeps context fresh.

**How to apply:**
1. At the very beginning of each session (after reading this memory), output a greeting with:
   - Current date
   - Project name (Fantasy NBA Demo)
   - Current phase/milestone status
   - List of active/pending tasks
   - Any blockers or critical items needing immediate attention
2. Keep the greeting concise but informative (3-5 sentences max)
3. Ask user what they'd like to focus on today
4. Update task_progress.md before providing the status
