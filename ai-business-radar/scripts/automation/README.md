# Nightly automation wrappers

These wrappers separate network fetch from local analysis generation.

```bash
# Network fetch only. Writes logs to outputs/automation/<asof>/.
scripts/automation/daily_fetch.sh YYYY-MM-DD

# Local-only feature/research/brief generation.
scripts/automation/build_and_brief.sh YYYY-MM-DD

# Morning diagnostic and local retry.
scripts/automation/retry_doctor.sh YYYY-MM-DD
```

## Install LaunchAgents manually

```bash
REPO_ROOT="$(cd ../../.. && pwd)"   # run from ai-business-radar/scripts/automation
sed "s|__REPO_ROOT__|$REPO_ROOT|g" com.radar.data-fetch.plist.template \
  > ~/Library/LaunchAgents/com.radar.data-fetch.plist
sed "s|__REPO_ROOT__|$REPO_ROOT|g" com.radar.build-and-brief.plist.template \
  > ~/Library/LaunchAgents/com.radar.build-and-brief.plist
sed "s|__REPO_ROOT__|$REPO_ROOT|g" com.radar.retry-doctor.plist.template \
  > ~/Library/LaunchAgents/com.radar.retry-doctor.plist

launchctl load ~/Library/LaunchAgents/com.radar.data-fetch.plist
launchctl load ~/Library/LaunchAgents/com.radar.build-and-brief.plist
launchctl load ~/Library/LaunchAgents/com.radar.retry-doctor.plist
```

Stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.radar.data-fetch.plist
launchctl unload ~/Library/LaunchAgents/com.radar.build-and-brief.plist
launchctl unload ~/Library/LaunchAgents/com.radar.retry-doctor.plist
```

The scripts do not print API keys or provider raw bodies. They rely on existing
`radar` commands for redaction and scope control.

`daily_fetch.sh` currently fetches:

- EDINET DB companies raw.
- EDINET DB financials raw in offset/limit batches.
- J-Quants Premium Bulk raw for `/equities/master`, `/equities/bars/daily`,
  `/fins/summary`, `/fins/dividend` for the requested asof date.
- Optional J-Quants watchlist REST when `data/metadata/jquants_watchlist.txt`
  exists.

It does not build features, research queues, evidence, LLM packets, rankings,
or trade instructions.
