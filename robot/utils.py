# -*- coding: utf-8-*-

import os
import tempfile
import wave
import struct
import shutil
import re
import time
import logging
from . import constants, config
from pydub import AudioSegment
from pytz import timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

do_not_bother = False

def sendEmail(SUBJECT, BODY, ATTACH_LIST, TO, FROM, SENDER,
              PASSWORD, SMTP_SERVER, SMTP_PORT):
    """Sends an email."""
    txt = MIMEText(BODY.encode('utf-8'), 'html', 'utf-8')
    msg = MIMEMultipart()
    msg.attach(txt)    

    for attach in ATTACH_LIST:
        try:
            att = MIMEText(open(attach, 'rb').read(), 'base64', 'utf-8')
            filename = os.path.basename(attach)
            att["Content-Type"] = 'application/octet-stream'
            att["Content-Disposition"] = 'attachment; filename="%s"' % filename
            msg.attach(att)
        except Exception:
            logger.error(u'附件 %s 发送失败！' % attach)
            continue

    msg['From'] = SENDER
    msg['To'] = TO
    msg['Subject'] = SUBJECT

    try:
        session = smtplib.SMTP()
        session.connect(SMTP_SERVER, SMTP_PORT)
        session.starttls()
        session.login(FROM, PASSWORD)
        session.sendmail(SENDER, TO, msg.as_string())
        session.close()
        return True
    except Exception as e:
        logger.error(e)
        return False


def emailUser(profile, SUBJECT="", BODY="", ATTACH_LIST=[]):
    """
    sends an email.

    Arguments:
        profile -- contains information related to the user (e.g., email
                   address)
        SUBJECT -- subject line of the email
        BODY -- body text of the email
    """
    # add footer
    if BODY:
        BODY = u"%s，<br><br>这是您要的内容：<br>%s<br>" % (profile['first_name'], BODY)

    recipient = profile['email']['address']
    robot_name = u'叮当'
    if profile['robot_name_cn']:
        robot_name = profile['robot_name_cn']
    recipient = robot_name + " <%s>" % recipient

    if not recipient:
        return False

    try:
        user = profile['email']['address']
        password = profile['email']['password']
        server = profile['email']['smtp_server']
        port = profile['email']['smtp_port']
        sendEmail(SUBJECT, BODY, ATTACH_LIST, user, user,
                  recipient, password, server, port)

        return True
    except Exception as e:
        logger.error(e)
        return False


def get_file_content(filePath):
    """ 读取文件 """
    with open(filePath, 'rb') as fp:
        return fp.read()

def check_and_delete(fp):
    """ 检查并删除文件 """
    if isinstance(fp, str) and os.path.exists(fp):
        os.remove(fp)

def write_temp_file(data, suffix):
    """ 二进制形式写入临时文件 """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        tmpfile = f.name
    return tmpfile

def get_pcm_from_wav(wav_path):
    """ 从 wav 文件中读取 pcm """
    wav = wave.open(wav_path, 'rb')
    return wav.readframes(wav.getnframes())

def convert_wav_to_mp3(wav_path):
    """ 将 wav 文件转成 mp3 """
    mp3_path = wav_path.replace('.wav', '.mp3')
    AudioSegment.from_wav(wav_path).export(mp3_path, format="mp3")
    return mp3_path

def clean():
    """ 清理垃圾数据 """
    temp = constants.TEMP_PATH
    temp_files = os.listdir(temp)
    for f in temp_files:
        if os.path.isfile(os.path.join(temp, f)) and re.match(r'output[\d]*\.wav', os.path.basename(f)):
            os.remove(os.path.join(temp, f))

def is_proper_time():
    """ 是否合适时间 """
    if do_not_bother:
        return False
    if not config.has('do_not_bother'):
        return True
    bother_profile = config.get('do_not_bother')
    if not bother_profile['enable']:
        return True
    if 'since' not in bother_profile or 'till' not in bother_profile:
        return True
    since = bother_profile['since']
    till = bother_profile['till']
    current = time.localtime(time.time()).tm_hour
    if till > since:
        return current not in range(since, till)
    else:
        return not (current in range(since, 25) or
                    current in range(-1, till))

def get_do_not_bother_on_hotword():
    """ 打开勿扰模式唤醒词 """
    default_hotword = '悟空别吵.pmdl'
    if not config.has('do_not_bother'):
        return default_hotword
    bother_profile = config.get('do_not_bother')
    return bother_profile.get('on_hotword', default_hotword)

def get_do_not_bother_off_hotword():
    """ 关闭勿扰模式唤醒词 """
    default_hotword = '悟空醒醒.pmdl'
    if not config.has('do_not_bother'):
        return default_hotword
    bother_profile = config.get('do_not_bother')
    return bother_profile.get('off_hotword', default_hotword)

def getTimezone():
    """ 获取时区 """
    return timezone(config.get('timezone', 'HKT'))
