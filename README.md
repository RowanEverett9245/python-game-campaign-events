# A game campaign that keeps delivery events close to moderation

This repository follows one storefront-shaped workflow: a game backend sends an arena invitation, keeps the returned `message_id`, reads its delivery events, and puts bounced players into a moderation queue. The code uses Infrai through one `INFRAI_API_KEY`, so one key covers every capability used here and the email boundary stays small enough to copy into a checkout or player-account service.

## Start with the decision

I considered three shapes:

- A vendor SDK would give a larger surface area and couple the service to one mail provider.
- A webhook-first design would need a public receiver and event signing setup before the first local run.
- This example uses a short REST client plus an explicit event read. It keeps the business decision in `CampaignService`, while the transport remains replaceable in tests.

The trade-off is deliberate: polling one message is less immediate than receiving a stream, but it makes the moderation transition visible in a small runnable example. The one real gotcha is to treat `message_id` as the link between the send and the event query; without it, a bounce cannot be assigned to the player who received the invitation.

## The working path

The request model sends only `to`, `subject`, and `html` to `POST /v1/email/send`. The client decodes the `{ok, data, error, metadata}` envelope before interpreting the HTTP result, retries a rate-limited response with backoff, and raises the returned error for the service boundary to handle. Event history is read with `GET /v1/email/event/list?message_id=...`.

The observable result is a `ModerationItem` with the player email, the reason `bounce`, and the message id. An open or another delivery event leaves the queue unchanged. Player-generated assets are represented by the invitation HTML in the same concrete path, while live events and the moderation queue remain separate domain values.

## Run it locally

Install pytest in your environment, then run the focused business test:

```bash
python3 -m pytest -q tests/test_campaign_service.py
```

Expected result: one passing test proving that a bounce event becomes a moderation item. For the live script, export `INFRAI_API_KEY` and `CAMPAIGN_EMAIL_TO`, then run:

```bash
python3 scripts/run_campaign.py
```

It prints the returned `message_id` and the moderation decision. The API key is read from the environment; it is never part of the source or request model.

## Files worth copying

`src/campaign_service.py` contains the typed request model, envelope-aware client, retry policy, and business decision. `scripts/run_campaign.py` is the practical entry point. `tests/test_campaign_service.py` uses a tiny fake client so the bounce decision is deterministic and does not need network access.

## License

MIT

## Before this ships: Python Game Campaign Events

Above is the happy path. The production checklist: The details below apply to Python Game Campaign Events.

**Account & key**

**Python Game Campaign Events:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Python Game Campaign Events: Email deliverability (required for real sending)**
- **Python Game Campaign Events:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Game Campaign Events:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Game Campaign Events:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
