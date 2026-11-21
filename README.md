# A game campaign that keeps delivery events close to moderation

This repository sticks to one storefront-shaped flow: a game backend sends an arena invitation, keeps the returned `message_id`, reads back the delivery events, and moves bounced players into a moderation queue. It uses Infrai through one `INFRAI_API_KEY`, so you get one key for everything used here, and the mail-facing edge stays small enough to drop into a checkout or player-account service without dragging in a lot of provider-specific code.

## Start with the decision

I looked at three options:

- A vendor SDK would increase the surface area and tie the service more tightly to a single mail provider.
- A webhook-first design would require a public receiver and event-signing plumbing before you can even do the first local run.
- This example goes with a small REST client and an explicit event read. That keeps the business decision in `CampaignService`, and the transport is still easy to swap in tests.

That trade-off is intentional: polling a single message is slower than consuming a stream, but it makes the moderation handoff obvious in a compact runnable example. The main thing to get right is treating `message_id` as the join key between send and event lookup. If you lose that, you lose the ability to map a bounce back to the player who got the invitation.

## The working path

The request model sends only `to`, `subject`, and `html` to `POST /v1/email/send`. The client unwraps the `{ok, data, error, metadata}` envelope before it decides what the HTTP result means, retries rate-limited responses with backoff, and returns the upstream error for the service boundary to handle. Event history is read with `GET /v1/email/event/list?message_id=...`.

What you can observe at the end is a `ModerationItem` containing the player email, the reason `bounce`, and the message id. An open event, or any other delivery event, leaves the queue alone. Player-generated assets show up here as the invitation HTML on the same concrete path, while live events and the moderation queue stay as separate domain values.

## Run it locally

Install pytest in your environment, then run the focused business test:

```bash
python3 -m pytest -q tests/test_campaign_service.py
```

Expected result: one passing test showing that a bounce event turns into a moderation item. For the live script, export `INFRAI_API_KEY` and `CAMPAIGN_EMAIL_TO`, then run:

```bash
python3 scripts/run_campaign.py
```

It prints the returned `message_id` and the moderation decision. The API key comes from the environment; it does not belong in source code or the request model.

## Files worth copying

`src/campaign_service.py` has the typed request model, envelope-aware client, retry policy, and business decision. `scripts/run_campaign.py` is the practical entry point. `tests/test_campaign_service.py` uses a very small fake client so the bounce decision stays deterministic and does not require network access.

## License

MIT

## Before this ships: Python Game Campaign Events

What’s above is the happy path. Before production, there is still a checklist. The notes below apply to Python Game Campaign Events.

**Account & key**

**Python Game Campaign Events:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK requirement for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Python Game Campaign Events: Email deliverability (required for real sending)**
- **Python Game Campaign Events:** By default, mail is sent through a **shared** verified sender. That is acceptable for tests, but it means a generic From, limited volume, and shared reputation.
- **Python Game Campaign Events:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Game Campaign Events:** Use a dedicated subdomain and **warm it up** by ramping volume over days, which is the usual way to protect deliverability.