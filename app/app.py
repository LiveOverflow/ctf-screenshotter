import asyncio
import hashlib
import hmac
import time
import uuid
import pyppeteer
import base64
import socket
from datetime import datetime
from logzero import logger
from functools import wraps
import sqlite3
from threading import Thread
from flask import Flask, render_template, g, url_for, request, Response, copy_current_request_context, jsonify


DATABASE = 'sqlite.db'
# hopefully this gets the chrome service's IP, because chrome debug doesn't allow access via hostname
try:
    CHROME_IP = socket.getaddrinfo('chrome',0)[0][4][0]
except socket.gaierror:
    CHROME_IP = '127.0.0.1'
try:
    SECRET = open('secret', 'rb').read()
except FileNotFoundError:
    SECRET = uuid.uuid4().bytes
    
app = Flask(__name__)


def redirect(location):
    "drop-in replacement for flask's redirect that doesn't sanitize the redirect target URL"
    response = Response('Redirecting...', 302, mimetype="text/html")
    response.headers["Location"] = location
    response.autocorrect_location_header = False
    return response

# https://github.com/fengsp/flask-snippets/blob/master/templatetricks/timesince_filter.py
@app.template_filter()
def timesince(dt, default="just now"):
    now = datetime.utcnow()
    # 2021-03-03 13:34:58
    diff = now - datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
    periods = (
        (int(diff.days / 365), "year", "years"),
        (int(diff.days / 30), "month", "months"),
        (int(diff.days / 7), "week", "weeks"),
        (diff.days, "day", "days"),
        (int(diff.seconds / 3600), "hour", "hours"),
        (int(diff.seconds / 60), "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default

def signature(s):
    '''
    generate a hmac signature for a given string
    '''
   
    m = hmac.new(SECRET, digestmod=hashlib.sha256)
    m.update(s.encode('ascii'))
    return m.hexdigest()

def get_db():
    '''
    helper function to get a sqlite database connection
    '''
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    '''
    helper function to close the database connection
    '''
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    '''
    helper function to do a SQL query like select
    '''
    #logger.info(f'{query} | {args}')
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def commit_db(query, args=()):
    '''
    helper function to do SQl queries like insert into
    '''
    #logger.info(f'{query} | {args}')
    get_db().cursor().execute(query, args)
    get_db().commit()

def login_required(f):
    '''
    login required decorator to ensure g.user exists
    '''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in g or g.user == None:
            return redirect('/logout')
        return f(*args, **kwargs)
    return decorated_function

def public_log(msg):
    logger.info(msg)
    commit_db('insert into logs (msg) values (?)', [msg])

@app.before_request
def before_request():
    '''
    session middleware. checks if we have a valid session and sets g.user
    '''
    # request - flask.request
    if 'session' not in request.cookies:
        return None
    session = request.cookies['session'].split('.')
    if not len(session) == 2:
        return None
    
    key, sig = session
    if not hmac.compare_digest(sig, signature(key)):
        return None
    g.user= query_db('select * from users where uuid = ?', 
                    [key], one=True)
    

async def screenshot(username, note_uuid, url):
    try:
        
        browser = await pyppeteer.connect(browserURL=f'http://{CHROME_IP}:9222')
        context = await browser.createIncognitoBrowserContext()
        page = await context.newPage()
        await page.goto(url)
        await asyncio.sleep(10) # wait until page is fully loaded
        title = await page.title()
        shot = await page.screenshot()
        await context.close()

        data = 'data:image/png;base64,'+base64.b64encode(shot).decode('ascii')
        commit_db('update notes set data = ?, title = ? where uuid = ?', [data, title, note_uuid])
        public_log(f"awesome! screenshot processed for {username}")
    except:
        public_log(f"sorry {username} :( your screenshot failed")
        commit_db('delete from notes where uuid = ?', [note_uuid])

    


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    response = redirect("/")
    response.set_cookie('session', '', expires=0)
    return response

@app.route('/notes')
@login_required
def notes():
    notes = query_db('select * from notes where user = ? order by timestamp desc', [g.user['uuid']])
    return render_template('notes.html', user=g.user, notes=notes)

@app.route('/activity.json')
def activity_json():
    log = query_db('select * from logs order by timestamp desc LIMIT 15')
    log_dict = [
        {'id': l['id'], 'timestamp': l['timestamp'], 'msg': l['msg']} 
        for l in log]
    return jsonify(log_dict)

@app.route('/activity')
def activity():
    logs = query_db('select * from logs order by timestamp desc LIMIT 15')
    
    return render_template('activity.html', logs=logs, len_logs=len(logs))

@app.route('/notes.json')
@login_required
def notes_json():
    notes = query_db('select * from notes where user = ? order by timestamp desc', [g.user['uuid']])
    notes_dict = [
        {'uuid': n['uuid'], 'body': n['body'], 'title': n['title'], 'timestamp': n['timestamp'], 'data': n['data']} 
        for n in notes]
    return jsonify(notes_dict)

@app.route('/delete_note', methods=['POST'])
@login_required
def delete_note():
    user = g.user['uuid']
    note_uuid = request.form['uuid']

    commit_db('delete from notes where uuid = ? and user = ?', [note_uuid, user])
    public_log(f"{g.user['username']} deleted a note")
    return redirect('/notes')

@app.route('/add_note', methods=['POST'])
@login_required
def add_note():
    new_note_uuid = uuid.uuid4().hex
    user = g.user['uuid']
    title = request.form['title']
    body = request.form['body']
    data = ''

    if body.startswith('https://www.cscg.de') or body.startswith('http://cscg.de'):

        @copy_current_request_context
        def screenshot_task(username, note_uuid, url):
            asyncio.set_event_loop(asyncio.SelectorEventLoop())
            asyncio.get_event_loop().run_until_complete(screenshot(username, note_uuid, url))

        title = 'processing screenshot...'
        data = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQYV2O4e/fufwAIyQOXgDhBOwAAAABJRU5ErkJggg=='
        thread = Thread(target=screenshot_task, args=(g.user['username'], new_note_uuid, body))
        thread.daemon = True
        thread.start()
        worker_name = base64.b64encode(CHROME_IP.encode('ascii')).decode('ascii').strip('=')
        public_log(f"{g.user['username']} requested a screenshot via worker chrome:{worker_name}")
    else:
        public_log(f"nice! {g.user['username']} added a note")
    commit_db('insert into notes (uuid, user, title, body, data) values (?, ?, ?, ?, ?)', 
            [new_note_uuid, user, title, body, data])
    return redirect('/notes')

@app.route('/registerlogin', methods=['POST'])
def registerlogin():
    username = request.form['username']
    password = request.form['password']
    pwhash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    user = query_db('select * from users where username = ? and password = ?', 
                    [username, pwhash], one=True)

    if not user:
        # new user. let's create it in the database
        new_user_uuid = uuid.uuid4().hex
        commit_db('insert into users (uuid, username, password) values (?, ?, ?)', 
                [new_user_uuid, username, pwhash])
        user= query_db('select * from users where uuid = ?', [new_user_uuid], one=True)
    
    # calculate signature for cookie
    key = user['uuid']
    sig = signature(user['uuid'])
    response = redirect('/notes')
    response.set_cookie('session', f'{key}.{sig}')
    return response

