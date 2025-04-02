from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key-123'  # 生产环境中应使用更安全的密钥

# 数据库初始化
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 数据库连接辅助函数
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# 检查电子邮件格式
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# 用户注册API
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    # 验证输入
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
    
    if email and not is_valid_email(email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码长度至少为6位'}), 400
    
    # 密码哈希处理
    hashed_password = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查用户名或邮箱是否已存在
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': '用户名或邮箱已被注册'}), 400
        
        # 插入新用户
        cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                      (username, email, hashed_password))
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user': {
                'id': cursor.lastrowid,
                'username': username,
                'email': email
            }
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# 用户登录API
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username_or_email = data.get('username')
    password = data.get('password')
    
    if not username_or_email or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询用户（支持用户名或邮箱登录）
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', 
                      (username_or_email, username_or_email))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            # 创建会话
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            return jsonify({
                'success': True,
                'message': '登录成功',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email']
                }
            })
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# 用户登出
@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'success': True, 'message': '已退出登录'})

# 检查登录状态
@app.route('/api/check-auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({
            'isAuthenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session['username']
            }
        })
    return jsonify({'isAuthenticated': False})

# 前端页面
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)