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
        assert msg.zapi_message_id is None

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

    def test_save_message_with_zapi_message_id(self, db_session, sample_conversation):
        msg = conversation_service.save_message(
            db_session,
            conversation=sample_conversation,
            direction="inbound",
            content="Oi",
            zapi_message_id="zapi-abc-123",
        )
        assert msg.zapi_message_id == "zapi-abc-123"


class TestIsDuplicateMessage:
    def test_returns_false_for_unknown_id(self, db_session):
        assert conversation_service.is_duplicate_message(db_session, "id-desconhecido") is False

    def test_returns_true_after_saving(self, db_session, sample_conversation):
        conversation_service.save_message(
            db_session,
            conversation=sample_conversation,
            direction="inbound",
            content="Oi",
            zapi_message_id="zapi-dup-001",
        )
        assert conversation_service.is_duplicate_message(db_session, "zapi-dup-001") is True


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


class TestCountRecentInbound:
    def test_returns_zero_when_none(self, db_session, sample_conversation):
        count = conversation_service.count_recent_inbound(db_session, sample_conversation.phone_number)
        assert count == 0

    def test_counts_inbound_messages(self, db_session, sample_conversation):
        conversation_service.save_message(db_session, sample_conversation, "inbound", "Msg 1")
        conversation_service.save_message(db_session, sample_conversation, "inbound", "Msg 2")
        count = conversation_service.count_recent_inbound(db_session, sample_conversation.phone_number)
        assert count == 2

    def test_does_not_count_outbound(self, db_session, sample_conversation):
        conversation_service.save_message(db_session, sample_conversation, "inbound", "Msg 1")
        conversation_service.save_message(db_session, sample_conversation, "outbound", "Resp 1")
        count = conversation_service.count_recent_inbound(db_session, sample_conversation.phone_number)
        assert count == 1

    def test_respects_window(self, db_session, sample_conversation):
        from datetime import UTC, datetime, timedelta
        from app.models.message import Message as MsgModel
        # Insere mensagem com timestamp fora da janela
        old_msg = MsgModel(
            conversation_id=sample_conversation.id,
            direction="inbound",
            content="Antiga",
        )
        db_session.add(old_msg)
        db_session.commit()
        # Força created_at para 2 minutos atrás
        db_session.query(MsgModel).filter(MsgModel.id == old_msg.id).update(
            {MsgModel.created_at: datetime.now(UTC) - timedelta(seconds=120)}
        )
        db_session.commit()
        # Janela de 60s: mensagem de 2min atrás não deve contar
        count = conversation_service.count_recent_inbound(
            db_session, sample_conversation.phone_number, window_seconds=60
        )
        assert count == 0


class TestHasConsecutiveOutOfScope:
    def test_returns_true_when_all_oos(self, db_session, sample_conversation):
        """3 OOS em 6 mensagens → acima do threshold → True."""
        for _ in range(3):
            conversation_service.save_message(
                db_session, sample_conversation, "outbound", "Desculpe", intent="Fora do Escopo"
            )
        assert conversation_service.has_consecutive_out_of_scope(db_session, sample_conversation.phone_number) is True

    def test_returns_false_when_below_threshold(self, db_session, sample_conversation):
        """2 OOS < threshold de 3 → False."""
        for _ in range(2):
            conversation_service.save_message(
                db_session, sample_conversation, "outbound", "Desculpe", intent="Fora do Escopo"
            )
        assert conversation_service.has_consecutive_out_of_scope(db_session, sample_conversation.phone_number) is False

    def test_returns_true_when_oos_intercalado_atinge_threshold(self, db_session, sample_conversation):
        """OOS intercalados com Ambíguo devem ativar o circuit breaker quando ≥ 3 no total.

        Replica o padrão do bot Sabesp: OOS → OOS → Ambíguo → OOS (3 OOS em 4 msgs = True).
        """
        intents = ["Fora do Escopo", "Fora do Escopo", "Ambíguo", "Fora do Escopo"]
        for intent in intents:
            conversation_service.save_message(
                db_session, sample_conversation, "outbound", "Msg", intent=intent
            )
        assert conversation_service.has_consecutive_out_of_scope(db_session, sample_conversation.phone_number) is True

    def test_returns_false_when_mixed_below_threshold(self, db_session, sample_conversation):
        """1 não-OOS + 2 OOS = 2 OOS < threshold de 3 → False."""
        conversation_service.save_message(
            db_session, sample_conversation, "outbound", "Oi", intent="Quero Doar"
        )
        conversation_service.save_message(
            db_session, sample_conversation, "outbound", "Desculpe", intent="Fora do Escopo"
        )
        conversation_service.save_message(
            db_session, sample_conversation, "outbound", "Desculpe", intent="Fora do Escopo"
        )
        assert conversation_service.has_consecutive_out_of_scope(db_session, sample_conversation.phone_number) is False


