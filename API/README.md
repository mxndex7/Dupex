
# API de Duplicatas Escriturais DUPEX

API RESTful para gerenciamento de duplicatas escriturais (emissão, aceite e liquidação).

## Endpoints

### 1. Criar Duplicata
```
POST /duplicatas
Content-Type: application/json

{
  "numero": "DUP-001",
  "valor": 1500.00,
  "emitente": "Empresa XYZ Ltda",
  "sacado": "Cliente ABC S.A.",
  "data_vencimento": "2024-12-31"
}
```

### 2. Listar Duplicatas
```
GET /duplicatas
GET /duplicatas?status=emitida
```

### 3. Buscar Duplicata por ID
```
GET /duplicatas/1
```

### 4. Atualizar Status
```
PATCH /duplicatas/1/status
Content-Type: application/json

{
  "status": "aceita"
}
```

Status válidos: `emitida`, `aceita`, `liquidada`, `cancelada`

### 5. Excluir Duplicata
```
DELETE /duplicatas/1
```

### 6. Health Check
```
GET /health
```

## Como executar

1. Instale as dependências: `pip install -r requirements.txt`
2. Execute: `python app.py`
3. A API estará disponível em `http://0.0.0.0:5000`
