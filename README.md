# NYC Restaurants

A static, single-page map and list of NYC restaurants to scout.

## Files

- `restaurants.json` — the data (single source of truth for restaurant entries)
- `index.template.html` — the page markup, styles, and scripts (single source of truth for layout/behavior)
- `build.py` — combines the two into `index.html`
- `index.html` — **generated**. Do not edit by hand; changes will be clobbered on the next build.

## Editing

- To add/edit/remove a restaurant: edit `restaurants.json`, then run `./build.py`.
- To change layout, styles, or behavior: edit `index.template.html`, then run `./build.py`.
- After running the build, commit `index.html` alongside the source change.

## Build

```sh
./build.py
```

The data array is inlined at the marker `/* %%RESTAURANTS%% */[]` in the template. The generated `index.html` carries a `<!-- GENERATED -->` banner at the top as a reminder.

## Blacklist (do not re-add)

Restaurants Jim has visited and didn't like get a `"blacklisted": true` flag
(optionally with `"blacklist_reason": "..."`) on their entry in
`restaurants.json`. The template filters these out at the top of the script so
they never appear on the map, in the list, or in any counts — but the entry
*stays in restaurants.json* as a tombstone.

**Future scout cycles must honor this.** When processing a new publication:

1. Look up each candidate by name (and address if the name is ambiguous) in
   `restaurants.json`.
2. If a match exists with `blacklisted: true`, **silently skip it** — do not
   propose it as a new add, do not surface it in the recommendation list, do
   not even mention it. The flag means "Jim has already decided."
3. If Jim asks to blacklist a place that's currently live in the list, add
   `"blacklisted": true` and `"blacklist_reason"` to its existing entry rather
   than deleting the entry. Run `./build.py`.

## Sources

Restaurants are added by hand from curated publications. When adding entries, check these regularly and set the `source` field accordingly:

- Eater NY (incl. Heatmaps, monthly roundups, previews)
- Infatuation (NYC + Brooklyn)
- Grub Street (New York Magazine)
- The New York Times — Food / Restaurant Review
- Luke Fortney's *Where to Eat* newsletter — Eater NY senior reporter's personal newsletter
- BK Mag
- SecretNYC
- Brooklyn Bridge Parents
- Welcome to Chinatown
- HelpNewYork.com
- What Now NY

Format the `source` field as `Publication Month Year` (e.g. `Eater NY April 2026`) so we can trace where each entry came from.
