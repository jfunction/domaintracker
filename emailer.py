# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText

import smtplib
import ConfigParser


def send_email(ascii_text, subject, src_email, dst_email):
  # Cast the text as a new MIMEText object for sending
  msg = MIMEText(ascii_text)
  
  # Add some obvious params
  msg['Subject'] = subject
  msg['From'] = src_email
  msg['To'] = dst_email

  # Send the message via our own SMTP server, but don't include the
  # envelope header.
  conf = get_configuration_dict()
  # for k, v in conf.iteritems():
  #   conf[k] = v.replace("'", "").replace('"', '')
  username = conf['email_username']
  password = ''.join(chr(int(i)) for i in conf['email_password'].replace(' ','').split(','))  # offers "some" protection
  print 'USER:', username
  print 'PASS:', '*'*len(password)
  server = smtplib.SMTP(conf['smtp_server'])
  server.ehlo()
  server.starttls()
  server.login(username, password)
  server.sendmail(src_email, [dst_email], msg.as_string())
  server.quit()


# TODO: Move this out to utils with param = sections as elements in list
def get_configuration_dict():
    config_reader = ConfigParser.ConfigParser()
    config_reader.readfp(open(r'settings.conf'))
    config = dict(config_reader.items("Email"))
    return config


def test_mail():
  conf = get_configuration_dict()
  me = conf['email_source']
  you = conf['email_destination']
  subject = "TESTING"
  txt =     "This is a test email from my pc."
  send_email(txt, subject, me, you)


def example_program():
    '''
        This is one way we can use this script - it is a bit hacky...
        basically, you keep around a variable called "previous_md5sum"
        whenever you call this script you md5sum your log file and compare it with this variable.
        If the log file has changed, you send the email and update the previous_md5sum variable.
        So you can call this script as a cron job frequently and it will only email you if there's new stuff.
    '''
    import hashlib
    file_to_monitor = "dns-track.log"
    with open("previous_md5sum", "r+") as f:
        previous_md5sum = f.read()

    log_text = "There was an error processing the log file. Please review the status of the software."
    with open(file_to_monitor, "r") as f:
        log_text = f.read()
        current_md5sum = hashlib.md5(log_text).hexdigest()

    if current_md5sum is not previous_md5sum:
        conf = get_configuration_dict()
        me = conf['email_source']
        you = conf['email_destination']
        subject = conf['email_subject']
        txt = "REPORT:\n\n%s" % (log_text)
        send_email(txt, subject, me, you)
        with open("previous_md5sum", "wb+") as f:
            f.write(current_md5sum)

if __name__ == "__main__":
    example_program()