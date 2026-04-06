# Gallery

Open the gallery with:

```bash
waysnip gallery
```

The gallery shows thumbnails of all screenshots in your save directory (`~/Pictures/Screenshots` by default).

## Browsing

Screenshots are displayed as a grid of thumbnails. The gallery watches the save directory and updates automatically when new screenshots are added or removed.

## Context menu

Right-click a thumbnail for these actions:

- **Copy image to clipboard** — copies the image
- **Copy filename** — copies just the filename
- **Copy full path** — copies the absolute file path
- **Edit** — opens the screenshot in the editor
- **Reveal in file manager** — opens the containing folder
- **Flatten** — bakes annotations into the image permanently (removes re-edit capability)
- **Delete** — removes the file from disk

## Re-editing

Double-click a thumbnail to open it in the editor. If the screenshot was saved in the default `annotated` mode, all annotations are still editable — you can move, resize, change colors, or delete them.

If the image was saved in `editable` mode or was flattened, annotations are baked into the pixels and can't be individually edited.
