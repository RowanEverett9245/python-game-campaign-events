from src.campaign_service import CampaignInvite, CampaignService


class FakeClient:
    def send(self, invite):
        assert invite.player_email == "player@example.com"
        assert invite.html
        return {"message_id": "msg-42"}

    def events(self, message_id):
        assert message_id == "msg-42"
        return {"events": [{"type": "bounce"}]}


def test_bounced_player_enters_moderation_queue():
    invite = CampaignInvite("player@example.com", "Arena invite", "<p>Join</p>")
    item = CampaignService(FakeClient()).moderation_item(invite, "msg-42")
    assert item is not None
    assert item.reason == "bounce"
    assert item.message_id == "msg-42"
