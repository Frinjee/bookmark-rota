# Website handoff: bookmark rota on jenhammond.me

Use this brief in a Cursor session on the **frinjee.github.io** repo. It is consume-side only. Do not run the Python pipeline from here.

## Scope (read this first)

- The bookmark rota exists **only on the main home page** of **https://jenhammond.me**.
- Source repo is `frinjee.github.io` (GitHub Pages). The custom domain visitors use is **jenhammond.me**, not the `*.github.io` host, for acceptance and smoke-checks.
- Implement the rota in the existing home-page box in `index.html`. Do **not** add it to Dragon Hoard (`hoard/`), other HTML pages, shared chrome that appears off-home, or any secondary section of the site.
- If a change would make the rota show up anywhere other than that one jenhammond.me home box, it is out of scope.

## What the producer already ships

The sibling **bookmark-rota** repo builds and validates a weekly JSON feed:

- Normal week: **12** items (schema allows 1–12).
- Items are already **PUBLIC** only. Never invent PRIVATE/REVIEW UI on the site.
- Producer Monday checklist lives in bookmark-rota `README.md` and `ig/task_plan.md`. You only need to consume the JSON.
- A feed file may already be present at `assets/json/bookmarks_rota.json` in this website repo from a local copy. It still needs JS wiring and a commit to go live.

## Feed path and fetch

| Role | Value |
|------|--------|
| Repo path | `assets/json/bookmarks_rota.json` |
| Same-origin fetch | `assets/json/bookmarks_rota.json` or `/assets/json/bookmarks_rota.json` |
| Public URL after deploy | `https://jenhammond.me/assets/json/bookmarks_rota.json` |
| Rollback sibling | `assets/json/bookmarks_rota.prev.json` (optional; restore over the live file if a bad feed ships) |

Fetch same-origin from the page. Do not hard-code a raw.githubusercontent.com or cross-origin URL.

## JSON contract

Array of objects. Schema source of truth in bookmark-rota: `schemas/bookmarks_rota.schema.json`.

Per item:

- **Required:** `bookmark_id`, `title`, `url`, `hash`, `display_week` (`YYYY-Www`), `display_date` (`YYYY-MM-DD`), `taxonomy_category`, `taxonomy_subcategory`, `tags` (string array)
- **Optional:** `note`
- `url` matches `^https?://`
- No extra properties on items (`additionalProperties: false`)

Sample item (from week `2026-W33`):

```json
{
  "bookmark_id": "7364c19955d32404",
  "title": "247CTF - The game never stops",
  "url": "https://247ctf.com/",
  "hash": "13ecf5891bff",
  "display_week": "2026-W33",
  "display_date": "2026-08-10",
  "taxonomy_category": "INFSEC",
  "taxonomy_subcategory": "PENTEST",
  "tags": ["INFSEC", "PENTEST", "WEB"],
  "note": ""
}
```

## Existing DOM and CSS (preserve)

Current home markup (hard-coded list today):

```html
<section class="box bookmark-rota-box">
  <h2>Bookmark Rota - Week of …</h2>
  <ul id="bookmark-rota-list">
    <li class="bookmark-rota-li"><a href="…">…</a></li>
    …
  </ul>
</section>
```

Keep these hooks:

- Section: `section.box.bookmark-rota-box`
- List: `ul#bookmark-rota-list`
- Items: `li.bookmark-rota-li` wrapping an `a[href]`

Styles already live in `assets/styles/main.css` under `.bookmark-rota-*` / `#bookmark-rota-list`. Do not replace this with a new card layout. Populate the same list structure from JS after fetch.

The `<h2>` can stay static for v1, or update from `display_week` / `display_date` if you touch it. Prefer minimal change.

## Rendering rules

1. Link text = `title`. `href` = `url`.
2. Match existing home-page link behavior: current hard-coded rota links do **not** use `target="_blank"`. Keep that unless the rest of the home page already opens externals differently and you are aligning to that established pattern.
3. Fail soft: if fetch or JSON parse fails, show a short fallback message inside the bookmark-rota box and leave the page layout intact. Do not blank the whole home page.
4. Skip malformed items (missing `url` or `title`) instead of throwing.
5. Do not client-filter by visibility. Upstream already filtered.
6. Category chips from `taxonomy_category` / `tags` are optional and **not** required for v1.

Suggested list item shape after render:

```html
<li class="bookmark-rota-li"><a href="https://example.com/">Example title</a></li>
```

## Monday / deploy touchpoints (website side)

1. After JS lands: commit `assets/json/bookmarks_rota.json` plus the HTML/JS changes in `frinjee.github.io`.
2. Smoke-check **https://jenhammond.me** at desktop and mobile widths (rota box only needs to work there).
3. Later Mondays: copy in a new JSON from bookmark-rota; HTML/JS stay put unless broken.
4. Cross-repo CI auto-push is deferred. Local copy or PR of the JSON is fine for now.

## Out of scope for the website session

- Running `bookmark_pipeline`, taxonomy edits, rotation quotas, or SQLite work
- Adding the rota anywhere except the jenhammond.me home `bookmark-rota-box`
- Building Phase 2 producer features in this repo

## Done when

- Home page on https://jenhammond.me loads links from `assets/json/bookmarks_rota.json`
- Hard-coded list items are gone (or only used as a last-resort static fallback you intentionally keep behind the soft-fail path)
- Fetch failure does not break the rest of the page
- No other site pages gained a bookmark rota
