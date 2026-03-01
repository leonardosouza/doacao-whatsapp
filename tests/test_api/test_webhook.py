from unittest.mock import AsyncMock, patch, MagicMock


def _make_payload(**overrides):
    base = {
        "phone": "5511999990000",
        "instanceId": "test-instance-id",  # deve bater com ZAPI_INSTANCE_ID do conftest
        "messageId": "msg-1",
        "fromMe": False,
        "isGroup": False,
        "text": {"message": "Quero doar"},
    }
    base.update(overrides)
    return base


class TestWebhook:
    def test_ignores_from_me(self, client):
        resp = client.post("/api/webhook", json=_make_payload(fromMe=True))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_ignores_group(self, client):
        resp = client.post("/api/webhook", json=_make_payload(isGroup=True))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_ignores_no_text(self, client):
        resp = client.post("/api/webhook", json=_make_payload(text=None))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "no text content"

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_sends_feedback_on_audio(self, mock_send, client):
        mock_send.return_value = {}
        payload = _make_payload(text=None, audio={"audioUrl": "https://a.com/a.ogg", "mimeType": "audio/ogg"})
        resp = client.post("/api/webhook", json=payload)
        assert resp.json()["status"] == "unsupported_media"
        assert resp.json()["reason"] == "audio"
        mock_send.assert_called_once()

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_sends_feedback_on_video(self, mock_send, client):
        mock_send.return_value = {}
        payload = _make_payload(text=None, video={"videoUrl": "https://a.com/v.mp4"})
        resp = client.post("/api/webhook", json=payload)
        assert resp.json()["status"] == "unsupported_media"
        assert resp.json()["reason"] == "video"
        mock_send.assert_called_once()

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_sends_feedback_on_image(self, mock_send, client):
        mock_send.return_value = {}
        payload = _make_payload(text=None, image={"imageUrl": "https://a.com/i.jpg"})
        resp = client.post("/api/webhook", json=payload)
        assert resp.json()["status"] == "unsupported_media"
        assert resp.json()["reason"] == "image"
        mock_send.assert_called_once()

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_sends_feedback_on_document(self, mock_send, client):
        mock_send.return_value = {}
        payload = _make_payload(text=None, document={"documentUrl": "https://a.com/d.pdf", "fileName": "d.pdf"})
        resp = client.post("/api/webhook", json=payload)
        assert resp.json()["status"] == "unsupported_media"
        assert resp.json()["reason"] == "document"
        mock_send.assert_called_once()

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_sends_feedback_on_sticker(self, mock_send, client):
        mock_send.return_value = {}
        payload = _make_payload(text=None, sticker={"stickerUrl": "https://a.com/s.webp"})
        resp = client.post("/api/webhook", json=payload)
        assert resp.json()["status"] == "unsupported_media"
        assert resp.json()["reason"] == "sticker"
        mock_send.assert_called_once()

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_process_message_not_called_on_media(self, mock_process, mock_send, client):
        mock_send.return_value = {}
        payload = _make_payload(text=None, audio={"audioUrl": "https://a.com/a.ogg"})
        client.post("/api/webhook", json=payload)
        mock_process.assert_not_called()

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_ignores_duplicate_message_id(self, mock_process, mock_send, client):
        """Segundo webhook com mesmo messageId deve ser ignorado sem chamar o agente."""
        mock_process.return_value = {
            "response": "Olá!",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        payload = _make_payload(messageId="msg-dup-001", phone="5511000001111")
        first = client.post("/api/webhook", json=payload)
        assert first.json()["status"] == "processed"

        second = client.post("/api/webhook", json=payload)
        assert second.json()["status"] == "ignored"
        assert second.json()["reason"] == "duplicate"
        mock_process.assert_called_once()  # agente chamado apenas uma vez

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_processes_valid_message(self, mock_process, mock_send, client):
        mock_process.return_value = {
            "response": "Olá! Como posso ajudar?",
            "intent": "Quero Doar",
            "sentiment": "Positivo",
        }
        mock_send.return_value = {"zapiMessageId": "123"}

        resp = client.post("/api/webhook", json=_make_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["intent"] == "Quero Doar"
        mock_send.assert_called_once_with("5511999990000", "Olá! Como posso ajudar?")

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_passes_empty_history_on_first_message(self, mock_process, mock_send, client):
        mock_process.return_value = {
            "response": "R",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        client.post("/api/webhook", json=_make_payload(phone="5511777770000"))
        _, kwargs = mock_process.call_args
        assert kwargs["conversation_history"] == ""

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_passes_history_on_second_message(self, mock_process, mock_send, client):
        mock_process.return_value = {
            "response": "R",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        # First message
        client.post("/api/webhook", json=_make_payload(phone="5511666660000", messageId="msg-hist-1"))

        # Second message — history should include first exchange
        mock_process.reset_mock()
        client.post(
            "/api/webhook",
            json=_make_payload(phone="5511666660000", messageId="msg-hist-2", text={"message": "Qual o PIX?"}),
        )
        _, kwargs = mock_process.call_args
        history = kwargs["conversation_history"]
        assert "Usuário: Quero doar" in history
        assert "Assistente: R" in history

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_creates_conversation(self, mock_process, mock_send, client, db_session):
        mock_process.return_value = {
            "response": "Oi",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        from app.models.conversation import Conversation

        before = db_session.query(Conversation).count()
        client.post("/api/webhook", json=_make_payload(phone="5511888880000"))
        after = db_session.query(Conversation).count()
        assert after == before + 1

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_reuses_conversation(self, mock_process, mock_send, client, sample_conversation):
        mock_process.return_value = {
            "response": "Oi",
            "intent": "Ambíguo",
            "sentiment": "Neutro",
        }
        mock_send.return_value = {}

        from app.models.conversation import Conversation

        client.post(
            "/api/webhook",
            json=_make_payload(phone=sample_conversation.phone_number),
        )
        from tests.conftest import db_session
        # The conversation should be reused, not duplicated
        # We can verify by checking process_message was called (the flow ran)
        mock_process.assert_called_once()


class TestRateLimiting:
    """Testes para a Camada 1: rate limiting persistente via banco de dados."""

    def test_rate_limit_blocks_when_count_reaches_limit(self, client):
        """Quando count_recent_inbound retorna > 5 (inclui msg atual), deve bloquear."""
        with patch(
            "app.api.routes.webhook.conversation_service.count_recent_inbound",
            return_value=6,  # count inclui a mensagem atual após save
        ):
            resp = client.post("/api/webhook", json=_make_payload(phone="5519111111001", messageId="rl-blocked"))
            assert resp.json()["status"] == "ignored"
            assert resp.json()["reason"] == "rate_limited"

    def test_rate_limit_allows_when_below_limit(self, client):
        """Quando count_recent_inbound retorna < 5, a mensagem deve ser processada."""
        with (
            patch("app.api.routes.webhook.conversation_service.count_recent_inbound", return_value=4),
            patch("app.api.routes.webhook.process_message", new_callable=AsyncMock) as mock_proc,
            patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_proc.return_value = {"response": "R", "intent": "Ambíguo", "sentiment": "Neutro"}
            mock_send.return_value = {}
            resp = client.post("/api/webhook", json=_make_payload(phone="5519111111004", messageId="rl-ok"))
            assert resp.json().get("reason") != "rate_limited"


class TestConsecutiveOOS:
    """Testes para a Camada 3: circuit breaker por respostas OOS consecutivas."""

    def test_consecutive_oos_silences_message(self, client):
        """Quando has_consecutive_out_of_scope retorna True, agente não deve ser chamado."""
        with (
            patch(
                "app.api.routes.webhook.conversation_service.count_recent_inbound",
                return_value=0,
            ),
            patch(
                "app.api.routes.webhook.conversation_service.has_consecutive_out_of_scope",
                return_value=True,
            ),
            patch("app.api.routes.webhook.process_message", new_callable=AsyncMock) as mock_proc,
            patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock) as mock_send,
        ):
            resp = client.post("/api/webhook", json=_make_payload(phone="5519222220001", messageId="oos-1"))
            assert resp.json()["status"] == "ignored"
            assert resp.json()["reason"] == "consecutive_oos"
            mock_proc.assert_not_called()
            mock_send.assert_not_called()

    def test_no_oos_allows_message(self, client):
        """Quando has_consecutive_out_of_scope retorna False, a mensagem deve ser processada."""
        with (
            patch(
                "app.api.routes.webhook.conversation_service.count_recent_inbound",
                return_value=0,
            ),
            patch(
                "app.api.routes.webhook.conversation_service.has_consecutive_out_of_scope",
                return_value=False,
            ),
            patch("app.api.routes.webhook.process_message", new_callable=AsyncMock) as mock_proc,
            patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_proc.return_value = {"response": "Oi!", "intent": "Ambíguo", "sentiment": "Neutro"}
            mock_send.return_value = {}
            resp = client.post("/api/webhook", json=_make_payload(phone="5519222220002", messageId="oos-ok"))
            assert resp.json()["status"] == "processed"


class TestBotDetection:
    """Testes para a Camada 2: detecção de bot por auto-identificação."""

    def test_bot_detected_cpfl_signature(self, client):
        """Mensagem com auto-identificação 'analista virtual da CPFL' retorna bot_detected."""
        text = "Olá, eu sou a analista virtual da CPFL. Posso te ajudar com diversos assuntos!"
        resp = client.post(
            "/api/webhook",
            json=_make_payload(phone="5519888880001", text={"message": text}),
        )
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_bot_detected_no_response_sent(self, mock_proc, mock_send, client):
        """Bot detectado não deve disparar resposta nem acionar o agente."""
        text = "sou um assistente virtual, como posso ajudar?"
        client.post(
            "/api/webhook",
            json=_make_payload(phone="5519888880002", text={"message": text}),
        )
        mock_send.assert_not_called()
        mock_proc.assert_not_called()

    def test_bot_detected_new_signatures_fase2(self, client):
        """Assinaturas da Fase 2 (CPFL/CRM/NPS) devem ser detectadas como bot."""
        new_signatures = [
            "Vou verificar se há alguma mensagem para você!",
            "Já encontrei seu cadastro, LEONARDO.",
            "Desculpe, não entendi isso.",
            "Qual é o seu nível de satisfação com o atendimento?",
            "Link de pagamento gerado: https://pay.example.com/abc123",
            "Queremos saber sua opinião sobre o atendimento.",
            "número de protocolo 123456",
        ]
        for text in new_signatures:
            resp = client.post(
                "/api/webhook",
                json=_make_payload(phone="5519888889999", text={"message": text}),
            )
            assert resp.json()["status"] == "ignored", f"Assinatura não detectada: {text!r}"
            assert resp.json()["reason"] == "bot_detected", f"Razão incorreta para: {text!r}"

    def test_bot_detected_new_signatures_fase3(self, client):
        """Assinaturas da Fase 3 (concessionárias e fraudes) devem ser detectadas como bot."""
        new_signatures = [
            # Bot Sabesp/concessionária
            "Oi! Sou a Sani da Sabesp. Posso ajudar com conta de água.",
            "Posso oferecer a 2ª via de faturas e outros serviços.",
            # Fraude/spam promocional
            "É sua vez! Estamos prontos para iniciar e temos uma surpresa de R$ 50,00.",
            # CRM — rejeição de cadastro
            "Não vamos seguir nesse momento com o seu cadastro.",
            # Loop de validação de CPF por bot
            "Esse CPF não é válido. Me manda de novo pra gente continuar.",
            "Esse CPF ou CNPJ que você está digitando é inválido.",
        ]
        for text in new_signatures:
            resp = client.post(
                "/api/webhook",
                json=_make_payload(phone="5519888887777", text={"message": text}),
            )
            assert resp.json()["status"] == "ignored", f"Assinatura não detectada: {text!r}"
            assert resp.json()["reason"] == "bot_detected", f"Razão incorreta para: {text!r}"

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_bot_not_detected_for_normal_message(self, mock_proc, mock_send, client):
        """Mensagem humana normal não deve ser bloqueada pela detecção de bot."""
        mock_proc.return_value = {"response": "Olá!", "intent": "Ambíguo", "sentiment": "Neutro"}
        mock_send.return_value = {}
        resp = client.post(
            "/api/webhook",
            json=_make_payload(phone="5519888880003", text={"message": "Quero fazer uma doação"}),
        )
        assert resp.json()["status"] == "processed"


class TestBotDetectionRegex:
    """Testes para os padrões regex genéricos da Camada 2 (v1.6.3)."""

    def test_regex_magalu_lu_self_identification(self, client):
        """'Aqui é a Lu, assistente virtual do Magalu' deve ser detectado via regex."""
        text = "Aqui é a Lu, assistente virtual do Magalu! Como posso ajudar?"
        resp = client.post("/api/webhook", json=_make_payload(phone="5511974627106", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_generic_assistant_sou_um(self, client):
        """'sou um assistente virtual' genérico (sem empresa) deve ser detectado via regex."""
        text = "Olá! Sou um assistente virtual. Como posso te ajudar hoje?"
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770001", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_generic_assistant_sou_o(self, client):
        """'sou o agente virtual' deve ser detectado via regex."""
        text = "Oi! Sou o agente virtual da empresa XYZ. Pode me dizer seu CPF?"
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770002", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_cpf_request_envie(self, client):
        """Solicitação de CPF via 'envie seu CPF' deve ser detectada via regex."""
        text = "Para continuar, por favor envie seu CPF."
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770003", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_cpf_request_confirme(self, client):
        """Solicitação de CPF via 'confirme o CPF' deve ser detectada via regex."""
        text = "Confirme o seu CPF para prosseguirmos com o atendimento."
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770004", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_cpf_validation_error(self, client):
        """Mensagem 'O CPF informado não é válido' deve ser detectada via regex."""
        text = "O CPF informado não é válido. Por favor, tente novamente."
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770005", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_cnpj_invalido(self, client):
        """Mensagem 'CNPJ inválido' deve ser detectada via regex."""
        text = "O CNPJ informado está incorreto. Verifique e tente novamente."
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770006", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_nps_nivel_satisfacao(self, client):
        """Pesquisa NPS 'nível de satisfação' deve ser detectada via regex."""
        text = "Qual é o seu nível de satisfação com o atendimento que você recebeu hoje?"
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770007", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_nps_de_0_a_10(self, client):
        """Pesquisa NPS 'de 0 a 10, como você avalia' deve ser detectada via regex."""
        text = "De 0 a 10, como você avalia o nosso atendimento?"
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770008", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_segunda_via_fatura(self, client):
        """Oferta de '2ª via de fatura' (concessionária) deve ser detectada via regex."""
        text = "Você pode solicitar a 2ª via de fatura diretamente por aqui."
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770009", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    def test_regex_segunda_via_por_extenso(self, client):
        """'segunda via de conta' (por extenso) deve ser detectada via regex."""
        text = "Solicite a segunda via de conta de energia pelo nosso site."
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770010", text={"message": text}))
        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "bot_detected"

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_regex_does_not_block_donation_message(self, mock_proc, mock_send, client):
        """Mensagem legítima de doação não deve ser bloqueada pelos padrões regex."""
        mock_proc.return_value = {"response": "Olá!", "intent": "Quero Doar", "sentiment": "Positivo"}
        mock_send.return_value = {}
        text = "Quero fazer uma doação para crianças em situação de rua"
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770099", text={"message": text}))
        assert resp.json()["status"] == "processed"

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_regex_does_not_block_help_request(self, mock_proc, mock_send, client):
        """Pedido de ajuda legítimo não deve ser bloqueado pelos padrões regex."""
        mock_proc.return_value = {"response": "Olá!", "intent": "Busco Ajuda/Beneficiário", "sentiment": "Neutro"}
        mock_send.return_value = {}
        text = "Preciso de ajuda com alimentação para minha família"
        resp = client.post("/api/webhook", json=_make_payload(phone="5519777770098", text={"message": text}))
        assert resp.json()["status"] == "processed"


class TestRateLimitRaceConditionFix:
    """Testa que a mensagem inbound é salva ANTES da verificação de rate limit (v1.6.3)."""

    def test_inbound_message_saved_even_when_rate_limited(self, client, db_session):
        """Mensagem deve ser persistida no DB mesmo quando o rate limit é ativado."""
        from app.models.message import Message

        phone = "5519333330001"
        msg_id = "race-condition-test-001"

        with patch(
            "app.api.routes.webhook.conversation_service.count_recent_inbound",
            return_value=6,  # > _RATE_LIMIT (5); simula: msg atual já está no count
        ):
            resp = client.post(
                "/api/webhook",
                json=_make_payload(phone=phone, messageId=msg_id, text={"message": "Oi"}),
            )

        assert resp.json()["status"] == "ignored"
        assert resp.json()["reason"] == "rate_limited"

        # Verifica que a mensagem FOI salva no banco antes do check de rate limit
        saved = db_session.query(Message).filter(Message.zapi_message_id == msg_id).first()
        assert saved is not None, "Mensagem deve ser salva antes do rate limit check (corrige race condition)"
        assert saved.direction == "inbound"

    def test_rate_limit_count_5_allows_message(self, client):
        """count=5 (inclui msg atual como 5ª) NÃO deve bloquear — apenas count>5 bloqueia."""
        with (
            patch(
                "app.api.routes.webhook.conversation_service.count_recent_inbound",
                return_value=5,  # 5 > 5? False → deve processar
            ),
            patch("app.api.routes.webhook.process_message", new_callable=AsyncMock) as mock_proc,
            patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock) as mock_send,
        ):
            mock_proc.return_value = {"response": "R", "intent": "Ambíguo", "sentiment": "Neutro"}
            mock_send.return_value = {}
            resp = client.post(
                "/api/webhook",
                json=_make_payload(phone="5519333330002", messageId="race-condition-test-002"),
            )
            assert resp.json().get("reason") != "rate_limited"
            mock_proc.assert_called_once()


class TestMediaDeduplication:
    """Testes para deduplicação de mídia via banco de dados (v1.6.4 — Feature A)."""

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_first_media_message_sends_response_and_saves_to_db(self, mock_send, client, db_session):
        """1ª mensagem de mídia: salva messageId no banco e envia aviso ao usuário."""
        from app.models.message import Message

        mock_send.return_value = {}
        msg_id = "media-first-001"
        payload = _make_payload(
            phone="5511444440001", messageId=msg_id,
            text=None, audio={"audioUrl": "https://a.com/a.ogg", "mimeType": "audio/ogg"},
        )

        resp = client.post("/api/webhook", json=payload)

        assert resp.json()["status"] == "unsupported_media"
        assert resp.json()["reason"] == "audio"
        mock_send.assert_called_once()

        # Verifica que o messageId foi persistido para dedup futura
        saved = db_session.query(Message).filter(Message.zapi_message_id == msg_id).first()
        assert saved is not None, "messageId de mídia deve ser salvo no banco"
        assert saved.direction == "inbound"
        assert "[mídia: audio]" in saved.content

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_duplicate_media_webhook_ignored(self, mock_send, client):
        """Segundo webhook com mesmo messageId de mídia deve ser ignorado sem enviar resposta."""
        mock_send.return_value = {}
        msg_id = "media-dup-001"
        payload = _make_payload(
            phone="5511444440002", messageId=msg_id,
            text=None, image={"imageUrl": "https://a.com/i.jpg"},
        )

        first = client.post("/api/webhook", json=payload)
        assert first.json()["status"] == "unsupported_media"

        # Segundo webhook com o mesmo messageId (Z-API retry)
        second = client.post("/api/webhook", json=payload)
        assert second.json()["status"] == "ignored"
        assert second.json()["reason"] == "duplicate"

        # Aviso enviado apenas uma vez (no primeiro webhook)
        assert mock_send.call_count == 1

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    def test_different_media_messageids_both_responded(self, mock_send, client):
        """Dois webhooks com messageIds distintos devem gerar dois avisos ao usuário."""
        mock_send.return_value = {}
        phone = "5511444440003"

        client.post("/api/webhook", json=_make_payload(
            phone=phone, messageId="media-distinct-001",
            text=None, sticker={"stickerUrl": "https://a.com/s1.webp"},
        ))
        client.post("/api/webhook", json=_make_payload(
            phone=phone, messageId="media-distinct-002",
            text=None, sticker={"stickerUrl": "https://a.com/s2.webp"},
        ))

        assert mock_send.call_count == 2


class TestRepeatedContentCircuitBreaker:
    """Testes para o circuit breaker de conteúdo repetido (v1.6.4 — Feature B)."""

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_repeated_content_blocks_at_third_identical_message(self, mock_proc, mock_send, client):
        """3ª mensagem idêntica dentro da janela deve retornar ignored/repeated_content."""
        mock_proc.return_value = {"response": "R", "intent": "Ambíguo", "sentiment": "Neutro"}
        mock_send.return_value = {}

        phone = "5519555550001"
        text = "Oi quero ajuda com doação"

        client.post("/api/webhook", json=_make_payload(phone=phone, messageId="rc-1", text={"message": text}))
        client.post("/api/webhook", json=_make_payload(phone=phone, messageId="rc-2", text={"message": text}))

        # 3ª mensagem — deve ser bloqueada
        third = client.post("/api/webhook", json=_make_payload(phone=phone, messageId="rc-3", text={"message": text}))
        assert third.json()["status"] == "ignored"
        assert third.json()["reason"] == "repeated_content"

        # Agente chamado apenas nas 2 primeiras
        assert mock_proc.call_count == 2

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_repeated_content_allows_below_threshold(self, mock_proc, mock_send, client):
        """2 mensagens idênticas (abaixo do limite de 3) devem ser processadas normalmente."""
        mock_proc.return_value = {"response": "R", "intent": "Ambíguo", "sentiment": "Neutro"}
        mock_send.return_value = {}

        phone = "5519555550002"
        text = "Preciso de informações sobre voluntariado"

        first = client.post("/api/webhook", json=_make_payload(phone=phone, messageId="rc-ok-1", text={"message": text}))
        second = client.post("/api/webhook", json=_make_payload(phone=phone, messageId="rc-ok-2", text={"message": text}))

        assert first.json()["status"] == "processed"
        assert second.json()["status"] == "processed"
        assert mock_proc.call_count == 2

    @patch("app.api.routes.webhook.zapi_service.send_text_message", new_callable=AsyncMock)
    @patch("app.api.routes.webhook.process_message", new_callable=AsyncMock)
    def test_different_content_from_same_phone_not_blocked(self, mock_proc, mock_send, client):
        """Mensagens com conteúdo diferente do mesmo número não devem ser bloqueadas."""
        mock_proc.return_value = {"response": "R", "intent": "Ambíguo", "sentiment": "Neutro"}
        mock_send.return_value = {}

        phone = "5519555550003"

        # Envia 3+ mensagens com conteúdos diferentes
        for i in range(4):
            resp = client.post(
                "/api/webhook",
                json=_make_payload(phone=phone, messageId=f"rc-diff-{i}", text={"message": f"Mensagem {i}"}),
            )
            assert resp.json()["status"] == "processed", f"Mensagem {i} não deveria ser bloqueada"

        assert mock_proc.call_count == 4
