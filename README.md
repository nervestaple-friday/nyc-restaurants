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
