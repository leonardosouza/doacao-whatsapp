from app.models.conversation import Conversation
from app.services import conversation_service


class TestGetOrCreateConversation:
    def test_creates_new_conversation(self, db_session):
        conv = conversation_service.get_or_create_conversation(db_session, "5511999990000")
        assert conv.phone_number == "5511999990000"
        assert conv.status == "active"
        assert conv.id is not None

    def test_returns_existing_active(self, db_session):
        conv1 = conversation_service.get_or_create_conversation(db_session, "5511999990000")
        conv2 = conversation_service.get_or_create_conversation(db_session, "5511999990000")
        assert conv1.id == conv2.id

    def test_creates_new_if_not_active(self, db_session):
        conv1 = conversation_service.get_or_create_conversation(db_session, "5511999990000")
        conv1.status = "closed"
        db_session.commit()
        conv2 = conversation_service.get_or_create_conversation(db_session, "5511999990000")
        assert conv1.id != conv2.id


class TestSaveMessage:
    def test_save_message(self, db_session, sample_conversation):
        msg = conversation_service.save_message(
            db_session,
            conversation=sample_conversation,
            direction="inbound",
            content="Olá",
        )
        assert msg.conversation_id == sample_conversation.id
        assert msg.direction == "inbound"
        assert msg.content == "Olá"
        assert msg.intent is None
        assert msg.sentiment is None

    def test_save_message_with_intent(self, db_session, sample_conversation):
        msg = conversation_service.save_message(
            db_session,
            conversation=sample_conversation,
            direction="outbound",
            content="Resposta",
            intent="Quero Doar",
            sentiment="Positivo",
        )
        assert msg.intent == "Quero Doar"
        assert msg.sentiment == "Positivo"
