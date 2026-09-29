# trend-analisis

An OpenClaw skill for news discovery and trade-the-news research with the
Trend Engine CLI. Get source-linked Hacker News headlines and supporting
Google Trends, YouTube, and TikTok attention signals. No market data or trading.

## Requirements

- OpenClaw with command execution available.
- Trend Engine `>=0.4.0,<0.5.0` with Python 3.12+ on Linux or macOS.
- The installed `trend-engine` command on your agent's execution PATH.
- A trusted Trend Engine TOML config, supplied as an absolute path.
- Network access for fresh collection. Stored reports work offline.

From your Trend Engine checkout, install its dependencies in a local environment:

```bash
python3 -m venv ./venv
./venv/bin/python -m pip install -e .
./venv/bin/trend-engine --version
```

Add that checkout's `venv/bin` directory to the PATH used by your agent process.
Activating a venv in an unrelated terminal does not update an already-running
OpenClaw gateway. A normal wheel installation also works; the skill does not need
the CLI's source checkout or a `TREND_ENGINE_ROOT` variable.

## Install

From this skills repository:

```bash
openclaw skills install ./trend-analisis
```

If this repository is already your OpenClaw workspace's `skills/` directory,
OpenClaw can discover the skill there without a separate installation.
See the [OpenClaw skills CLI documentation](https://docs.openclaw.ai/cli/skills)
for local directory installation and discovery checks.

## Configure

Add this entry to your OpenClaw configuration, preserving your existing settings.
Replace the path with your trusted config's absolute path:

```json
{
  "skills": {
    "entries": {
      "trend-analisis": {
        "enabled": true,
        "env": {"TREND_ENGINE_CONFIG": "/absolute/path/to/config.toml"}
      }
    }
  }
}
```

`TREND_ENGINE_CONFIG` tells the skill which path to pass as `--config`; it is not
auto-loaded by the CLI. You can also supply the config path in your request.
Edit that TOML file to choose countries, sources, and sample limits. Database and
report paths inside it are relative to the config's directory.

Optional `YOUTUBE_API_KEY` goes in the agent's execution environment to enable
YouTube collection. No other provider key is used.

Hacker News does not require a key. The CLI does not automatically load `.env`.
Keep credentials out of this repository and agent conversations. Use the CLI's
`doctor` command to check compatibility and key presence without revealing values:

```bash
trend-engine doctor --json --config /absolute/path/to/config.toml --min-version 0.4.0 --max-version 0.5.0 --require-report-schema 3 --require-doctor-schema 2
```

This check is offline. Success does not prove that keys work or data is fresh.
A bare `doctor --json` can check the installed version without a config; it reports
`configuration.status: "not_checked"` if there is no local `config.toml`.

For sandboxed agents, make the analyzer installation and environment variables
available inside the sandbox. OpenClaw's host skill environment injection does not
automatically configure the sandbox. See the [OpenClaw configuration guide](https://docs.openclaw.ai/tools/skills-config).

## Usage

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
the supported CLI range and output versions. Input uses regular CLI arguments,
not a separate JSON request format.

Older report files must be regenerated with the compatible CLI. Stored history
is preserved; historical market data is omitted from new news-focused reports.

The skill calls the CLI directly; it does not install an MCP server or custom tool.
See [SKILL.md](trend-analisis/SKILL.md) for the agent's operating instructions.

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