class TestUpdateUserProfile:
    def test_sets_name(self, db_session, sample_conversation):
        result = conversation_service.update_user_profile(
            db_session, sample_conversation, user_name="Maria"
        )
        assert result.user_name == "Maria"

    def test_persists_to_db(self, db_session, sample_conversation):
        conversation_service.update_user_profile(
            db_session, sample_conversation, user_name="Pedro"
        )
        db_session.expire(sample_conversation)
        refreshed = db_session.get(Conversation, sample_conversation.id)
        assert refreshed.user_name == "Pedro"


class TestHasRepeatedContent:
    """Testes para has_repeated_content() — circuit breaker de conteúdo repetido (v1.6.4)."""

    def test_returns_false_when_below_limit(self, db_session, sample_conversation):
        """2 mensagens com mesmo conteúdo, limit=3 → False."""
        for _ in range(2):
            conversation_service.save_message(
                db_session, sample_conversation, "inbound", "Oi tudo bem"
            )
        assert conversation_service.has_repeated_content(
            db_session, sample_conversation.phone_number, "Oi tudo bem", limit=3
        ) is False

    def test_returns_true_when_at_limit(self, db_session, sample_conversation):
        """3 mensagens idênticas com limit=3 → True."""
        for _ in range(3):
            conversation_service.save_message(
                db_session, sample_conversation, "inbound", "Quero doações"
            )
        assert conversation_service.has_repeated_content(
            db_session, sample_conversation.phone_number, "Quero doações", limit=3
        ) is True

    def test_different_phone_not_counted(self, db_session, sample_conversation):
        """Mensagens idênticas de outro número não devem interferir no count."""
        from app.models.conversation import Conversation as ConvModel
        other = ConvModel(phone_number="5522999990000")
        db_session.add(other)
        db_session.commit()
        for _ in range(3):
            conversation_service.save_message(db_session, other, "inbound", "Texto igual")
        # mesmo texto, mas de outro telefone → não deve bloquear sample_conversation.phone_number
        assert conversation_service.has_repeated_content(
            db_session, sample_conversation.phone_number, "Texto igual", limit=3
        ) is False

    def test_different_content_not_counted(self, db_session, sample_conversation):
        """Mensagens com conteúdo diferente do alvo não devem ser contadas."""
        for i in range(3):
            conversation_service.save_message(
                db_session, sample_conversation, "inbound", f"Mensagem diferente {i}"
            )
        assert conversation_service.has_repeated_content(
            db_session, sample_conversation.phone_number, "Outro conteúdo", limit=3
        ) is False

    def test_outbound_not_counted(self, db_session, sample_conversation):
        """Mensagens outbound com o mesmo conteúdo não devem ser contadas."""
        for _ in range(3):
            conversation_service.save_message(
                db_session, sample_conversation, "outbound", "Resposta repetida"
            )
        assert conversation_service.has_repeated_content(
            db_session, sample_conversation.phone_number, "Resposta repetida", limit=3
        ) is False

    def test_respects_window(self, db_session, sample_conversation):
        """Mensagens fora da janela de tempo não devem ser contadas."""
        from datetime import UTC, datetime, timedelta
        from app.models.message import Message as MsgModel

        # Insere 3 mensagens antigas (fora da janela de 60s)
        for i in range(3):
            old = MsgModel(
                conversation_id=sample_conversation.id,
                direction="inbound",
                content="Mensagem antiga",
            )
            db_session.add(old)
            db_session.commit()
            db_session.query(MsgModel).filter(MsgModel.id == old.id).update(
                {MsgModel.created_at: datetime.now(UTC) - timedelta(seconds=120)}
            )
            db_session.commit()

        # Dentro da janela (60s): count deve ser 0 → False
        assert conversation_service.has_repeated_content(
            db_session, sample_conversation.phone_number, "Mensagem antiga",
            limit=3, window_seconds=60,
        ) is False
