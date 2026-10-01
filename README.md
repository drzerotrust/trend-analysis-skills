# trend-analisis

An OpenClaw skill for news discovery and trade-the-news research with the
Trend Engine CLI. Get source-linked Hacker News headlines and supporting
Google Trends, YouTube, and TikTok attention signals. No market data or trading.
Trend Engine is a separately installed dependency; its code and provider
credentials are not included in this repository.

## Install Trend Engine

- OpenClaw with command execution available.
- Trend Engine `>=0.4.1,<0.5.0` with Python 3.12+ on Linux or macOS.
- The installed `trend-engine` command on your agent's execution PATH.
- A trusted Trend Engine TOML config, supplied as an absolute path.
- Network access for fresh collection. Stored reports work offline.

This release uses report schema **3** and doctor schema **2**. From a compatible
Trend Engine checkout, install the CLI in a local environment:

```bash
python3 -m venv ./venv
./venv/bin/python -m pip install -e .
./venv/bin/trend-engine --version
```

Add that checkout's `venv/bin` directory to the PATH used by your agent process.
For a process launched from your current terminal:

```bash
export PATH="/absolute/path/to/trend-engine/venv/bin:$PATH"
trend-engine --version
```

Activating a venv in an unrelated terminal does not update an already-running
OpenClaw gateway. A normal wheel installation also works; the skill does not need
the CLI's source checkout or a `TREND_ENGINE_ROOT` variable. Repeat a normal install
after CLI updates; the editable install above follows changes in its checkout.

The skill requires `trend-engine` on PATH; detecting the binary does not check its
version or install it automatically. The offline doctor preflight below checks
compatibility before the skill runs collection or reports.

## Configuration

Use the CLI checkout's `config.toml`, or keep a trusted copy at an absolute path.
Edit it to choose countries, sources, and sample limits. Database and report paths
inside it are relative to the config's directory. Supply that absolute config path
in your request, or set `TREND_ENGINE_CONFIG` as shown below. The skill passes it
as `--config`; the CLI does not read `TREND_ENGINE_CONFIG` itself.

Optional `YOUTUBE_API_KEY` enables YouTube collection. No other provider key is used;
Hacker News is keyless. Export the key in the agent's execution environment or set
`TREND_ENGINE_ENV_FILE` to a trusted absolute dotenv path inside that environment.
The CLI loads one file for collection and doctor: explicit `TREND_ENGINE_ENV_FILE`,
then its source checkout's `.env`, then `$XDG_CONFIG_HOME/trend-engine/.env`
(or `~/.config/trend-engine/.env`). Existing process variables always win.
It does not search the skill directory or an arbitrary working directory for `.env`.
`TREND_ENGINE_CONFIG` still selects TOML settings, not the credential file.

Keep credentials out of this repository and agent conversations. Use the CLI's
`doctor` command to check compatibility and key presence without revealing values:

```bash
trend-engine doctor --json --config /absolute/path/to/config.toml --min-version 0.4.1 --max-version 0.5.0 --require-report-schema 3 --require-doctor-schema 2
```

This check is offline. Success does not prove that keys work or data is fresh.
A bare `doctor --json` can check the installed version without a config; it reports
`configuration.status: "not_checked"` if there is no local `config.toml`.
An invalid selected credential file produces `environment_invalid` with exit 2;
paths and contents are not printed. Reports and discovery commands do not load
credential files.

