from flask import Flask, render_template, request, redirect, url_for, session
import pyodbc
import requests
from datetime import datetime
from threading import Thread, Lock
from flask_caching import Cache
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

app = Flask(__name__)
# 全局浏览器实例和锁
driver = None
driver_lock = Lock()
app.secret_key = 'your_secure_secret_key_here'
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# 数据库配置
SERVER = 'SAB\\YXQ'
DATABASE = 'DB'
USERNAME = 'sa'
PASSWORD = '1234yang'
DRIVER = '{ODBC Driver 17 for SQL Server}'

def get_db_connection():
    return pyodbc.connect(
        f'DRIVER={DRIVER};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'UID={USERNAME};'
        f'PWD={PASSWORD};'
    )

def fetch_balance(captcha=None):
    global driver
    with driver_lock:
        try:
            # 初始化浏览器实例
            if driver is None:
                driver = webdriver.Chrome()
            
            # 打开统一认证登录页面
            driver.get("https://yikatong.tongji.edu.cn/user/user")

            # 等待"统一认证登录"链接加载完成并点击
            login_link = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.LINK_TEXT, "统一认证登陆"))
            )
            login_link.click()

            # 等待登录页面加载完成，输入用户名和密码
            username_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.NAME, "j_username"))
            )
            password_input = driver.find_element(By.NAME, "j_password")
            
            # 填写用户名和密码
            username_input.send_keys("2253867")  # 替换为你的工号或学号
            password_input.send_keys("No2022053854")  # 替换为你的密码
            
            # 首次提交用户名和密码
            password_input.send_keys(Keys.RETURN)
            
            # 检查是否需要验证码（提交后才会显示）
            try:
 
                
                # 显式等待验证码相关元素
                send_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "smsBtn"))
                )
                
                if captcha is None:
                    # 点击发送验证码按钮
                    send_btn.click()
                    # 保持浏览器打开状态，等待用户输入验证码
                    return "NEED_CAPTCHA"
                
                # 输入6位数字验证码
                captcha_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "sms_otpOrSms24"))
                )
                captcha_input.clear()
                captcha_input.send_keys(captcha)
                
                # 按下 Enter 键提交验证码
                captcha_input.send_keys(Keys.RETURN)
                
            except:
                # 不需要验证码，继续正常流程
                pass
            
            # 等待页面跳转并加载 iframe
            WebDriverWait(driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "forcomepage"))
            )

            # 等待账户余额元素的加载
            WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.ID, "liku123"))
            )

            time.sleep(1)
            
            # 获取账户余额
            balance_element = driver.find_element(By.ID, "liku123")
            balance = balance_element.text.strip()
            return balance
        except Exception as e:
            return "加载中..."

def get_balance_async(username, captcha=None):
    with app.app_context():
        balance = fetch_balance(captcha)
        cache.set(f'balance_{username}', balance, timeout=60*60)  # 缓存1小时

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 参数化查询防止SQL注入
            cursor.execute(
                "SELECT username FROM users WHERE username = ? AND password = ?",
                (username, password)
            )
            user = cursor.fetchone()
            
            if user:
                session['loggedin'] = True
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = '用户名或密码错误！'
            
        except Exception as e:
            error = f'数据库错误: {str(e)}'
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

    return render_template('login.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    username = session['username']
    captcha = request.form.get('captcha') if request.method == 'POST' else None

    # 获取天气数据
    weather_api_url = "https://api.seniverse.com/v3/weather/now.json"
    params = {
        "location": "上海",
        "key": "SRv8C_EQcS3bCsvN2",
    }
    try:
        weather_response = requests.get(weather_api_url, params=params)
        weather_data = weather_response.json()
        if "results" in weather_data and len(weather_data["results"]) > 0:
            weather = f"天气：{weather_data['results'][0]['now']['text']}，温度：{weather_data['results'][0]['now']['temperature']}°C"
        else:
            weather = "无法获取天气信息"
    except Exception as e:
        weather = f"无法获取天气信息: {str(e)}"

    # 获取当前时间和当天课程
    current_time = datetime.now()
    current_day = current_time.strftime('%A')  # 星期几
    current_time_str = current_time.strftime('%H:%M:%S')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT course_name, location, start_time, end_time FROM schedule "
            "WHERE username = ? AND day_of_week = ? AND start_time > ? "
            "ORDER BY start_time ASC",
            (username, current_day, current_time_str)
        )
        courses = cursor.fetchall()
    except Exception as e:
        return f"数据库错误: {str(e)}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    if courses:
        next_course = courses[0]
    else:
        next_course = None

    # 处理验证码逻辑
    balance = cache.get(f'balance_{username}')
    
    # 如果是POST请求且提供了验证码，先尝试获取余额
    if request.method == 'POST' and captcha:
        Thread(target=get_balance_async, args=(username, captcha)).start()
        balance = "加载中..."
    
    # 如果需要验证码，直接显示输入框
    if balance == "NEED_CAPTCHA":
        return render_template('dashboard.html', 
                            username=username, 
                            weather=weather, 
                            balance="NEED_CAPTCHA",
                            next_course=next_course,
                            courses=courses)
    
    # 异步获取校园卡余额（首次加载或刷新）
    if balance is None:
        Thread(target=get_balance_async, args=(username, captcha)).start()
        balance = "加载中..."

    return render_template('dashboard.html', username=username, weather=weather, balance=balance, next_course=next_course, courses=courses)

