
from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DATABASE = 'duplicatas.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(DATABASE):
        conn = get_db()
        conn.execute('''
            CREATE TABLE duplicatas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL UNIQUE,
                valor REAL NOT NULL,
                emitente TEXT NOT NULL,
                sacado TEXT NOT NULL,
                data_emissao TEXT NOT NULL,
                data_vencimento TEXT NOT NULL,
                status TEXT DEFAULT 'emitida',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/duplicatas', methods=['POST'])
def criar_duplicata():
    data = request.get_json()
    
    required_fields = ['numero', 'valor', 'emitente', 'sacado', 'data_vencimento']
    for field in required_fields:
        if field not in data:
            return jsonify({'erro': f'Campo obrigatório ausente: {field}'}), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO duplicatas (numero, valor, emitente, sacado, data_emissao, data_vencimento, status)
            VALUES (?, ?, ?, ?, ?, ?, 'emitida')
        ''', (
            data['numero'],
            data['valor'],
            data['emitente'],
            data['sacado'],
            datetime.now().strftime('%Y-%m-%d'),
            data['data_vencimento']
        ))
        conn.commit()
        duplicata_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'id': duplicata_id,
            'mensagem': 'Duplicata criada com sucesso',
            'numero': data['numero']
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({'erro': 'Duplicata com este número já existe'}), 409
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/duplicatas', methods=['GET'])
def listar_duplicatas():
    status = request.args.get('status')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('SELECT * FROM duplicatas WHERE status = ?', (status,))
    else:
        cursor.execute('SELECT * FROM duplicatas')
    
    duplicatas = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(duplicatas), 200

@app.route('/duplicatas/<int:id>', methods=['GET'])
def buscar_duplicata(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM duplicatas WHERE id = ?', (id,))
    duplicata = cursor.fetchone()
    conn.close()
    
    if duplicata:
        return jsonify(dict(duplicata)), 200
    return jsonify({'erro': 'Duplicata não encontrada'}), 404

@app.route('/duplicatas/<int:id>/status', methods=['PATCH'])
def atualizar_status(id):
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({'erro': 'Campo status é obrigatório'}), 400
    
    novo_status = data['status']
    status_validos = ['emitida', 'aceita', 'liquidada', 'cancelada']
    
    if novo_status not in status_validos:
        return jsonify({'erro': f'Status inválido. Use: {", ".join(status_validos)}'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM duplicatas WHERE id = ?', (id,))
    duplicata = cursor.fetchone()
    
    if not duplicata:
        conn.close()
        return jsonify({'erro': 'Duplicata não encontrada'}), 404
    
    cursor.execute('''
        UPDATE duplicatas 
        SET status = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (novo_status, id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'mensagem': 'Status atualizado com sucesso',
        'id': id,
        'novo_status': novo_status
    }), 200

@app.route('/duplicatas/<int:id>', methods=['DELETE'])
def excluir_duplicata(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM duplicatas WHERE id = ?', (id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected > 0:
        return jsonify({'mensagem': 'Duplicata excluída com sucesso'}), 200
    return jsonify({'erro': 'Duplicata não encontrada'}), 404

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'servico': 'API Duplicatas Escriturais'}), 200

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
