# -*- coding: UTF-8 -*-
import requests
import datetime
import time
import xlwt
import pymysql
from bs4 import BeautifulSoup
from pathlib import Path
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from configobj import ConfigObj


def main():
    global bookNames    # 书名
    global kindlemail   # kindle邮箱
    global sendmail     # 发送方邮箱
    global smtpserver   # smtp服务地址
    global serverport   # smtp端口
    global password     # 发送方邮箱密码
    global encryption   # smtp加密方式 0:明文 1:tls 2:ssl
    configfile = Path("config/config.cfg")
    if configfile.exists():
        config = ConfigObj("config/config.cfg", encoding="utf-8")
        # 书名
        bookNames = config["book"]["bookName"]
        # kindle邮箱地址
        kindlemail = config["mail"]["kindlemail"]
        # 发送邮件的邮箱
        sendmail = config["mail"]["sendmail"]
        # 发送邮件的服务器 比如163邮箱:SMTP.163.com 需要开启smtp服务
        smtpserver = config["mail"]["smtpserver"]
        serverport = config["mail"]["serverport"]
        # 邮箱密码 这个密码是发送邮件那个邮箱的密码
        password = config["mail"]["password"]
        encryption = config["mail"]["encryption"]
        if bookNames != '':
            if kindlemail != '':
                if sendmail != '':
                    if smtpserver != '':
                        if serverport != '':
                            if password != '':
                                if encryption != '':
                                    catchnovel()
                                    return
        print("配置有误,程序将在3秒后重新进入配置")
        time.sleep(3)
        setconfig()
    else:
        print("---------------------本软件不会上传用户个人信息(邮箱,密码之类的)请您放心使用---------------")
        print("------------------------如有疑问,您可以github获取源码,或通过邮箱联系到我------------------")
        print("-------------git:https://github.com/weishengliang/kindle_lastest_chapter_push--------")
        print("--------------------------------mail:cnweisl@163.com---------------------------------")
        print("-------------------------------输入回车继续使用,退出请右上角----------------------------")
        input()
        setconfig()

# 爬取解析数据
def catchnovel():
    log("开始查找。。。")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
                      '(KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36'}
    website = ["http://www.booksky.cc", "http://www.booksky.so"]
    searchcontent = "/modules/article/search.php?searchkey="
    while 1:
        for bookName in bookNames:
            targeturl = website[0] + searchcontent + bookName
            response = requests.get(targeturl, headers=headers)
            time.sleep(1)
            if response.status_code == 200:
                response.encoding = "utf-8"
                # 解析获得的html文本
                soup = BeautifulSoup(response.text, 'lxml')
                # 获取小说名a标签
                bookinfo = soup.find('a', class_="novelname")
                bookinfourl = bookinfo['href']
                # 获取小说详情页
                bookinfores = requests.get(website[0]+bookinfourl, headers=headers)
                time.sleep(1)
                if bookinfores.status_code == 200:
                    bookinfores.encoding = "utf-8"
                    bookinfosoup = BeautifulSoup(bookinfores.text, "lxml")
                    # 解析出最新章节的标签
                    ul = bookinfosoup.find(class_="novelinfo-l").find("ul")
                    last = ul.find_all("li")[5].find("a")
                    # 获取最新章节的名称 用来判断该章节是否获取过 同时用作文件名
                    newChapterName = last["title"]
                    # 最新章节的url
                    newChapterUrl = last["href"]
                    # print(str(newChapterName) + ":" + str(newChapterUrl))
                    # 检查最新章节是否已经获取过
                    filepath = Path(bookName+"/"+newChapterName + ".txt")
                    if filepath.exists():   # 获取过最新章节则跳过该章节的获取
                        log(bookName+"暂无更新")
                        continue
                    log("发现最新章节:"+newChapterName)
                    if not Path(bookName).exists():
                        Path(bookName).mkdir()
                    # 未获取过 则开始获取最新章节html文本
                    lastResponse = requests.get(website[0]+newChapterUrl, headers=headers)
                    time.sleep(1)
                    lastResponse.encoding = "utf-8"
                    # 解析
                    lastSoup = BeautifulSoup(lastResponse.text, "lxml")
                    # 获取内容
                    lastcontent = lastSoup.find(class_="content")
                    if lastcontent.length < 1000:
                        continue
                    # 写入文件
                    file = open(bookName+"/"+newChapterName + ".txt", mode="w+", encoding="utf-8")
                    # print(lastcontent.get_text())
                    file.write(lastcontent.get_text())
                    file.flush()
                    file.close()
                    # 调用接口发送邮件
                    sendMail(bookName, newChapterName)
            # 为避免ip被禁 等待35s再请求下一本书
            time.sleep(3)
        print('下次搜索将在5分钟后进行，如需停止，请直接退出，否则程序将一直运行')
        time.sleep(300)


