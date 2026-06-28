---
name: touki-navi-collaboration
description: Touki Navi project collaboration rules. Use when working in the touki-navi repository, especially for code reading, refactoring, debugging, testing, or explaining modules with the user.
---

# Touki Navi Collaboration

Follow these project-specific collaboration rules:

- Do not add, edit, delete, format, or otherwise change code unless the user explicitly asks for code changes.
- When the user wants to study or review the project, proceed one module at a time: read the module, explain its responsibility, identify issues or refactoring candidates, then wait for the user's direction before editing.
- Before any code change, state the intended edit target and purpose in plain language.
- Preserve the user's existing handwritten comments as much as possible when editing. Remove or rewrite comments only when they are clearly stale, misleading, or directly conflict with the requested change.
- Prefer small, focused changes over broad rewrites.
- Keep explanations beginner-friendly for someone familiar with ChatGPT but new to Codex.
- When creating a new module, add its repository path as the first line comment, such as `# app/article/parser/xml_loader.py`, so the user can refer to modules easily.
- Treat half-width characters inside original Japanese legal XML `Sentence` text as system-added marks or metadata only; official Japanese legal text should be assumed to use full-width characters.
