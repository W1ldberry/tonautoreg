import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailNotifier:
    def __init__(self, login, password, smtp_server, smtp_port):
        self.login = login
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send(self, address, message, subject='TON validator node notification'):
        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.starttls()
        server.login(self.login, self.password)

        msg = MIMEMultipart()
        msg['From'] = self.login
        msg['To'] = address
        # Make sure you add a new line in the subject
        msg['Subject'] = subject + '\n'
        # Make sure you also add new lines to your body
        body = message + '\n'
        # and then attach that body furthermore you can also send html content.
        msg.attach(MIMEText(body, 'plain'))

        sms = msg.as_string()

        server.sendmail(self.login, address, sms)

        # lastly quit the server
        server.quit()
