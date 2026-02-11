from unittest.mock import MagicMock

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


class TestGetConversationHistory:
    def test_empty_history(self, db_session, sample_conversation):
        result = conversation_service.get_conversation_history(db_session, sample_conversation)
        assert result == []

    def test_excludes_message_by_id(self, db_session, sample_conversation):
        msg1 = conversation_service.save_message(db_session, sample_conversation, "inbound", "Msg 1")
        msg2 = conversation_service.save_message(db_session, sample_conversation, "outbound", "Resp 1")
        msg3 = conversation_service.save_message(db_session, sample_conversation, "inbound", "Msg atual")
        result = conversation_service.get_conversation_history(
            db_session, sample_conversation, exclude_message_id=msg3.id
        )
        assert len(result) == 2
        contents = {m.content for m in result}
        assert "Msg 1" in contents
        assert "Resp 1" in contents
        assert "Msg atual" not in contents

    def test_without_exclude_returns_all(self, db_session, sample_conversation):
        conversation_service.save_message(db_session, sample_conversation, "inbound", "Msg 1")
        conversation_service.save_message(db_session, sample_conversation, "outbound", "Resp 1")
        result = conversation_service.get_conversation_history(db_session, sample_conversation)
        assert len(result) == 2

    def test_respects_limit(self, db_session, sample_conversation):
        for i in range(10):
            direction = "inbound" if i % 2 == 0 else "outbound"
            conversation_service.save_message(db_session, sample_conversation, direction, f"Msg {i}")
        result = conversation_service.get_conversation_history(
            db_session, sample_conversation, limit=4
        )
        assert len(result) == 4

    def test_only_returns_messages_from_conversation(self, db_session):
        conv1 = Conversation(phone_number="5511111111111")
        conv2 = Conversation(phone_number="5522222222222")
        db_session.add_all([conv1, conv2])
        db_session.commit()
        conversation_service.save_message(db_session, conv1, "inbound", "Conv1 msg")
        conversation_service.save_message(db_session, conv2, "inbound", "Conv2 msg")
        result = conversation_service.get_conversation_history(db_session, conv1)
        assert len(result) == 1
        assert result[0].content == "Conv1 msg"


class TestFormatHistory:
    def test_empty_messages(self):
        assert conversation_service.format_history([]) == ""

    def test_formats_inbound_outbound(self):
        msg1 = MagicMock(direction="inbound", content="Oi")
        msg2 = MagicMock(direction="outbound", content="Olá!")
        result = conversation_service.format_history([msg1, msg2])
        assert result == "Usuário: Oi\nAssistente: Olá!"

    def test_single_message(self):
        msg = MagicMock(direction="inbound", content="Quero doar")
        result = conversation_service.format_history([msg])
        assert result == "Usuário: Quero doar"
