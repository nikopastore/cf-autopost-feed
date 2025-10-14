# Career Forge Autopost Feed

## Engagement Analytics

1. Add a GitHub Actions secret named `BUFFER_TOKEN` containing your Buffer access token.
2. Find profile IDs with `BUFFER_TOKEN=... python tools/buffer_list_profiles.py` and copy each `id` value.
3. Edit `.github/workflows/metrics.yml` to replace `PROFILE_IDS` with the comma-separated Buffer profile IDs.
4. Manually run the `Engagement Metrics` workflow once, then view `analytics/dashboard.html` on GitHub Pages to explore totals and charts.

*Note:* If you haven’t enabled Buffer API access yet, the workflow still succeeds by writing sample engagement metrics so you can test the dashboard. Once you add real credentials, rerun the workflow to replace the sample data.
