from models import db, Task, UserProgress, User
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = os.getenv('EMAIL_USER')
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
        server.starttls()
        server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
        server.send_message(msg)
        server.quit()
        print(f"メール送信完了 → {to_email}")
    except Exception as e:
        print(f"メール送信失敗: {e}")


def check_and_send_reminders(app):
    with app.app_context():
        now = datetime.utcnow()
        tomorrow = now + timedelta(hours=24)

        # 期限が24時間以内の未完了タスク
        tasks = Task.query.filter(Task.deadline <= tomorrow, Task.deadline > now).all()

        for task in tasks:
            # そのタスクで未完了のユーザー全員に通知
            progresses = UserProgress.query.filter_by(task_id=task.id).all()
            for p in progresses:
                if p.status != 'done':
                    user = User.query.get(p.user_id)
                    if user:
                        body = f"""
こんにちは {user.username} さん

以下の課題の期限が近づいています：
【課題】{task.title}
【期限】{task.deadline.strftime('%Y年%m月%d日 %H:%M')}

現在のあなたの進捗：{p.status}
メモ：{p.notes or 'なし'}

今すぐ対応をお願いします！

SharedTask
                        """
                        send_email(user.email, "【期限接近】未完了課題のお知らせ", body)