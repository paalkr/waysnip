# Annotation tools

All tools are available from the toolbar at the top of the editor. Each has a single-key shortcut.

## Select (V)

The default tool. Click an annotation to select it, drag to move it. Selected annotations show resize handles at the corners and edges. Hold **Ctrl** and click to add to the selection.

- **Delete** removes selected annotations
- **Ctrl+D** clones (duplicates) selected annotations
- **Ctrl+A** selects all annotations

Right-click a selected annotation to open the context menu with layer ordering, delete, and clone options.

### Layer ordering

Annotations stack in the order they are drawn. You can reorder them via the Edit menu or context menu:

- **Bring to front** (Ctrl+Shift+]) — move above all other annotations
- **Send to back** (Ctrl+Shift+[) — move below all other annotations
- **Move up** (Ctrl+]) — swap with the annotation one layer above
- **Move down** (Ctrl+[) — swap with the annotation one layer below

Layer order is preserved when saving and re-opening images.

## Rectangle (R)

Click and drag to draw a rectangle. Supports border color, fill color, and corner radius.

## Ellipse (E)

Click and drag to draw an ellipse. Hold **Shift** to constrain to a circle. Supports border and fill colors.

## Arrow (A)

Click and drag from start to end. An arrowhead is drawn at the end point. Hold **Shift** to snap to 45-degree angles.

## Line (L)

Click and drag to draw a line. Supports solid, dashed, and dotted styles.

## Text (T)

Click to place a text box, then type. Double-click an existing text annotation to re-edit it. Font family and size are configurable.

## Numbered marker (N)

Click to place a numbered circle. Numbers auto-increment (1, 2, 3, ...). If you delete a marker, the remaining markers renumber automatically.

## Freehand pen (P)

Click and drag to draw smooth freehand strokes.

## Highlight (H)

Click and drag to draw a semi-transparent wide stroke, like a highlighter pen. Good for drawing attention to a region without obscuring it.

## Blur (B)

Click and drag to draw a blur region. The area is pixelated with a configurable block size (default 10px). Use this to obscure sensitive information.

Blur regions always stay below other annotations in the layer stack — they only pixelate the background image, not annotations drawn on top. This means you can blur a region and then draw arrows or text over it without those being affected. Blur regions are not affected by layer ordering commands.

## Crop (C)

Click and drag to define a crop region, then confirm to trim the image.
