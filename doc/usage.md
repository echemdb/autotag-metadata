---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.13.8
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

User manual
===========

autotag-metadata watches a folder and, whenever a new file appears, writes a sidecar
`<filename>.meta.yaml` next to it containing the metadata you have prepared. The interface
follows your operating system's light or dark theme.

The window has a **two-row toolbar** at the top, the **metadata editor** in the centre, and
optional **Library**, **Drop files**, and **Log** panels that you can show or hide.

```{figure} images/placeholder_main_window.png
:alt: The autotag-metadata main window
:width: 100%

The main window: the two-row toolbar (with the **Form / YAML** switch at the far left, above
the Library side panel), the central metadata editor, and the Library panel on the left.
*(Placeholder — to be replaced with a screenshot.)*
```

```{contents} On this page
:local:
:depth: 1
```

## The toolbar

**Top row — actions**

| Control | Purpose |
|---------|---------|
| ☰ **Library** | Show / hide the Snippets · Templates · Views side panel. |
| **Folder** field + **Browse…** | Choose the folder to watch for newly created files. |
| **Activate** | Start / stop watching the selected folder. Files are only tagged while active. |
| **Form** / **YAML** tabs | Switch the editor between the structured form and the raw YAML text. |
| **Drop files** | Toggle the drop zone for tagging individual files (see [below](tagging-individual-files)). |
| **Log** | Toggle the log panel. |

**Bottom row — settings**

| Control | Purpose |
|---------|---------|
| **Patterns** | Comma-separated filename globs (e.g. `*.csv, *.dat`). Only matching new files are tagged. Empty = all files. |
| **Recursive** | Also watch sub-folders of the selected folder. |
| **Live file** + **Select…** / **Use** | Mirror the current metadata to a chosen file continuously, so an external schema-aware editor can validate it as you type. **Use** toggles to **Do not use** while active. |

While watching, **Activate** changes to **Deactivate** and the **window title** shows the watched
folder, so multiple windows are easy to tell apart.

## Menus and keyboard shortcuts

Most actions are also reachable from the menu bar, and the common ones have shortcuts.

**Template menu**

| Action | Shortcut | Effect |
|--------|----------|--------|
| Load Template… | `Ctrl+O` | Open a dialog to load a saved template into the editor. |
| Save Template | `Ctrl+S` | Start saving the current document as a template (name it inline in the Templates list). |

**View menu**

| Action | Shortcut | Effect |
|--------|----------|--------|
| Drop files | — | Show / hide the drop-files panel. |
| Log | `Ctrl+L` | Show / hide the log panel. |
| Save View | — | Save the current multi-view layout (name it inline in the Views list). |
| Load View… | — | Open a dialog to load a saved layout. |
| Manage Views… | — | Open a dialog to delete saved layouts. |

**Other shortcuts**

| Shortcut | Effect |
|----------|--------|
| `Ctrl+Tab` | Switch between the **Form** and **YAML** views. |
| `Ctrl+Q` | Quit the program. |

Templates and views can be managed two ways: **inline in the Library list** (Save in the panel,
double-click to load, delete from the list), or through these **menu dialogs**. Both act on the
same saved entries.

## Editing metadata

