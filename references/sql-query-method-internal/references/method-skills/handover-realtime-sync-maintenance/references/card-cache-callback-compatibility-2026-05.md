# 2026-05 card cache / old-card callback compatibility

Context: the handover dashboard card top metrics were changed from four display metrics (`当前加微率`, `选期率`, `选期加微率`, `衔接课开课率`) to three display metrics: `开课率 / 加微率 / 选期率`.

Files involved:
- `~/.hermes/scripts/handover_team_report_card.py`
- `~/.hermes/scripts/handover_daily_card.py`
- gateway callback handler: `~/.hermes/hermes-agent/gateway/platforms/feishu.py`, `_handle_handover_daily_page_card_action` / `_build_handover_daily_page_card`
- cache: `~/.hermes/cache/handover_daily_card_page_cache.json`

Observed sequence:
1. Code-only change succeeded and local mock validation showed top titles `['开课率', '加微率', '选期率']`.
2. User later requested cache-only refresh, not a new push.
3. The cache refresh uploaded five SKU images and rewrote `handover_daily_card_page_cache.json`; no `message_id` was produced.
4. After cache refresh, clicking an old card appeared to do nothing.
5. Gateway logs showed the click arrived but rebuild failed:
   - `Failed to build handover daily page card for sku=声乐: 'selected_wechat'`
6. Before cache refresh, old-card clicks had succeeded; after cache refresh, the refreshed cached dataset no longer carried `selected_wechat` in `datasets[*]['totals']`.

Key lesson:
- Old Feishu cards are not self-contained after click. The button payload identifies the target SKU and may carry an image key, but the callback rebuilds the page from the current cache and current card-service code.
- Therefore a cache-only refresh can break old-card pagination if the cache schema or cached metric inventory changes incompatibly.

Preferred future fix pattern:
- For presentation-only changes, separate display order from cached metric inventory.
- Keep compatibility-only metrics, such as `selected_wechat`, in `datasets[*]['totals']` even when not displayed at the top, or make `total_metric(...)` callers tolerant of missing metrics.
- Update only render/status/table helpers to choose the three displayed metrics.
- If the fix touches gateway callback code under `~/.hermes/hermes-agent/gateway/platforms/feishu.py`, restart the active Feishu gateway profile after verifying the local build path. A local direct call to `_build_handover_daily_page_card(...)` can prove the code path is fixed, but the live button callback will keep failing until the long-lived gateway process has loaded the new code.
- Verify the actual serving profile, not only the default log. For the Feishu group gateway, check `hermes gateway status --profile feishu-group` and `~/.hermes/profiles/feishu-group/logs/gateway.log`; the default `~/.hermes/logs/gateway.log` can still contain the last failure from an older/default process and may mislead diagnosis.
- If `hermes gateway restart --profile feishu-group` hangs or is inconclusive, use launchd directly and then verify PID/start time plus WebSocket connection:
  ```bash
  uid=$(id -u)
  launchctl kickstart -k gui/$uid/ai.hermes.gateway-feishu-group
  hermes gateway status --profile feishu-group
  tail -80 ~/.hermes/profiles/feishu-group/logs/gateway.log
  ```
- Verify both:
  1. new display titles are `开课率 / 加微率 / 选期率`
  2. an old/new-card-style callback rebuild can run from the refreshed cache without requiring a new card push
  3. after the gateway restart, a real button click logs `Patched handover daily card ... to sku=...` rather than another `Failed to build ... 'selected_wechat'`.

No-push diagnostic checklist:
- Do not send a new Feishu card when the user says “仅排查，不要发新的”.
- Check gateway process state.
- Check cache mtime, `data_updated_at`, `sku_image_keys`, and cached `datasets[*]['totals']` keys/titles.
- Search logs for:
  - `Patched handover daily card`
  - `Failed to build handover daily page card`
  - `Failed to patch handover daily card`
  - missing-key exceptions such as `'selected_wechat'`
- Distinguish event delivery from rebuild failure: if logs show `Failed to build...`, the button event reached Hermes; the issue is service/cache compatibility, not no callback delivery.
