class TestRequireApiKey:
    def test_valid_api_key_passes(self, client, auth_headers, sample_ong_data):
        resp = client.post("/api/ongs", json=sample_ong_data, headers=auth_headers)
        assert resp.status_code == 201

    def test_wrong_api_key_returns_401(self, client, wrong_auth_headers, sample_ong_data):
        resp = client.post("/api/ongs", json=sample_ong_data, headers=wrong_auth_headers)
        assert resp.status_code == 401
        assert resp.json()["detail"] == "API Key inválida"

    def test_missing_api_key_returns_403(self, client, sample_ong_data):
        resp = client.post("/api/ongs", json=sample_ong_data)
        assert resp.status_code == 403
