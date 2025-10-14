# Backup Operations

Duplicati ships with the Docker Compose stack to safeguard the PostgreSQL
cluster, optional Redis cache, and the CSV rate tables used by Quote Tool's
pricing engine. The container persists its configuration database, exported job
files, and run history beneath `./data/duplicati` on the host (mounted to
`/config` inside the container). Keeping that directory in your server backups
retains schedules, destination credentials, and encryption settings after
upgrades or rebuilds.

## Automating job exports and imports

Operations teams can automate configuration drift checks by exporting Duplicati
jobs with the bundled CLI. Run the commands from the repository root so they
inherit the Compose project context:

```bash
docker compose --profile backup exec duplicati duplicati-cli help export
```

The help output confirms the parameter order for your installed version. A
typical export workflow writes the job definition (including credentials) into
`/config/backups/` where it is captured by your server snapshots:

```bash
# Replace "Quote Tool production" with your job name.
docker compose --profile backup exec duplicati duplicati-cli export \
  "Quote Tool production" "/config/backups/quote-tool.json" \
  --include-secrets=true
```

Store the exported JSON in version control or a secret manager to track
configuration drift between environments. To bootstrap a new server, import the
saved definition and immediately update the encryption passphrase if your
security policy requires rotation:

```bash
# Import the exported job and re-run the destination test afterwards.
docker compose --profile backup exec duplicati duplicati-cli import \
  "/config/backups/quote-tool.json"
```

Follow up with `duplicati-cli list-broken-files "Quote Tool production"` (via
`docker compose exec`) or the web UI's *Run now* button to confirm the job still
reaches its destination.

## Retention guidance

The deployment guide recommends enabling **Smart backup retention** with 7 daily,
4 weekly, and 12 monthly versions. Adjust these values to satisfy your
organization's recovery point objectives—Duplicati will automatically collapse
older versions into the requested cadence. Storing the retention policy under
*Options → Settings* keeps it synchronized with the exported JSON above.

If you need more stringent compliance windows, layer Duplicati's retention with
cloud-provider lifecycle policies (for example, Amazon S3 Glacier transitions or
Azure Blob immutability timers) so unexpected deletions cannot remove every
version.

## Monitoring and health

- `docker compose ps duplicati` reports the health-check status driven by the
  Compose file. An `unhealthy` container indicates the UI failed to respond at
  `https://127.0.0.1:8200/ngax/index.html` during the last probe.
- `docker compose logs -f duplicati` tails service output, while detailed job
  histories accumulate in `data/duplicati/logs/`.
- Configure Duplicati's built-in email or webhook notifications so production
  schedules alert your monitoring stack. The *Settings → Send notifications*
  wizard supports SMTP, webhook URLs, and integrations like Slack.

## Firewalling and access controls

The Compose file binds the Duplicati UI to `127.0.0.1:8200`. Maintain a host
firewall (e.g., `ufw` or cloud security groups) that blocks external access to
this port and require administrators to reach it via SSH tunnelling or your
bastion host. When exposing the UI through a reverse proxy, enforce SSO or
mutual TLS so only trusted engineers can modify backup jobs.

Combine these operational practices with the runbook in
[`DEPLOYMENT.md`](../DEPLOYMENT.md#backups) to keep Quote Tool's data and rate
assets restorable.
