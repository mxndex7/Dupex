
# API de Duplicatas Escriturais Dupex

### API RESTful para gerenciamento de duplicatas escriturais (emissão, aceite e liquidação).

### Duplicatas escriturais são a evolução digital dos títulos de crédito, emitidas e armazenadas eletronicamente em sistemas de registro autorizados pelo Banco Central, eliminando a necessidade do documento físico em papel. Elas servem como uma ferramenta estratégica para a gestão financeira, permitindo que empresas comprovem direitos de recebimento e realizem a antecipação de recebíveis (troca de títulos por dinheiro à vista) com muito mais segurança e agilidade. Ao centralizar o registro, ela impede fraudes — como a venda da mesma fatura para múltiplos bancos — e reduz o custo do crédito, tornando o fluxo de caixa das empresas mais dinâmico e transparente.


![Capa](https://github.com/mxndex7/Dupex/blob/main/Slide%20Dupex/1.jpg)

## Contexto Geral do Sistema

![contexto](https://github.com/mxndex7/Dupex/blob/main/Slide%20Dupex/2.jpg)

## Funcionamento e Especificações Técnicas

![funcionamento](https://github.com/mxndex7/Dupex/blob/main/Slide%20Dupex/3.jpg)

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
## Telas

![Imagens](https://github.com/mxndex7/Dupex/blob/main/Slide%20Dupex/4.jpg)

## Como executar

1. Instale as dependências: `pip install -r requirements.txt`
2. Execute: `python app.py`
3. A API estará disponível em `http://0.0.0.0:5000`

## Lógica

![Imagens](https://github.com/mxndex7/Dupex/blob/main/Slide%20Dupex/5.jpg)


