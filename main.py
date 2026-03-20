import telebot
from telebot import types
import sqlite3
import json
import time
import re
import uuid
import requests
from datetime import datetime
from threading import Thread
import os

# ================== إعدادات البوت الأساسية ==================
BOT_TOKEN = '8601914091:AAG1xuF4RWuE3OjHb6XA-ZapGkKzo9rmdBY'
ADMIN_ID = '8262266475'

# الإعدادات الافتراضية
SERIATEL_AUTO_NUMBER = '19995235'
SERIATEL_MANUAL_NUMBER = '19995235'
SHAM_DOLLAR_ADDRESS = '0e94b177573563679dc517712edf55a1'
SHAM_DOLLAR_IMAGE = ''
SHAM_LIRA_ADDRESS = '0e94b177573563679dc517712edf55a1'
SHAM_LIRA_IMAGE = ''

# إعدادات API
API_BASE = 'https://api.shams4store.com/client/api/'
API_TOKEN = '4UHDa4tKHVQdaeOFG64Ga_S3Oivr2AXai-3ws6RQONnGSKhg2TxSnlbQJB0QHCP4'

ITEMS_PER_PAGE = 5
CREDIT_VALUE = 122

# رموز المنتجات
PRODUCTS = {
    'FREE FIRE': {
        '110 💎': '1940',
        '221 💎': '1941',
        '583 💎': '1942',
        '1188 💎': '1943',
        '2420 💎': '1944',
        'عضوية شهرية': '644',
        'عضوية أسبوعية': '643'
    },
    'PUBG MOBILE': {
        '60 UC': '645',
        '325 UC': '646',
        '660 UC': '647',
        '1800 UC': '648',
        '3850 UC': '649'
    }
}

bot = telebot.TeleBot(BOT_TOKEN)
api_session = requests.Session()
api_session.headers.update({'api-token': API_TOKEN})

