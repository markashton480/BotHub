# Django admin UX upgrades plan

## Context
- Admin site uses [Unfold](https://github.com/unfoldadmin/django-unfold) with custom `BotHubAdminSite` (@bothub/admin_site.py) and sidebar config in settings (`UNFOLD` dict) (@bothub/settings.py).
- Models registered on `bot_admin_site` live in `hub/admin.py` and already use inlines, `autocomplete_fields`, and `formfield_overrides`.
- Goal: improve UX without relying on Unfold paid features; keep future work discoverable for any agent.

## Goals
1) Add a dashboard-like landing experience using open-source building blocks (no Unfold paid features).
2) Re-enable history in the command palette.
3) Improve list pages with inline edits and better filters.
4) Speed up list rendering with `list_select_related` and expand autocomplete usage.
5) Enhance JSON/text editing ergonomics.
6) Add collapsible navigation sections similar to the user’s other admin.

## Current state (baseline)
- Admin site branding: `site_header = "BotHub Admin"`, `index_title = "Dashboard"` (@bothub/admin_site.py).
- Unfold sidebar navigation is explicitly defined with "Core", "Collaboration", "Ops", "Accounts" sections and icons (@bothub/settings.py, `UNFOLD["SIDEBAR"]["navigation"]`).
- Command palette: `search_models=True`, `show_history=False` (@bothub/settings.py `UNFOLD["COMMAND"]`).
- Styling: custom CSS entry `/static/admin/bothub.css` (@bothub/settings.py `UNFOLD["STYLES"]`).

## Implementation plan

### 1) Dashboard alternative (open-source)

- **Custom admin view (recommended, zero extra deps):** Add a `dashboard` view on `BotHubAdminSite` (e.g., `admin_site.get_urls` override), rendering a template with stats (counts of Projects/Tasks/Threads/Users), recent Activity (AuditEvents), and quick links to common changelists. Use cached queries to keep it light. Link it as the index view (override `index_template`) and/or add a prominent sidebar link.


Steps:
1. Create `templates/admin/dashboard.html` aligned with Unfold styles; include cards for key metrics and a “recent activity” list using `AuditEvent` and `LogEntry`.
2. Add an admin view in `bothub/admin_site.py` (or a small `dashboard.py`) to serve the template; decorate with `admin_site.admin_view`.
3. Set `index_template = "admin/dashboard.html"` and ensure `index` uses the custom context, or redirect `/admin/` to the dashboard view.
4. Add a sidebar link to the dashboard (top of navigation). Keep link stable for future agents.

### 2) Command palette history
- Toggle `UNFOLD["COMMAND"]["show_history"] = True` so object history is discoverable via palette. Verify Unfold version supports this flag.

### 3) List page improvements
- **Inline edits:** For high-traffic models, add `list_editable`:
  - Project: `is_archived`
  - Task: `status`, `priority`, possibly `due_at`/`position` if safe
- **Filters:** Add `DateRangeFilter` on `created_at` (via `django-admin-rangefilter` or built-in `DateFieldListFilter` if avoiding deps). Keep existing status/priority filters.
- **Batch actions:** Ensure bulk “archive” or “mark done” actions exist for Tasks/Projects; add if missing.

### 4) Performance: related lookups & autocomplete
- Add `list_select_related` to heavy list views to avoid N+1 queries:
  - Task: (`project`, `parent`, `created_by`)
  - Thread: (`project`, `task`, `created_by`)
  - Message: (`thread`, `created_by`)
  - TaskAssignment: (`task`, `assignee`, `added_by`)
- Expand `autocomplete_fields` where lookups are currently dropdowns (e.g., `TagAdmin` tags, any FK with large cardinality) to speed form load times.

### 5) Better editors for JSON/text
- Adopt a JSON editor widget (options):
  - **`django-jsoneditor`** (MIT) for `JSONField` (AuditEvent.metadata, Message.metadata, Webhook.events/payload). Provides validation + tree view.
  - Fallback: keep textarea but add monospace class + client-side validation (simple JSON parse) and syntax highlighting via `CodeMirror` or `django-ace`.
- For long text fields, keep existing `Textarea` but consider row tweaks per model.

### 6) Collapsible navigation sections
- Implement collapsible groups for the existing sidebar sections:
  - If Unfold supports per-section collapse via config/classes, add the class and remember expanded state in localStorage.
  - Otherwise, add a small JS/CSS enhancement in `/static/admin/bothub.css` and a companion JS (e.g., `/static/admin/bothub.js`) that:
    1. Wraps each navigation group in a toggle with an icon.
    2. Persists open/closed state per section key in `localStorage`.
    3. Provides sensible defaults (Core open, others collapsed if desired).
- Keep HTML structure stable so future upgrades to Unfold are low-risk.

## Task ordering (suggested)
1) Enable command history (low risk, quick win).
2) Add `list_select_related` + `list_editable`/filters to key admins; add any bulk actions.
3) Add collapsible navigation JS/CSS and wire to existing Unfold sidebar.
4) Introduce JSON editor widget (or validation shim) for `JSONField` models.
5) Implement dashboard view/template with cached stats and recent activity; add sidebar link.

## Testing & rollout
- Add unit tests for custom admin view (permissions, context keys) and simple smoke tests for admin changelists (ensure `list_select_related` doesn’t break pagination).
- Manually verify in browser:
  - Command palette shows history.
  - Inline edits save correctly and respect required fields.
  - Collapsible nav persists state across refresh.
  - JSON editor validates and saves round-trip.
  - Dashboard renders without heavy queries (profile with `django-debug-toolbar` if enabled).

## Notes for future agents
- If Unfold releases native collapsible sections or free dashboard widgets, prefer upstream config over custom JS/CSS.
- Keep dependencies minimal; prefer custom admin view before adding packages. If adding packages (`django-jsoneditor`, `django-admin-rangefilter`, `django-admin-tools`), document them in `requirements` and `INSTALLED_APPS` with migration notes.
- Preserve the existing sidebar structure and icon choices when enhancing collapse behavior.
