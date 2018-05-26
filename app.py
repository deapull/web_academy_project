from flask import Flask, render_template, flash, redirect, url_for, session , logging, request, Response
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from flask_socketio import SocketIO, send, emit
import cv2

app = Flask(__name__)

#Config MySQL

app.config['MySQL_HOST'] = 'localhost'
app.config['MySQL_USER'] = 'mrlandovskiy'
app.config['MYSQL_PASSWORD'] = 'deapul12345a'
app.config['MYSQL_DB'] = 'punchy'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#Initialize MySQL
mysql = MySQL(app)
socketio = SocketIO(app)


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1,max=50)])
    username = StringField('Username', [validators.Length(min=4,max=25)])
    email = StringField('Email',[validators.Length(min=6,max=50)])
    password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')


class VideoCamera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)
    def __del__(self):
        self.video.release()

    def get_frame(self):
        ret,image = self.video.read()
        ret,jpeg = cv2.imencode('.jpg',image)
        return jpeg.tobytes()


@app.route('/video_feed')
def video_feed():
    value = (Response(gen(VideoCamera()),content_type="multipart/x-mixed-replace;boundary=frame"))
    print(value)
    return value


def gen(camera):
    while True:
        frame = camera.get_frame()

        yield(b'--frame\r\n'
        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


@app.route('/', methods=['GET','POST'])
def index():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)",(name,email,username,password))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('index'))

    return render_template('home.html', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':

        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()

        result = cur.execute('SELECT * FROM users WHERE username = %s', [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate, password):
                app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('main'))
            else:
                error = 'Invalid login'
                return render_template('login.html')
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html')

    return render_template('login.html')

@app.route('/main')
def main():
    return render_template('main.html')

@socketio.on('login_message')
def handle_message(msg):
    if session['logged_in'] == True:
        msg['username'] = session['username']

        emit('my response', msg,broadcast=True)
    else:
        emit('my response', 'Guest logged in')

@socketio.on('messages')
def handle_message(msg):
    msg['username'] = session['username']
    emit('my response', msg, broadcast=True)

if __name__ == '__main__':
    app.secret_key='secret'
    socketio.run(app, debug=True)