from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Task, UserProgress
from datetime import datetime
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
import reminder  # 後で作成

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 初回DB作成
with app.app_context():
    db.create_all()

# ==================== ルート ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に登録されています')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('登録が完了しました。ログインしてください')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('tasks'))
        flash('メールアドレスまたはパスワードが間違っています')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@login_required
def tasks():
    from datetime import datetime
# tasks() 関数の return の直前
return render_template('tasks.html', tasks=task_list, now=datetime.utcnow())
    if request.method == 'POST':
        # タスク作成
        title = request.form['title']
        description = request.form.get('description', '')
        deadline_str = request.form['deadline']
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')

        task = Task(title=title, description=description, deadline=deadline, created_by=current_user.id)
        db.session.add(task)
        db.session.commit()
        flash('タスクを作成しました')

    # 全タスク取得 + 自分の進捗情報
    tasks = Task.query.order_by(Task.deadline).all()
    task_list = []
    for task in tasks:
        progress = UserProgress.query.filter_by(user_id=current_user.id, task_id=task.id).first()
        if not progress:
            progress = UserProgress(user_id=current_user.id, task_id=task.id, status='todo')
            db.session.add(progress)
            db.session.commit()

        task_list.append({
            'task': task,
            'progress': progress
        })

    return render_template('tasks.html', tasks=task_list)


@app.route('/update_progress/<int:task_id>', methods=['POST'])
@login_required
def update_progress(task_id):
    status = request.form['status']
    notes = request.form.get('notes', '')

    progress = UserProgress.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    if progress:
        progress.status = status
        progress.notes = notes
        db.session.commit()
    flash('進捗を更新しました')
    return redirect(url_for('tasks'))


if __name__ == '__main__':
    # 自動リマインダー（1時間ごとにチェック）
    scheduler = BackgroundScheduler()
    scheduler.add_job(reminder.check_and_send_reminders, 'interval', hours=1, args=[app])
    scheduler.start()
    print("自動リマインダー起動中...")

    app.run(debug=True)
