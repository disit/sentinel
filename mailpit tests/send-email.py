from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import smtplib


def send_emails(sender_email, sender_password, receiver_emails, data_to_be_sent):
    smtp_port = 1025
    if False:
        server = smtplib.SMTP_SSL("localhost", smtp_port)
    else:
        server = smtplib.SMTP("localhost", smtp_port)
        server.starttls()
    if False:
        server.login(sender_email, sender_password)
    composite_message = data_to_be_sent
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ','.join(receiver_emails)
    msg['Subject'] = "Salutations!"
    msg.attach(MIMEText(str(composite_message), 'html'))
    server.send_message(msg)
    server.quit()


send_emails("originemail@gmail.com","this passowrd isn't valid",["aaa@bcd.com","zzz@yxw.com"],"Hello World!")