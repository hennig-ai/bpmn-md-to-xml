---
name: bpmn-md-to-xml
description: >
  Convert BPMN markdown tables to BPMN 2.0 XML (.bpmn) and/or visualize .bpmn files live in bpmn.io. TRIGGER when: user wants to convert/export a BPMN markdown model to XML, or visualize/display/render a .bpmn file in the browser.
metadata:
  version: "0.2.0"
---

# BPMN MD to XML & Visualizer

Two independent capabilities that can be used separately or together:

- **Part A — Conversion**: BPMN markdown tables → BPMN 2.0 XML (.bpmn files)
- **Part B — Visualization**: Open a .bpmn file in bpmn.io in the browser

---

## Part A — Conversion (Markdown → BPMN XML)

### Prerequisites

- The BPMN model exists as a markdown file (`.md`) with pipe-delimited tables
- The user provides the path to this file

### Workflow

#### Step 1 — Run the export script

```bash
python <skill-path>/scripts/export_bpmn_xml.py <input.md> <output_dir>
```

Where `<input.md>` is the markdown file and `<output_dir>` is the target directory.

The script creates one `.bpmn` file per process found in the model.

If the script errors, check that:
- The markdown file has proper `## TableName` headings
- `bpmn_element`, `event`, and `sequence_flow` tables are present

#### Step 2 — Report results

List the generated `.bpmn` files to the user.

---

## Part B — Visualization (.bpmn → bpmn.io)

### Prerequisites

- A `.bpmn` file exists (either from Part A or provided by the user)

### Workflow

#### Step 1 — Read the .bpmn file

Read the content of the `.bpmn` file.

#### Step 2 — Open bpmn.io and load the diagram

Use the browser tools:

1. Navigate to `https://demo.bpmn.io`
2. Wait for the page to load (title should be "BPMN Editor | bpmn-js modeler Demo")
3. Close the cookie banner if present — click the "Nicht wesentliche Cookies ablehnen"
   button or the x icon
4. Inject the XML via JavaScript:

```javascript
const modeler = window.bpmnio.modeler;
modeler.importXML(bpmnXML).then(() => {
  modeler.get('canvas').zoom('fit-viewport');
}).catch(err => console.error('BPMN import error:', err));
```

Where `bpmnXML` is the string content of the `.bpmn` file.

> **Note on IDs**: XML `id` attributes must start with a letter or underscore —
> numeric IDs like `001` are invalid XML and cause silent import failures in bpmn.io.
> The export script handles this automatically.

5. Take a screenshot to confirm the diagram loaded correctly

---

## Tips & Edge Cases

**Cookie banner**: If bpmn.io shows a cookie consent dialog in a different language,
look for any "reject" / "decline" / "ablehnen" button, or simply close the x.

**If `window.bpmnio` is undefined**: The page may not have finished loading. Wait 1-2
seconds and retry.
