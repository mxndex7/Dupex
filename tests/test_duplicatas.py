from datetime import date, timedelta

import pytest

from tests.conftest import duplicata_payload

URL = "/api/v1/duplicatas"


def criar(client, auth, **overrides):
    return client.post(URL, json=duplicata_payload(**overrides), headers=auth)


# --- criação ---------------------------------------------------------------------------------


def test_criar_duplicata(client, auth):
    response = criar(client, auth)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["numero"] == "DUP-001"
    assert body["valor"] == "1500.00"
    assert body["status"] == "emitida"
    assert body["data_emissao"] == date.today().isoformat()
    assert body["created_at"].endswith("Z") or "+00:00" in body["created_at"]


@pytest.mark.parametrize("valor", ["19.99", "0.01", "0.10", "1234567890.12"])
def test_valor_nao_perde_precisao(client, auth, valor):
    # Com float, 19.99 * 100 vira 1998.9999999999998; aqui o valor guardado é exato.
    response = criar(client, auth, valor=valor, numero=f"N-{valor}")
    assert response.status_code == 201
    assert response.json()["valor"] == valor


@pytest.mark.parametrize(
    "overrides",
    [
        {"valor": "0"},
        {"valor": "-10.00"},
        {"valor": "10.999"},
        {"valor": "abc"},
        {"numero": ""},
        {"numero": "x" * 31},
        {"emitente": "A"},
        {"sacado": ""},
        {"data_vencimento": "31/12/2030"},
        {"data_vencimento": (date.today() - timedelta(days=1)).isoformat()},
    ],
)
def test_criar_valida_campos(client, auth, overrides):
    assert criar(client, auth, **overrides).status_code == 422


def test_criar_exige_todos_os_campos(client, auth):
    payload = duplicata_payload()
    del payload["sacado"]
    assert client.post(URL, json=payload, headers=auth).status_code == 422


def test_criar_com_corpo_invalido_nao_derruba_a_api(client, auth):
    response = client.post(
        URL, content="isso não é json", headers={**auth, "Content-Type": "application/json"}
    )
    assert response.status_code == 422


def test_vencimento_hoje_e_aceito(client, auth):
    assert criar(client, auth, data_vencimento=date.today().isoformat()).status_code == 201


def test_numero_duplicado_retorna_409(client, auth):
    assert criar(client, auth).status_code == 201
    assert criar(client, auth).status_code == 409


def test_mesmo_numero_em_usuarios_diferentes_e_permitido(client, auth, other_auth):
    assert criar(client, auth).status_code == 201
    assert criar(client, other_auth).status_code == 201


def test_campos_sao_aparados(client, auth):
    body = criar(client, auth, numero="  DUP-9  ", sacado="  Cliente  ").json()
    assert body["numero"] == "DUP-9"
    assert body["sacado"] == "Cliente"


# --- listagem --------------------------------------------------------------------------------


def test_listar_com_paginacao_e_ordem(client, auth):
    for i in range(5):
        criar(client, auth, numero=f"D-{i}")

    page = client.get(URL, params={"limit": 2, "offset": 0}, headers=auth).json()
    assert page["total"] == 5
    assert page["limit"] == 2
    assert page["offset"] == 0
    assert [item["numero"] for item in page["items"]] == ["D-4", "D-3"]  # mais recentes primeiro

    last = client.get(URL, params={"limit": 2, "offset": 4}, headers=auth).json()
    assert [item["numero"] for item in last["items"]] == ["D-0"]


def test_listar_filtra_por_status(client, auth):
    first = criar(client, auth, numero="A").json()
    criar(client, auth, numero="B")
    client.patch(f"{URL}/{first['id']}/status", json={"status": "aceita"}, headers=auth)

    aceitas = client.get(URL, params={"status": "aceita"}, headers=auth).json()
    assert aceitas["total"] == 1
    assert aceitas["items"][0]["numero"] == "A"
    assert client.get(URL, params={"status": "liquidada"}, headers=auth).json()["total"] == 0


@pytest.mark.parametrize(
    "params", [{"status": "inexistente"}, {"limit": 0}, {"limit": 101}, {"offset": -1}]
)
def test_listar_valida_parametros(client, auth, params):
    assert client.get(URL, params=params, headers=auth).status_code == 422


# --- busca, status e exclusão ------------------------------------------------------------------


def test_buscar_por_id(client, auth):
    created = criar(client, auth).json()
    response = client.get(f"{URL}/{created['id']}", headers=auth)
    assert response.status_code == 200
    assert response.json() == created


def test_buscar_inexistente_retorna_404(client, auth):
    assert client.get(f"{URL}/999", headers=auth).status_code == 404


def test_atualizar_status(client, auth):
    created = criar(client, auth).json()
    response = client.patch(
        f"{URL}/{created['id']}/status", json={"status": "liquidada"}, headers=auth
    )
    assert response.status_code == 200
    assert response.json()["status"] == "liquidada"
    assert client.get(f"{URL}/{created['id']}", headers=auth).json()["status"] == "liquidada"


def test_atualizar_status_invalido(client, auth):
    created = criar(client, auth).json()
    response = client.patch(f"{URL}/{created['id']}/status", json={"status": "paga"}, headers=auth)
    assert response.status_code == 422
    assert client.patch(f"{URL}/{created['id']}/status", json={}, headers=auth).status_code == 422


def test_atualizar_status_inexistente(client, auth):
    assert (
        client.patch(f"{URL}/999/status", json={"status": "aceita"}, headers=auth).status_code
        == 404
    )


def test_excluir(client, auth):
    created = criar(client, auth).json()
    assert client.delete(f"{URL}/{created['id']}", headers=auth).status_code == 204
    assert client.get(f"{URL}/{created['id']}", headers=auth).status_code == 404
    assert client.delete(f"{URL}/{created['id']}", headers=auth).status_code == 404


# --- autorização -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "", duplicata_payload()),
        ("get", "", None),
        ("get", "/1", None),
        ("patch", "/1/status", {"status": "aceita"}),
        ("delete", "/1", None),
    ],
)
def test_rotas_exigem_autenticacao(client, method, path, body):
    response = client.request(method, URL + path, json=body)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_usuario_nao_acessa_duplicata_de_outro(client, auth, other_auth):
    created = criar(client, auth).json()
    url = f"{URL}/{created['id']}"

    # 404 (e não 403): não revela que o recurso existe.
    assert client.get(url, headers=other_auth).status_code == 404
    assert (
        client.patch(f"{url}/status", json={"status": "cancelada"}, headers=other_auth).status_code
        == 404
    )
    assert client.delete(url, headers=other_auth).status_code == 404

    assert client.get(URL, headers=other_auth).json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }
    # E a duplicata original segue intacta.
    assert client.get(url, headers=auth).json()["status"] == "emitida"
