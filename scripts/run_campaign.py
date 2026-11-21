import json
import os

from src.campaign_service import CampaignInvite, CampaignService, build_client


def main() -> None:
    recipient = os.environ.get("CAMPAIGN_EMAIL_TO")
    if not recipient:
        raise SystemExit("CAMPAIGN_EMAIL_TO is required")
    service = CampaignService(build_client())
    invite = CampaignInvite(
        player_email=recipient,
        subject="Your arena season invite",
        html="<h1>Arena season</h1><p>Your player-created banner is ready for review.</p>",
    )
    message_id = service.invite_player(invite)
    item = service.moderation_item(invite, message_id)
    print(json.dumps({"message_id": message_id, "moderation": item.__dict__ if item else None}))


if __name__ == "__main__":
    main()