Type your metadata as [YAML](https://en.wikipedia.org/wiki/YAML). When the program starts the
editor is empty; for example:

```yaml
experimentalist: Max Mustermann
project: degradation
starting temperature:
  value: 300
  unit: K
```

There are two equivalent views, switched with the **Form / YAML** tabs:

- **YAML tab** — a raw text editor with lightweight syntax highlighting and indentation guides.
  The tab label turns **green** when the YAML is valid and **red** when it is not.
- **Form tab** — a structured form generated from the YAML. Nested keys become collapsible
  groups, `value` / `unit` pairs are shown side by side, and a list of mappings (such as
  electrolyte `components`) becomes a collapsible list with a `[index] name` heading per item.
  Each value gets an input matched to its type — a checkbox for true/false, a number box for
  numbers, a comma-separated field for simple lists, and a text field otherwise.

Edits in either view update the same underlying document, so you can move freely between them.

Elaborate examples of metadata files can be found in the example section of
[echemdb's metadata-schema](https://github.com/echemdb/metadata-schema/tree/main/examples).

## Multi-view: editing distant parts at once

The Form tab is a **tiling multi-view**. A large metadata file often has fields you want to edit
together but that live far apart in the document. Each panel can be focused on a sub-tree:

- Type a dotted **path** in a panel's header to zoom that panel onto that part of the document.
  Leave it empty to show the whole document.
- **Split** a panel with **⊢** (split right) or **⊟** (split down) to view another path beside it.
- **Drag** a panel by its handle (⠿) and drop it on another panel's edge to rearrange the tiling.
- Close a panel with **×**.

All panels share one document, so a change in one is reflected in the others immediately. When
more than one panel is open, the **active panel** (the one you are working in, and the source for
its **⊕** snippet button) is shown with a highlighted border.

```{figure} images/placeholder_multiview_active_panel.png
:alt: The tiling multi-view with several panels
:width: 100%

The multi-view tiling several panels onto different paths of the same document; the active panel
is outlined. *(Placeholder — to be replaced with a screenshot.)*
```

### Path syntax

A panel path is a sequence of keys and list indices separated by dots:

| Path | Shows |
|------|-------|
| *(empty)* | the whole document |
| `electrochemical system.electrolyte` | the `electrolyte` mapping |
| `electrochemical system.electrolyte.components` | the `components` list |
| `electrochemical system.electrolyte.components.0` | the **first** list element (`.1`, `.-1`, …) |
| `electrochemical system.electrolyte.components.0.type` | a single **leaf value**, shown as one editable field |

If a path does not exist the panel shows a "not found" notice; fix the path to continue.

## Snippets, Templates, and Views

Open the **Library** panel (☰ Library) to reuse work. It has three tabs, and all three behave the
same way: click **Save** to add an entry — you name it **inline in the list** — and double-click an
entry to use it. Right-click (or use the delete action) to remove one.

```{figure} images/placeholder_library_panel.png
:alt: The Library panel with Snippets, Templates and Views tabs
:width: 60%

The Library panel: Snippets, Templates, and Views, each named inline in the list.
*(Placeholder — to be replaced with a screenshot.)*
```

### Templates

A **template** is a complete metadata document you reuse across sessions. Save the current editor
contents as a template, and load it later to repopulate the whole editor. Templates are ideal for
"the standard set of fields for this kind of experiment".

### Snippets

A **snippet** is a *part* of a document — a sub-tree — that you drop into place when needed.
Snippets remember the **full path** where they were captured, so they re-insert at the correct
point in the structure.

- **Capture:** click **⊕** in a Form panel to save that panel's sub-tree; click **Save snippet**
  at the bottom of the Snippets list to capture the **active panel** (the outlined one); or select
  lines in the raw YAML editor and choose **Save selection as snippet…** from the right-click menu.
  Any of these preserves the parent path — including the list position when you capture a single
  component (e.g. `components.0`) or a single leaf value.
- **Apply:** **double-click** a snippet to merge it in **non-destructively**: existing values are
  kept, missing keys are added, and an empty (`null`) placeholder is filled in. Items in a list of
  components are matched **by their `name`**, so re-applying a snippet *enriches* the matching
  component (adding its missing fields) and only appends genuinely new ones — it does not create
  duplicates. Hold **Ctrl** while double-clicking to **overwrite** existing values instead. You can
  also **drag** a snippet onto a Form panel (merges, as above) or onto the raw YAML editor (inserts
  its text at the cursor).

### Views

A **view** saves the multi-view *layout*: which paths each panel shows, how the panels are tiled,
and each panel's scroll position. Save a view once you have arranged panels for a particular task,
and load it to return to that arrangement later.

(tagging-individual-files)=
## Tagging individual files

Besides watching a folder, you can tag files on demand. Enable the **Drop files** panel from the
toolbar and drag one or more files (or whole folders) onto it.

```{figure} images/placeholder_drop_zone.png
:alt: The Drop files panel
:width: 60%

The Drop files panel: drop files or folders here to tag them on demand.
*(Placeholder — to be replaced with a screenshot.)*
```
 Each dropped file gets a
`.meta.yaml` written with the current metadata. Dropped folders are searched recursively and the
**Patterns** filter is applied to their contents; files you drop directly are tagged regardless of
the pattern. Existing `.meta.yaml` files are skipped.

## Where things are stored

Settings and your saved entries live under `~/.config/autotag-metadata/`:

```
~/.config/autotag-metadata/
    config.toml      window/folder settings + the template/snippet/view index
    templates/       one YAML file per template
    snippets/        one YAML file per snippet
    views/           one file per saved layout
```

```{note}
Multiple instances of the program can be launched to watch different folders simultaneously.
```