@app.route('/add_schedule', methods=['GET', 'POST'])
def add_schedule():
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    username = session['username']

    if request.method == 'POST':
        day_of_week = request.form['day_of_week']
        time_slot = request.form['time_slot']
        start_time, end_time = time_slot.split('-')
        course_name = request.form['course_name']
        location = request.form['location']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO schedule (username, day_of_week, start_time, end_time, course_name, location)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, day_of_week, start_time.strip(), end_time.strip(), course_name, location)
            )
            conn.commit()
        except Exception as e:
            return f"数据库错误: {str(e)}"
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'conn' in locals(): conn.close()

        return redirect(url_for('add_schedule'))

    # 查询已保存的课表
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, day_of_week, CONVERT(VARCHAR, start_time, 8) AS start_time,
                   CONVERT(VARCHAR, end_time, 8) AS end_time, course_name, location
            FROM schedule
            WHERE username = ?
            ORDER BY day_of_week, start_time
            """,
            (username,)
        )
        rows = cursor.fetchall()
        saved_courses = [
            {
                "id": row.id,
                "day_of_week": row.day_of_week,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "course_name": row.course_name,
                "location": row.location,
            }
            for row in rows
        ]
    except Exception as e:
        return f"数据库错误: {str(e)}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    return render_template('add_schedule.html', saved_courses=saved_courses)

@app.route('/update_schedule/<int:schedule_id>', methods=['POST'])
def update_schedule(schedule_id):
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    # 获取表单数据
    day_of_week = request.form['day_of_week']
    time_slot = request.form['time_slot']
    try:
        start_time, end_time = time_slot.split('-')  # 解析时间段
    except ValueError:
        return "时间段格式错误，请检查输入！"

    course_name = request.form['course_name']
    location = request.form['location']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 更新数据库
        cursor.execute(
            """
            UPDATE schedule
            SET day_of_week = ?, start_time = ?, end_time = ?, course_name = ?, location = ?
            WHERE id = ? AND username = ?
            """,
            (day_of_week, start_time.strip(), end_time.strip(), course_name, location, schedule_id, session['username'])
        )
        conn.commit()
    except Exception as e:
        return f"数据库错误: {str(e)}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    return redirect(url_for('add_schedule'))

@app.route('/delete_schedule/<int:schedule_id>', methods=['POST'])
def delete_schedule(schedule_id):
    if not session.get('loggedin'):
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM schedule WHERE id = ? AND username = ?", (schedule_id, session['username']))
        conn.commit()  # 确保提交事务
    except Exception as e:
        return f"数据库错误: {str(e)}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    return redirect(url_for('add_schedule'))

@app.route('/check_balance_status', methods=['GET'])
def check_balance_status():
    if not session.get('loggedin'):
        return {"status": "error", "message": "未登录"}

    username = session['username']
    balance = cache.get(f'balance_{username}')

    if balance == "NEED_CAPTCHA":
        return {"status": "need_captcha"}
    elif balance is None:
        return {"status": "loading"}
    else:
        return {"status": "success", "balance": balance}

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=5000)