def log(str):
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + str)

# 发送邮件
def sendMail(bookName, newChapterName):

    # 设置发送的内容 MIMEMultipart 几乎可以发送所有的附件类型
    message = MIMEMultipart()
    # 转化为邮件文本
    file = open(bookName+"/"+newChapterName + ".txt", "rb")
    content = MIMEText(file.read(), 'base64', 'utf-8')

    content["content_Type"] = 'application/octet-stream'
    content.add_header("Content-Disposition", "attachment", fileName=("utf-8", "", newChapterName+".txt"))
    file.close()

    message.attach(content)
    # 主题
    message["Subject"] = newChapterName
    # 发送者
    message["From"] = sendmail

    # 创建SMTP 服务器 连接
    if encryption == '2':
        mailServer = smtplib.SMTP_SSL(smtpserver, serverport)   # ssl加密方式
    else:
        mailServer = smtplib.SMTP(smtpserver, serverport)       # smtp普通连接
        if encryption == '1':                                   # tls加密
            mailServer.ehlo()
            mailServer.starttls()                               # 添加tls加密

    # 登陆邮箱
    mailServer.login(sendmail, password)
    # 发送邮件
    mailServer.sendmail(sendmail, [kindlemail], message.as_string())
    # 退出邮箱
    mailServer.quit()
    log("发送成功")

# 设置配置文件
def setconfig():
    config = ConfigObj("config/config.cfg", encoding="utf-8")
    config.filename = "config/config.cfg"
    print("请输入您的kindle邮箱:")
    kindlemail = input()

    print("请输入用来发送邮件的邮箱地址:")
    sendmail = input()

    print("请输入发送邮箱smtp服务器地址(如网易:smtp.163.com):")
    smtpserver = input()

    print("请输入smtp服务器的端口(如网易:25):")
    serverport = input()

    print("请输入发送邮箱密码(将会明文保存在根目录下config/config.cfg中):")
    password = input()

    print("请选择该smtp服务是否tls加密(:0：无加密明文 1：tls加密 2：ssl加密):")
    encryption = input()

    books = []
    while 1:
        print("请输入要追更的小说(多次输入，没有了直接回车):")
        bookName = input()
        if bookName == '':
            break
        else:
            books.append(bookName)

    config["mail"] = {
        "kindlemail": kindlemail,
        "sendmail": sendmail,
        "smtpserver": smtpserver,
        'serverport': serverport,
        'password': password,
        'encryption': encryption
    }
    config["mail"].comments = {
        "kindlemail": ["接收邮箱", ],
        "sendmail": ["发送邮箱", ],
        "smtpserver": ['smtp服务地址', ],
        'serverport': ['smtp服务端口', ],
        'password': ['发送邮箱密码', ],
        'encryption': ['邮箱加密方式 0:明文 1:tls 2:ssl'],
    }
    config["book"] = {
        "bookName": books
    }
    config["book"].comments = {
        "bookName": ["多本书用英文逗号隔开','"]
    }
    if not Path("config").exists():
        Path("config").mkdir()
    config.write()
    print("设置成功,程序3秒后开始搜书")
    time.sleep(3)
    main()


if __name__ == "__main__":
    main()