# ================== دوال قاعدة البيانات ==================
def get_db_connection():
    conn = sqlite3.connect('BaronDev.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        balance INTEGER DEFAULT 0,
        total_spent INTEGER DEFAULT 0,
        purchases_count INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        credits_balance INTEGER DEFAULT 0
    )''')
    
    # جدول الطلبات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game TEXT,
        category TEXT,
        price INTEGER,
        player_id TEXT,
        product_id TEXT,
        order_uuid TEXT UNIQUE,
        status TEXT DEFAULT 'pending',
        api_status TEXT DEFAULT 'pending',
        admin_action TEXT DEFAULT 'none',
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        attempts INTEGER DEFAULT 0,
        success_method TEXT,
        last_message_id INTEGER,
        admin_notify_msg_id INTEGER,
        check_status_active INTEGER DEFAULT 1,
        quantity INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    
    # جدول سجل محاولات API
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS api_attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        method TEXT,
        endpoint TEXT,
        payload TEXT,
        response TEXT,
        status_code INTEGER,
        success INTEGER DEFAULT 0,
        attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
    )''')
    
    # جدول طلبات شحن الرصيد
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposit_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        credits_amount INTEGER DEFAULT 0,
        transaction_id TEXT,
        deposit_type TEXT DEFAULT 'seriatel',
        status TEXT DEFAULT 'pending',
        admin_action TEXT DEFAULT 'none',
        request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_message_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    
    # جدول إعدادات البوت
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # جدول المنتجات (للألعاب)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        game TEXT,
        category TEXT,
        price INTEGER,
        credits_price INTEGER DEFAULT 0,
        product_id TEXT,
        is_active INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0,
        type TEXT DEFAULT 'api',
        api_source TEXT DEFAULT 'source1',
        min_qty INTEGER,
        max_qty INTEGER,
        price_per_unit INTEGER,
        product_type TEXT DEFAULT 'package',
        PRIMARY KEY (game, category)
    )''')

    # جدول المشرفين
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        is_main_admin INTEGER DEFAULT 0
    )''')
    
    # جدول القناة الإجبارية
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mandatory_channel (
        channel_id TEXT PRIMARY KEY,
        channel_link TEXT,
        is_active INTEGER DEFAULT 0
    )''')
    
    # جدول إعدادات قنوات الطلبات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channel_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # جدول تتبع المعاملات المكتملة
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS processed_transactions (
        transaction_id TEXT PRIMARY KEY,
        amount INTEGER,
        user_id INTEGER,
        processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول رسائل SMS
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sms_messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT,
        amount INTEGER,
        message_text TEXT,
        received_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # جدول طرق الإيداع
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposit_methods (
        method_name TEXT PRIMARY KEY,
        is_active INTEGER DEFAULT 1
    )''')
    
    # جدول الألعاب
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS games (
        game_name TEXT PRIMARY KEY,
        is_active INTEGER DEFAULT 1
    )''')

    # جدول الصور (يخزن روابط الصور)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bot_images (
        image_key TEXT PRIMARY KEY,
        image_url TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # جدول التطبيقات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS apps (
        app_name TEXT PRIMARY KEY,
        is_active INTEGER DEFAULT 1
    )''')

    # جدول منتجات التطبيقات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS app_products (
        app TEXT,
        category TEXT,
        price INTEGER,
        credits_price INTEGER DEFAULT 0,
        product_id TEXT,
        is_active INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0,
        type TEXT DEFAULT 'api',
        api_source TEXT DEFAULT 'source1',
        min_qty INTEGER,
        max_qty INTEGER,
        price_per_unit INTEGER,
        product_type TEXT DEFAULT 'package',
        PRIMARY KEY (app, category)
    )''')

    # جدول الخدمات (العملات والبطاقات)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
        service_name TEXT PRIMARY KEY,
        is_active INTEGER DEFAULT 1
    )''')

    # جدول منتجات الخدمات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS service_products (
        service TEXT,
        category TEXT,
        price INTEGER,
        credits_price INTEGER DEFAULT 0,
        product_id TEXT,
        is_active INTEGER DEFAULT 1,
        display_order INTEGER DEFAULT 0,
        type TEXT DEFAULT 'api',
        api_source TEXT DEFAULT 'source1',
        min_qty INTEGER,
        max_qty INTEGER,
        price_per_unit INTEGER,
        product_type TEXT DEFAULT 'package',
        PRIMARY KEY (service, category)
    )''')

    # إضافة الأعمدة المفقودة (إذا لم تكن موجودة)
    try:
        cursor.execute("SELECT type FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN type TEXT DEFAULT "api"')
    
    try:
        cursor.execute("SELECT api_source FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN api_source TEXT DEFAULT "source1"')
    
    try:
        cursor.execute("SELECT min_qty FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN min_qty INTEGER')
    
    try:
        cursor.execute("SELECT max_qty FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN max_qty INTEGER')
    
    try:
        cursor.execute("SELECT price_per_unit FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN price_per_unit INTEGER')
    
    try:
        cursor.execute("SELECT product_type FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN product_type TEXT DEFAULT "package"')

    try:
        cursor.execute("SELECT credits_balance FROM users LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE users ADD COLUMN credits_balance INTEGER DEFAULT 0')
    
    try:
        cursor.execute("SELECT credits_price FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE products ADD COLUMN credits_price INTEGER DEFAULT 0')
    
    try:
        cursor.execute("SELECT credits_amount FROM deposit_requests LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE deposit_requests ADD COLUMN credits_amount INTEGER DEFAULT 0')
    
    try:
        cursor.execute("SELECT attempts FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE orders ADD COLUMN attempts INTEGER DEFAULT 0')
    
    try:
        cursor.execute("SELECT success_method FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE orders ADD COLUMN success_method TEXT')
    
    try:
        cursor.execute("SELECT last_message_id FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE orders ADD COLUMN last_message_id INTEGER')
    
    try:
        cursor.execute("SELECT check_status_active FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE orders ADD COLUMN check_status_active INTEGER DEFAULT 1')
    
    try:
        cursor.execute("SELECT last_message_id FROM deposit_requests LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE deposit_requests ADD COLUMN last_message_id INTEGER')
    
    try:
        cursor.execute("SELECT quantity FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE orders ADD COLUMN quantity INTEGER DEFAULT 1')
    
    try:
        cursor.execute("SELECT full_name FROM users LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT')
    
    try:
        cursor.execute("SELECT admin_notify_msg_id FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE orders ADD COLUMN admin_notify_msg_id INTEGER')

    try:
        cursor.execute("SELECT product_id FROM service_products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE service_products ADD COLUMN product_id TEXT')
    try:
        cursor.execute("SELECT type FROM service_products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE service_products ADD COLUMN type TEXT DEFAULT "api"')
    try:
        cursor.execute("SELECT api_source FROM service_products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE service_products ADD COLUMN api_source TEXT DEFAULT "source1"')
    try:
        cursor.execute("SELECT min_qty FROM service_products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE service_products ADD COLUMN min_qty INTEGER')
    try:
        cursor.execute("SELECT max_qty FROM service_products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE service_products ADD COLUMN max_qty INTEGER')
    try:
        cursor.execute("SELECT price_per_unit FROM service_products LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute('ALTER TABLE service_products ADD COLUMN price_per_unit INTEGER')

    # حذف البيانات القديمة للمنتجات
    cursor.execute('DELETE FROM products')
    
    # إدخال البيانات الافتراضية للمنتجات
    default_products = []
    display_order = 1
    
    for category, product_id in PRODUCTS['FREE FIRE'].items():
        price = 115 if category == '110 💎' else \
                230 if category == '221 💎' else \
                575 if category == '583 💎' else \
                1150 if category == '1188 💎' else \
                2300 if category == '2420 💎' else \
                300 if category == 'عضوية أسبوعية' else \
                100 if category == 'عضوية شهرية' else 0
        default_products.append(('FREE FIRE', category, price, product_id, 1, display_order, 'api', 'source1', None, None, None, 'package'))
        display_order += 1
    
    display_order = 1
    for category, product_id in PRODUCTS['PUBG MOBILE'].items():
        price = 110 if category == '60 UC' else \
                550 if category == '325 UC' else \
                1100 if category == '660 UC' else \
                330 if category == '1800 UC' else \
                8250 if category == '3850 UC' else 0
        default_products.append(('PUBG MOBILE', category, price, product_id, 1, display_order, 'api', 'source1', None, None, None, 'package'))
        display_order += 1
    
    cursor.executemany('''
    INSERT INTO products (game, category, price, product_id, is_active, display_order, type, api_source, min_qty, max_qty, price_per_unit, product_type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', default_products)
    
    # إدخال الألعاب الافتراضية
    cursor.execute('INSERT OR IGNORE INTO games (game_name, is_active) VALUES (?, ?)', ('FREE FIRE', 1))
    cursor.execute('INSERT OR IGNORE INTO games (game_name, is_active) VALUES (?, ?)', ('PUBG MOBILE', 1))
    
    # ترحيل الإعدادات القديمة
    old_seriatel = cursor.execute('SELECT value FROM settings WHERE key = "seriatel_number"').fetchone()
    old_seriatel_value = old_seriatel['value'] if old_seriatel else SERIATEL_AUTO_NUMBER
    
    old_sham = cursor.execute('SELECT value FROM settings WHERE key = "sham_number"').fetchone()
    old_sham_value = old_sham['value'] if old_sham else SHAM_LIRA_ADDRESS
    
    # إدخال الإعدادات الجديدة
    settings_data = [
        ('seriatel_auto_number', old_seriatel_value),
        ('seriatel_manual_number', old_seriatel_value),
        ('sham_dollar_address', SHAM_DOLLAR_ADDRESS),
        ('sham_dollar_image', SHAM_DOLLAR_IMAGE),
        ('sham_lira_address', old_sham_value),
        ('sham_lira_image', SHAM_LIRA_IMAGE),
        ('bot_active', '1'),
        ('support_username', '@Bar0nSupport'),
        ('welcome_message', '𝑾𝑬𝑳𝑪𝑶𝑴𝑬 𝑻𝑶 𝑴𝒀 𝑩𝑶𝑻 🪐✨\n♪ اخــتـر أحــد الأوامــر الــتـالـيــة :')
    ]
    
    for key, value in settings_data:
        cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    # إعدادات قنوات الطلبات
    channel_settings = [
        ('orders_channel_id', ''),
        ('deposit_channel_id', ''),
        ('sms_channel_id', ''),
        ('send_to_channels', '0'),
        ('new_users_channel_id', '')
    ]
    for key, value in channel_settings:
        cursor.execute('INSERT OR IGNORE INTO channel_settings (key, value) VALUES (?, ?)', (key, value))
    
    # إضافة الأدمن الأساسي
    cursor.execute('INSERT OR IGNORE INTO admins (user_id, is_main_admin) VALUES (?, ?)', (ADMIN_ID, 1))
    
    # طرق الإيداع الافتراضية
    deposit_methods = [
        ('seriatel', 1),
        ('seriatel_manual', 1),
        ('sham_dollar', 1),
        ('sham_lira', 1)
    ]
    for method, active in deposit_methods:
        cursor.execute('INSERT OR IGNORE INTO deposit_methods (method_name, is_active) VALUES (?, ?)', (method, active))
    
    conn.commit()
    conn.close()

init_db()

# ================== دوال الصور ==================
def set_image(key, image_url):
    conn = get_db_connection()
    conn.execute('''
        INSERT OR REPLACE INTO bot_images (image_key, image_url, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (key, image_url))
    conn.commit()
    conn.close()

def get_image(key):
    conn = get_db_connection()
    row = conn.execute('SELECT image_url FROM bot_images WHERE image_key = ?', (key,)).fetchone()
    conn.close()
    return row['image_url'] if row else None

def delete_image(key):
    conn = get_db_connection()
    conn.execute('DELETE FROM bot_images WHERE image_key = ?', (key,))
    conn.commit()
    conn.close()

# ================== دوال API ==================
def get_api_balance():
    try:
        url = f"{API_BASE}profile"
        headers = {'api-token': API_TOKEN, 'Accept': 'application/json'}
        response = requests.get(url, headers=headers, timeout=10)
        result = response.json()
        if response.status_code == 200:
            return {'success': True, 'balance': result.get('balance', '0'), 'email': result.get('email', 'غير معروف')}
        else:
            return {'success': False, 'error': result.get('message', f'خطأ HTTP: {response.status_code}')}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_api_products():
    try:
        url = f"{API_BASE}products"
        response = api_session.get(url, timeout=10)
        if response.status_code == 200:
            products = response.json()
            return {'success': True, 'products': products} if isinstance(products, list) else {'success': False, 'error': 'تنسيق استجابة غير صحيح'}
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def search_api_products(search_term, page=1):
    result = get_api_products()
    if not result['success']:
        return result
    
    products = result['products']
    search_term_lower = search_term.lower()
    matches = []
    for p in products:
        name = p.get('name', '').lower()
        pid = str(p.get('id', ''))
        cat = p.get('category_name', '').lower()
        game = p.get('game_name', '').lower()
        if search_term_lower in name or search_term in pid or search_term_lower in cat or search_term_lower in game:
            matches.append(p)
    
    total = len(matches)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = matches[start:end]
    
    return {
        'success': True, 
        'results': page_items, 
        'total': total,
        'page': page,
        'total_pages': (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1,
        'search_term': search_term
    }

def check_api_product(product_id):
    try:
        url = f"{API_BASE}products?products_id={product_id}"
        response = api_session.get(url, timeout=10)
        if response.status_code == 200:
            products = response.json()
            if products and len(products) > 0:
                p = products[0]
                return {
                    'success': True,
                    'exists': True,
                    'available': p.get('available', False),
                    'name': p.get('name', ''),
                    'price': p.get('price', 0),
                    'product_type': p.get('product_type', 'package'),
                    'qty_values': p.get('qty_values')
                }
        return {'success': False, 'exists': False}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_api_order_form_data(product_id, player_id, order_uuid, quantity=1):
    try:
        url = f"{API_BASE}newOrder/{product_id}"
        data = {'playerId': str(player_id), 'order_uuid': order_uuid, 'quantity': str(quantity)}
        headers = {'api-token': API_TOKEN, 'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, data=data, headers=headers)
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            try:
                cleaned_text = response.text.replace('\n', '').replace('\r', '')
                result = json.loads(cleaned_text)
            except:
                result = {'raw_response': response.text, 'status': 'ERROR', 'error': 'Invalid JSON response'}
        
        # كشف رصيد غير كافي
        if result.get('code') == 100:
            message = str(result.get('message', '')).lower()
            if 'insufficient' in message or 'balance' in message or 'رصيد' in message:
                return {'success': False, 'method': 'form_data', 'error': 'رصيد الموقع غير كافي', 'api_response': result, 'insufficient_balance': True}
        
        response_text = str(response.text).lower()
        if 'insufficient balance' in response_text:
            return {'success': False, 'method': 'form_data', 'error': 'رصيد الموقع غير كافي', 'api_response': result, 'insufficient_balance': True}
        
        if result.get('status') == 'ERROR':
            error_msg = str(result.get('message', '')).lower()
            if 'insufficient' in error_msg or 'balance' in error_msg:
                return {'success': False, 'method': 'form_data', 'error': 'رصيد الموقع غير كافي', 'api_response': result, 'insufficient_balance': True}
        
        if response.status_code == 200 and result.get('status') == 'OK':
            return {
                'success': True,
                'method': 'form_data',
                'order_id': result['data'].get('order_id'),
                'api_status': result['data'].get('status', 'wait'),
                'price': result['data'].get('price'),
                'data': result['data'].get('data', {}),
                'replay_api': result['data'].get('replay_api', [])
            }
        else:
            error_msg = result.get('message', f'خطأ HTTP: {response.status_code}')
            return {'success': False, 'method': 'form_data', 'error': error_msg, 'api_response': result, 'insufficient_balance': False}
    except Exception as e:
        return {'success': False, 'method': 'form_data', 'error': str(e), 'insufficient_balance': False}

def check_api_order_by_uuid(order_uuid):
    try:
        url = f"{API_BASE}check?orders=[\"{order_uuid}\"]&uuid=1"
        response = api_session.get(url)
        result = response.json()
        
        if response.status_code == 200 and result.get('status') == 'OK':
            if result.get('data') and len(result['data']) > 0:
                order_data = result['data'][0]
                return {
                    'success': True,
                    'order_id': order_data.get('order_id'),
                    'status': order_data.get('status', 'pending'),
                    'quantity': order_data.get('quantity', 1),
                    'data': order_data.get('data', {}),
                    'created_at': order_data.get('created_at'),
                    'product_name': order_data.get('product_name'),
                    'price': order_data.get('price'),
                    'replay_api': order_data.get('replay_api', [])
                }
            else:
                return {'success': False, 'error': 'لم يتم العثور على الطلب'}
        else:
            error_msg = result.get('message', 'خطأ غير معروف')
            return {'success': False, 'error': error_msg}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_order_message(order_id, user_id, status_text=None):
    try:
        order = get_order_details(order_id)
        if not order:
            return
        
        last_message_id = order['last_message_id']
        api_status = order['api_status']
        
        if status_text:
            final_status_text = status_text
        else:
            final_status_text = {
                'accept': '✅ تم تنفيذ طلبك',
                'reject': '❌ مرفوض',
                'wait': '🔄 جاري التنفيذ'
            }.get(api_status, '🔄 جاري التنفيذ')
        
        message_text = f"""
✅ تم تأكيد طلبك بنجاح!

🎮 الخدمة: {order['game']}
📦 الفئة: {order['category']}
💰 السعر: {order['price']} ل.س
🆔 معرف اللاعب: {order['player_id']}
📊 {final_status_text}
        """
        
        if last_message_id:
            try:
                bot.edit_message_text(chat_id=user_id, message_id=last_message_id, text=message_text, parse_mode='HTML')
            except:
                msg = bot.send_message(user_id, message_text, parse_mode='HTML')
                update_order_last_message(order_id, msg.message_id)
        else:
            msg = bot.send_message(user_id, message_text, parse_mode='HTML')
            update_order_last_message(order_id, msg.message_id)
    except Exception as e:
        print(f"❌ خطأ في update_order_message: {e}")

def start_order_status_checker(order_id, user_id):
    def checker():
        while True:
            try:
                order = get_order_details(order_id)
                if not order:
                    break
                    
                if not order['check_status_active']:
                    break
                
                if order['api_status'] in ['accept', 'reject']:
                    break
                
                if order['order_uuid']:
                    check_result = check_api_order_by_uuid(order['order_uuid'])
                    if check_result['success']:
                        new_status = check_result['status']
                        if new_status != order['api_status']:
                            update_order_api_status(order_id, new_status)
                            if new_status in ['accept', 'reject']:
                                if new_status == 'reject':
                                    update_user_balance(user_id, order['price'])
                                status_text = '✅ تم تنفيذ طلبك' if new_status == 'accept' else '❌ مرفوض'
                                update_order_message(order_id, user_id, status_text)
                                update_order_notification(order_id, new_status)
                                conn = get_db_connection()
                                conn.execute('UPDATE orders SET check_status_active = 0 WHERE order_id = ?', (order_id,))
                                conn.commit()
                                conn.close()
                                break
                time.sleep(10)
            except Exception as e:
                print(f"❌ خطأ في مدقق الحالة: {e}")
                time.sleep(10)
    
    thread = Thread(target=checker)
    thread.daemon = True
    thread.start()

def process_order_with_api(order_id, user_id, game, category, player_id, product_id, quantity=1):
    conn = None
    try:
        order_uuid = str(uuid.uuid4())
        conn = get_db_connection()
        conn.execute('UPDATE orders SET order_uuid = ?, product_id = ?, attempts = attempts + 1, quantity = ? WHERE order_id = ?', (order_uuid, product_id, quantity, order_id))
        conn.commit()
        
        update_order_message(order_id, user_id, ' سيتم اعلامك بحالة طلبك ...')
        
        api_result = create_api_order_form_data(product_id, player_id, order_uuid, quantity)
        
        if conn:
            conn.close()
        
        if isinstance(api_result, dict) and api_result.get('insufficient_balance'):
            conn = get_db_connection()
            conn.execute('UPDATE orders SET status = "failed", api_status = "reject", last_check = CURRENT_TIMESTAMP, check_status_active = 0 WHERE order_id = ?', (order_id,))
            conn.commit()
            
            price = get_product_price(game, category) * quantity if get_product_info(game, category)['product_type'] == 'quantity' else get_product_price(game, category)
            update_user_balance(user_id, price)
            
            message = f"""
❌ تم رفض طلبك!

🎮 اللعبة: {game}
📦 الفئة: {category}
💰 السعر: {price} ل.س
🆔 معرف اللاعب: {player_id}
📊 الكمية: {quantity}

⚠️ السبب : رصيد الموقع غير كافي

💡 تم إرجاع المبلغ ({price} ل.س) إلى رصيدك تلقائياً.
"""
            bot.send_message(user_id, message)
            update_order_notification(order_id, 'reject')
            conn.close()
            return
        
        elif isinstance(api_result, dict) and api_result.get('success'):
            conn = get_db_connection()
            success_method = api_result.get('method', 'unknown')
            api_status = api_result.get('api_status', 'wait')
            
            check_result = check_api_order_by_uuid(order_uuid)
            if check_result and check_result.get('success'):
                api_status = check_result.get('status', 'wait')
            
            conn.execute('UPDATE orders SET status = ?, api_status = ?, success_method = ?, last_check = CURRENT_TIMESTAMP WHERE order_id = ?', ('completed', api_status, success_method, order_id))
            
            if api_status == 'reject':
                price = get_product_price(game, category) * quantity if get_product_info(game, category)['product_type'] == 'quantity' else get_product_price(game, category)
                update_user_balance(user_id, price)
                conn.execute('UPDATE users SET total_spent = total_spent - ? WHERE user_id = ? AND total_spent >= ?', (price, user_id, price))
                conn.execute('UPDATE users SET purchases_count = purchases_count - 1 WHERE user_id = ? AND purchases_count > 0', (user_id,))
            
            conn.commit()
            
            if api_status not in ['accept', 'reject']:
                start_order_status_checker(order_id, user_id)
            else:
                if api_status == 'accept':
                    bot.send_message(user_id, f" ✅ تم قبول وتنفيذ طلبك للخدمة {game}!")
                    update_order_notification(order_id, 'accept')
                elif api_status == 'reject':
                    bot.send_message(user_id, f"❌ تم رفض طلبك للعبة {game}! تم إرجاع المبلغ.")
                    update_order_notification(order_id, 'reject')
            conn.close()
        else:
            conn = get_db_connection()
            conn.execute('UPDATE orders SET status = "failed", api_status = "failed", last_check = CURRENT_TIMESTAMP, check_status_active = 0 WHERE order_id = ?', (order_id,))
            price = get_product_price(game, category) * quantity if get_product_info(game, category)['product_type'] == 'quantity' else get_product_price(game, category)
            update_user_balance(user_id, price)
            conn.commit()
            update_order_message(order_id, user_id, '❌ فشل في المعالجة')
            update_order_notification(order_id, 'reject')
            bot.send_message(user_id, f"❌ فشل في معالجة طلبك! تم إرجاع {price} ل.س.")
            conn.close()
    except Exception as e:
        try:
            if conn is None:
                conn = get_db_connection()
            conn.execute('UPDATE orders SET status = "failed", api_status = "error", last_check = CURRENT_TIMESTAMP WHERE order_id = ?', (order_id,))
            conn.commit()
            price = get_product_price(game, category) * quantity if get_product_info(game, category)['product_type'] == 'quantity' else get_product_price(game, category)
            update_user_balance(user_id, price)
            update_order_notification(order_id, 'reject')
            bot.send_message(user_id, f"⚠️ حدث خطأ في معالجة طلبك! تم إرجاع {price} ل.س.")
        except Exception as inner_error:
            print(f"❌ فشل في إرجاع المبلغ بعد الخطأ: {inner_error}")
        finally:
            if conn:
                conn.close()

# ================== دوال المعاملات ==================
def is_transaction_processed(transaction_id):
    conn = get_db_connection()
    row = conn.execute('SELECT 1 FROM processed_transactions WHERE transaction_id = ?', (transaction_id,)).fetchone()
    conn.close()
    return row is not None

def mark_transaction_processed(transaction_id, amount, user_id):
    conn = get_db_connection()
    conn.execute('INSERT INTO processed_transactions (transaction_id, amount, user_id) VALUES (?, ?, ?)', (transaction_id, amount, user_id))
    conn.commit()
    conn.close()

def save_sms_message(transaction_id, amount, message_text):
    conn = get_db_connection()
    conn.execute('INSERT INTO sms_messages (transaction_id, amount, message_text) VALUES (?, ?, ?)', (transaction_id, amount, message_text))
    conn.commit()
    conn.close()

def find_sms_by_transaction(transaction_id):
    conn = get_db_connection()
    sms = conn.execute('SELECT * FROM sms_messages WHERE transaction_id = ? ORDER BY received_date DESC LIMIT 1', (transaction_id,)).fetchone()
    conn.close()
    return sms

def extract_amount_and_transaction(text):
    patterns = [
        r'تم استلام مبلغ (\d+) ل\.س.*رقم العملية هو (\d+)',
        r'تم استلام مبلغ (\d+) ل\.س.*رقم العمليه (\d+)',
        r'مبلغ (\d+) ل\.س.*رقم العمليه (\d+)',
        r'(\d+) ل\.س.*رقم العمليه (\d+)',
        r'(\d+) ليرة.*رقم العمليه (\d+)',
        r'Amount:? (\d+).*Transaction:? (\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), match.group(2)
    return None, None

def process_deposit_request(user_id, amount, transaction_id, deposit_type='seriatel'):
    if is_transaction_processed(transaction_id):
        return False, "❌ رقم العملية هذا تم استخدامه مسبقاً"
    
    if deposit_type == 'seriatel':
        sms_message = find_sms_by_transaction(transaction_id)
        if not sms_message:
            return False, "❌ لم يتم العثور على العملية، إما أن رقم العملية غير صحيح أو لم تصل بعد"
        
        if amount != sms_message['amount']:
            return False, f"❌ المبلغ غير مطابق. المبلغ المدخل: {amount}, المبلغ المرسل: {sms_message['amount']}"
        
        update_user_balance(user_id, amount)
        mark_transaction_processed(transaction_id, amount, user_id)
        request_id = create_deposit_request(user_id, amount, transaction_id, deposit_type)
        update_deposit_request_status(request_id, 'completed', 'accepted')
        
        new_balance = get_user_balance(user_id)
        user_notification = f"""
✅ تم شحن رصيدك بنجاح!

💳 المبلغ: {amount} ل.س
🔢 رقم العملية: {transaction_id}
💰 رصيدك الحالي: {new_balance} ل.س

شكراً لاستخدامك خدماتنا! 🎮
        """
        try:
            bot.send_message(user_id, user_notification)
        except:
            pass
        
        deposits_channel_id = get_channel_setting('deposit_channel_id')
        send_to_channels = get_channel_setting('send_to_channels')
        
        notification = f"""
✅ إيداع مكتمل (سيرياتيل كاش أوتو):

👤 المستخدم: {user_id}
💳 المبلغ: {amount} ل.س  
🔢 رقم العملية: {transaction_id}
⏰ الوقت: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        if not deposits_channel_id or send_to_channels != '1':
            for admin in get_all_admins():
                try:
                    bot.send_message(admin['user_id'], notification)
                except:
                    pass
        elif send_to_channels == '1' and deposits_channel_id:
            try:
                bot.send_message(deposits_channel_id, notification)
            except:
                pass
        return True, "✅ تم إضافة الرصيد بنجاح"
    else:
        request_id = create_deposit_request(user_id, amount, transaction_id, deposit_type)
        deposits_channel_id = get_channel_setting('deposit_channel_id')
        send_to_channels = get_channel_setting('send_to_channels')
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ قبول", callback_data=f"accept_deposit_{request_id}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_deposit_{request_id}")
        )
        
        type_names = {
            'sham_dollar': 'شام دولار',
            'sham_lira': 'شام ليرة',
            'seriatel_manual': 'سيرياتيل يدوي'
        }
        type_name = type_names.get(deposit_type, deposit_type)
        
        notification = f"""
📨 طلب إيداع جديد ({type_name}):

👤 المستخدم: {user_id}
💳 المبلغ: {amount} ل.س
🔢 رقم العملية: {transaction_id}
📅 التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        if not deposits_channel_id or send_to_channels != '1':
            for admin in get_all_admins():
                try:
                    bot.send_message(admin['user_id'], notification, reply_markup=keyboard)
                except:
                    pass
        elif send_to_channels == '1' and deposits_channel_id:
            try:
                bot.send_message(deposits_channel_id, notification, reply_markup=keyboard)
            except:
                pass
        return False, "📨 تم إرسال طلب الإيداع للمشرفين للموافقة عليه"

def send_order_status_notification(user_id, order_id, api_status):
    try:
        order = get_order_details(order_id)
        if not order:
            return
        
        if api_status == 'accept':
            message_text = f"""
✅ تم قبول وتنفيذ طلبك بنجاح!

🎮 اللعبة: {order['game']}
📦 الفئة: {order['category']}
💰 السعر: {order['price']} ل.س
🆔 معرف اللاعب: {order['player_id']}

شكراً لاستخدامك خدماتنا! 🎮
            """
        elif api_status == 'reject':
            message_text = f"""
❌ تم رفض طلبك!

🎮 اللعبة: {order['game']}
📦 الفئة: {order['category']}
💰 السعر: {order['price']} ل.س
🆔 معرف اللاعب: {order['player_id']}

💡 تم إرجاع المبلغ إلى رصيدك تلقائياً.

للمساعدة تواصل مع {get_setting('support_username') or '@Bar0nSupport'}
            """
        elif api_status == 'insufficient_balance':
            message_text = f"""
❌ تم رفض طلبك!

🎮 اللعبة: {order['game']}
📦 الفئة: {order['category']}
💰 السعر: {order['price']} ل.س
🆔 معرف اللاعب: {order['player_id']}

⚠ السبب: رصيد الموقع غير كافي

💡 تم إرجاع المبلغ إلى رصيدك تلقائياً.

للمساعدة تواصل مع {get_setting('support_username') or '@Bar0nSupport'}
            """
        else:
            return
        
        bot.send_message(user_id, message_text)
    except Exception as e:
        print(f"❌ خطأ في إرسال إشعار الحالة: {e}")

# ================== دوال إدارة الألعاب والمنتجات (الألعاب) ==================
def get_all_games():
    conn = get_db_connection()
    games = conn.execute('SELECT game_name, is_active FROM games ORDER BY game_name').fetchall()
    conn.close()
    return games

def add_game(game_name):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO games (game_name, is_active) VALUES (?, 1)', (game_name,))
    conn.commit()
    conn.close()

def delete_game(game_name):
    conn = get_db_connection()
    conn.execute('DELETE FROM games WHERE game_name = ?', (game_name,))
    conn.execute('DELETE FROM products WHERE game = ?', (game_name,))
    conn.commit()
    conn.close()

def toggle_game_status(game_name, is_active):
    conn = get_db_connection()
    conn.execute('UPDATE games SET is_active = ? WHERE game_name = ?', (is_active, game_name))
    conn.commit()
    conn.close()

def is_game_active(game_name):
    conn = get_db_connection()
    row = conn.execute('SELECT is_active FROM games WHERE game_name = ?', (game_name,)).fetchone()
    conn.close()
    return row and row['is_active'] == 1

def get_products_by_game(game_name, only_active=False, page=1):
    conn = get_db_connection()
    if only_active:
        products = conn.execute('SELECT * FROM products WHERE game = ? AND is_active = 1 ORDER BY display_order', (game_name,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM products WHERE game = ? ORDER BY display_order', (game_name,)).fetchall()
    conn.close()
    
    total = len(products)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return products[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def toggle_product_status(game, category, is_active):
    conn = get_db_connection()
    conn.execute('UPDATE products SET is_active = ? WHERE game = ? AND category = ?', (is_active, game, category))
    conn.commit()
    conn.close()

def update_product_price(game, category, new_price):
    conn = get_db_connection()
    conn.execute('UPDATE products SET price = ? WHERE game = ? AND category = ?', (new_price, game, category))
    conn.commit()
    conn.close()

def update_product_code(game, category, new_code):
    conn = get_db_connection()
    conn.execute('UPDATE products SET product_id = ? WHERE game = ? AND category = ?', (new_code, game, category))
    conn.commit()
    conn.close()

def get_product_info(game, category):
    conn = get_db_connection()
    row = conn.execute('SELECT price, product_id, type, product_type, min_qty, max_qty, price_per_unit FROM products WHERE game = ? AND category = ?', (game, category)).fetchone()
    conn.close()
    return row

def add_product(game, category, price, product_id, ptype='api', api_source='source1', product_type='package', min_qty=None, max_qty=None, price_per_unit=None):
    conn = get_db_connection()
    max_order = conn.execute('SELECT MAX(display_order) FROM products WHERE game = ?', (game,)).fetchone()[0] or 0
    new_order = max_order + 1
    conn.execute('''
        INSERT OR REPLACE INTO products (game, category, price, product_id, is_active, display_order, type, api_source, min_qty, max_qty, price_per_unit, product_type)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
    ''', (game, category, price, product_id, new_order, ptype, api_source, min_qty, max_qty, price_per_unit, product_type))
    conn.commit()
    conn.close()

def delete_product(game, category):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE game = ? AND category = ?', (game, category))
    conn.commit()
    conn.close()

def get_product_price(game, category):
    conn = get_db_connection()
    row = conn.execute('SELECT price, price_per_unit, product_type FROM products WHERE game = ? AND category = ? AND is_active = 1', (game, category)).fetchone()
    conn.close()
    if row and row['product_type'] == 'quantity':
        return row['price_per_unit']
    return row['price'] if row else None

# ================== دوال إدارة التطبيقات ==================
def get_all_apps():
    conn = get_db_connection()
    apps = conn.execute('SELECT app_name, is_active FROM apps ORDER BY app_name').fetchall()
    conn.close()
    return apps

def add_app(app_name):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO apps (app_name, is_active) VALUES (?, 1)', (app_name,))
    conn.commit()
    conn.close()

def delete_app(app_name):
    conn = get_db_connection()
    conn.execute('DELETE FROM apps WHERE app_name = ?', (app_name,))
    conn.execute('DELETE FROM app_products WHERE app = ?', (app_name,))
    conn.commit()
    conn.close()

def toggle_app_status(app_name, is_active):
    conn = get_db_connection()
    conn.execute('UPDATE apps SET is_active = ? WHERE app_name = ?', (is_active, app_name))
    conn.commit()
    conn.close()

def is_app_active(app_name):
    conn = get_db_connection()
    row = conn.execute('SELECT is_active FROM apps WHERE app_name = ?', (app_name,)).fetchone()
    conn.close()
    return row and row['is_active'] == 1

def get_app_products_by_app(app_name, only_active=False, page=1):
    conn = get_db_connection()
    if only_active:
        products = conn.execute('SELECT * FROM app_products WHERE app = ? AND is_active = 1 ORDER BY display_order', (app_name,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM app_products WHERE app = ? ORDER BY display_order', (app_name,)).fetchall()
    conn.close()
    
    total = len(products)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return products[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def toggle_app_product_status(app, category, is_active):
    conn = get_db_connection()
    conn.execute('UPDATE app_products SET is_active = ? WHERE app = ? AND category = ?', (is_active, app, category))
    conn.commit()
    conn.close()

def update_app_product_price(app, category, new_price):
    conn = get_db_connection()
    conn.execute('UPDATE app_products SET price = ? WHERE app = ? AND category = ?', (new_price, app, category))
    conn.commit()
    conn.close()

def update_app_product_code(app, category, new_code):
    conn = get_db_connection()
    conn.execute('UPDATE app_products SET product_id = ? WHERE app = ? AND category = ?', (new_code, app, category))
    conn.commit()
    conn.close()

def get_app_product_info(app, category):
    conn = get_db_connection()
    row = conn.execute('SELECT price, product_id, type, product_type, min_qty, max_qty, price_per_unit FROM app_products WHERE app = ? AND category = ?', (app, category)).fetchone()
    conn.close()
    return row

def add_app_product(app, category, price, product_id, ptype='api', api_source='source1', product_type='package', min_qty=None, max_qty=None, price_per_unit=None):
    conn = get_db_connection()
    max_order = conn.execute('SELECT MAX(display_order) FROM app_products WHERE app = ?', (app,)).fetchone()[0] or 0
    new_order = max_order + 1
    conn.execute('''
        INSERT OR REPLACE INTO app_products (app, category, price, product_id, is_active, display_order, type, api_source, min_qty, max_qty, price_per_unit, product_type)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
    ''', (app, category, price, product_id, new_order, ptype, api_source, min_qty, max_qty, price_per_unit, product_type))
    conn.commit()
    conn.close()

def delete_app_product(app, category):
    conn = get_db_connection()
    conn.execute('DELETE FROM app_products WHERE app = ? AND category = ?', (app, category))
    conn.commit()
    conn.close()

def get_app_product_price(app, category):
    conn = get_db_connection()
    row = conn.execute('SELECT price, price_per_unit, product_type FROM app_products WHERE app = ? AND category = ? AND is_active = 1', (app, category)).fetchone()
    conn.close()
    if row and row['product_type'] == 'quantity':
        return row['price_per_unit']
    return row['price'] if row else None

def link_app_product(app, category, api_product_id, api_source='source1', ptype='api'):
    conn = get_db_connection()
    conn.execute('UPDATE app_products SET product_id = ?, api_source = ?, type = ? WHERE app = ? AND category = ?', (api_product_id, api_source, ptype, app, category))
    conn.commit()
    conn.close()

# ================== دوال إدارة الخدمات (العملات والبطاقات) ==================
def get_all_services():
    conn = get_db_connection()
    services = conn.execute('SELECT service_name, is_active FROM services ORDER BY service_name').fetchall()
    conn.close()
    return services

def add_service(service_name):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO services (service_name, is_active) VALUES (?, 1)', (service_name,))
    conn.commit()
    conn.close()

def delete_service(service_name):
    conn = get_db_connection()
    conn.execute('DELETE FROM services WHERE service_name = ?', (service_name,))
    conn.execute('DELETE FROM service_products WHERE service = ?', (service_name,))
    conn.commit()
    conn.close()

def toggle_service_status(service_name, is_active):
    conn = get_db_connection()
    conn.execute('UPDATE services SET is_active = ? WHERE service_name = ?', (is_active, service_name))
    conn.commit()
    conn.close()

def is_service_active(service_name):
    conn = get_db_connection()
    row = conn.execute('SELECT is_active FROM services WHERE service_name = ?', (service_name,)).fetchone()
    conn.close()
    return row and row['is_active'] == 1

def get_service_products_by_service(service_name, only_active=False, page=1):
    conn = get_db_connection()
    if only_active:
        products = conn.execute('SELECT * FROM service_products WHERE service = ? AND is_active = 1 ORDER BY display_order', (service_name,)).fetchall()
    else:
        products = conn.execute('SELECT * FROM service_products WHERE service = ? ORDER BY display_order', (service_name,)).fetchall()
    conn.close()
    
    total = len(products)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return products[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def toggle_service_product_status(service, category, is_active):
    conn = get_db_connection()
    conn.execute('UPDATE service_products SET is_active = ? WHERE service = ? AND category = ?', (is_active, service, category))
    conn.commit()
    conn.close()

def update_service_product_price(service, category, new_price):
    conn = get_db_connection()
    conn.execute('UPDATE service_products SET price = ? WHERE service = ? AND category = ?', (new_price, service, category))
    conn.commit()
    conn.close()

def update_service_product_code(service, category, new_code):
    conn = get_db_connection()
    conn.execute('UPDATE service_products SET product_id = ? WHERE service = ? AND category = ?', (new_code, service, category))
    conn.commit()
    conn.close()

def get_service_product_info(service, category):
    conn = get_db_connection()
    row = conn.execute('SELECT price, product_id, type, product_type, min_qty, max_qty, price_per_unit FROM service_products WHERE service = ? AND category = ?', (service, category)).fetchone()
    conn.close()
    return row

def add_service_product(service, category, price, product_id=None, ptype='api', api_source='source1', product_type='package', min_qty=None, max_qty=None, price_per_unit=None):
    conn = get_db_connection()
    max_order = conn.execute('SELECT MAX(display_order) FROM service_products WHERE service = ?', (service,)).fetchone()[0] or 0
    new_order = max_order + 1
    conn.execute('''
        INSERT OR REPLACE INTO service_products (service, category, price, product_id, is_active, display_order, type, api_source, min_qty, max_qty, price_per_unit, product_type)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
    ''', (service, category, price, product_id, new_order, ptype, api_source, min_qty, max_qty, price_per_unit, product_type))
    conn.commit()
    conn.close()

def delete_service_product(service, category):
    conn = get_db_connection()
    conn.execute('DELETE FROM service_products WHERE service = ? AND category = ?', (service, category))
    conn.commit()
    conn.close()

def link_service_product(service, category, api_product_id, api_source='source1', ptype='api'):
    conn = get_db_connection()
    conn.execute('UPDATE service_products SET product_id = ?, api_source = ?, type = ? WHERE service = ? AND category = ?', (api_product_id, api_source, ptype, service, category))
    conn.commit()
    conn.close()

def link_api_product(game, category, api_product_id, api_source='source1', ptype='api'):
    conn = get_db_connection()
    conn.execute('UPDATE products SET product_id = ?, api_source = ?, type = ? WHERE game = ? AND category = ?', (api_product_id, api_source, ptype, game, category))
    conn.commit()
    conn.close()

def get_linked_products(page=1):
    conn = get_db_connection()
    products = conn.execute('''
        SELECT game, category, product_id, api_source, type
        FROM products
        WHERE product_id IS NOT NULL AND product_id != ''
        ORDER BY game, category
    ''').fetchall()
    conn.close()
    
    total = len(products)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return products[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def get_api_orders(page=1):
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders WHERE product_id IS NOT NULL ORDER BY order_date DESC').fetchall()
    conn.close()
    
    total = len(orders)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return orders[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

# ================== دوال المستخدمين والرصيد ==================
def get_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user

def create_user(user_id, username, full_name):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)', (user_id, username, full_name))
    conn.commit()
    conn.close()

def update_user_balance(user_id, amount):
    conn = get_db_connection()
    conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return row['balance'] if row else 0

def get_user_total_spent(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT SUM(price) FROM orders WHERE user_id = ? AND api_status IN ("accept", "completed")', (user_id,)).fetchone()
    conn.close()
    return row[0] if row and row[0] else 0

def ban_user(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_db_connection()
    row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else None

def update_setting(key, value):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

# ================== دوال إعدادات سعر الصرف ==================
def get_exchange_rate():
    """الحصول على سعر الصرف الحالي"""
    rate = get_setting('exchange_rate')
    return int(rate) if rate else CREDIT_VALUE

def update_exchange_rate(new_rate):
    """تحديث سعر الصرف"""
    update_setting('exchange_rate', str(new_rate))

def get_user_orders(user_id, page=1):
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC', (user_id,)).fetchall()
    conn.close()
    total = len(orders)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return orders[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def get_user_deposits(user_id, page=1):
    conn = get_db_connection()
    deposits = conn.execute('SELECT * FROM deposit_requests WHERE user_id = ? ORDER BY request_date DESC', (user_id,)).fetchall()
    conn.close()
    total = len(deposits)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return deposits[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def create_order(user_id, game, category, price, player_id, product_id=None, quantity=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (user_id, game, category, price, player_id, product_id, attempts, quantity) VALUES (?, ?, ?, ?, ?, ?, 0, ?)', (user_id, game, category, price, player_id, product_id, quantity))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_last_message(order_id, message_id):
    conn = get_db_connection()
    conn.execute('UPDATE orders SET last_message_id = ? WHERE order_id = ?', (message_id, order_id))
    conn.commit()
    conn.close()

def update_order_admin_notify_msg(order_id, message_id):
    conn = get_db_connection()
    conn.execute('UPDATE orders SET admin_notify_msg_id = ? WHERE order_id = ?', (message_id, order_id))
    conn.commit()
    conn.close()

def update_order_status(order_id, status, admin_action='none'):
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ?, admin_action = ? WHERE order_id = ?', (status, admin_action, order_id))
    conn.commit()
    conn.close()

def update_order_api_status(order_id, api_status):
    conn = get_db_connection()
    conn.execute('UPDATE orders SET api_status = ?, last_check = CURRENT_TIMESTAMP WHERE order_id = ?', (api_status, order_id))
    conn.commit()
    conn.close()

def get_order_details(order_id):
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,)).fetchone()
    conn.close()
    return order

def create_deposit_request(user_id, amount, transaction_id, deposit_type='seriatel'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO deposit_requests (user_id, amount, transaction_id, deposit_type) VALUES (?, ?, ?, ?)', (user_id, amount, transaction_id, deposit_type))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id

def update_deposit_request_status(request_id, status, admin_action='none'):
    conn = get_db_connection()
    conn.execute('UPDATE deposit_requests SET status = ?, admin_action = ? WHERE request_id = ?', (status, admin_action, request_id))
    conn.commit()
    conn.close()

def get_deposit_request(request_id):
    conn = get_db_connection()
    req = conn.execute('SELECT * FROM deposit_requests WHERE request_id = ?', (request_id,)).fetchone()
    conn.close()
    return req

def get_recent_orders(page=1):
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders ORDER BY order_date DESC').fetchall()
    conn.close()
    total = len(orders)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return orders[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def get_recent_deposits(page=1):
    conn = get_db_connection()
    deposits = conn.execute('SELECT * FROM deposit_requests ORDER BY request_date DESC').fetchall()
    conn.close()
    total = len(deposits)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    return deposits[start:end], total, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE if total > 0 else 1

def get_user_stats():
    conn = get_db_connection()
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    active_users = conn.execute('SELECT COUNT(DISTINCT user_id) FROM orders WHERE order_date > ?', (time.time() - 30*24*60*60,)).fetchone()[0]
    banned_users = conn.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1').fetchone()[0]
    pending_deposits = conn.execute('SELECT COUNT(*) FROM deposit_requests WHERE status = "pending"').fetchone()[0]
    completed_orders = conn.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"').fetchone()[0]
    completed_deposits = conn.execute('SELECT COUNT(*) FROM deposit_requests WHERE status = "completed"').fetchone()[0]
    api_success = conn.execute('SELECT COUNT(*) FROM orders WHERE api_status IN ("accept", "completed", "wait")').fetchone()[0]
    api_failed = conn.execute('SELECT COUNT(*) FROM orders WHERE api_status IN ("reject", "failed")').fetchone()[0]
    conn.close()
    return {
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'pending_deposits': pending_deposits,
        'completed_orders': completed_orders,
        'completed_deposits': completed_deposits,
        'api_success': api_success,
        'api_failed': api_failed
    }

def is_admin(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT 1 FROM admins WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return row is not None

def is_main_admin(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT is_main_admin FROM admins WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return row and row['is_main_admin'] == 1

def add_admin(user_id):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM admins WHERE user_id = ? AND is_main_admin = 0', (user_id,))
    conn.commit()
    conn.close()

def get_all_admins():
    conn = get_db_connection()
    admins = conn.execute('SELECT user_id, is_main_admin FROM admins').fetchall()
    conn.close()
    return admins

def set_mandatory_channel(channel_id, channel_link):
    conn = get_db_connection()
    conn.execute('DELETE FROM mandatory_channel')
    conn.execute('INSERT INTO mandatory_channel (channel_id, channel_link, is_active) VALUES (?, ?, ?)', (channel_id, channel_link, 1))
    conn.commit()
    conn.close()

def get_mandatory_channel():
    conn = get_db_connection()
    channel = conn.execute('SELECT channel_id, channel_link, is_active FROM mandatory_channel LIMIT 1').fetchone()
    conn.close()
    return channel

def toggle_mandatory_channel(is_active):
    conn = get_db_connection()
    conn.execute('UPDATE mandatory_channel SET is_active = ?', (is_active,))
    conn.commit()
    conn.close()

def get_deposit_method_status(method_name):
    conn = get_db_connection()
    row = conn.execute('SELECT is_active FROM deposit_methods WHERE method_name = ?', (method_name,)).fetchone()
    conn.close()
    return row['is_active'] if row else 0

def toggle_deposit_method(method_name, status):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO deposit_methods (method_name, is_active) VALUES (?, ?)', (method_name, status))
    conn.commit()
    conn.close()

def is_deposit_method_active(method_name):
    return get_deposit_method_status(method_name) == 1

def get_channel_setting(key):
    conn = get_db_connection()
    row = conn.execute('SELECT value FROM channel_settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return row['value'] if row else None

def update_channel_setting(key, value):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO channel_settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def _get_status_text(api_status):
    return {
        'wait': '🔄 جاري التنفيذ',
        'processing': '🔄 جاري التنفيذ',
        'pending': '🔄 جاري التنفيذ',
        'accept': '✅ تم تنفيذ طلبك',
        'completed': '✅ تم تنفيذ طلبك',
        'reject': '❌ مرفوض - تم إرجاع المبلغ',
        'rejected': '❌ مرفوض - تم إرجاع المبلغ',
        'failed': '❌ مرفوض - تم إرجاع المبلغ',
        'insufficient_balance': '❌ رصيد الموقع غير كافي - تم إرجاع المبلغ'
    }.get(api_status, '🔄 جاري التنفيذ')

# ================== دوال إشعارات جديدة ==================
def send_new_user_notification(user_id, full_name, username):
    """إرسال إشعار عند دخول مستخدم جديد"""
    total_users = get_user_stats()['total_users']
    
    text = f"""
*تم دخول شخص جديد إلى البوت الخاص بك* 👾
-----------------------
• معلومات العضو الجديد :

• الاسم : {full_name}
• معرف : @{username}
• الايدي : `{user_id}`
-----------------------
• عدد الأعضاء الكلي : {total_users}
    """
    
    new_users_channel = get_channel_setting('new_users_channel_id')
    send_to_channels = get_channel_setting('send_to_channels')
    
    if new_users_channel and send_to_channels == '1':
        try:
            bot.send_message(new_users_channel, text, parse_mode='Markdown')
            return
        except:
            pass
    
    for admin in get_all_admins():
        try:
            bot.send_message(admin['user_id'], text, parse_mode='Markdown')
        except:
            pass

def send_new_order_notification(order_id, user_id, game, category, price, player_id, quantity=1):
    """إرسال إشعار طلب جديد للمشرفين وتخزين message_id"""
    user = get_user(user_id)
    full_name = user['full_name'] if user and user['full_name'] else 'غير معروف'
    username = user['username'] if user and user['username'] else 'لا يوجد'
    
    text = f"""
🆕 طلب شحن جديد
━━━━━━━━━━━━━━
👤 المستخدم: {full_name}
🆔 ايدي: `{user_id}`
📱 يوزر: @{username}
━━━━━━━━━━━━━━
🎮 الخدمة: {game}
📦 الفئة: {category}
💰 السعر: {price} ل.س
🆔 معرف اللاعب: `{player_id}`
📦 الكمية: {quantity}
━━━━━━━━━━━━━━
📊 الحالة: ⏳ قيد المعالجة
    """
    
    orders_channel = get_channel_setting('orders_channel_id')
    send_to_channels = get_channel_setting('send_to_channels')
    
    sent_message = None
    
    if orders_channel and send_to_channels == '1':
        try:
            sent_message = bot.send_message(orders_channel, text, parse_mode='Markdown')
        except:
            pass
    
    if not sent_message:
        for admin in get_all_admins():
            try:
                sent_message = bot.send_message(admin['user_id'], text, parse_mode='Markdown')
                break
            except:
                continue
    
    if sent_message:
        update_order_admin_notify_msg(order_id, sent_message.message_id)

def update_order_notification(order_id, new_status):
    """تحديث رسالة إشعار الطلب عند تغيير الحالة"""
    order = get_order_details(order_id)
    if not order or not order['admin_notify_msg_id']:
        return
    
    user = get_user(order['user_id'])
    full_name = user['full_name'] if user and user['full_name'] else 'غير معروف'
    username = user['username'] if user and user['username'] else 'لا يوجد'
    
    status_emoji = {
        'accept': '✅',
        'reject': '❌',
        'pending': '⏳',
        'wait': '⏳',
        'processing': '⏳',
        'completed': '✅',
        'failed': '❌'
    }.get(new_status, '⏳')
    
    status_text = _get_status_text(new_status)
    
    text = f"""
{status_emoji} تحديث حالة الطلب #{order_id}
━━━━━━━━━━━━━━
👤 المستخدم: {full_name}
🆔 ايدي: `{order['user_id']}`
📱 يوزر: @{username}
━━━━━━━━━━━━━━
🎮 الخدمة: {order['game']}
📦 الفئة: {order['category']}
💰 السعر: {order['price']} ل.س
🆔 معرف اللاعب: `{order['player_id']}`
📦 الكمية: {order['quantity']}
━━━━━━━━━━━━━━
📊 الحالة: {status_text}
    """
    
    try:
        bot.edit_message_text(chat_id=order['admin_notify_msg_id'], text=text, parse_mode='Markdown')
    except:
        pass

# ================== دوال إنشاء لوحات المفاتيح ==================
def create_main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.row(
        types.InlineKeyboardButton("شــحن تطبيقــات", callback_data="apps"),
        types.InlineKeyboardButton("شــحن ألــعاب", callback_data="games")
    )
    keyboard.row(types.InlineKeyboardButton("الــبطاقات و الــعملات الــرقمية", callback_data="currencies"))
    keyboard.row(
        types.InlineKeyboardButton("مــعلومات حــسابي", callback_data="account"),
        types.InlineKeyboardButton("تــعبئة رصــيدي", callback_data="deposit_methods")
    )
    keyboard.row(types.InlineKeyboardButton("حــساب الإدارة", callback_data="help"))
    return keyboard

def create_games_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    games = get_all_games()
    for game in games:
        if game['is_active'] == 1:
            game_name = game['game_name']
            keyboard.add(types.InlineKeyboardButton(game_name, callback_data=f"game_{game_name}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return keyboard

def create_categories_keyboard(game, is_admin=False):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    conn = get_db_connection()
    if is_admin:
        products = conn.execute('SELECT category, price, is_active, product_type, min_qty, max_qty, price_per_unit FROM products WHERE game = ? ORDER BY display_order', (game,)).fetchall()
    else:
        products = conn.execute('SELECT category, price, product_type, min_qty, max_qty, price_per_unit FROM products WHERE game = ? AND is_active = 1 ORDER BY display_order', (game,)).fetchall()
    conn.close()
    
    for row in products:

        display_price = row['price_per_unit'] if row['product_type'] == 'quantity' else row['price']
        
        if is_admin:
            btn_text = f"{row['category']} - {display_price} ل.س {'(غير مفعل)' if not row['is_active'] else ''}"
            callback = f"admin_category_{game}_{row['category']}"
        else:
            btn_text = f"{row['category']} - {display_price} ل.س"
            callback = f"category_{game}_{row['category']}"
            
        keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=callback))
    
    back_target = "games" if not is_admin else "admin_main"
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=back_target))
    return keyboard

def create_apps_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    apps = get_all_apps()
    for app in apps:
        if app['is_active'] == 1:
            app_name = app['app_name']
            keyboard.add(types.InlineKeyboardButton(app_name, callback_data=f"app_{app_name}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return keyboard

def create_app_categories_keyboard(app, is_admin=False):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    conn = get_db_connection()
    if is_admin:
        products = conn.execute('SELECT category, price, is_active, product_type, min_qty, max_qty, price_per_unit FROM app_products WHERE app = ? ORDER BY display_order', (app,)).fetchall()
    else:
        products = conn.execute('SELECT category, price, product_type, min_qty, max_qty, price_per_unit FROM app_products WHERE app = ? AND is_active = 1 ORDER BY display_order', (app,)).fetchall()
    conn.close()
    
    for row in products:

        display_price = row['price_per_unit'] if row['product_type'] == 'quantity' else row['price']
        
        if is_admin:
            btn_text = f"{row['category']} - {display_price} ل.س {'(غير مفعل)' if not row['is_active'] else ''}"
            callback = f"admin_app_category_{app}_{row['category']}"
        else:
            btn_text = f"{row['category']} - {display_price} ل.س"
            callback = f"category_app_{app}_{row['category']}"
            
        keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=callback))
    
    back_target = "apps" if not is_admin else "admin_main"
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=back_target))
    return keyboard

def create_services_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    services = get_all_services()
    for service in services:
        if service['is_active'] == 1:
            service_name = service['service_name']
            keyboard.add(types.InlineKeyboardButton(service_name, callback_data=f"service_{service_name}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return keyboard

def create_service_categories_keyboard(service, is_admin=False):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    conn = get_db_connection()
    if is_admin:
        products = conn.execute('SELECT category, price, is_active, product_type, min_qty, max_qty, price_per_unit FROM service_products WHERE service = ? ORDER BY display_order', (service,)).fetchall()
    else:
        products = conn.execute('SELECT category, price, product_type, min_qty, max_qty, price_per_unit FROM service_products WHERE service = ? AND is_active = 1 ORDER BY display_order', (service,)).fetchall()
    conn.close()
    
    for row in products:

        display_price = row['price_per_unit'] if row['product_type'] == 'quantity' else row['price']
        
        if is_admin:
            btn_text = f"{row['category']} - {display_price} ل.س {'(غير مفعل)' if not row['is_active'] else ''}"
            callback = f"admin_service_category_{service}_{row['category']}"
        else:
            btn_text = f"{row['category']} - {display_price} ل.س"
            callback = f"category_service_{service}_{row['category']}"
            
        keyboard.add(types.InlineKeyboardButton(btn_text, callback_data=callback))
    
    back_target = "currencies" if not is_admin else "admin_main"
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=back_target))
    return keyboard

def create_confirmation_keyboard(order_id):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("تأكيد العملية✅", callback_data=f"confirm_{order_id}"),
        types.InlineKeyboardButton("ألغاء العملية❌", callback_data=f"cancel_{order_id}")
    )
    return keyboard

def create_deposit_methods_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    if is_deposit_method_active('seriatel'):
        keyboard.add(types.InlineKeyboardButton("𝑺𝒀𝑹 𝑪𝑨𝑺𝑯 (𝑨𝑼𝑻𝑶)", callback_data="deposit_seriatel"))
    if is_deposit_method_active('seriatel_manual'):
        keyboard.add(types.InlineKeyboardButton("𝑺𝒀𝑹 𝑪𝑨𝑺𝑯 (𝑴𝑨𝑵𝑼𝑨𝑳)", callback_data="deposit_seriatel_manual"))
    if is_deposit_method_active('sham_dollar'):
        keyboard.add(types.InlineKeyboardButton("𝑺𝑯𝑨𝑴 𝑪𝑨𝑺𝑯 (𝑫𝑶𝑳𝑳𝑨𝑹)", callback_data="deposit_sham_dollar"))
    if is_deposit_method_active('sham_lira'):
        keyboard.add(types.InlineKeyboardButton("𝑺𝑯𝑨𝑴 𝑪𝑨𝑺𝑯 (𝑳𝑰𝑹𝑨)", callback_data="deposit_sham_lira"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="main_menu"))
    return keyboard

def create_admin_main_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        types.InlineKeyboardButton("طلبات الشحن", callback_data="admin_recent_orders"),
        types.InlineKeyboardButton("طلبات الإيداع", callback_data="admin_recent_deposits")
    )
    keyboard.add(types.InlineKeyboardButton("الإحصائيات", callback_data="admin_stats"))
    keyboard.add(
        types.InlineKeyboardButton("إضافة رصيد", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("خصم رصيد", callback_data="admin_deduct_balance")
    )
    keyboard.add(
        types.InlineKeyboardButton("حظر عضو", callback_data="admin_ban_user"),
        types.InlineKeyboardButton("رفع حظر", callback_data="admin_unban_user")
    )
    keyboard.add(types.InlineKeyboardButton("معلومات عضو", callback_data="admin_user_info"))
    keyboard.add(
        types.InlineKeyboardButton("تغيير سيرياتيل أوتو", callback_data="admin_change_seriatel_auto"),
        types.InlineKeyboardButton("تغيير سيرياتيل يدوي", callback_data="admin_change_seriatel_manual")
    )
    keyboard.add(
        types.InlineKeyboardButton("تغيير شام دولار", callback_data="admin_change_sham_dollar"),
        types.InlineKeyboardButton("تغيير شام ليرة", callback_data="admin_change_sham_lira")
    )
    keyboard.add(
        types.InlineKeyboardButton("إعدادات SMS", callback_data="admin_sms_settings"),
        types.InlineKeyboardButton("قنوات الطلبات", callback_data="admin_orders_channels")
    )
    keyboard.add(types.InlineKeyboardButton("إدارة الصور", callback_data="admin_images_main"))
    keyboard.add(types.InlineKeyboardButton("تشغيل/إيقاف البوت", callback_data="admin_toggle_bot"))
    keyboard.add(
        types.InlineKeyboardButton("تغيير يوزر الدعم", callback_data="admin_change_support"),
        types.InlineKeyboardButton("إذاعة رسالة", callback_data="admin_broadcast")
    )
    keyboard.add(
        types.InlineKeyboardButton("التحكم بطرق الدفع", callback_data="admin_deposit_methods"),
        types.InlineKeyboardButton("تغيير رسالة البدء", callback_data="admin_change_welcome")
    )
    keyboard.add(
        types.InlineKeyboardButton("إدارة المنتجات", callback_data="admin_manage_products_main"),
        types.InlineKeyboardButton("إدارة الألعاب", callback_data="admin_manage_games")
    )
    keyboard.add(
        types.InlineKeyboardButton("إدارة التطبيقات", callback_data="admin_manage_apps"),
        types.InlineKeyboardButton("إدارة العملات والبطاقات", callback_data="admin_manage_services")
    )
    keyboard.add(types.InlineKeyboardButton("إدارة API", callback_data="admin_api_management"))
    
    if is_main_admin(user_id):
        keyboard.add(
            types.InlineKeyboardButton("الاشتراك الإجباري", callback_data="admin_channel_settings"),
            types.InlineKeyboardButton("إدارة المشرفين", callback_data="admin_admins_panel")
        )
        current_rate = get_exchange_rate()
        keyboard.add(
            types.InlineKeyboardButton(f"سعر الصرف: {current_rate}", callback_data="admin_exchange_rate")
        )

    return keyboard

def create_manage_products_main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🎮 ألعاب", callback_data="admin_manage_products_games"),
        types.InlineKeyboardButton("📱 تطبيقات", callback_data="admin_manage_products_apps"),
        types.InlineKeyboardButton("💳 خدمات", callback_data="admin_manage_products_services")
    )
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_manage_products_games_keyboard():
    games = get_all_games()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for game in games:
        keyboard.add(types.InlineKeyboardButton(game['game_name'], callback_data=f"admin_products_game_{game['game_name']}_1"))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_product_select_game"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_main"))
    return keyboard

def create_manage_products_apps_keyboard():
    apps = get_all_apps()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(app['app_name'], callback_data=f"admin_app_products_app_{app['app_name']}_1"))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_app_product_select_app"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_main"))
    return keyboard

def create_manage_products_services_keyboard():
    services = get_all_services()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for service in services:
        safe_service_name = service['service_name'].replace(' ', '_')
        keyboard.add(types.InlineKeyboardButton(
            service['service_name'], 
            callback_data=f"admin_service_products_service_{safe_service_name}_1"
        ))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_service_product_select_service"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_main"))
    return keyboard

def create_manage_games_keyboard():
    games = get_all_games()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for game in games:
        status = "✅" if game['is_active'] else "❌"
        keyboard.add(types.InlineKeyboardButton(f"{status} {game['game_name']}", callback_data=f"admin_toggle_game_{game['game_name']}"))
    keyboard.add(
        types.InlineKeyboardButton("➕ إضافة لعبة جديدة", callback_data="admin_add_game"),
        types.InlineKeyboardButton("➖ حذف لعبة", callback_data="admin_delete_game")
    )
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_delete_game_keyboard():
    games = get_all_games()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for game in games:
        keyboard.add(types.InlineKeyboardButton(f"🗑️ {game['game_name']}", callback_data=f"admin_confirm_delete_game_{game['game_name']}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_games"))
    return keyboard

def create_manage_apps_keyboard():
    apps = get_all_apps()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for app in apps:
        status = "✅" if app['is_active'] else "❌"
        keyboard.add(types.InlineKeyboardButton(f"{status} {app['app_name']}", callback_data=f"admin_toggle_app_{app['app_name']}"))
    keyboard.add(
        types.InlineKeyboardButton("➕ إضافة تطبيق جديد", callback_data="admin_add_app"),
        types.InlineKeyboardButton("➖ حذف تطبيق", callback_data="admin_delete_app")
    )
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_delete_app_keyboard():
    apps = get_all_apps()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(f"🗑️ {app['app_name']}", callback_data=f"admin_confirm_delete_app_{app['app_name']}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_apps"))
    return keyboard

def create_manage_services_keyboard():
    services = get_all_services()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for service in services:
        status = "✅" if service['is_active'] else "❌"
        keyboard.add(types.InlineKeyboardButton(f"{status} {service['service_name']}", callback_data=f"admin_toggle_service_{service['service_name']}"))
    keyboard.add(
        types.InlineKeyboardButton("➕ إضافة خدمة جديدة", callback_data="admin_add_service"),
        types.InlineKeyboardButton("➖ حذف خدمة", callback_data="admin_delete_service")
    )
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_delete_service_keyboard():
    services = get_all_services()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for service in services:
        keyboard.add(types.InlineKeyboardButton(f"🗑️ {service['service_name']}", callback_data=f"admin_confirm_delete_service_{service['service_name']}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_services"))
    return keyboard

def create_manage_products_keyboard():
    games = get_all_games()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for game in games:
        keyboard.add(types.InlineKeyboardButton(game['game_name'], callback_data=f"admin_products_game_{game['game_name']}_1"))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_product_select_game"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_manage_app_products_keyboard():
    apps = get_all_apps()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for app in apps:
        keyboard.add(types.InlineKeyboardButton(app['app_name'], callback_data=f"admin_app_products_app_{app['app_name']}_1"))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_app_product_select_app"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_manage_service_products_keyboard():
    services = get_all_services()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for service in services:
        keyboard.add(types.InlineKeyboardButton(service['service_name'], callback_data=f"admin_service_products_service_{service['service_name']}_1"))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data="admin_add_service_product_select_service"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_product_actions_keyboard(game, category):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    conn = get_db_connection()
    row = conn.execute('SELECT is_active, type, product_type FROM products WHERE game = ? AND category = ?', (game, category)).fetchone()
    conn.close()
    is_active, ptype, product_type = (row['is_active'], row['type'], row['product_type']) if row else (1, 'api', 'package')
    
    keyboard.add(
        types.InlineKeyboardButton("💰 تغيير السعر", callback_data=f"admin_change_price_{game}_{category}"),
        types.InlineKeyboardButton("🔑 تغيير رمز API", callback_data=f"admin_change_api_{game}_{category}")
    )
    
    if product_type == 'quantity':
        keyboard.add(types.InlineKeyboardButton("📊 تعديل الكميات", callback_data=f"admin_edit_quantity_{game}_{category}"))
    
    if is_active:
        keyboard.add(types.InlineKeyboardButton("⛔ تعطيل", callback_data=f"admin_deactivate_{game}_{category}"))
    else:
        keyboard.add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"admin_activate_{game}_{category}"))
    
    keyboard.add(types.InlineKeyboardButton("🗑️ حذف المنتج", callback_data=f"admin_delete_product_{game}_{category}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=f"admin_products_game_{game}_1"))
    return keyboard

def create_app_product_actions_keyboard(app, category):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    conn = get_db_connection()
    row = conn.execute('SELECT is_active, type, product_type FROM app_products WHERE app = ? AND category = ?', (app, category)).fetchone()
    conn.close()
    is_active, ptype, product_type = (row['is_active'], row['type'], row['product_type']) if row else (1, 'api', 'package')
    
    keyboard.add(
        types.InlineKeyboardButton("💰 تغيير السعر", callback_data=f"admin_change_app_price_{app}_{category}"),
        types.InlineKeyboardButton("🔑 تغيير رمز API", callback_data=f"admin_change_app_api_{app}_{category}")
    )
    
    if product_type == 'quantity':
        keyboard.add(types.InlineKeyboardButton("📊 تعديل الكميات", callback_data=f"admin_edit_app_quantity_{app}_{category}"))
    
    if is_active:
        keyboard.add(types.InlineKeyboardButton("⛔ تعطيل", callback_data=f"admin_deactivate_app_{app}_{category}"))
    else:
        keyboard.add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"admin_activate_app_{app}_{category}"))
    
    keyboard.add(types.InlineKeyboardButton("🗑️ حذف المنتج", callback_data=f"admin_delete_app_product_{app}_{category}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=f"admin_app_products_app_{app}_1"))
    return keyboard

def create_service_product_actions_keyboard(service, category):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    conn = get_db_connection()
    row = conn.execute('SELECT is_active, type, product_type FROM service_products WHERE service = ? AND category = ?', (service, category)).fetchone()
    conn.close()
    is_active, ptype, product_type = (row['is_active'], row['type'], row['product_type']) if row else (1, 'api', 'package')
    
    keyboard.add(
        types.InlineKeyboardButton("💰 تغيير السعر", callback_data=f"admin_change_service_price_{service}_{category}")
    )
    
    if product_type == 'quantity':
        keyboard.add(types.InlineKeyboardButton("📊 تعديل الكميات", callback_data=f"admin_edit_service_quantity_{service}_{category}"))
    
    # للباقة أو الكمية يوجد زر تغيير رمز API
    if product_type == 'package' or product_type == 'quantity':
        keyboard.add(types.InlineKeyboardButton("🔑 تغيير رمز API", callback_data=f"admin_change_service_api_{service}_{category}"))
    
    if is_active:
        keyboard.add(types.InlineKeyboardButton("⛔ تعطيل", callback_data=f"admin_deactivate_service_{service}_{category}"))
    else:
        keyboard.add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"admin_activate_service_{service}_{category}"))
    
    keyboard.add(types.InlineKeyboardButton("🗑️ حذف المنتج", callback_data=f"admin_delete_service_product_{service}_{category}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=f"admin_service_products_service_{service}_1"))
    return keyboard

def create_game_codes_keyboard():
    # تم إزالتها لأن نظام الأكواد ألغي
    return create_back_keyboard("admin_main")

def create_codes_management_keyboard(game, category, page=1, total_pages=1):
    # تم إزالتها لأن نظام الأكواد ألغي
    return create_back_keyboard("admin_main")

def create_api_management_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🧪 اختبار الاتصال", callback_data="admin_api_test"),
        types.InlineKeyboardButton("🔍 بحث منتج", callback_data="admin_api_search")
    )
    keyboard.add(
        types.InlineKeyboardButton("🔗 ربط منتج", callback_data="admin_api_link_select_game"),
        types.InlineKeyboardButton("📋 المنتجات المرتبطة", callback_data="admin_api_linked_1")
    )
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_api_link_game_keyboard():
    games = get_all_games()
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for game in games:
        keyboard.add(types.InlineKeyboardButton(game['game_name'], callback_data=f"admin_api_link_game_{game['game_name']}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_api_management"))
    return keyboard

def create_api_link_product_keyboard(game):
    conn = get_db_connection()
    products = conn.execute('SELECT category FROM products WHERE game = ? ORDER BY display_order', (game,)).fetchall()
    conn.close()
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for p in products:
        keyboard.add(types.InlineKeyboardButton(p['category'], callback_data=f"admin_api_link_product_{game}_{p['category']}"))
    keyboard.add(types.InlineKeyboardButton("➕ إضافة منتج جديد", callback_data=f"admin_api_add_product_{game}"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_api_link_select_game"))
    return keyboard

def create_back_keyboard(target):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data=target))
    return keyboard

def create_broadcast_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("إرسال للجميع", callback_data="admin_broadcast_all"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_orders_channels_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    send_to_channels = get_channel_setting('send_to_channels')
    toggle_status = "تعطيل" if send_to_channels == '1' else "تفعيل"
    toggle_data = '0' if send_to_channels == '1' else '1'
    keyboard.add(types.InlineKeyboardButton(f"{toggle_status} إرسال للقنوات", callback_data=f"admin_toggle_orders_channels_{toggle_data}"))
    keyboard.add(types.InlineKeyboardButton("🔗 قناة طلبات الشحن", callback_data="admin_set_orders_channel"))
    keyboard.add(types.InlineKeyboardButton("🔗 قناة طلبات الإيداع", callback_data="admin_set_deposits_channel"))
    keyboard.add(types.InlineKeyboardButton("🔗 قناة المستخدمين الجدد", callback_data="admin_set_new_users_channel"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_sms_settings_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("تحديد قناة SMS", callback_data="admin_set_sms_channel"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_admins_list_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    admins = get_all_admins()
    for admin in admins:
        if not admin['is_main_admin']:
            keyboard.add(types.InlineKeyboardButton(f"حذف المشرف {admin['user_id']}", callback_data=f"admin_remove_{admin['user_id']}"))
    keyboard.add(types.InlineKeyboardButton("إضافة مشرف جديد", callback_data="admin_add_new_admin"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_channel_settings_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    channel = get_mandatory_channel()
    if channel and channel['is_active'] == 1:
        keyboard.add(types.InlineKeyboardButton("تعطيل الاشتراك الإجباري", callback_data="admin_toggle_channel_0"))
    else:
        keyboard.add(types.InlineKeyboardButton("تفعيل الاشتراك الإجباري", callback_data="admin_toggle_channel_1"))
    keyboard.add(types.InlineKeyboardButton("تحديد القناة", callback_data="admin_set_channel"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_deposit_methods_control_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    seriatel_active = is_deposit_method_active('seriatel')
    seriatel_manual_active = is_deposit_method_active('seriatel_manual')
    sham_dollar_active = is_deposit_method_active('sham_dollar')
    sham_lira_active = is_deposit_method_active('sham_lira')
    
    keyboard.add(types.InlineKeyboardButton(
        f"{'تعطيل' if seriatel_active else 'تفعيل'} سيرياتيل كاش (أوتوماتيك)",
        callback_data=f"admin_toggle_deposit_seriatel_{'0' if seriatel_active else '1'}"
    ))
    keyboard.add(types.InlineKeyboardButton(
        f"{'تعطيل' if seriatel_manual_active else 'تفعيل'} سيرياتيل كاش (يدوي)",
        callback_data=f"admin_toggle_deposit_seriatel_manual_{'0' if seriatel_manual_active else '1'}"
    ))
    keyboard.add(types.InlineKeyboardButton(
        f"{'تعطيل' if sham_dollar_active else 'تفعيل'} شام دولار",
        callback_data=f"admin_toggle_deposit_sham_dollar_{'0' if sham_dollar_active else '1'}"
    ))
    keyboard.add(types.InlineKeyboardButton(
        f"{'تعطيل' if sham_lira_active else 'تفعيل'} شام ليرة",
        callback_data=f"admin_toggle_deposit_sham_lira_{'0' if sham_lira_active else '1'}"
    ))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

def create_images_main_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("رسالة البدء", callback_data="admin_image_start"))
    keyboard.add(types.InlineKeyboardButton("قائمة الألعاب", callback_data="admin_image_games"))
    keyboard.add(types.InlineKeyboardButton("قائمة التطبيقات", callback_data="admin_image_apps"))
    keyboard.add(types.InlineKeyboardButton("قائمة العملات والبطاقات", callback_data="admin_image_services"))
    keyboard.add(types.InlineKeyboardButton("صورة لعبة محددة", callback_data="admin_image_game_select"))
    keyboard.add(types.InlineKeyboardButton("صورة تطبيق محدد", callback_data="admin_image_app_select"))
    keyboard.add(types.InlineKeyboardButton("صورة خدمة محددة", callback_data="admin_image_service_select"))
    keyboard.add(types.InlineKeyboardButton("صورة منتج لعبة محدد", callback_data="admin_image_product_game_select"))
    keyboard.add(types.InlineKeyboardButton("صورة منتج تطبيق محدد", callback_data="admin_image_app_product_select"))
    keyboard.add(types.InlineKeyboardButton("صورة منتج خدمة محددة", callback_data="admin_image_service_product_select"))
    keyboard.add(types.InlineKeyboardButton("صورة طريقة دفع", callback_data="admin_image_currency_select"))
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    return keyboard

# ================== دوال عرض الصفحات ==================
def show_user_orders_page(chat_id, message_id, user_id, orders, page, total_pages):
    if not orders:
        safe_edit_message_text(chat_id, message_id, "📭 لم تقم بعمليات شحن بعد.", create_back_keyboard("account"))
        return
    
    text = f"🛒 طلبات الشحن (صفحة {page}/{total_pages}):\n\n"
    for o in orders:
        status_text = _get_status_text(o['api_status'])
        text += f"#{o['order_id']} - {o['game']} - {o['category']}\n"
        text += f"💰 {o['price']} ل.س\n"
        if o['quantity'] > 1:
            text += f"📦 الكمية: {o['quantity']}\n"
        text += f"📊 {status_text}\n"
        text += f"🆔 اللاعب: `{o['player_id']}`\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"my_purchase_orders_page_{page-1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"my_purchase_orders_page_{page+1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="account"))
    safe_edit_message_text(chat_id, message_id, text, keyboard, parse_mode="Markdown")

def show_user_deposits_page(chat_id, message_id, user_id, deposits, page, total_pages):
    if not deposits:
        safe_edit_message_text(chat_id, message_id, "📭 لم تقم بعمليات إيداع بعد.", create_back_keyboard("account"))
        return
    
    text = f"💳 طلبات الإيداع (صفحة {page}/{total_pages}):\n\n"
    for d in deposits:
        status_text = "معلق" if d['status'] == 'pending' else "مكتمل" if d['status'] == 'completed' else "مرفوض"
        type_names = {
            'seriatel': 'سيرياتيل (أوتو)',
            'seriatel_manual': 'سيرياتيل (يدوي)',
            'sham_dollar': 'شام دولار',
            'sham_lira': 'شام ليرة'
        }
        dep_type = type_names.get(d['deposit_type'], d['deposit_type'])
        text += f"#{d['request_id']} - 💰: {d['amount']} ل.س ({dep_type})\n"
        text += f"📊 {status_text}\n"
        text += f"🔢 {d['transaction_id']}\n"
        text += f"📅 {d['request_date'][:16] if d['request_date'] else 'N/A'}\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"my_deposit_orders_page_{page-1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"my_deposit_orders_page_{page+1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="account"))
    safe_edit_message_text(chat_id, message_id, text, keyboard)

def show_admin_orders_page(chat_id, message_id, orders, page, total_pages):
    if not orders:
        safe_edit_message_text(chat_id, message_id, "لا توجد طلبات حالياً", create_back_keyboard("admin_main"))
        return
    
    text = f"📋 طلبات الشحن (صفحة {page}/{total_pages}):\n\n"
    for o in orders:
        status_text = _get_status_text(o['api_status'])
        text += f"#{o['order_id']} - {o['game']} - {o['category']}\n"
        text += f"👤: {o['user_id']} | 💰: {o['price']} | 📊: {status_text}\n"
        if o['quantity'] > 1:
            text += f"📦 الكمية: {o['quantity']}\n"
        text += f"🆔: `{o['player_id'][:20]}` | 📅: {o['order_date'][:16] if o['order_date'] else 'N/A'}\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_recent_orders_page_{page-1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_recent_orders_page_{page+1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    safe_edit_message_text(chat_id, message_id, text, keyboard, parse_mode="Markdown")

def show_admin_deposits_page(chat_id, message_id, deposits, page, total_pages):
    if not deposits:
        safe_edit_message_text(chat_id, message_id, "لا توجد طلبات إيداع حالياً", create_back_keyboard("admin_main"))
        return
    
    text = f"💳 طلبات الإيداع (صفحة {page}/{total_pages}):\n\n"
    for d in deposits:
        status_text = "معلق" if d['status'] == 'pending' else "مكتمل" if d['status'] == 'completed' else "مرفوض"
        type_names = {
            'seriatel': 'سيرياتيل (أوتو)',
            'seriatel_manual': 'سيرياتيل (يدوي)',
            'sham_dollar': 'شام دولار',
            'sham_lira': 'شام ليرة'
        }
        dep_type = type_names.get(d['deposit_type'], d['deposit_type'])
        text += f"#{d['request_id']} - 💰: {d['amount']} ل.س ({dep_type})\n"
        text += f"👤: {d['user_id']} | 📊: {status_text}\n"
        text += f"🔢: {d['transaction_id']} | 📅: {d['request_date'][:16] if d['request_date'] else 'N/A'}\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_recent_deposits_page_{page-1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_recent_deposits_page_{page+1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    safe_edit_message_text(chat_id, message_id, text, keyboard)

def show_api_orders_page(chat_id, message_id, orders, page, total_pages):
    text = f"📊 طلبات API (صفحة {page}/{total_pages}):\n\n"
    for o in orders:
        status_text = _get_status_text(o['api_status'] or 'pending')
        text += f"#{o['order_id']} - {o['game']} - {o['category']}\n👤 {o['user_id']} | {status_text}\n🆔 `{o['player_id'][:20]}`\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_api_orders_page_{page-1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_api_orders_page_{page+1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_main"))
    safe_edit_message_text(chat_id, message_id, text, keyboard, parse_mode="Markdown")

def show_linked_products_page(chat_id, message_id, products, page, total_pages):
    if not products:
        bot.send_message(chat_id, "لا توجد منتجات مرتبطة.")
        return
    
    text = f"📋 المنتجات المرتبطة (صفحة {page}/{total_pages}):\n\n"
    for p in products:
        text += f"🎮 {p['game']} - {p['category']}\n🆔 `{p['product_id']}`\n🌐 {p['api_source']}\n📦 {p['type']}\n\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav = []
    if page > 1:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_api_linked_{page-1}"))
    if page < total_pages:
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_api_linked_{page+1}"))
    if nav:
        keyboard.add(*nav)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_api_management"))
    safe_edit_message_text(chat_id, message_id, text, keyboard, parse_mode="Markdown")

# ================== دوال التحقق من الاشتراك الإجباري ==================
def check_mandatory_subscription(user_id):
    channel_info = get_mandatory_channel()
    if not channel_info or not channel_info['is_active']:
        return True, None, None
    
    try:
        member = bot.get_chat_member(chat_id=channel_info['channel_id'], user_id=user_id)
        if member.status in ['member', 'creator', 'administrator']:
            return True, None, None
        else:
            return False, channel_info['channel_link'], channel_info['channel_id']
    except:
        return False, channel_info['channel_link'], channel_info['channel_id']

# ================== دوال مساعدة للتعامل الآمن مع التعديل ==================
def safe_delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        print(f"⚠️ فشل حذف الرسالة {message_id}: {e}")

def safe_edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    try:
        bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception as e:
        # إذا فشل التعديل (ربما لأن الرسالة محذوفة أو تحتوي على صورة)، نرسل رسالة جديدة
        try:
            bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except:
            return False

# ================== دوال مساعدة للخطوات ==================
def save_step(user_id, step):
    with open(f"steps/{user_id}", 'w', encoding='utf-8') as f:
        f.write(step)

def get_step(user_id):
    try:
        with open(f"steps/{user_id}", 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return None

def delete_step(user_id):
    try:
        os.remove(f"steps/{user_id}")
    except:
        pass

# ================== معالجة الأوامر الرئيسية ==================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    full_name = message.from_user.full_name or "غير معروف"
    
    user = get_user(user_id)
    if user and user['is_banned'] == 1:
        bot.send_message(message.chat.id, "🚫 تم حظرك من استخدام البوت ، تواصل مع @Bar0nSupport لمعرفة سبب الحظر")
        return
    
    is_subscribed, channel_link, channel_id = check_mandatory_subscription(user_id)
    if not is_subscribed:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("اضغط للانضمام للقناة", url=channel_link))
        keyboard.add(types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription"))
        bot.send_message(message.chat.id, "📢 يجب عليك الانضمام إلى قناتنا لمتابعة استخدام البوت .", reply_markup=keyboard)
        return
    
    # إذا كان المستخدم جديداً (لم يكن موجوداً)
    if not user:
        create_user(user_id, username, full_name)
        # إرسال إشعار للمشرفين
        send_new_user_notification(user_id, full_name, username)
    
    if get_setting('bot_active') == '0':
        bot.send_message(message.chat.id, "البوت متوقف حاليًا عن العمل. يرجى المحاولة لاحقًا.")
        return
    
    welcome_text = get_setting('welcome_message')
    
    start_image = get_image('start')
    if start_image:
        try:
            bot.send_photo(message.chat.id, photo=start_image, caption=welcome_text, reply_markup=create_main_keyboard())
            return
        except Exception as e:
            print(f"خطأ في إرسال صورة البدء: {e}")
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_main_keyboard())

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "ليس لديك صلاحية للوصول إلى لوحة الأدمن.")
        return
    
    bot.send_message(message.chat.id, "🗽 𝑩𝑨𝑹𝑶𝑵 𝑫𝑬𝑽\n• أهــلاً بــك فــي لــوحة الإدارة الــخاصة بــك :", reply_markup=create_admin_main_keyboard(user_id))

@bot.channel_post_handler(content_types=['text'])
def handle_channel_post(message):
    sms_channel_id = get_channel_setting('sms_channel_id')
    if not sms_channel_id or str(message.chat.id) != sms_channel_id:
        return
    
    amount, transaction_id = extract_amount_and_transaction(message.text)
    if amount and transaction_id:
        save_sms_message(transaction_id, amount, message.text)
        
        deposits_channel_id = get_channel_setting('deposit_channel_id')
        send_to_channels = get_channel_setting('send_to_channels')
        
        report = f"""
📨 رسالة SMS جديدة:

📝 النص: {message.text}
💰 المبلغ: {amount}
🔢 رقم العملية: {transaction_id}
⏰ الوقت: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        """
        
        if not deposits_channel_id or send_to_channels != '1':
            for admin in get_all_admins():
                try:
                    bot.send_message(admin['user_id'], report)
                except:
                    pass
        elif send_to_channels == '1' and deposits_channel_id:
            try:
                bot.send_message(deposits_channel_id, report)
            except:
                pass

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    step = get_step(user_id)
    
    if step and step.startswith("wait_image_url_"):
        key = step.replace("wait_image_url_", "")
        image_url = message.text.strip()
        if image_url.startswith('http://') or image_url.startswith('https://'):
            set_image(key, image_url)
            delete_step(user_id)
            bot.reply_to(message, f"✅ تم حفظ رابط الصورة للمفتاح: {key}")
        else:
            bot.reply_to(message, "❌ الرابط غير صالح. يجب أن يبدأ بـ http:// أو https://")
        return

# ================== معالج الـ Callback Queries (مع التعديلات الآمنة) ==================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    chat_id = call.message.chat.id
    
    if call.data.startswith('admin_') and not is_admin(user_id):
        bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا القسم.")
        return
    
    if not call.data.startswith('admin_') and not call.data.startswith('check_subscription'):
        is_subscribed, channel_link, channel_id = check_mandatory_subscription(user_id)
        if not is_subscribed:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton("اضغط للانضمام للقناة", url=channel_link))
            keyboard.add(types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription"))
            try:
                safe_edit_message_text(chat_id, message_id, "📢 يجب عليك الانضمام إلى قناتنا لمتابعة استخدام البوت .", keyboard)
            except:
                pass
            bot.answer_callback_query(call.id)
            return
    
    # ========== التحقق من الاشتراك ==========
    if call.data == "check_subscription":
        is_subscribed, channel_link, channel_id = check_mandatory_subscription(user_id)
        if is_subscribed:
            welcome_text = get_setting('welcome_message')
            safe_delete_message(chat_id, message_id)
            start_image = get_image('start')
            if start_image:
                try:
                    bot.send_photo(chat_id, photo=start_image, caption=welcome_text, reply_markup=create_main_keyboard())
                except:
                    bot.send_message(chat_id, welcome_text, reply_markup=create_main_keyboard())
            else:
                bot.send_message(chat_id, welcome_text, reply_markup=create_main_keyboard())
        else:
            bot.answer_callback_query(call.id, "❌ لم يتم التحقق من اشتراكك بعد.")
        return
    
    # ========== القوائم الرئيسية ==========
    elif call.data == "main_menu":
        welcome_text = get_setting('welcome_message')
        safe_delete_message(chat_id, message_id)
        start_image = get_image('start')
        if start_image:
            try:
                bot.send_photo(chat_id, photo=start_image, caption=welcome_text, reply_markup=create_main_keyboard())
            except:
                bot.send_message(chat_id, welcome_text, reply_markup=create_main_keyboard())
        else:
            bot.send_message(chat_id, welcome_text, reply_markup=create_main_keyboard())
    
    elif call.data == "games":
        games_image = get_image('games')
        text = "🎮 قائمة الألعاب المتاحة (أوتوماتيك)"
        safe_delete_message(chat_id, message_id)
        if games_image:
            try:
                bot.send_photo(chat_id, photo=games_image, caption=text, reply_markup=create_games_keyboard())
            except:
                bot.send_message(chat_id, text, reply_markup=create_games_keyboard())
        else:
            bot.send_message(chat_id, text, reply_markup=create_games_keyboard())
    
    elif call.data == "apps":
        apps_image = get_image('apps')
        text = "📱 قائمة التطبيقات المتاحة"
        safe_delete_message(chat_id, message_id)
        if apps_image:
            try:
                bot.send_photo(chat_id, photo=apps_image, caption=text, reply_markup=create_apps_keyboard())
            except:
                bot.send_message(chat_id, text, reply_markup=create_apps_keyboard())
        else:
            bot.send_message(chat_id, text, reply_markup=create_apps_keyboard())
    
    elif call.data == "currencies":
        services_image = get_image('services')
        text = "💳 قائمة العملات و البطاقات الرقمية المتاحة"
        safe_delete_message(chat_id, message_id)
        if services_image:
            try:
                bot.send_photo(chat_id, photo=services_image, caption=text, reply_markup=create_services_keyboard())
            except:
                bot.send_message(chat_id, text, reply_markup=create_services_keyboard())
        else:
            bot.send_message(chat_id, text, reply_markup=create_services_keyboard())
    
    elif call.data == "account":
        safe_delete_message(chat_id, message_id)

        user = get_user(user_id)
        if user:
            total_spent = get_user_total_spent(user_id)
            account_text = f"""
♠️𝑴𝒀 𝑨𝑪𝑪𝑶𝑼𝑵𝑻♠️

♠️ الاسم : <b>{user['full_name'] or 'غير معروف'}</b>
♠️ الــيوزر : @{user['username'] or 'لا يوجد'}     
♠️ الأيــدي : <code>{user['user_id']}</code>          

♠️ رصــيدي : {user['balance']} ل.س
♠️ إجــمالي الــمصروفات : {total_spent} ل.س
        """
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("📋 سـجل الـشحن", callback_data="my_purchase_orders"),
                types.InlineKeyboardButton("📜 ســجل الإيــداع", callback_data="my_deposit_orders")
            )
            keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
    
            bot.send_message(chat_id, account_text, reply_markup=keyboard, parse_mode="HTML")
    
    elif call.data == "help":
        safe_delete_message(chat_id, message_id)
        support_username = get_setting('support_username') or '@Bar0nSupport'
        help_text = f'''إذا كــان لــديك أي ســؤال تــفضل و أخــبرنا:  
    
     {support_username}'''
        bot.send_message(chat_id, help_text)
    
    # ========== طلبات المستخدم ==========
    elif call.data == "my_purchase_orders":
        orders, total, total_pages = get_user_orders(user_id, 1)
        show_user_orders_page(chat_id, message_id, user_id, orders, 1, total_pages)
    
    elif call.data.startswith("my_purchase_orders_page_"):
        page = int(call.data.split("_")[4])
        orders, total, total_pages = get_user_orders(user_id, page)
        show_user_orders_page(chat_id, message_id, user_id, orders, page, total_pages)
    
    elif call.data == "my_deposit_orders":
        deposits, total, total_pages = get_user_deposits(user_id, 1)
        show_user_deposits_page(chat_id, message_id, user_id, deposits, 1, total_pages)
    
    elif call.data.startswith("my_deposit_orders_page_"):
        page = int(call.data.split("_")[4])
        deposits, total, total_pages = get_user_deposits(user_id, page)
        show_user_deposits_page(chat_id, message_id, user_id, deposits, page, total_pages)
    
    # ========== طرق الإيداع ==========
    elif call.data == "deposit_methods":
        safe_delete_message(chat_id, message_id)
        bot.send_message(chat_id, "اختر طريقة الإيداع المطلوبة:", reply_markup=create_deposit_methods_keyboard())
    
    elif call.data == "deposit_seriatel":
        if not is_deposit_method_active('seriatel'):
            bot.answer_callback_query(call.id, "❌ طريقة سيرياتيل كاش أوتوماتيك معطلة حالياً")
            return
        number = get_setting('seriatel_auto_number')
        image = get_image('currency_seriatel')  
        text = f"""قم بتحويل المبلغ المطلوب "*تحويل يدوي*" إلى الرمز التالي:

    `{number}`

علماً أنّ:
 *1 credit = {get_exchange_rate()} ل.س*"""
    
        safe_delete_message(chat_id, message_id)  
    
        if image:  
            try:
                bot.send_photo(chat_id, photo=image, caption=text, parse_mode="Markdown")
            except:
                bot.send_message(chat_id, text, parse_mode="Markdown")
        else:  
            bot.send_message(chat_id, text, parse_mode="Markdown")
    
        msg = bot.send_message(chat_id, "● يرجى ارسال المبلغ الذي قمت بتحويله :")
        bot.register_next_step_handler(msg, process_deposit_amount, 'seriatel')
    
    elif call.data == "deposit_seriatel_manual":
        if not is_deposit_method_active('seriatel_manual'):
            bot.answer_callback_query(call.id, "❌ طريقة سيرياتيل كاش يدوي معطلة حالياً")
            return
        number = get_setting('seriatel_manual_number')
        image = get_image('currency_seriatel_manual')  
        text = f"""• طريقة الإيداع اليدوي:
    
قم بتحويل المبلغ المطلوب "*تحويل يدوي*" إلى الرمز التالي:

    `{number}`

• سيتم مراجعة الطلب من قبل المشرفين خلال دقائق"""
    
        safe_delete_message(chat_id, message_id)  
    
        if image:  
            try:
                bot.send_photo(chat_id, photo=image, caption=text, parse_mode="Markdown")
            except:
                bot.send_message(chat_id, text, parse_mode="Markdown")
        else:  
            bot.send_message(chat_id, text, parse_mode="Markdown")
    
        msg = bot.send_message(chat_id, "● أرسل رقم عملية التحويل:")
        bot.register_next_step_handler(msg, process_seriatel_manual_step1)
    
    elif call.data == "deposit_sham_dollar":
        if not is_deposit_method_active('sham_dollar'):
            bot.answer_callback_query(call.id, "❌ الإيداع عبر شام دولار معطل حالياً")
            return
        address = get_setting('sham_dollar_address')
        image = get_image('currency_sham_dollar')
        text = f"""Sham Cash (دولار) 

قم بإيداع المبلغ المطلوب على العنوان التالي:

`{address}`

علماً أنَّ:
1 $ = {get_exchange_rate()} ل.س"""
        safe_delete_message(chat_id, message_id)
        if image:
            try:
                bot.send_photo(chat_id, photo=image, caption=text, parse_mode="Markdown")
            except:
                bot.send_message(chat_id, text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown")
        msg = bot.send_message(chat_id, "● يرجى ارسال المبلغ الذي قمت بتحويله (بالدولار):")
        bot.register_next_step_handler(msg, process_deposit_amount_sham, 'dollar')
    
    elif call.data == "deposit_sham_lira":
        if not is_deposit_method_active('sham_lira'):
            bot.answer_callback_query(call.id, "❌ الإيداع عبر شام ليرة معطل حالياً")
            return
        address = get_setting('sham_lira_address')
        image = get_image('currency_sham_lira')
        text = f"""Sham Cash (ليرة) 

قم بإيداع المبلغ المطلوب على العنوان التالي:

`{address}`"""
        safe_delete_message(chat_id, message_id)
        if image:
            try:
                bot.send_photo(chat_id, photo=image, caption=text, parse_mode="Markdown")
            except:
                bot.send_message(chat_id, text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown")
        msg = bot.send_message(chat_id, "● يرجى ارسال المبلغ الذي قمت بتحويله (بالليرة):")
        bot.register_next_step_handler(msg, process_deposit_amount_sham, 'lira')
    
    # ========== معالجة قبول/رفض الإيداع ==========
    elif call.data.startswith("accept_manual_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا الأمر.")
            return
        request_id = int(call.data.split("_")[2])
        process_admin_accept_manual_deposit(user_id, request_id, call)
        try:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        except:
            pass
        bot.answer_callback_query(call.id, "✅ تم قبول طلب الإيداع اليدوي")
    
    elif call.data.startswith("reject_manual_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا الأمر.")
            return
        request_id = int(call.data.split("_")[2])
        process_admin_reject_manual_deposit(user_id, request_id, call)
        try:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        except:
            pass
        bot.answer_callback_query(call.id, "❌ تم رفض طلب الإيداع اليدوي")
    
    elif call.data.startswith("accept_deposit_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا الأمر.")
            return
        request_id = int(call.data.split("_")[2])
        process_admin_accept_deposit(user_id, request_id, call)
        try:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        except:
            pass
        bot.answer_callback_query(call.id, "✅ تم قبول طلب الإيداع")
    
    elif call.data.startswith("reject_deposit_"):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا الأمر.")
            return
        request_id = int(call.data.split("_")[2])
        process_admin_reject_deposit(user_id, request_id, call)
        try:
            bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
        except:
            pass
        bot.answer_callback_query(call.id, "❌ تم رفض طلب الإيداع")
    
    # ========== الألعاب والفئات ==========
    elif call.data.startswith("game_"):
        game = call.data.split("_")[1]
        game_image = get_image(f"game_{game}")
        text = f"🛒 اختر فئة الشحن المناسبة :"
        safe_delete_message(chat_id, message_id)
        if game_image:
            try:
                bot.send_photo(chat_id, photo=game_image, caption=text, reply_markup=create_categories_keyboard(game))
            except:
                bot.send_message(chat_id, text, reply_markup=create_categories_keyboard(game))
        else:
            bot.send_message(chat_id, text, reply_markup=create_categories_keyboard(game))
    
    elif call.data.startswith("category_") and not call.data.startswith("admin_category_") and not call.data.startswith("category_app_") and not call.data.startswith("category_service_"):
        parts = call.data.split("_")
        game = parts[1]
        category = "_".join(parts[2:])
        
        product_info = get_product_info(game, category)
        if not product_info:
            bot.answer_callback_query(call.id, "هذه الفئة غير متوفرة حاليا ❌")
            return
        
        price = product_info['price'] if product_info['product_type'] == 'package' else product_info['price_per_unit']
        product_id = product_info['product_id']
        ptype = product_info['type']
        product_type = product_info['product_type']
        min_qty = product_info['min_qty']
        max_qty = product_info['max_qty']
        
        if product_type == 'quantity':
            text = f"""
🧩 اللعبة : {game}

📊 الفئة : {category}

💳 سعر الواحدة : {price} ل.س

🔽 الحد الادنى: {min_qty}

🔼 الحد الاعلى: {max_qty}

🌌 طريقة الشحن : Id
        """
        else:
            text = f"""
🧩 اللعبة : {game}

📊 الفئة : {category}

💳 السعر : {price} ل.س

🌌 طريقة الشحن : Id
        """
        
        product_image_key = f"product_{game}_{category}".replace(' ', '_').replace('💎', 'diamond')
        product_image = get_image(product_image_key)
        safe_delete_message(chat_id, message_id)
        if product_image:
            try:
                bot.send_photo(chat_id, photo=product_image, caption=text)
            except:
                bot.send_message(chat_id, text)
        else:
            bot.send_message(chat_id, text)
        
        user_data = {"game": game, "category": category, "price": price, "product_id": product_id, "type": ptype, "product_type": product_type, "min_qty": min_qty, "max_qty": max_qty}
        msg = bot.send_message(chat_id, "🎮 أرسل معرف اللاعب : ")
        bot.register_next_step_handler(msg, process_player_id, user_data)
    
    # ========== التطبيقات والفئات ==========
    elif call.data.startswith("app_"):
        app = call.data.split("_")[1]
        app_image = get_image(f"app_{app}")
        text = f"🛒 اختر فئة الشحن المناسبة :"
        safe_delete_message(chat_id, message_id)
        if app_image:
            try:
                bot.send_photo(chat_id, photo=app_image, caption=text, reply_markup=create_app_categories_keyboard(app))
            except:
                bot.send_message(chat_id, text, reply_markup=create_app_categories_keyboard(app))
        else:
            bot.send_message(chat_id, text, reply_markup=create_app_categories_keyboard(app))
    
    elif call.data.startswith("category_app_"):
        parts = call.data.split("_")
        app = parts[2]
        category = "_".join(parts[3:])
        
        product_info = get_app_product_info(app, category)
        if not product_info:
            bot.answer_callback_query(call.id, "هذه الفئة غير متوفرة حاليا ❌")
            return
        
        price = product_info['price'] if product_info['product_type'] == 'package' else product_info['price_per_unit']
        product_id = product_info['product_id']
        ptype = product_info['type']
        product_type = product_info['product_type']
        min_qty = product_info['min_qty']
        max_qty = product_info['max_qty']
        
        if product_type == 'quantity':
            text = f"""
🧩 التطبيق : {app}

📊 الفئة : {category}

💳 سعر الواحدة : {price} ل.س

🔽 الحد الادنى: {min_qty}

🔼 الحد الاعلى: {max_qty}

🌌 طريقة الشحن : Id
        """
        else:
            text = f"""
🧩 التطبيق : {app}

📊 الفئة : {category}

💳 السعر : {price} ل.س

🌌 طريقة الشحن : Id
        """
        
        product_image_key = f"product_app_{app}_{category}".replace(' ', '_')
        product_image = get_image(product_image_key)
        safe_delete_message(chat_id, message_id)
        if product_image:
            try:
                bot.send_photo(chat_id, photo=product_image, caption=text)
            except:
                bot.send_message(chat_id, text)
        else:
            bot.send_message(chat_id, text)
        
        user_data = {"app": app, "category": category, "price": price, "product_id": product_id, "type": ptype, "product_type": product_type, "min_qty": min_qty, "max_qty": max_qty, "is_app": True}
        msg = bot.send_message(chat_id, "🎮 أرسل معرف المستخدم (ايميل أو رقم محفظة): ")
        bot.register_next_step_handler(msg, process_app_player_id, user_data)
    
    # ========== الخدمات والفئات ==========
    elif call.data.startswith("service_"):
        service = call.data.split("_")[1]
        service_image = get_image(f"service_{service}")
        text = f"🛒 اختر الفئة المطلوبة :"
        safe_delete_message(chat_id, message_id)
        if service_image:
            try:
                bot.send_photo(chat_id, photo=service_image, caption=text, reply_markup=create_service_categories_keyboard(service))
            except:
                bot.send_message(chat_id, text, reply_markup=create_service_categories_keyboard(service))
        else:
            bot.send_message(chat_id, text, reply_markup=create_service_categories_keyboard(service))
    
    elif call.data.startswith("category_service_"):
        parts = call.data.split("_")
        service = parts[2]
        category = "_".join(parts[3:])
        
        product_info = get_service_product_info(service, category)
        if not product_info:
            bot.answer_callback_query(call.id, "هذه الفئة غير متوفرة حاليا ❌")
            return
        
        price = product_info['price'] if product_info['product_type'] == 'package' else product_info['price_per_unit']
        product_id = product_info['product_id']
        ptype = product_info['type']
        product_type = product_info['product_type']
        min_qty = product_info['min_qty']
        max_qty = product_info['max_qty']
        
        if product_type == 'quantity':
            text = f"""
🧩 الخدمة : {service}

📊 الفئة : {category}

💳 سعر الواحدة : {price} ل.س

🔽 الحد الادنى: {min_qty}

🔼 الحد الاعلى: {max_qty}

🌌 طريقة الشحن : Id
        """
        else:
            text = f"""
🧩 الخدمة : {service}

📊 الفئة : {category}

💳 السعر : {price} ل.س

🌌 طريقة الشحن : API
        """
        
        safe_delete_message(chat_id, message_id)
        bot.send_message(chat_id, text)
        
        user_data = {"service": service, "category": category, "price": price, "product_id": product_id, "type": ptype, "product_type": product_type, "min_qty": min_qty, "max_qty": max_qty}
        msg = bot.send_message(chat_id, "🎮 أرسل معرف المستخدم (ايميل أو رقم محفظة): ")
        bot.register_next_step_handler(msg, process_service_player_id, user_data)
    
    # ========== تأكيد وإلغاء الطلبات ==========
    elif call.data.startswith("confirm_") or call.data.startswith("cancel_"):
        order_id = call.data.split("_")[1]
        order = get_order_details(order_id)
        
        if order:
            if call.data.startswith("confirm_"):
                balance = get_user_balance(order['user_id'])
                if balance >= order['price']:
                    update_user_balance(order['user_id'], -order['price'])
                    update_order_status(order_id, "confirmed")
                    
                    confirmation_message = f"""
✅ تم تأكيد طلبك بنجاح!

🎮 الخدمة: {order['game']}
📦 الفئة: {order['category']}
💰 السعر: {order['price']} ل.س
🆔 معرف اللاعب: {order['player_id']}
📊 سيتم اعلامك بحالة طلبك ...
                    """
                    
                    msg = bot.send_message(order['user_id'], confirmation_message, parse_mode='HTML')
                    update_order_last_message(order_id, msg.message_id)
                    
                    # إرسال إشعار للمشرفين بالطلب الجديد
                    send_new_order_notification(order_id, order['user_id'], order['game'], order['category'], order['price'], order['player_id'], order['quantity'])
                    
                    # إذا كان المنتج من نوع خدمة (API)
                    if order['game'] in [s['service_name'] for s in get_all_services()]:
                        product_info = get_service_product_info(order['game'], order['category'])
                        if product_info and product_info['product_type'] in ['package', 'quantity'] and product_info['product_id']:
                            # منتج API (باقة أو كمية)
                            thread = Thread(target=process_order_with_api, args=(order_id, order['user_id'], order['game'], order['category'], order['player_id'], product_info['product_id'], order['quantity']))
                            thread.start()
                    elif order['product_id']:
                        thread = Thread(target=process_order_with_api, args=(order_id, order['user_id'], order['game'], order['category'], order['player_id'], order['product_id'], order['quantity']))
                        thread.start()
                    else:
                        product_info = get_product_info(order['game'], order['category'])
                        if product_info:
                            thread = Thread(target=process_order_with_api, args=(order_id, order['user_id'], order['game'], order['category'], order['player_id'], product_info['product_id'], order['quantity']))
                            thread.start()
                else:
                    bot.answer_callback_query(call.id, "ليس لديك رصيد كافي ❌")
            else:
                update_order_status(order_id, "cancelled")
                try:
                    safe_edit_message_text(chat_id, message_id, "❌ تم إلغاء العملية", create_back_keyboard("main_menu"))
                except:
                    pass
    
    # ========== لوحة الأدمن الرئيسية ==========
    elif call.data == "admin_main":
        safe_edit_message_text(chat_id, message_id, "🗽 𝑩𝑨𝑹𝑶𝑵 𝑫𝑬𝑽\n• أهــلاً بــك فــي لــوحة الإدارة الــخاصة بــك :", create_admin_main_keyboard(user_id))
    
    elif call.data == "admin_stats":
        stats = get_user_stats()
        stats_text = f"""
إجمالي المستخدمين: {stats['total_users']}
المستخدمين النشطين: {stats['active_users']}
المستخدمين المحظورين: {stats['banned_users']}

طلبات الايداع:
- تحتاج مراجعة: {stats['pending_deposits']}
- مكتملة: {stats['completed_deposits']}

طلبات الشحن:
- مكتملة: {stats['completed_orders']}

طلبات API:
- ناجحة: {stats['api_success']}
- فاشلة: {stats['api_failed']}
        """
        safe_edit_message_text(chat_id, message_id, stats_text, create_back_keyboard("admin_main"))
    
    elif call.data == "admin_recent_orders":
        orders, total, total_pages = get_recent_orders(1)
        show_admin_orders_page(chat_id, message_id, orders, 1, total_pages)
    
    elif call.data.startswith("admin_recent_orders_page_"):
        page = int(call.data.split("_")[4])
        orders, total, total_pages = get_recent_orders(page)
        show_admin_orders_page(chat_id, message_id, orders, page, total_pages)
    
    elif call.data == "admin_recent_deposits":
        deposits, total, total_pages = get_recent_deposits(1)
        show_admin_deposits_page(chat_id, message_id, deposits, 1, total_pages)
    
    elif call.data.startswith("admin_recent_deposits_page_"):
        page = int(call.data.split("_")[4])
        deposits, total, total_pages = get_recent_deposits(page)
        show_admin_deposits_page(chat_id, message_id, deposits, page, total_pages)
    
    elif call.data == "admin_broadcast":
        safe_edit_message_text(chat_id, message_id, "إرسال رسالة للجميع:", create_broadcast_keyboard())
    
    elif call.data == "admin_broadcast_all":
        msg = bot.send_message(chat_id, "📝 أرسل الرسالة التي تريد إذاعتها للجميع:")
        bot.register_next_step_handler(msg, process_broadcast_message)
    
    # ========== إدارة المستخدمين ==========
    elif call.data == "admin_add_balance":
        msg = bot.send_message(chat_id, "👤 أرسل ايدي المستخدم الذي تريد إضافة رصيد له:")
        bot.register_next_step_handler(msg, process_admin_add_balance_user)
    
    elif call.data == "admin_deduct_balance":
        msg = bot.send_message(chat_id, "👤 أرسل ايدي المستخدم الذي تريد خصم رصيد منه:")
        bot.register_next_step_handler(msg, process_admin_deduct_balance_user)
    
    elif call.data == "admin_ban_user":
        msg = bot.send_message(chat_id, "👤 أرسل ايدي المستخدم الذي تريد حظره:")
        bot.register_next_step_handler(msg, process_admin_ban_user)
    
    elif call.data == "admin_unban_user":
        msg = bot.send_message(chat_id, "👤 أرسل ايدي المستخدم الذي تريد رفع حظره:")
        bot.register_next_step_handler(msg, process_admin_unban_user)
    
    elif call.data == "admin_user_info":
        msg = bot.send_message(chat_id, "👤 أرسل ايدي المستخدم الذي تريد معلوماته:")
        bot.register_next_step_handler(msg, process_admin_user_info)
    
    # ========== إعدادات الدفع ==========
    elif call.data == "admin_change_seriatel_auto":
        msg = bot.send_message(chat_id, "📱 أرسل الرقم الجديد لسيرياتيل كاش (أوتوماتيك):")
        bot.register_next_step_handler(msg, process_admin_change_seriatel_auto)
    
    elif call.data == "admin_change_seriatel_manual":
        msg = bot.send_message(chat_id, "📱 أرسل الرقم الجديد لسيرياتيل كاش (يدوي):")
        bot.register_next_step_handler(msg, process_admin_change_seriatel_manual)
    
    elif call.data == "admin_change_sham_dollar":
        msg = bot.send_message(chat_id, "📱 أرسل عنوان محفظة شام دولار الجديد:")
        bot.register_next_step_handler(msg, process_admin_change_sham_dollar)
    
    elif call.data == "admin_change_sham_lira":
        msg = bot.send_message(chat_id, "📱 أرسل عنوان محفظة شام ليرة الجديد:")
        bot.register_next_step_handler(msg, process_admin_change_sham_lira)
    
    # ========== إعدادات القنوات ==========
    elif call.data == "admin_sms_settings":
        sms_channel_id = get_channel_setting('sms_channel_id')
        text = f"""
📨 إعدادات قناة SMS:

🔗 قناة SMS: `{sms_channel_id if sms_channel_id else 'لم يتم التحديد'}`

استخدم الزر أدناه لتحديد قناة SMS:
        """
        safe_edit_message_text(chat_id, message_id, text, create_sms_settings_keyboard(), parse_mode="Markdown")
    
    elif call.data == "admin_set_sms_channel":
        msg = bot.send_message(chat_id, "🔗 أرسل معرف قناة SMS (مثال: `-1001234567890`)")
        bot.register_next_step_handler(msg, process_set_sms_channel)
    
    elif call.data == "admin_orders_channels":
        orders_channel_id = get_channel_setting('orders_channel_id')
        deposits_channel_id = get_channel_setting('deposit_channel_id')
        new_users_channel_id = get_channel_setting('new_users_channel_id')
        send_to_channels = get_channel_setting('send_to_channels')
        status_text = "مفعل" if send_to_channels == '1' else "معطل"
        text = f"📤 إعدادات قنوات الطلبات:\n\nحالة إرسال للقنوات: {status_text}\nقناة طلبات الشحن: `{orders_channel_id if orders_channel_id else 'لم يتم التحديد'}`\nقناة طلبات الإيداع: `{deposits_channel_id if deposits_channel_id else 'لم يتم التحديد'}`\nقناة المستخدمين الجدد: `{new_users_channel_id if new_users_channel_id else 'لم يتم التحديد'}`"
        safe_edit_message_text(chat_id, message_id, text, create_orders_channels_keyboard(), parse_mode="Markdown")
    
    elif call.data.startswith("admin_toggle_orders_channels_"):
        status = call.data.split("_")[-1]
        update_channel_setting('send_to_channels', status)
        bot.answer_callback_query(call.id, f"✅ تم {'تفعيل' if status == '1' else 'تعطيل'} إرسال للقنوات.")
        orders_channel_id = get_channel_setting('orders_channel_id')
        deposits_channel_id = get_channel_setting('deposit_channel_id')
        new_users_channel_id = get_channel_setting('new_users_channel_id')
        text = f"📤 إعدادات قنوات الطلبات:\n\nحالة إرسال للقنوات: {'مفعل' if status == '1' else 'معطل'}\nقناة طلبات الشحن: `{orders_channel_id if orders_channel_id else 'لم يتم التحديد'}`\nقناة طلبات الإيداع: `{deposits_channel_id if deposits_channel_id else 'لم يتم التحديد'}`\nقناة المستخدمين الجدد: `{new_users_channel_id if new_users_channel_id else 'لم يتم التحديد'}`"
        safe_edit_message_text(chat_id, message_id, text, create_orders_channels_keyboard(), parse_mode="Markdown")
    
    elif call.data == "admin_set_orders_channel":
        msg = bot.send_message(chat_id, "🔗 أرسل معرف قناة طلبات الشحن (مثال: -1003869617899)")
        bot.register_next_step_handler(msg, process_set_orders_channel)
    
    elif call.data == "admin_set_deposits_channel":
        msg = bot.send_message(chat_id, "🔗 أرسل معرف قناة طلبات الإيداع (مثال: -1003869617899)")
        bot.register_next_step_handler(msg, process_set_deposits_channel)
    
    elif call.data == "admin_set_new_users_channel":
        msg = bot.send_message(chat_id, "🔗 أرسل معرف قناة المستخدمين الجدد (مثال: -1003869617899)")
        bot.register_next_step_handler(msg, process_set_new_users_channel)
    
    # ========== إدارة الصور ==========
    elif call.data == "admin_images_main":
        safe_edit_message_text(chat_id, message_id, "🖼️ إدارة الصور\n\nاختر القسم الذي تريد إدارة صورته:", create_images_main_keyboard())
    
    elif call.data == "admin_image_start":
        key = "start"
        current = get_image(key)
        text = f"صورة رسالة البدء الحالية: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_games":
        key = "games"
        current = get_image(key)
        text = f"صورة قائمة الألعاب الحالية: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_apps":
        key = "apps"
        current = get_image(key)
        text = f"صورة قائمة التطبيقات الحالية: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_services":
        key = "services"
        current = get_image(key)
        text = f"صورة قائمة العملات والبطاقات الحالية: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_game_select":
        games = get_all_games()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for game in games:
            keyboard.add(types.InlineKeyboardButton(game['game_name'], callback_data=f"admin_image_game_{game['game_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر اللعبة:", keyboard)
    
    elif call.data.startswith("admin_image_game_"):
        game = call.data.replace("admin_image_game_", "")
        key = f"game_{game}"
        current = get_image(key)
        text = f"صورة لعبة {game}: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_game_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_app_select":
        apps = get_all_apps()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for app in apps:
            keyboard.add(types.InlineKeyboardButton(app['app_name'], callback_data=f"admin_image_app_{app['app_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر التطبيق:", keyboard)
    
    elif call.data.startswith("admin_image_app_"):
        app = call.data.replace("admin_image_app_", "")
        key = f"app_{app}"
        current = get_image(key)
        text = f"صورة تطبيق {app}: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_app_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_service_select":
        services = get_all_services()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for service in services:
            keyboard.add(types.InlineKeyboardButton(service['service_name'], callback_data=f"admin_image_service_{service['service_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر الخدمة:", keyboard)
    
    elif call.data.startswith("admin_image_service_"):
        service = call.data.replace("admin_image_service_", "")
        key = f"service_{service}"
        current = get_image(key)
        text = f"صورة خدمة {service}: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_service_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_product_game_select":
        games = get_all_games()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for game in games:
            keyboard.add(types.InlineKeyboardButton(game['game_name'], callback_data=f"admin_image_product_game_{game['game_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر اللعبة:", keyboard)
    
    elif call.data.startswith("admin_image_product_game_"):
        game = call.data.replace("admin_image_product_game_", "")
        products, _, _ = get_products_by_game(game, only_active=False, page=1)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            keyboard.add(types.InlineKeyboardButton(p['category'], callback_data=f"admin_image_product_{game}_{p['category']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_product_game_select"))
        safe_edit_message_text(chat_id, message_id, "اختر المنتج:", keyboard)
    
    elif call.data == "admin_image_app_product_select":
        apps = get_all_apps()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for app in apps:
            keyboard.add(types.InlineKeyboardButton(app['app_name'], callback_data=f"admin_image_app_product_app_{app['app_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر التطبيق:", keyboard)
    
    elif call.data.startswith("admin_image_app_product_app_"):
        app = call.data.replace("admin_image_app_product_app_", "")
        products, _, _ = get_app_products_by_app(app, only_active=False, page=1)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            keyboard.add(types.InlineKeyboardButton(p['category'], callback_data=f"admin_image_app_product_{app}_{p['category']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_app_product_select"))
        safe_edit_message_text(chat_id, message_id, "اختر المنتج:", keyboard)
    
    elif call.data == "admin_image_service_product_select":
        services = get_all_services()
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for service in services:
            keyboard.add(types.InlineKeyboardButton(service['service_name'], callback_data=f"admin_image_service_product_service_{service['service_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر الخدمة:", keyboard)
    
    elif call.data.startswith("admin_image_service_product_service_"):
        service = call.data.replace("admin_image_service_product_service_", "")
        products, _, _ = get_service_products_by_service(service, only_active=False, page=1)
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            keyboard.add(types.InlineKeyboardButton(p['category'], callback_data=f"admin_image_service_product_{service}_{p['category']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_service_product_select"))
        safe_edit_message_text(chat_id, message_id, "اختر المنتج:", keyboard)
    
    elif call.data.startswith("admin_image_product_"):
        parts = call.data.split("_")
        game = parts[3]
        category = "_".join(parts[4:])
        key = f"product_{game}_{category}".replace(' ', '_').replace('💎', 'diamond')
        current = get_image(key)
        text = f"صورة منتج {game} - {category}: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_product_game_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data.startswith("admin_image_app_product_"):
        parts = call.data.split("_")
        app = parts[4]
        category = "_".join(parts[5:])
        key = f"product_app_{app}_{category}".replace(' ', '_')
        current = get_image(key)
        text = f"صورة منتج تطبيق {app} - {category}: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_app_product_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data.startswith("admin_image_service_product_"):
        parts = call.data.split("_")
        service = parts[4]
        category = "_".join(parts[5:])
        key = f"product_service_{service}_{category}".replace(' ', '_')
        current = get_image(key)
        text = f"صورة منتج خدمة {service} - {category}: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_service_product_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_image_currency_select":
        methods = [
            ("سيرياتيل أوتوماتيك", "currency_seriatel"),
            ("سيرياتيل يدوي", "currency_seriatel_manual"),
            ("شام دولار", "currency_sham_dollar"),
            ("شام ليرة", "currency_sham_lira")
        ]
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for name, key in methods:
            keyboard.add(types.InlineKeyboardButton(name, callback_data=f"admin_image_currency_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_images_main"))
        safe_edit_message_text(chat_id, message_id, "اختر طريقة الدفع:", keyboard)
    
    elif call.data.startswith("admin_image_currency_"):
        key = call.data.replace("admin_image_currency_", "")
        current = get_image(key)
        text = f"صورة طريقة الدفع: {'✅ موجودة' if current else '❌ لا توجد'}"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(types.InlineKeyboardButton("🔄 تغيير الصورة", callback_data=f"admin_image_change_{key}"))
        if current:
            keyboard.add(types.InlineKeyboardButton("🗑️ حذف الصورة", callback_data=f"admin_image_delete_{key}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_image_currency_select"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data.startswith("admin_image_change_"):
        key = call.data.replace("admin_image_change_", "")
        save_step(user_id, f"wait_image_url_{key}")
        bot.send_message(chat_id, "🔗 أرسل رابط الصورة الجديدة (يبدأ بـ http:// أو https://):")
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("admin_image_delete_"):
        key = call.data.replace("admin_image_delete_", "")
        delete_image(key)
        bot.answer_callback_query(call.id, f"✅ تم حذف الصورة")
        safe_edit_message_text(chat_id, message_id, "🖼️ إدارة الصور\n\nتم حذف الصورة.", create_images_main_keyboard())
    
    # ========== إعدادات عامة ==========
    elif call.data == "admin_toggle_bot":
        current = get_setting('bot_active')
        new = '0' if current == '1' else '1'
        update_setting('bot_active', new)
        status = "متوقف" if new == '0' else "يعمل"
        bot.answer_callback_query(call.id, f"✅ تم تغيير حالة البوت إلى: {status}")
        safe_edit_message_text(chat_id, message_id, f"✅ حالة البوت الآن: {status}", create_back_keyboard("admin_main"))
    
    elif call.data == "admin_change_support":
        msg = bot.send_message(chat_id, "👤 أرسل يوزر الدعم الجديد (مثال: @Bar0nSupport):")
        bot.register_next_step_handler(msg, process_admin_change_support)
    
    elif call.data == "admin_change_welcome":
        msg = bot.send_message(chat_id, "📝 أرسل رسالة البداية الجديدة:")
        bot.register_next_step_handler(msg, process_admin_change_welcome)
    
    elif call.data == "admin_deposit_methods":
        safe_edit_message_text(chat_id, message_id, "💳 التحكم بطرق الإيداع:\n\nاستخدم الأزرار أدناه لتفعيل/تعطيل طرق الإيداع:", create_deposit_methods_control_keyboard())
    
    elif call.data.startswith("admin_toggle_deposit_"):
        data = call.data.replace("admin_toggle_deposit_", "")
        if data.startswith("seriatel_manual_"):
            method = "seriatel_manual"
            status = int(data.replace("seriatel_manual_", ""))
        elif data.startswith("seriatel_"):
            method = "seriatel"
            status = int(data.replace("seriatel_", ""))
        elif data.startswith("sham_dollar_"):
            method = "sham_dollar"
            status = int(data.replace("sham_dollar_", ""))
        elif data.startswith("sham_lira_"):
            method = "sham_lira"
            status = int(data.replace("sham_lira_", ""))
        else:
            method, status_str = data.split("_")
            status = int(status_str)
        
        toggle_deposit_method(method, status)
        bot.answer_callback_query(call.id, f"✅ تم {'تفعيل' if status == 1 else 'تعطيل'} الطريقة")
        safe_edit_message_text(chat_id, message_id, "💳 التحكم بطرق الإيداع:\n\nتم التحديث.", create_deposit_methods_control_keyboard())
    
    # ========== إدارة المشرفين ==========
    elif call.data == "admin_admins_panel":
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا القسم.")
            return
        admins = get_all_admins()
        text = "👑 قائمة المشرفين:\n"
        for admin in admins:
            text += f"- ID: {admin['user_id']} {' (أساسي)' if admin['is_main_admin'] else ''}\n"
        safe_edit_message_text(chat_id, message_id, text, create_admins_list_keyboard())
    
    elif call.data == "admin_add_new_admin":
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية لإضافة مشرفين.")
            return
        msg = bot.send_message(chat_id, "👤 أرسل ايدي المستخدم الذي تريد إضافته كمشرف:")
        bot.register_next_step_handler(msg, process_add_new_admin)
    
    elif call.data.startswith("admin_remove_"):
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية لحذف مشرفين.")
            return
        admin_to_remove = int(call.data.split("_")[2])
        remove_admin(admin_to_remove)
        bot.answer_callback_query(call.id, f"✅ تم حذف المشرف {admin_to_remove}.")
        admins = get_all_admins()
        text = "👑 قائمة المشرفين:\n"
        for admin in admins:
            text += f"- ID: {admin['user_id']} {' (أساسي)' if admin['is_main_admin'] else ''}\n"
        safe_edit_message_text(chat_id, message_id, text, create_admins_list_keyboard())
    
    # ========== الاشتراك الإجباري ==========
    elif call.data == "admin_channel_settings":
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية للوصول إلى هذا القسم.")
            return
        channel = get_mandatory_channel()
        if channel:
            status = "مفعل" if channel['is_active'] else "معطل"
            text = f"🔗 القناة الحالية: {channel['channel_link']}\nالحالة: {status}"
        else:
            text = "🔗 لم يتم تحديد قناة اشتراك بعد."
        safe_edit_message_text(chat_id, message_id, text, create_channel_settings_keyboard())
    
    elif call.data == "admin_set_channel":
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية لتحديد القناة.")
            return
        msg = bot.send_message(chat_id, "أرسل رابط القناة (مثل: `https://t.me/channel_username`) مع التأكد أن البوت مشرف فيها:")
        bot.register_next_step_handler(msg, process_set_mandatory_channel)
    
    elif call.data.startswith("admin_toggle_channel_"):
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية لتغيير حالة القناة.")
            return
        status = int(call.data.split("_")[3])
        toggle_mandatory_channel(status)
        bot.answer_callback_query(call.id, f"✅ تم {'تفعيل' if status == 1 else 'تعطيل'} الاشتراك الإجباري.")
        channel = get_mandatory_channel()
        if channel:
            status_text = "مفعل" if channel['is_active'] else "معطل"
            text = f"🔗 القناة الحالية: {channel['channel_link']}\nالحالة: {status_text}"
        else:
            text = "🔗 لم يتم تحديد قناة اشتراك بعد."
        safe_edit_message_text(chat_id, message_id, text, create_channel_settings_keyboard())
        
    # ========== سعر الصرف ==========
    elif call.data == "admin_exchange_rate":
        if not is_main_admin(user_id):
            bot.answer_callback_query(call.id, "ليس لديك صلاحية لتغيير سعر الصرف.")
            return
        
        current_rate = get_exchange_rate()
        text = f"💰 سعر الصرف الحالي: {current_rate}\n\nأرسل سعر الصرف الجديد (بالليرة السورية):"
        safe_edit_message_text(chat_id, message_id, text, create_back_keyboard("admin_main"))
        msg = bot.send_message(chat_id, "📝 أرسل القيمة الجديدة:")
        bot.register_next_step_handler(msg, process_admin_exchange_rate)
    
    # ========== إدارة الألعاب ==========
    elif call.data == "admin_manage_games":
        safe_edit_message_text(chat_id, message_id, "🎮 إدارة الألعاب:", create_manage_games_keyboard())
    
    elif call.data == "admin_add_game":
        msg = bot.send_message(chat_id, "📝 أرسل اسم اللعبة الجديدة:")
        bot.register_next_step_handler(msg, process_add_game)
    
    elif call.data == "admin_delete_game":
        safe_edit_message_text(chat_id, message_id, "🗑️ اختر اللعبة التي تريد حذفها:", create_delete_game_keyboard())
    
    elif call.data.startswith("admin_confirm_delete_game_"):
        game_name = call.data.replace("admin_confirm_delete_game_", "")
        delete_game(game_name)
        bot.answer_callback_query(call.id, f"✅ تم حذف اللعبة {game_name}")
        safe_edit_message_text(chat_id, message_id, "🎮 إدارة الألعاب:", create_manage_games_keyboard())
    
    elif call.data.startswith("admin_toggle_game_"):
        game_name = call.data.replace("admin_toggle_game_", "")
        current = is_game_active(game_name)
        toggle_game_status(game_name, 0 if current else 1)
        bot.answer_callback_query(call.id, f"تم {'إيقاف' if current else 'تشغيل'} اللعبة")
        safe_edit_message_text(chat_id, message_id, "🎮 إدارة الألعاب:", create_manage_games_keyboard())
    
    # ========== إدارة التطبيقات ==========
    elif call.data == "admin_manage_apps":
        safe_edit_message_text(chat_id, message_id, "📱 إدارة التطبيقات:", create_manage_apps_keyboard())
    
    elif call.data == "admin_add_app":
        msg = bot.send_message(chat_id, "📝 أرسل اسم التطبيق الجديد:")
        bot.register_next_step_handler(msg, process_add_app)
    
    elif call.data == "admin_delete_app":
        safe_edit_message_text(chat_id, message_id, "🗑️ اختر التطبيق الذي تريد حذفه:", create_delete_app_keyboard())
    
    elif call.data.startswith("admin_confirm_delete_app_"):
        app_name = call.data.replace("admin_confirm_delete_app_", "")
        delete_app(app_name)
        bot.answer_callback_query(call.id, f"✅ تم حذف التطبيق {app_name}")
        safe_edit_message_text(chat_id, message_id, "📱 إدارة التطبيقات:", create_manage_apps_keyboard())
    
    elif call.data.startswith("admin_toggle_app_"):
        app_name = call.data.replace("admin_toggle_app_", "")
        current = is_app_active(app_name)
        toggle_app_status(app_name, 0 if current else 1)
        bot.answer_callback_query(call.id, f"تم {'إيقاف' if current else 'تشغيل'} التطبيق")
        safe_edit_message_text(chat_id, message_id, "📱 إدارة التطبيقات:", create_manage_apps_keyboard())
    
    # ========== إدارة الخدمات ==========
    elif call.data == "admin_manage_services":
        safe_edit_message_text(chat_id, message_id, "💳 إدارة العملات والبطاقات:", create_manage_services_keyboard())
    
    elif call.data == "admin_add_service":
        msg = bot.send_message(chat_id, "📝 أرسل اسم الخدمة الجديدة (مثل: جوجل بلاي, ستيم, ...):")
        bot.register_next_step_handler(msg, process_add_service)
    
    elif call.data == "admin_delete_service":
        safe_edit_message_text(chat_id, message_id, "🗑️ اختر الخدمة التي تريد حذفها:", create_delete_service_keyboard())
    
    elif call.data.startswith("admin_confirm_delete_service_"):
        service_name = call.data.replace("admin_confirm_delete_service_", "")
        delete_service(service_name)
        bot.answer_callback_query(call.id, f"✅ تم حذف الخدمة {service_name}")
        safe_edit_message_text(chat_id, message_id, "💳 إدارة العملات والبطاقات:", create_manage_services_keyboard())
    
    elif call.data.startswith("admin_toggle_service_"):
        service_name = call.data.replace("admin_toggle_service_", "")
        current = is_service_active(service_name)
        toggle_service_status(service_name, 0 if current else 1)
        bot.answer_callback_query(call.id, f"تم {'إيقاف' if current else 'تشغيل'} الخدمة")
        safe_edit_message_text(chat_id, message_id, "💳 إدارة العملات والبطاقات:", create_manage_services_keyboard())
    
    # ========== إدارة المنتجات الرئيسية ==========
    elif call.data == "admin_manage_products_main":
        safe_edit_message_text(chat_id, message_id, "📦 إدارة المنتجات\n\nاختر القسم:", create_manage_products_main_keyboard())
    
    elif call.data == "admin_manage_products_games":
        safe_edit_message_text(chat_id, message_id, "🎮 إدارة منتجات الألعاب", create_manage_products_games_keyboard())
    
    elif call.data == "admin_manage_products_apps":
        safe_edit_message_text(chat_id, message_id, "📱 إدارة منتجات التطبيقات", create_manage_products_apps_keyboard())
    
    elif call.data == "admin_manage_products_services":
        safe_edit_message_text(chat_id, message_id, "💳 إدارة منتجات الخدمات", create_manage_products_services_keyboard())
    
    # ========== إدارة المنتجات (الألعاب) ==========
    elif call.data.startswith("admin_products_game_"):
        parts = call.data.split("_")
        game = parts[3]
        page = int(parts[4])
        products, total, total_pages = get_products_by_game(game, only_active=False, page=page)
        text = f"📦 منتجات {game} (صفحة {page}/{total_pages}):\n\n"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            status = "✅" if p['is_active'] else "❌"
            display_price = p['price_per_unit'] if p['product_type'] == 'quantity' else p['price']
            keyboard.add(types.InlineKeyboardButton(f"{status} {p['category']} - {display_price} ل.س", callback_data=f"admin_product_{game}_{p['category']}"))
        nav_row = []
        if page > 1:
            nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_products_game_{game}_{page-1}"))
        if page < total_pages:
            nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_products_game_{game}_{page+1}"))
        if nav_row:
            keyboard.add(*nav_row)
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_games"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_add_product_select_game":
        games = get_all_games()
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for game in games:
            keyboard.add(types.InlineKeyboardButton(game['game_name'], callback_data=f"admin_add_product_game_{game['game_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_games"))
        safe_edit_message_text(chat_id, message_id, "📦 اختر اللعبة لإضافة منتج جديد:", keyboard)
    
    elif call.data.startswith("admin_add_product_game_"):
        game = call.data.replace("admin_add_product_game_", "")
        msg = bot.send_message(chat_id, f"📝 أرسل اسم المنتج الجديد للعبة {game}:")
        bot.register_next_step_handler(msg, process_add_product_name, game)
    
    elif call.data.startswith("admin_add_product_type_"):
        parts = call.data.split("_")
        product_type = parts[-1]
        rest = "_".join(parts[4:-1])
        first_underscore = rest.find('_')
        if first_underscore == -1:
            bot.answer_callback_query(call.id, "خطأ في البيانات.")
            return
        game = rest[:first_underscore]
        product_name = rest[first_underscore+1:]
        
        bot.delete_message(chat_id, message_id)
        msg = bot.send_message(chat_id, f"💰 أرسل سعر {'الوحدة' if product_type == 'quantity' else 'المنتج'} (بالليرة):")
        bot.register_next_step_handler(msg, process_add_product_price, game, product_name, product_type)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("admin_product_"):
        parts = call.data.split("_")
        game = parts[2]
        category = "_".join(parts[3:])
        safe_edit_message_text(chat_id, message_id, f"🎮 {game}\n📦 {category}\n\nاختر الإجراء:", create_product_actions_keyboard(game, category))
    
    elif call.data.startswith("admin_delete_product_"):
        parts = call.data.split("_")
        game = parts[3]
        category = "_".join(parts[4:])
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"admin_confirm_delete_{game}_{category}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data=f"admin_product_{game}_{category}")
        )
        safe_edit_message_text(chat_id, message_id, f"⚠️ هل أنت متأكد من حذف المنتج {category} من لعبة {game}؟", keyboard)
    
    elif call.data.startswith("admin_confirm_delete_"):
        parts = call.data.split("_")
        game = parts[3]
        category = "_".join(parts[4:])
        delete_product(game, category)
        bot.answer_callback_query(call.id, f"✅ تم حذف المنتج {category}")
        products, total, total_pages = get_products_by_game(game, only_active=False, page=1)
        text = f"📦 منتجات {game} (صفحة 1/{total_pages}):\n\n"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            status = "✅" if p['is_active'] else "❌"
            display_price = p['price_per_unit'] if p['product_type'] == 'quantity' else p['price']
            keyboard.add(types.InlineKeyboardButton(f"{status} {p['category']} - {display_price} ل.س", callback_data=f"admin_product_{game}_{p['category']}"))
        if total_pages > 1:
            keyboard.add(types.InlineKeyboardButton("1/2 ▶️", callback_data=f"admin_products_game_{game}_2"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_games"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data.startswith("admin_change_price_"):
        parts = call.data.split("_")
        game = parts[3]
        category = "_".join(parts[4:])
        msg = bot.send_message(chat_id, f"💰 أرسل السعر الجديد لفئة {category}:")
        bot.register_next_step_handler(msg, process_admin_change_price, game, category)
    
    elif call.data.startswith("admin_change_api_"):
        parts = call.data.split("_")
        game = parts[3]
        category = "_".join(parts[4:])
        msg = bot.send_message(chat_id, f"🔑 أرسل رمز API الجديد (product_id) لفئة {category}:")
        bot.register_next_step_handler(msg, process_admin_change_code, game, category)
    
    elif call.data.startswith("admin_edit_quantity_"):
        parts = call.data.split("_")
        game = parts[3]
        category = "_".join(parts[4:])
        msg = bot.send_message(chat_id, f"📊 أرسل سعر الوحدة الجديد (يمكن استخدام الفاصلة للكسور):")
        bot.register_next_step_handler(msg, process_admin_edit_quantity_price, game, category)
    
    elif call.data.startswith("admin_activate_"):
        parts = call.data.split("_")
        game = parts[2]
        category = "_".join(parts[3:])
        toggle_product_status(game, category, 1)
        bot.answer_callback_query(call.id, f"✅ تم تفعيل {category}")
        safe_edit_message_text(chat_id, message_id, f"🎮 {game}\n📦 {category}\n\nاختر الإجراء:", create_product_actions_keyboard(game, category))
    
    elif call.data.startswith("admin_deactivate_"):
        parts = call.data.split("_")
        game = parts[2]
        category = "_".join(parts[3:])
        toggle_product_status(game, category, 0)
        bot.answer_callback_query(call.id, f"⛔ تم تعطيل {category}")
        safe_edit_message_text(chat_id, message_id, f"🎮 {game}\n📦 {category}\n\nاختر الإجراء:", create_product_actions_keyboard(game, category))
    
    # ========== إدارة منتجات التطبيقات ==========
    elif call.data.startswith("admin_app_products_app_"):
        parts = call.data.split("_")
        app = parts[4]
        page = int(parts[5])
        products, total, total_pages = get_app_products_by_app(app, only_active=False, page=page)
        text = f"📦 منتجات {app} (صفحة {page}/{total_pages}):\n\n"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            status = "✅" if p['is_active'] else "❌"
            display_price = p['price_per_unit'] if p['product_type'] == 'quantity' else p['price']
            keyboard.add(types.InlineKeyboardButton(f"{status} {p['category']} - {display_price} ل.س", callback_data=f"admin_app_product_{app}_{p['category']}"))
        nav_row = []
        if page > 1:
            nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_app_products_app_{app}_{page-1}"))
        if page < total_pages:
            nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_app_products_app_{app}_{page+1}"))
        if nav_row:
            keyboard.add(*nav_row)
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_apps"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data == "admin_add_app_product_select_app":
        apps = get_all_apps()
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for app in apps:
            keyboard.add(types.InlineKeyboardButton(app['app_name'], callback_data=f"admin_add_app_product_app_{app['app_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_apps"))
        safe_edit_message_text(chat_id, message_id, "📱 اختر التطبيق لإضافة منتج جديد:", keyboard)
    
    elif call.data.startswith("admin_add_app_product_app_"):
        app = call.data.replace("admin_add_app_product_app_", "")
        msg = bot.send_message(chat_id, f"📝 أرسل اسم المنتج الجديد للتطبيق {app}:")
        bot.register_next_step_handler(msg, process_add_app_product_name, app)
    
    elif call.data.startswith("admin_add_app_product_type_"):
        parts = call.data.split("_")
        product_type = parts[-1]
        rest = "_".join(parts[5:-1])
        first_underscore = rest.find('_')
        if first_underscore == -1:
            bot.answer_callback_query(call.id, "خطأ في البيانات.")
            return
        app = rest[:first_underscore]
        product_name = rest[first_underscore+1:]
        
        bot.delete_message(chat_id, message_id)
        msg = bot.send_message(chat_id, f"💰 أرسل سعر {'الوحدة' if product_type == 'quantity' else 'المنتج'} (بالليرة):")
        bot.register_next_step_handler(msg, process_add_app_product_price, app, product_name, product_type)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("admin_app_product_"):
        parts = call.data.split("_")
        app = parts[3]
        category = "_".join(parts[4:])
        safe_edit_message_text(chat_id, message_id, f"📱 {app}\n📦 {category}\n\nاختر الإجراء:", create_app_product_actions_keyboard(app, category))
    
    elif call.data.startswith("admin_delete_app_product_"):
        parts = call.data.split("_")
        app = parts[4]
        category = "_".join(parts[5:])
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"admin_confirm_delete_app_product_{app}_{category}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data=f"admin_app_product_{app}_{category}")
        )
        safe_edit_message_text(chat_id, message_id, f"⚠️ هل أنت متأكد من حذف المنتج {category} من تطبيق {app}؟", keyboard)
    
    elif call.data.startswith("admin_confirm_delete_app_product_"):
        parts = call.data.split("_")
        app = parts[5]
        category = "_".join(parts[6:])
        delete_app_product(app, category)
        bot.answer_callback_query(call.id, f"✅ تم حذف المنتج {category}")
        products, total, total_pages = get_app_products_by_app(app, only_active=False, page=1)
        text = f"📦 منتجات {app} (صفحة 1/{total_pages}):\n\n"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            status = "✅" if p['is_active'] else "❌"
            display_price = p['price_per_unit'] if p['product_type'] == 'quantity' else p['price']
            keyboard.add(types.InlineKeyboardButton(f"{status} {p['category']} - {display_price} ل.س", callback_data=f"admin_app_product_{app}_{p['category']}"))
        if total_pages > 1:
            keyboard.add(types.InlineKeyboardButton("1/2 ▶️", callback_data=f"admin_app_products_app_{app}_2"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_apps"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data.startswith("admin_change_app_price_"):
        parts = call.data.split("_")
        app = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"💰 أرسل السعر الجديد لفئة {category}:")
        bot.register_next_step_handler(msg, process_admin_change_app_price, app, category)
    
    elif call.data.startswith("admin_change_app_api_"):
        parts = call.data.split("_")
        app = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"🔑 أرسل رمز API الجديد (product_id) لفئة {category}:")
        bot.register_next_step_handler(msg, process_admin_change_app_code, app, category)
    
    elif call.data.startswith("admin_edit_app_quantity_"):
        parts = call.data.split("_")
        app = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"📊 أرسل سعر الوحدة الجديد (يمكن استخدام الفاصلة للكسور):")
        bot.register_next_step_handler(msg, process_admin_edit_app_quantity_price, app, category)
    
    elif call.data.startswith("admin_activate_app_"):
        parts = call.data.split("_")
        app = parts[3]
        category = "_".join(parts[4:])
        toggle_app_product_status(app, category, 1)
        bot.answer_callback_query(call.id, f"✅ تم تفعيل {category}")
        safe_edit_message_text(chat_id, message_id, f"📱 {app}\n📦 {category}\n\nاختر الإجراء:", create_app_product_actions_keyboard(app, category))
    
    elif call.data.startswith("admin_deactivate_app_"):
        parts = call.data.split("_")
        app = parts[3]
        category = "_".join(parts[4:])
        toggle_app_product_status(app, category, 0)
        bot.answer_callback_query(call.id, f"⛔ تم تعطيل {category}")
        safe_edit_message_text(chat_id, message_id, f"📱 {app}\n📦 {category}\n\nاختر الإجراء:", create_app_product_actions_keyboard(app, category))
    
    # ========== إدارة منتجات الخدمات ==========
    elif call.data.startswith("admin_service_products_service_"):
        try:
            print(f"📌 تم استدعاء admin_service_products_service_ بـ: {call.data}")
        
            parts = call.data.split("_")
 
            service_parts = []
            page = 1
        
            for i in range(4, len(parts)):
                if i == len(parts) - 1:  
                    try:
                        page = int(parts[i])
                    except ValueError:
                        page = 1
                else:
                    service_parts.append(parts[i])
         
            service = "_".join(service_parts)
        
            print(f"✅ الخدمة المستخرجة: {service}, الصفحة: {page}")
        
            products, total, total_pages = get_service_products_by_service(service, only_active=False, page=page)
        
            if not products:
                text = f"📦 لا توجد منتجات لخدمة {service}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_services"))
                safe_edit_message_text(chat_id, message_id, text, keyboard)
                return
        
            text = f"📦 منتجات {service} (صفحة {page}/{total_pages}):\n\n"
            keyboard = types.InlineKeyboardMarkup(row_width=1)
        
            for p in products:
                status = "✅" if p['is_active'] else "❌"
                display_price = p['price_per_unit'] if p['product_type'] == 'quantity' else p['price']
            # تأكد من أن اسم المنتج لا يسبب مشاكل
                safe_category = p['category'].replace(' ', '_')
                keyboard.add(types.InlineKeyboardButton(
                    f"{status} {p['category']} - {display_price} ل.س", 
                    callback_data=f"admin_service_product_{service}_{safe_category}"
                ))
        
            nav_row = []
            if page > 1:
                nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"admin_service_products_service_{service}_{page-1}"))
            if page < total_pages:
                nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"admin_service_products_service_{service}_{page+1}"))
            if nav_row:
                keyboard.add(*nav_row)
        
            keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_services"))
            safe_edit_message_text(chat_id, message_id, text, keyboard)
        
        except Exception as e:
            print(f"❌ خطأ في معالجة admin_service_products_service_: {e}")
            import traceback
            traceback.print_exc()
            bot.answer_callback_query(call.id, f"حدث خطأ: {str(e)}")
    
    elif call.data == "admin_add_service_product_select_service":
        services = get_all_services()
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for service in services:
            keyboard.add(types.InlineKeyboardButton(service['service_name'], callback_data=f"admin_add_service_product_service_{service['service_name']}"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_services"))
        safe_edit_message_text(chat_id, message_id, "💳 اختر الخدمة لإضافة منتج جديد:", keyboard)
    
    elif call.data.startswith("admin_add_service_product_service_"):
        service = call.data.replace("admin_add_service_product_service_", "")
        msg = bot.send_message(chat_id, f"📝 أرسل اسم المنتج الجديد للخدمة {service}:")
        bot.register_next_step_handler(msg, process_add_service_product_name, service)
    
    elif call.data.startswith("admin_add_service_product_type_"):
        parts = call.data.split("_")
        product_type = parts[-1]
        rest = "_".join(parts[5:-1])
        first_underscore = rest.find('_')
        if first_underscore == -1:
            bot.answer_callback_query(call.id, "خطأ في البيانات.")
            return
        service = rest[:first_underscore]
        product_name = rest[first_underscore+1:]
        
        bot.delete_message(chat_id, message_id)
        msg = bot.send_message(chat_id, f"💰 أرسل سعر {'الوحدة' if product_type == 'quantity' else 'المنتج'} (بالليرة):")
        bot.register_next_step_handler(msg, process_add_service_product_price, service, product_name, product_type)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("admin_service_product_"):
        parts = call.data.split("_")
        service = parts[3]
        category = "_".join(parts[4:])
        safe_edit_message_text(chat_id, message_id, f"💳 {service}\n📦 {category}\n\nاختر الإجراء:", create_service_product_actions_keyboard(service, category))
    
    elif call.data.startswith("admin_delete_service_product_"):
        parts = call.data.split("_")
        service = parts[4]
        category = "_".join(parts[5:])
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"admin_confirm_delete_service_product_{service}_{category}"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data=f"admin_service_product_{service}_{category}")
        )
        safe_edit_message_text(chat_id, message_id, f"⚠️ هل أنت متأكد من حذف المنتج {category} من خدمة {service}؟", keyboard)
    
    elif call.data.startswith("admin_confirm_delete_service_product_"):
        parts = call.data.split("_")
        service = parts[5]
        category = "_".join(parts[6:])
        delete_service_product(service, category)
        bot.answer_callback_query(call.id, f"✅ تم حذف المنتج {category}")
        products, total, total_pages = get_service_products_by_service(service, only_active=False, page=1)
        text = f"📦 منتجات {service} (صفحة 1/{total_pages}):\n\n"
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in products:
            status = "✅" if p['is_active'] else "❌"
            display_price = p['price_per_unit'] if p['product_type'] == 'quantity' else p['price']
            keyboard.add(types.InlineKeyboardButton(f"{status} {p['category']} - {display_price} ل.س", callback_data=f"admin_service_product_{service}_{p['category']}"))
        if total_pages > 1:
            keyboard.add(types.InlineKeyboardButton("1/2 ▶️", callback_data=f"admin_service_products_service_{service}_2"))
        keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_manage_products_services"))
        safe_edit_message_text(chat_id, message_id, text, keyboard)
    
    elif call.data.startswith("admin_change_service_price_"):
        parts = call.data.split("_")
        service = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"💰 أرسل السعر الجديد لفئة {category}:")
        bot.register_next_step_handler(msg, process_admin_change_service_price, service, category)
    
    elif call.data.startswith("admin_change_service_api_"):
        parts = call.data.split("_")
        service = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"🔑 أرسل رمز API الجديد (product_id) لفئة {category}:")
        bot.register_next_step_handler(msg, process_admin_change_service_code, service, category)
    
    elif call.data.startswith("admin_edit_service_quantity_"):
        parts = call.data.split("_")
        service = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"📊 أرسل سعر الوحدة الجديد (يمكن استخدام الفاصلة للكسور):")
        bot.register_next_step_handler(msg, process_admin_edit_service_quantity_price, service, category)
    
    elif call.data.startswith("admin_activate_service_"):
        parts = call.data.split("_")
        service = parts[3]
        category = "_".join(parts[4:])
        toggle_service_product_status(service, category, 1)
        bot.answer_callback_query(call.id, f"✅ تم تفعيل {category}")
        safe_edit_message_text(chat_id, message_id, f"💳 {service}\n📦 {category}\n\nاختر الإجراء:", create_service_product_actions_keyboard(service, category))
    
    elif call.data.startswith("admin_deactivate_service_"):
        parts = call.data.split("_")
        service = parts[3]
        category = "_".join(parts[4:])
        toggle_service_product_status(service, category, 0)
        bot.answer_callback_query(call.id, f"⛔ تم تعطيل {category}")
        safe_edit_message_text(chat_id, message_id, f"💳 {service}\n📦 {category}\n\nاختر الإجراء:", create_service_product_actions_keyboard(service, category))
    
    # ========== إدارة API ==========
    elif call.data == "admin_api_orders_page_1":
        orders, total, total_pages = get_api_orders(1)
        show_api_orders_page(chat_id, message_id, orders, 1, total_pages)
    
    elif call.data.startswith("admin_api_orders_page_"):
        page = int(call.data.split("_")[4])
        orders, total, total_pages = get_api_orders(page)
        show_api_orders_page(chat_id, message_id, orders, page, total_pages)
    
    elif call.data == "admin_api_management":
        safe_edit_message_text(chat_id, message_id, "🔌 إدارة API", create_api_management_keyboard())
    
    elif call.data == "admin_api_test":
        result = get_api_balance()
        if result['success']:
            msg = f"✅ اتصال ناجح\n📧 البريد: {result['email']}\n💰 الرصيد: {result['balance']}"
        else:
            msg = f"❌ فشل الاتصال: {result['error']}"
        bot.send_message(chat_id, msg)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_api_search":
        msg = bot.send_message(chat_id, "🔍 أرسل كلمة البحث (اسم المنتج، ID، أو اسم الفئة):")
        bot.register_next_step_handler(msg, process_api_search, 1)
    
    elif call.data.startswith("admin_api_search_page_"):
        parts = call.data.split("_")
        page = int(parts[4])
        search_term = "_".join(parts[5:])
        process_api_search_paginated(chat_id, message_id, search_term, page)
    
    elif call.data == "admin_api_link_select_game":
        safe_edit_message_text(chat_id, message_id, "🎮 اختر اللعبة لربط منتج:", create_api_link_game_keyboard())
    
    elif call.data.startswith("admin_api_link_game_"):
        game = call.data.replace("admin_api_link_game_", "")
        safe_edit_message_text(chat_id, message_id, f"📦 اختر المنتج لربطه في لعبة {game}:", create_api_link_product_keyboard(game))
    
    elif call.data.startswith("admin_api_link_product_"):
        parts = call.data.split("_")
        game = parts[4]
        category = "_".join(parts[5:])
        msg = bot.send_message(chat_id, f"🔗 أرسل معرف المنتج في API (api_product_id) للمنتج {category} في لعبة {game}:")
        bot.register_next_step_handler(msg, process_api_link_simple, game, category)
    
    elif call.data.startswith("admin_api_add_product_"):
        game = call.data.replace("admin_api_add_product_", "")
        msg = bot.send_message(chat_id, f"📝 أرسل اسم المنتج الجديد للعبة {game}:")
        bot.register_next_step_handler(msg, process_api_add_product_name, game)
    
    elif call.data == "admin_api_linked_1":
        products, total, total_pages = get_linked_products(1)
        show_linked_products_page(chat_id, message_id, products, 1, total_pages)
    
    elif call.data.startswith("admin_api_linked_"):
        page = int(call.data.split("_")[3])
        products, total, total_pages = get_linked_products(page)
        show_linked_products_page(chat_id, message_id, products, page, total_pages)
    
    # ========== أزرار بدون عملية ==========
    elif call.data == "noop":
        bot.answer_callback_query(call.id)
    
    bot.answer_callback_query(call.id)

# ================== دوال الخطوات المتتابعة ==================
def process_player_id(message, user_data):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    player_id = message.text.strip()
    
    if user_data.get('product_type') == 'quantity':
        # نطلب الكمية أولاً
        msg = bot.send_message(message.chat.id, f"🔢 أرسل الكمية المطلوبة (بين {user_data['min_qty']} و {user_data['max_qty']}):")
        bot.register_next_step_handler(msg, process_quantity, user_data, player_id)
    else:
        # باقة: ننشئ الطلب مباشرة
        order_id = create_order(message.from_user.id, user_data["game"], user_data["category"], user_data["price"], player_id, user_data.get("product_id"), 1)
        
        text = f"""
🧩 اللعبة : {user_data["game"]}

📊 الفئة : {user_data["category"]}

💳 السعر : {user_data["price"]} ل.س

🌌 طريقة الشحن : Id

🆔 معرف اللاعب : {player_id}

لطلب الفئة هذه اضغط تأكيد 👇🏻
        """
        bot.send_message(message.chat.id, text, reply_markup=create_confirmation_keyboard(order_id))

def process_quantity(message, user_data, player_id):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        qty = int(message.text.strip())
        if qty < user_data['min_qty'] or qty > user_data['max_qty']:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, f"❌ الكمية غير صالحة. يجب أن تكون بين {user_data['min_qty']} و {user_data['max_qty']}. أعد الإدخال:")
        bot.register_next_step_handler(msg, process_quantity, user_data, player_id)
        return
    
    total_price = user_data['price'] * qty
    order_id = create_order(message.from_user.id, user_data["game"], user_data["category"], total_price, player_id, user_data.get("product_id"), qty)
    
    text = f"""
🧩 اللعبة : {user_data["game"]}

📊 الفئة : {user_data["category"]}

💳 السعر النهائي : {total_price} ل.س

🌌 طريقة الشحن : Id

🆔 معرف اللاعب : {player_id}

🏷️ الكمية المطلوبة : {qty}

لطلب الفئة هذه اضغط تأكيد 👇🏻
    """
    bot.send_message(message.chat.id, text, reply_markup=create_confirmation_keyboard(order_id))

def process_app_player_id(message, user_data):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    player_id = message.text.strip()
    
    if user_data.get('product_type') == 'quantity':
        msg = bot.send_message(message.chat.id, f"🔢 أرسل الكمية المطلوبة (بين {user_data['min_qty']} و {user_data['max_qty']}):")
        bot.register_next_step_handler(msg, process_app_quantity, user_data, player_id)
    else:
        order_id = create_order(message.from_user.id, user_data["app"], user_data["category"], user_data["price"], player_id, user_data.get("product_id"), 1)
        
        text = f"""
🧩 التطبيق : {user_data["app"]}

📊 الفئة : {user_data["category"]}

💳 السعر : {user_data["price"]} ل.س

🌌 طريقة الشحن : Id

🆔 معرف المستخدم : {player_id}

لطلب الفئة هذه اضغط تأكيد 👇🏻
        """
        bot.send_message(message.chat.id, text, reply_markup=create_confirmation_keyboard(order_id))

def process_app_quantity(message, user_data, player_id):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        qty = int(message.text.strip())
        if qty < user_data['min_qty'] or qty > user_data['max_qty']:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, f"❌ الكمية غير صالحة. يجب أن تكون بين {user_data['min_qty']} و {user_data['max_qty']}. أعد الإدخال:")
        bot.register_next_step_handler(msg, process_app_quantity, user_data, player_id)
        return
    
    total_price = user_data['price'] * qty
    order_id = create_order(message.from_user.id, user_data["app"], user_data["category"], total_price, player_id, user_data.get("product_id"), qty)
    
    text = f"""
🧩 التطبيق : {user_data["app"]}

📊 الفئة : {user_data["category"]}

💳 السعر النهائي : {total_price} ل.س

🌌 طريقة الشحن : Id

🆔 معرف المستخدم : {player_id}

🏷️ الكمية المطلوبة : {qty}

لطلب الفئة هذه اضغط تأكيد 👇🏻
    """
    bot.send_message(message.chat.id, text, reply_markup=create_confirmation_keyboard(order_id))

def process_service_player_id(message, user_data):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    player_id = message.text.strip()
    
    if user_data.get('product_type') == 'quantity':
        # نطلب الكمية أولاً
        msg = bot.send_message(message.chat.id, f"🔢 أرسل الكمية المطلوبة (بين {user_data['min_qty']} و {user_data['max_qty']}):")
        bot.register_next_step_handler(msg, process_service_quantity, user_data, player_id)
    else:
        # باقة API
        order_id = create_order(message.from_user.id, user_data["service"], user_data["category"], user_data["price"], player_id, user_data.get("product_id"), 1)
        
        text = f"""
🧩 الخدمة : {user_data["service"]}

📊 الفئة : {user_data["category"]}

💳 السعر : {user_data["price"]} ل.س

🌌 طريقة الشحن : API

🆔 معرف المستخدم : {player_id}

لطلب الفئة هذه اضغط تأكيد 👇🏻
        """
        bot.send_message(message.chat.id, text, reply_markup=create_confirmation_keyboard(order_id))

def process_service_quantity(message, user_data, player_id):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        qty = int(message.text.strip())
        if qty < user_data['min_qty'] or qty > user_data['max_qty']:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, f"❌ الكمية غير صالحة. يجب أن تكون بين {user_data['min_qty']} و {user_data['max_qty']}. أعد الإدخال:")
        bot.register_next_step_handler(msg, process_service_quantity, user_data, player_id)
        return
    
    total_price = user_data['price'] * qty
    order_id = create_order(message.from_user.id, user_data["service"], user_data["category"], total_price, player_id, user_data.get("product_id"), qty)
    
    text = f"""
🧩 الخدمة : {user_data["service"]}

📊 الفئة : {user_data["category"]}

💳 السعر النهائي : {total_price} ل.س

🌌 طريقة الشحن : API

🆔 معرف المستخدم : {player_id}

🏷️ الكمية المطلوبة : {qty}

لطلب الفئة هذه اضغط تأكيد 👇🏻
    """
    bot.send_message(message.chat.id, text, reply_markup=create_confirmation_keyboard(order_id))

def process_deposit_amount(message, deposit_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح. اكتب المبلغ مرة أخرى:")
        bot.register_next_step_handler(msg, process_deposit_amount, deposit_type)
        return
    
    msg = bot.send_message(message.chat.id, "● ثـم أرسـل الآن رقم العملية : ")
    bot.register_next_step_handler(msg, process_transaction_id, amount, message.from_user.id, deposit_type)

def process_transaction_id(message, amount, user_id, deposit_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    transaction_id = message.text.strip()
    bot.send_message(message.chat.id, "🔄 جاري التحميل ...")
    success, msg_text = process_deposit_request(user_id, amount, transaction_id, deposit_type)
    bot.send_message(message.chat.id, msg_text)

def process_deposit_amount_sham(message, currency):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح. اكتب المبلغ مرة أخرى:")
        bot.register_next_step_handler(msg, process_deposit_amount_sham, currency)
        return
    
    msg = bot.send_message(message.chat.id, "● ثـم أرسـل الآن رقم العملية : ")
    bot.register_next_step_handler(msg, process_transaction_id_sham, amount, message.from_user.id, currency)

def process_transaction_id_sham(message, amount, user_id, currency):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    transaction_id = message.text.strip()
    bot.send_message(message.chat.id, "🔄 جاري التحميل ...")
    
    if currency == 'dollar':
        lira_amount = int(amount * get_exchange_rate())
        deposit_type = 'sham_dollar'
    else:
        lira_amount = int(amount)
        deposit_type = 'sham_lira'
    
    success, msg_text = process_deposit_request(user_id, lira_amount, transaction_id, deposit_type)
    bot.send_message(message.chat.id, msg_text)

def process_seriatel_manual_step1(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    transaction_id = message.text.strip()
    if not transaction_id.isdigit():
        msg = bot.send_message(message.chat.id, "❌ رقم العملية يجب أن يكون أرقام فقط. أرسل رقم العملية مرة أخرى:")
        bot.register_next_step_handler(msg, process_seriatel_manual_step1)
        return
    
    msg = bot.send_message(message.chat.id, "● أرسل المبلغ الذي قمت بتحويله:")
    bot.register_next_step_handler(msg, process_seriatel_manual_step2, transaction_id)

def process_seriatel_manual_step2(message, transaction_id):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        amount = int(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح. أرسل المبلغ مرة أخرى:")
        bot.register_next_step_handler(msg, process_seriatel_manual_step2, transaction_id)
        return
    
    msg = bot.send_message(message.chat.id, "● أرسل الرمز الذي أرسل لك:")
    bot.register_next_step_handler(msg, process_seriatel_manual_step3, transaction_id, amount)

def process_seriatel_manual_step3(message, transaction_id, amount):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    code = message.text.strip()
    if not code or len(code) < 3:
        msg = bot.send_message(message.chat.id, "❌ الرمز غير صالح. أرسل الرمز مرة أخرى:")
        bot.register_next_step_handler(msg, process_seriatel_manual_step3, transaction_id, amount)
        return
    
    user_id = message.from_user.id
    bot.send_message(message.chat.id, "✅ تم استلام طلبك بنجاح!\n\n🔄 جاري إرسال طلب الإيداع للمشرفين للمراجعة...")
    
    request_id = create_deposit_request(user_id, amount, transaction_id, 'seriatel_manual')
    
    deposits_channel_id = get_channel_setting('deposit_channel_id')
    send_to_channels = get_channel_setting('send_to_channels')
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ قبول", callback_data=f"accept_manual_{request_id}"),
        types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_manual_{request_id}")
    )
    
    notification = f"""
📨 طلب إيداع جديد (سيرياتيل كاش - يدوي):

👤 المستخدم: {user_id}
💳 المبلغ: {amount} ل.س
🔢 رقم العملية: {transaction_id}
🔐 الرمز المرسل: {code}
📅 التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """
    
    if not deposits_channel_id or send_to_channels != '1':
        for admin in get_all_admins():
            try:
                bot.send_message(admin['user_id'], notification, reply_markup=keyboard)
            except:
                pass
    elif send_to_channels == '1' and deposits_channel_id:
        try:
            bot.send_message(deposits_channel_id, notification, reply_markup=keyboard)
        except:
            pass
    
    bot.send_message(message.chat.id, f"""
📨 تم إرسال طلب الإيداع للمشرفين

📋 معلومات الطلب:
🔢 رقم العملية: {transaction_id}
💰 المبلغ: {amount} ل.س
🔐 الرمز: {code}
🆔 رقم الطلب: {request_id}

⏰ سيتم مراجعة طلبك خلال دقائق
""")

def process_admin_accept_manual_deposit(admin_id, request_id, call=None):
    request = get_deposit_request(request_id)
    if not request:
        bot.send_message(admin_id, "❌ طلب الإيداع غير موجود.")
        return
    
    if request['status'] != 'pending':
        if call:
            try:
                bot.edit_message_text("❌ هذا الطلب تم معالجته مسبقاً.\n\n🔄 يرجى تحديث الصفحة", call.message.chat.id, call.message.message_id, reply_markup=None)
            except:
                pass
        bot.send_message(admin_id, "❌ هذا الطلب تم معالجته مسبقاً.")
        return
    
    update_deposit_request_status(request_id, 'completed', 'accepted')
    update_user_balance(request['user_id'], request['amount'])
    mark_transaction_processed(request['transaction_id'], request['amount'], request['user_id'])
    
    new_balance = get_user_balance(request['user_id'])
    user_notification = f"""
✅ تم قبول طلب إيداعك اليدوي!

💳 المبلغ: {request['amount']} ل.س
🔢 رقم العملية: {request['transaction_id']}
💰 رصيدك الحالي: {new_balance} ل.س

شكراً لاستخدامك خدماتنا! 🎮
    """
    try:
        bot.send_message(request['user_id'], user_notification)
    except:
        pass
    
    bot.send_message(admin_id, f"✅ تم قبول طلب الإيداع اليدوي #{request_id} وإضافة {request['amount']} ل.س للمستخدم {request['user_id']}.")

def process_admin_reject_manual_deposit(admin_id, request_id, call=None):
    request = get_deposit_request(request_id)
    if not request:
        bot.send_message(admin_id, "❌ طلب الإيداع غير موجود.")
        return
    
    if request['status'] != 'pending':
        if call:
            try:
                bot.edit_message_text("❌ هذا الطلب تم معالجته مسبقاً.\n\n🔄 يرجى تحديث الصفحة", call.message.chat.id, call.message.message_id, reply_markup=None)
            except:
                pass
        bot.send_message(admin_id, "❌ هذا الطلب تم معالجته مسبقاً.")
        return
    
    update_deposit_request_status(request_id, 'rejected', 'rejected')
    
    user_notification = f"""
❌ تم رفض طلب إيداعك اليدوي!

💳 المبلغ: {request['amount']} ل.س
🔢 رقم العملية: {request['transaction_id']}
ℹ️ السبب: لم يتم التحقق من العملية

للمساعدة تواصل مع @Bar0nSupport
    """
    try:
        bot.send_message(request['user_id'], user_notification)
    except:
        pass
    
    bot.send_message(admin_id, f"✅ تم رفض طلب الإيداع اليدوي #{request_id}.")

def process_admin_accept_deposit(admin_id, request_id, call=None):
    request = get_deposit_request(request_id)
    if not request:
        bot.send_message(admin_id, "❌ طلب الإيداع غير موجود.")
        return
    
    if request['status'] != 'pending':
        if call:
            try:
                bot.edit_message_text("❌ هذا الطلب تم معالجته مسبقاً.\n\n🔄 يرجى تحديث الصفحة", call.message.chat.id, call.message.message_id, reply_markup=None)
            except:
                pass
        bot.send_message(admin_id, "❌ هذا الطلب تم معالجته مسبقاً.")
        return
    
    update_deposit_request_status(request_id, 'completed', 'accepted')
    update_user_balance(request['user_id'], request['amount'])
    mark_transaction_processed(request['transaction_id'], request['amount'], request['user_id'])
    
    new_balance = get_user_balance(request['user_id'])
    user_notification = f"""
✅ تم قبول طلب إيداعك!

💳 المبلغ: {request['amount']} ل.س
🔢 رقم العملية: {request['transaction_id']}
💰 رصيدك الحالي: {new_balance} ل.س

شكراً لاستخدامك خدماتنا! 🎮
    """
    try:
        bot.send_message(request['user_id'], user_notification)
    except:
        pass
    
    bot.send_message(admin_id, f"✅ تم قبول طلب الإيداع #{request_id} وإضافة {request['amount']} ل.س للمستخدم {request['user_id']}.")

def process_admin_reject_deposit(admin_id, request_id, call=None):
    request = get_deposit_request(request_id)
    if not request:
        bot.send_message(admin_id, "❌ طلب الإيداع غير موجود.")
        return
    
    if request['status'] != 'pending':
        if call:
            try:
                bot.edit_message_text("❌ هذا الطلب تم معالجته مسبقاً.\n\n🔄 يرجى تحديث الصفحة", call.message.chat.id, call.message.message_id, reply_markup=None)
            except:
                pass
        bot.send_message(admin_id, "❌ هذا الطلب تم معالجته مسبقاً.")
        return
    
    update_deposit_request_status(request_id, 'rejected', 'rejected')
    
    user_notification = f"""
❌ تم رفض طلب إيداعك!

💳 المبلغ: {request['amount']} ل.س
🔢 رقم العملية: {request['transaction_id']}
ℹ️ السبب: لم يتم التحقق من العملية

للمساعدة تواصل مع @Bar0nSupport
    """
    try:
        bot.send_message(request['user_id'], user_notification)
    except:
        pass
    
    bot.send_message(admin_id, f"✅ تم رفض طلب الإيداع #{request_id}.")

def process_broadcast_message(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    broadcast_text = message.text
    conn = get_db_connection()
    users = conn.execute('SELECT user_id FROM users').fetchall()
    conn.close()
    
    total = len(users)
    successful = 0
    failed = 0
    
    bot.send_message(message.chat.id, f"📤 بدء إرسال الإذاعة لـ {total} مستخدم...")
    
    for user in users:
        try:
            bot.send_message(user['user_id'], broadcast_text)
            successful += 1
            time.sleep(0.1)
        except:
            failed += 1
    
    report = f"""
📊 تقرير الإذاعة:

📝 النوع: للجميع
👥 إجمالي المستخدمين: {total}
✅ الناجحة: {successful}
❌ الفاشلة: {failed}
📊 النسبة: {round((successful/total)*100, 2) if total > 0 else 0}%
    """
    bot.send_message(message.chat.id, report)

def process_admin_add_balance_user(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "💵 أرسل المبلغ الذي تريد إضافته:")
        bot.register_next_step_handler(msg, process_admin_add_balance_amount, user_id)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال ايدي صحيح. أرسل ايدي المستخدم مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_add_balance_user)

def process_admin_add_balance_amount(message, user_id):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        amount = int(message.text)
        update_user_balance(user_id, amount)
        new_balance = get_user_balance(user_id)
        bot.send_message(message.chat.id, f"✅ تم إضافة {amount} ل.س إلى رصيد المستخدم {user_id}. 💰الرصيد الجديد: {new_balance} ل.س")
        bot.send_message(user_id, f"✅ تم إضافة {amount} ل.س إلى رصيدك. 💰رصيدك الآن: {new_balance} ل.س")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح. أرسل المبلغ مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_add_balance_amount, user_id)

def process_admin_deduct_balance_user(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "💵 أرسل المبلغ الذي تريد خصمه:")
        bot.register_next_step_handler(msg, process_admin_deduct_balance_amount, user_id)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال ايدي صحيح. أرسل ايدي المستخدم مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_deduct_balance_user)

def process_admin_deduct_balance_amount(message, user_id):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        amount = int(message.text)
        update_user_balance(user_id, -amount)
        new_balance = get_user_balance(user_id)
        bot.send_message(message.chat.id, f"✅ تم خصم {amount} ل.س من رصيد المستخدم {user_id}. 💰الرصيد الجديد: {new_balance} ل.س")
        bot.send_message(user_id, f"⚠️ تم خصم {amount} ل.س من رصيدك. 💰رصيدك الآن: {new_balance} ل.س")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال مبلغ صحيح. أرسل المبلغ مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_deduct_balance_amount, user_id)

def process_admin_ban_user(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        user_id = int(message.text)
        ban_user(user_id)
        bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {user_id}.")
        bot.send_message(user_id, "🚫 تم حظرك من استخدام البوت ، تواصل مع @Bar0nSupport لمعرفة سبب الحظر")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال ايدي صحيح. أرسل ايدي المستخدم مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_ban_user)

def process_admin_unban_user(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        user_id = int(message.text)
        unban_user(user_id)
        bot.send_message(message.chat.id, f"✅ تم رفع حظر المستخدم {user_id}.")
        bot.send_message(user_id, "✅ تم رفع حظرك ، اذا لم يتم رفع الحظر تواصل مع @Bar0nSupport .")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال ايدي صحيح. أرسل ايدي المستخدم مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_unban_user)

def process_admin_user_info(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        user_id = int(message.text)
        user = get_user(user_id)
        if user:
            total_spent = get_user_total_spent(user_id)
            text = f"""
👤 الـحـسـاب و الـمـعـلـومـات 

الاسم : {user['full_name'] or 'غير معروف'}            
معرف : @{user['username'] or 'لا يوجد'} 
            
ايدي الحساب : {user['user_id']} 
            
الرصيد الحالي : {user['balance']} ل.س 
            
إجـمـالـي الـمـصـروفـات : {total_spent} ل.س
            
عدد المشتريات : {user['purchases_count']} منتج .
            """
            bot.send_message(message.chat.id, text)
        else:
            bot.send_message(message.chat.id, "❌ المستخدم غير موجود")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال ايدي صحيح. أرسل ايدي المستخدم مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_user_info)

def process_admin_change_seriatel_auto(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_number = message.text.strip()
    update_setting('seriatel_auto_number', new_number)
    bot.send_message(message.chat.id, f"✅ تم تغيير رقم سيرياتيل أوتوماتيك إلى: {new_number}")

def process_admin_change_seriatel_manual(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_number = message.text.strip()
    update_setting('seriatel_manual_number', new_number)
    bot.send_message(message.chat.id, f"✅ تم تغيير رقم سيرياتيل يدوي إلى: {new_number}")

def process_admin_change_sham_dollar(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_address = message.text.strip()
    update_setting('sham_dollar_address', new_address)
    bot.send_message(message.chat.id, f"✅ تم تغيير عنوان شام دولار إلى: {new_address}")

def process_admin_change_sham_lira(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_address = message.text.strip()
    update_setting('sham_lira_address', new_address)
    bot.send_message(message.chat.id, f"✅ تم تغيير عنوان شام ليرة إلى: {new_address}")

def process_admin_change_support(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_support = message.text.strip()
    update_setting('support_username', new_support)
    bot.send_message(message.chat.id, f"✅ تم تغيير يوزر الدعم إلى: {new_support}")

def process_admin_change_welcome(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_welcome = message.text
    update_setting('welcome_message', new_welcome)
    bot.send_message(message.chat.id, f"✅ تم تغيير رسالة البداية بنجاح.")

def process_add_new_admin(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        user_id = int(message.text)
        add_admin(user_id)
        bot.send_message(message.chat.id, f"✅ تم إضافة المستخدم {user_id} كمشرف.")
        bot.send_message(user_id, "👑 تهانينا! لقد تم تعيينك كمشرف في البوت. استخدم أمر /admin للوصول إلى لوحة التحكم.")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال ايدي صحيح. أرسل ايدي المستخدم مرة أخرى:")
        bot.register_next_step_handler(msg, process_add_new_admin)

def process_set_mandatory_channel(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    channel_link = message.text.strip()
    
    try:
        if "t.me/" in channel_link:
            username = channel_link.split("t.me/")[1]
            if not username.startswith("@"):
                username = "@" + username
        elif channel_link.startswith("@"):
            username = channel_link
        else:
            bot.send_message(message.chat.id, "❌ يرجى إدخال رابط أو معرف قناة صحيح.")
            return
        
        chat_info = bot.get_chat(username)
        bot.get_chat_member(chat_id=chat_info.id, user_id=bot.get_me().id)
        set_mandatory_channel(chat_info.id, channel_link)
        bot.send_message(message.chat.id, f"✅ تم تعيين قناة الاشتراك الإجباري بنجاح: {channel_link}")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ حدث خطأ: يرجى التأكد من أن البوت مشرف في القناة وأن المعرف صحيح.")

def process_set_orders_channel(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    channel_id = message.text.strip()
    update_channel_setting('orders_channel_id', channel_id)
    bot.send_message(message.chat.id, f"✅ تم تعيين قناة طلبات الشحن بنجاح: `{channel_id}`", parse_mode="Markdown")

def process_set_deposits_channel(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    channel_id = message.text.strip()
    update_channel_setting('deposit_channel_id', channel_id)
    bot.send_message(message.chat.id, f"✅ تم تعيين قناة طلبات الإيداع بنجاح: `{channel_id}`", parse_mode="Markdown")

def process_set_new_users_channel(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    channel_id = message.text.strip()
    update_channel_setting('new_users_channel_id', channel_id)
    bot.send_message(message.chat.id, f"✅ تم تعيين قناة المستخدمين الجدد بنجاح: `{channel_id}`", parse_mode="Markdown")

def process_set_sms_channel(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    channel_id = message.text.strip()
    update_channel_setting('sms_channel_id', channel_id)
    bot.send_message(message.chat.id, f"✅ تم تعيين قناة SMS بنجاح: `{channel_id}`", parse_mode="Markdown")

def process_admin_change_price(message, game, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        new_price = int(message.text)
        update_product_price(game, category, new_price)
        bot.send_message(message.chat.id, f"✅ تم تغيير سعر فئة {category} إلى {new_price} ل.س")
    except ValueError:
        bot.send_message(message.chat.id, "❌ قيمة غير صالحة")

def process_admin_change_code(message, game, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_code = message.text.strip()
    update_product_code(game, category, new_code)
    bot.send_message(message.chat.id, f"✅ تم تغيير رمز API لفئة {category} إلى {new_code}")

def process_admin_edit_quantity_price(message, game, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price_per_unit = float(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأدنى للكمية:")
        bot.register_next_step_handler(msg, process_admin_edit_quantity_min, game, category, price_per_unit)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال سعر الوحدة:")
        bot.register_next_step_handler(msg, process_admin_edit_quantity_price, game, category)

def process_admin_edit_quantity_min(message, game, category, price_per_unit):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        min_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأعلى للكمية:")
        bot.register_next_step_handler(msg, process_admin_edit_quantity_max, game, category, price_per_unit, min_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأدنى:")
        bot.register_next_step_handler(msg, process_admin_edit_quantity_min, game, category, price_per_unit)

def process_admin_edit_quantity_max(message, game, category, price_per_unit, min_qty):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        max_qty = int(message.text.strip())
        conn = get_db_connection()
        conn.execute('UPDATE products SET price_per_unit = ?, min_qty = ?, max_qty = ? WHERE game = ? AND category = ?', (price_per_unit, min_qty, max_qty, game, category))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تم تحديث بيانات الكمية للمنتج {category}.")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأعلى:")
        bot.register_next_step_handler(msg, process_admin_edit_quantity_max, game, category, price_per_unit, min_qty)

def process_admin_change_app_price(message, app, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        new_price = int(message.text)
        update_app_product_price(app, category, new_price)
        bot.send_message(message.chat.id, f"✅ تم تغيير سعر فئة {category} إلى {new_price} ل.س")
    except ValueError:
        bot.send_message(message.chat.id, "❌ قيمة غير صالحة")

def process_admin_change_app_code(message, app, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_code = message.text.strip()
    update_app_product_code(app, category, new_code)
    bot.send_message(message.chat.id, f"✅ تم تغيير رمز API لفئة {category} إلى {new_code}")

def process_admin_edit_app_quantity_price(message, app, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price_per_unit = float(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأدنى للكمية:")
        bot.register_next_step_handler(msg, process_admin_edit_app_quantity_min, app, category, price_per_unit)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال سعر الوحدة:")
        bot.register_next_step_handler(msg, process_admin_edit_app_quantity_price, app, category)

def process_admin_edit_app_quantity_min(message, app, category, price_per_unit):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        min_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأعلى للكمية:")
        bot.register_next_step_handler(msg, process_admin_edit_app_quantity_max, app, category, price_per_unit, min_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأدنى:")
        bot.register_next_step_handler(msg, process_admin_edit_app_quantity_min, app, category, price_per_unit)

def process_admin_edit_app_quantity_max(message, app, category, price_per_unit, min_qty):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        max_qty = int(message.text.strip())
        conn = get_db_connection()
        conn.execute('UPDATE app_products SET price_per_unit = ?, min_qty = ?, max_qty = ? WHERE app = ? AND category = ?', (price_per_unit, min_qty, max_qty, app, category))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تم تحديث بيانات الكمية للمنتج {category}.")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأعلى:")
        bot.register_next_step_handler(msg, process_admin_edit_app_quantity_max, app, category, price_per_unit, min_qty)

def process_admin_change_service_price(message, service, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        new_price = int(message.text)
        update_service_product_price(service, category, new_price)
        bot.send_message(message.chat.id, f"✅ تم تغيير سعر فئة {category} إلى {new_price} ل.س")
    except ValueError:
        bot.send_message(message.chat.id, "❌ قيمة غير صالحة")

def process_admin_change_service_code(message, service, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    new_code = message.text.strip()
    update_service_product_code(service, category, new_code)
    bot.send_message(message.chat.id, f"✅ تم تغيير رمز API لفئة {category} إلى {new_code}")

def process_admin_edit_service_quantity_price(message, service, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price_per_unit = float(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأدنى للكمية:")
        bot.register_next_step_handler(msg, process_admin_edit_service_quantity_min, service, category, price_per_unit)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال سعر الوحدة:")
        bot.register_next_step_handler(msg, process_admin_edit_service_quantity_price, service, category)

def process_admin_edit_service_quantity_min(message, service, category, price_per_unit):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        min_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأعلى للكمية:")
        bot.register_next_step_handler(msg, process_admin_edit_service_quantity_max, service, category, price_per_unit, min_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأدنى:")
        bot.register_next_step_handler(msg, process_admin_edit_service_quantity_min, service, category, price_per_unit)

def process_admin_edit_service_quantity_max(message, service, category, price_per_unit, min_qty):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        max_qty = int(message.text.strip())
        conn = get_db_connection()
        conn.execute('UPDATE service_products SET price_per_unit = ?, min_qty = ?, max_qty = ? WHERE service = ? AND category = ?', (price_per_unit, min_qty, max_qty, service, category))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ تم تحديث بيانات الكمية للمنتج {category}.")
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأعلى:")
        bot.register_next_step_handler(msg, process_admin_edit_service_quantity_max, service, category, price_per_unit, min_qty)

def process_add_game(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    game_name = message.text.strip()
    add_game(game_name)
    bot.send_message(message.chat.id, f"✅ تم إضافة اللعبة {game_name} بنجاح")
    admin_panel(message)

def process_add_app(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    app_name = message.text.strip()
    add_app(app_name)
    bot.send_message(message.chat.id, f"✅ تم إضافة التطبيق {app_name} بنجاح")
    admin_panel(message)

def process_add_service(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    service_name = message.text.strip()
    add_service(service_name)
    bot.send_message(message.chat.id, f"✅ تم إضافة الخدمة {service_name} بنجاح")
    admin_panel(message)

def process_add_product_name(message, game):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    product_name = message.text.strip()
    # نسأل عن نوع المنتج: باقة أم كمية (تم إزالة كود)
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("باقة", callback_data=f"admin_add_product_type_{game}_{product_name}_package"),
        types.InlineKeyboardButton("كمية", callback_data=f"admin_add_product_type_{game}_{product_name}_quantity")
    )
    bot.send_message(message.chat.id, "📦 اختر نوع المنتج:", reply_markup=keyboard)

def process_add_product_price(message, game, product_name, product_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price = float(message.text.strip())
        if product_type == 'quantity':
            # سعر الوحدة
            msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأدنى للكمية:")
            bot.register_next_step_handler(msg, process_add_product_min_qty, game, product_name, price, product_type)
        else:
            # باقة: نسأل عن السعر النهائي ثم رمز API
            msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
            bot.register_next_step_handler(msg, process_add_product_api_id, game, product_name, int(price), product_type, None, None, None)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال سعر صحيح. أرسل السعر مرة أخرى:")
        bot.register_next_step_handler(msg, process_add_product_price, game, product_name, product_type)

def process_add_product_min_qty(message, game, product_name, price_per_unit, product_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        min_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأعلى للكمية:")
        bot.register_next_step_handler(msg, process_add_product_max_qty, game, product_name, price_per_unit, min_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأدنى:")
        bot.register_next_step_handler(msg, process_add_product_min_qty, game, product_name, price_per_unit)

def process_add_product_max_qty(message, game, product_name, price_per_unit, min_qty):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        max_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
        bot.register_next_step_handler(msg, process_add_product_api_id, game, product_name, None, 'quantity', price_per_unit, min_qty, max_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأعلى:")
        bot.register_next_step_handler(msg, process_add_product_max_qty, game, product_name, price_per_unit, min_qty)

def process_add_product_api_id(message, game, product_name, price, product_type, price_per_unit=None, min_qty=None, max_qty=None):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    api_id = message.text.strip()
    if product_type == 'quantity':
        add_product(game, product_name, 0, api_id, product_type='quantity', price_per_unit=price_per_unit, min_qty=min_qty, max_qty=max_qty)
        bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} (كمية) بنجاح")
    else:
        add_product(game, product_name, price, api_id, product_type='package')
        bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} (باقة) بنجاح")

def process_add_app_product_name(message, app):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    product_name = message.text.strip()
    # نسأل عن نوع المنتج: باقة أم كمية
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("باقة", callback_data=f"admin_add_app_product_type_{app}_{product_name}_package"),
        types.InlineKeyboardButton("كمية", callback_data=f"admin_add_app_product_type_{app}_{product_name}_quantity")
    )
    bot.send_message(message.chat.id, "📦 اختر نوع المنتج:", reply_markup=keyboard)

def process_add_app_product_price(message, app, product_name, product_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price = float(message.text.strip())
        if product_type == 'quantity':
            msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأدنى للكمية:")
            bot.register_next_step_handler(msg, process_add_app_product_min_qty, app, product_name, price, product_type)
        else:
            msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
            bot.register_next_step_handler(msg, process_add_app_product_api_id, app, product_name, int(price), product_type, None, None, None)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال سعر صحيح. أرسل السعر مرة أخرى:")
        bot.register_next_step_handler(msg, process_add_app_product_price, app, product_name, product_type)

def process_add_app_product_min_qty(message, app, product_name, price_per_unit, product_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        min_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأعلى للكمية:")
        bot.register_next_step_handler(msg, process_add_app_product_max_qty, app, product_name, price_per_unit, min_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأدنى:")
        bot.register_next_step_handler(msg, process_add_app_product_min_qty, app, product_name, price_per_unit)

def process_add_app_product_max_qty(message, app, product_name, price_per_unit, min_qty):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        max_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
        bot.register_next_step_handler(msg, process_add_app_product_api_id, app, product_name, None, 'quantity', price_per_unit, min_qty, max_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأعلى:")
        bot.register_next_step_handler(msg, process_add_app_product_max_qty, app, product_name, price_per_unit, min_qty)

def process_add_app_product_api_id(message, app, product_name, price, product_type, price_per_unit=None, min_qty=None, max_qty=None):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    api_id = message.text.strip()
    if product_type == 'quantity':
        add_app_product(app, product_name, 0, api_id, product_type='quantity', price_per_unit=price_per_unit, min_qty=min_qty, max_qty=max_qty)
        bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} (كمية) بنجاح")
    else:
        add_app_product(app, product_name, price, api_id, product_type='package')
        bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} (باقة) بنجاح")

def process_add_service_product_name(message, service):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    product_name = message.text.strip()
    # نسأل عن نوع المنتج: باقة، كمية (تم إزالة كود)
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("باقة", callback_data=f"admin_add_service_product_type_{service}_{product_name}_package"),
        types.InlineKeyboardButton("كمية", callback_data=f"admin_add_service_product_type_{service}_{product_name}_quantity")
    )
    bot.send_message(message.chat.id, "📦 اختر نوع المنتج:", reply_markup=keyboard)

def process_add_service_product_price(message, service, product_name, product_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price = float(message.text.strip())
        if product_type == 'quantity':
            # سعر الوحدة
            msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأدنى للكمية:")
            bot.register_next_step_handler(msg, process_add_service_product_min_qty, service, product_name, price, product_type)
        else:
            # باقة
            msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
            bot.register_next_step_handler(msg, process_add_service_product_api_id, service, product_name, int(price), product_type, None, None, None)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال سعر صحيح. أرسل السعر مرة أخرى:")
        bot.register_next_step_handler(msg, process_add_service_product_price, service, product_name, product_type)

def process_add_service_product_min_qty(message, service, product_name, price_per_unit, product_type):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        min_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📊 أرسل الحد الأعلى للكمية:")
        bot.register_next_step_handler(msg, process_add_service_product_max_qty, service, product_name, price_per_unit, min_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأدنى:")
        bot.register_next_step_handler(msg, process_add_service_product_min_qty, service, product_name, price_per_unit)

def process_add_service_product_max_qty(message, service, product_name, price_per_unit, min_qty):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        max_qty = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
        bot.register_next_step_handler(msg, process_add_service_product_api_id, service, product_name, None, 'quantity', price_per_unit, min_qty, max_qty)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ قيمة غير صالحة. أعد إدخال الحد الأعلى:")
        bot.register_next_step_handler(msg, process_add_service_product_max_qty, service, product_name, price_per_unit, min_qty)

def process_add_service_product_api_id(message, service, product_name, price, product_type, price_per_unit=None, min_qty=None, max_qty=None):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    api_id = message.text.strip()
    if product_type == 'quantity':
        add_service_product(service, product_name, 0, product_id=api_id, product_type='quantity', price_per_unit=price_per_unit, min_qty=min_qty, max_qty=max_qty)
        bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} (كمية) بنجاح")
    else:
        add_service_product(service, product_name, price, product_id=api_id, product_type='package')
        bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} (باقة) بنجاح")

def process_api_search(message, page=1):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    term = message.text.strip()
    result = search_api_products(term, page)
    if not result['success']:
        bot.send_message(message.chat.id, f"❌ خطأ: {result.get('error')}")
        return
    
    if not result['results']:
        bot.send_message(message.chat.id, f"❌ لا توجد نتائج للبحث عن '{term}'.")
        return
    
    text = f"🔍 *نتائج البحث عن:* `{term}`\n📄 الصفحة {result['page']} من {result['total_pages']}\n\n"
    for p in result['results']:
        name = p.get('name', 'غير معروف')
        pid = p.get('id', 'غير معروف')
        price = p.get('price', 0)
        cat = p.get('category_name', 'غير محدد')
        game = p.get('game_name', 'غير محدد')
        available = p.get('available', False)
        product_type = p.get('product_type', 'package')
        status = "✅ متاح" if available else "❌ غير متاح"
        
        text += f"━━━━━━━━━━━━━━━━\n"
        text += f"📌 *الاسم:* {name}\n"
        text += f"🆔 *المعرف:* `{pid}`\n"
        text += f"💰 *السعر:* {price} دولار\n"
        text += f"📂 *الفئة:* {cat}\n"
        text += f"📦 *النوع:* {'باقة' if product_type == 'package' else 'كمية'}\n"
        text += f"📊 *الحالة:* {status}\n"
        
        # عرض معلومات الكمية إذا كانت متوفرة
        if product_type == 'quantity' and p.get('qty_values'):
            qty = p['qty_values']
            min_qty = qty.get('min', 'غير محدد')
            max_qty = qty.get('max', 'غير محدد')
            text += f"🔽 *الحد الأدنى:* {min_qty}\n"
            text += f"🔼 *الحد الأقصى:* {max_qty}\n"
        
        text += "\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav_row = []
    if result['page'] > 1:
        nav_row.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"admin_api_search_page_{result['page']-1}_{term}"))
    nav_row.append(types.InlineKeyboardButton(f"{result['page']}/{result['total_pages']}", callback_data="noop"))
    if result['page'] < result['total_pages']:
        nav_row.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"admin_api_search_page_{result['page']+1}_{term}"))
    if nav_row:
        keyboard.add(*nav_row)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_api_management"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")

def process_api_search_paginated(chat_id, message_id, search_term, page):
    result = search_api_products(search_term, page)
    if not result['success'] or not result['results']:
        try:
            safe_edit_message_text(chat_id, message_id, f"❌ لا توجد نتائج للبحث عن '{search_term}'.", create_back_keyboard("admin_api_management"))
        except:
            pass
        return
    
    text = f"🔍 *نتائج البحث عن:* `{search_term}`\n📄 الصفحة {result['page']} من {result['total_pages']}\n\n"
    for p in result['results']:
        name = p.get('name', 'غير معروف')
        pid = p.get('id', 'غير معروف')
        price = p.get('price', 0)
        cat = p.get('category_name', 'غير محدد')
        game = p.get('game_name', 'غير محدد')
        available = p.get('available', False)
        product_type = p.get('product_type', 'package')
        status = "✅ متاح" if available else "❌ غير متاح"
        
        text += f"━━━━━━━━━━━━━━━━\n"
        text += f"📌 *الاسم:* {name}\n"
        text += f"🆔 *المعرف:* `{pid}`\n"
        text += f"💰 *السعر:* {price} دولار\n"
        text += f"📂 *الفئة:* {cat}\n"
        text += f"📦 *النوع:* {'باقة' if product_type == 'package' else 'كمية'}\n"
        text += f"📊 *الحالة:* {status}\n"
        
        if product_type == 'quantity' and p.get('qty_values'):
            qty = p['qty_values']
            min_qty = qty.get('min', 'غير محدد')
            max_qty = qty.get('max', 'غير محدد')
            text += f"🔽 *الحد الأدنى:* {min_qty}\n"
            text += f"🔼 *الحد الأقصى:* {max_qty}\n"
        
        text += "\n"
    
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    nav_row = []
    if result['page'] > 1:
        nav_row.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"admin_api_search_page_{result['page']-1}_{search_term}"))
    nav_row.append(types.InlineKeyboardButton(f"{result['page']}/{result['total_pages']}", callback_data="noop"))
    if result['page'] < result['total_pages']:
        nav_row.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"admin_api_search_page_{result['page']+1}_{search_term}"))
    if nav_row:
        keyboard.add(*nav_row)
    keyboard.add(types.InlineKeyboardButton("رجوع", callback_data="admin_api_management"))
    
    try:
        safe_edit_message_text(chat_id, message_id, text, keyboard, parse_mode="Markdown")
    except:
        pass

def process_api_link_simple(message, game, category):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    api_id = message.text.strip()
    check = check_api_product(api_id)
    if not check['success'] or not check.get('exists'):
        bot.send_message(message.chat.id, f"❌ المنتج {api_id} غير موجود في API.")
        return
    
    # نأخذ نوع المنتج من API ونخزنه
    product_type = check.get('product_type', 'package')
    conn = get_db_connection()
    conn.execute('UPDATE products SET product_id = ?, product_type = ? WHERE game = ? AND category = ?', (api_id, product_type, game, category))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ تم ربط {game} - {category} مع API ID `{api_id}` (نوع: {product_type})", parse_mode="Markdown")
    bot.send_message(message.chat.id, "🔌 إدارة API", reply_markup=create_api_management_keyboard())

def process_api_add_product_name(message, game):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    product_name = message.text.strip()
    msg = bot.send_message(message.chat.id, f"💰 أرسل سعر المنتج {product_name}:")
    bot.register_next_step_handler(msg, process_api_add_product_price, game, product_name)

def process_api_add_product_price(message, game, product_name):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        price = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"🔑 أرسل معرف المنتج في API (api_product_id):")
        bot.register_next_step_handler(msg, process_api_add_product_api_id, game, product_name, price)
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال سعر صحيح. أرسل السعر مرة أخرى:")
        bot.register_next_step_handler(msg, process_api_add_product_price, game, product_name)

def process_api_add_product_api_id(message, game, product_name, price):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    api_id = message.text.strip()
    check = check_api_product(api_id)
    product_type = check.get('product_type', 'package') if check.get('success') else 'package'
    add_product(game, product_name, price, api_id, product_type=product_type)
    bot.send_message(message.chat.id, f"✅ تم إضافة المنتج {product_name} وربطه مع API ID `{api_id}` (نوع: {product_type})", parse_mode="Markdown")
    bot.send_message(message.chat.id, "🔌 إدارة API", reply_markup=create_api_management_keyboard())

def process_admin_exchange_rate(message):
    if message.text.lower() in ['/start', 'رجوع']:
        send_welcome(message)
        return
    
    try:
        new_rate = int(message.text.strip())
        if new_rate <= 0:
            raise ValueError
        
        update_exchange_rate(new_rate)
        bot.send_message(message.chat.id, f"✅ تم تحديث سعر الصرف إلى: {new_rate} ل.س")
        
        # عرض لوحة الأدمن مرة أخرى
        bot.send_message(message.chat.id, "🗽 𝑩𝑨𝑹𝑶𝑵 𝑫𝑬𝑽\n• أهــلاً بــك فــي لــوحة الإدارة الــخاصة بــك :", 
                        reply_markup=create_admin_main_keyboard(message.from_user.id))
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ يرجى إدخال رقم صحيح موجب. أرسل القيمة مرة أخرى:")
        bot.register_next_step_handler(msg, process_admin_exchange_rate)

def run_bot():
    print("🤖 The bot works...")
    
    if not os.path.exists("steps"):
        os.makedirs("steps")
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except KeyboardInterrupt:
        print("👋 The bot was manually stopped.")
    except Exception as e:
        print(f"⚠️ Error: {e}")
        print("🔄 Restart the bot...")
        time.sleep(5)
        run_bot()

if __name__ == '__main__':
    run_bot()