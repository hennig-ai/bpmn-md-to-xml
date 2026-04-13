# BPMN MD to XML

An agent skill that converts BPMN Markdown tables to BPMN 2.0 XML
(.bpmn files) and optionally visualizes them in bpmn.io.

This skill follows the open [Agent Skills](https://agentskills.io) standard
and works across multiple AI platforms.

## What it does

This skill enables AI agents to export BPMN models from structured
Markdown tables into standards-compliant BPMN 2.0 XML. It supports:

- **Markdown to XML conversion** via `export_bpmn_xml.py`
- **Auto-layout** for generated BPMN diagrams
- **Live visualization** by loading .bpmn files into bpmn.io in the browser
- One `.bpmn` file per process found in the model

## Installation

Skills are installed by cloning the repository into the directory where your AI agent looks for skills. There is no separate install command — placing the files in the right location is all it takes. The agent automatically discovers any `SKILL.md` file in its skills directory.

### Claude Code

From your project root, clone the skill into the skills directory:

```bash
# Project-level (shared via git)
git clone https://github.com/hennig-ai/bpmn-md-to-xml.git .claude/skills/bpmn-md-to-xml
pip install .claude/skills/bpmn-md-to-xml

# Personal (available across all projects)
git clone https://github.com/hennig-ai/bpmn-md-to-xml.git ~/.claude/skills/bpmn-md-to-xml
pip install ~/.claude/skills/bpmn-md-to-xml
```

### Claude.ai (Cowork)

Download `bpmn-md-to-xml-skill.zip` from the [latest GitHub Release](https://github.com/hennig-ai/bpmn-md-to-xml/releases/latest) and upload it via the Claude.ai interface. The zip includes bundled wheels for offline dependency installation. See [Using skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude) for details.

### OpenAI Codex CLI

```bash
git clone https://github.com/hennig-ai/bpmn-md-to-xml.git .agents/skills/bpmn-md-to-xml
pip install .agents/skills/bpmn-md-to-xml
```

### GitHub Copilot

```bash
git clone https://github.com/hennig-ai/bpmn-md-to-xml.git .github/skills/bpmn-md-to-xml
pip install .github/skills/bpmn-md-to-xml
```

### Other platforms

Any AI agent that supports the [Agent Skills standard](https://agentskills.io) can use this skill. Clone the repository into the platform's skills directory.

> **Note:** This skill has only been tested on Claude Code and Claude.ai (Cowork). It should work on any platform that supports the Agent Skills standard, but is not guaranteed.

## Usage

Trigger the skill with conversion or visualization requests, e.g.:
- "Convert the BPMN model to XML"
- "Export the markdown model to a .bpmn file"
- "Visualize the .bpmn file in bpmn.io"
- "Convert and display the BPMN model"

## License

MIT — see [LICENSE](LICENSE) for details.