For sandboxed agents, make the analyzer installation and environment variables
available inside the sandbox, along with the config file and its data paths.
OpenClaw's host skill environment injection does not
automatically configure the sandbox. See the [OpenClaw configuration guide](https://docs.openclaw.ai/tools/skills-config).

## Load the skill

Clone this repository, then merge its absolute directory into
`skills.load.extraDirs` in your OpenClaw configuration, preserving existing entries.
The clone root directly contains `trend-analisis/`; do not point at an additional
`skills/` directory or at `SKILL.md` itself.

```json
{
  "skills": {
    "load": {
      "extraDirs": ["/absolute/path/to/trend-analisis-skills"]
    },
    "entries": {
      "trend-analisis": {
        "enabled": true,
        "env": {"TREND_ENGINE_CONFIG": "/absolute/path/to/config.toml"}
      }
    }
  }
}
```

Replace both placeholder paths. If this repository is nested in a CLI checkout at
`/path/to/trend-engine/skills`, use that directory for `extraDirs`. The repositories
remain independent. A repository already placed in your OpenClaw workspace's
`skills/` directory can be discovered there without an extra directory entry.
See [OpenClaw skill loading configuration](https://docs.openclaw.ai/tools/skills-config).

Check discovery with the [OpenClaw skills CLI](https://docs.openclaw.ai/cli/skills):

```bash
openclaw skills list --eligible
openclaw skills info trend-analisis
openclaw skills check
```

## Use

Ask your agent:

> Use trend-analisis to collect the latest Hacker News technology trends.

> Use trend-analisis to compare news-related attention in North America and Asia, with evidence links and coverage gaps.

> Use trend-analisis to summarize the latest stored report without collecting new data.

Fresh collection saves a snapshot to the analyzer's SQLite database. Reading a
stored report does not make network requests or change the database. Reports
include evidence links, observation times, source health, and freshness indicators.

Hacker News is a global feed, not regional evidence. Search/social feeds are not
news-only or fact verification. TikTok coverage is limited, and Instagram is not
supported. Reports do not predict market moves or recommend trades.

## JSON output

- [Report schema](trend-analisis/references/report.schema.json): the version 3 JSON
  report returned by `run --json` and `report --json`.
- [Doctor schema](trend-analisis/references/doctor.schema.json): version 2 offline compatibility
  and configuration checks, separate from trend reports.

Both schemas ship with the skill and are available offline from `trend-engine schema`
and `trend-engine schema doctor`. [compatibility.json](compatibility.json) records
the supported CLI range and output versions for this repository's tests; OpenClaw
does not interpret it. Input uses regular CLI arguments, not a separate JSON request
format. `--json` prints to stdout without creating Markdown/JSON report files;
`run --json` still saves a database snapshot.

Older report files must be regenerated with the compatible CLI. Stored history
is preserved; historical market data is omitted from new news-focused reports.

The skill calls the CLI directly; it does not install an MCP server or custom tool.
See [SKILL.md](trend-analisis/SKILL.md) for the agent's operating instructions.

## View reports in a browser (optional)

The skill uses JSON and does not need a web server. For a manual visual report,
use the **Trend Engine source checkout**, not this skills repository. The checkout
includes `dirtyServer.py` and `reports/static/reports.css`; they are not bundled
with the installed CLI.

First, set the config's `reports_dir` to the absolute path of the CLI checkout's
`reports/` directory. The viewer serves that directory and does not read your TOML
settings. Then, from that CLI checkout, using its local venv:

```bash
./venv/bin/python -m pip install 'Markdown>=3.7,<4'
./venv/bin/trend-engine report --window 24 --config /absolute/path/to/config.toml
./venv/bin/python dirtyServer.py
```

`report` uses stored history without collecting. Use `run` instead if fresh
collection is wanted. Leave off `--json` so the CLI writes the report files.

Open [the local report viewer](http://127.0.0.1:8002/) on the server's machine,
choose a date/run directory, and open `report.md`. Markdown is rendered as HTML
with the shared stylesheet, and report links open in a new tab. New visual reports
show up to 50 scored topics across the configured report's global and regional
lists, with nested evidence instead of repeated platform highlights. This visual
cap does not trim the agent-facing JSON or stored history. Generate a new report
to get the shorter layout; existing files are unchanged. Stop the server with `Ctrl+C`.
This is a local preview with no authentication, not a production service.
The skill does not start it automatically.

## Compatibility tests

With `trend-engine` on PATH, run from this skills repository using a Python 3.12+
environment (for example, the analyzer's local venv):

```bash
python -m unittest discover -s tests -v
```

The tests use only Python's standard library and the installed CLI. They run offline,
use temporary configs/databases, and do not require the analyzer's source tree.

The **Compatibility** GitHub Actions workflow runs the same checks against a normal
CLI installation. Start it with the CLI's GitHub `owner/repository` and a pinned
release tag or commit. It has no default upstream repository or branch; each run
uses the explicit revision you select. No API keys are needed.
