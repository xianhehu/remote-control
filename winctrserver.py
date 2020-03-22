#-*- coding: UTF-8 -*-
import socket
import json
import threading
import time
import os

gConfigFile= "wincs.ini"
gUserName = "cdc"
gPassWord = "123456"
gCommands = []

def readConfig():
    global gCommands,gUserName,gPassWord,gConfigFile
    try:
        f = open(gConfigFile, "r+")
        jrec = json.load(f)
        f.close()

        if jrec == None:
            return

        if "username" in jrec:
            gUserName = jrec["username"]

        if "password" in jrec:
            gPassWord = jrec["password"]

        if "commands" in jrec:
            gCommands = jrec["commands"]
    except BaseException,e:
        repr(e)

def saveConfig():
    global gCommands, gUserName, gPassWord, gConfigFile
    try:
        jrec = {"username":gUserName,"password":gPassWord,"commands":gCommands}
        str = json.dumps(jrec)

        f = open(gConfigFile, "w+")
        f.write(str)
        f.close()
    except BaseException,e:
        repr(e)

def addCommand(commandstr, comment):
    global gCommands
    jcmd = {"cmd":commandstr,"cmt":comment}
    gCommands.append(jcmd)

    saveConfig()

    return True

def chgCommand(indx, commandstr, comment):
    global gCommands
    if indx >= len(gCommands):
        return False

    jcmd = {"cmd": commandstr, "cmt": comment}
    gCommands[indx] = jcmd

    saveConfig()

    return True

def delCommand(indx):
    global gCommands

    if indx >= len(gCommands):
        return False

    cmds = gCommands[:indx]
    cmds.extend(gCommands[indx+1:])
    gCommands = cmds

    saveConfig()

    return True

def execCommand(indx):
    global gCommands
    if indx >= len(gCommands):
        return False

    if "cmd" not in gCommands[indx]:
        return False

    os.system(gCommands[indx]["cmd"])

    return True

class ThreadCtrl(threading.Thread):
    def __init__(self, s, a):
        threading.Thread.__init__(self)
        self.authed = False
        self.sock = s
        self.addr = a
        self.gMsgFuncs = {
            u"login": self.handleLogin,
            u"help": self.handleHelp,
            u"exec": self.handleCommandExec,
            u"add": self.handleCommandAdd,
            u"del": self.handleCommandDel,
            u"change": self.handleCommandChange
        }
        self.done = False

    def handleLogin(self, jmsg):
        if "username" not in jmsg or "password" not in jmsg:
            return 11,"must contain username and password"

        if jmsg["username"] != gUserName or jmsg["password"] != gPassWord:
            return 11, "username or password error"

        if len(gCommands) < 1:
            self.authed = True
            return 0, " "

        jres = {}
        for i in range(len(gCommands)):
            jres[i] = gCommands[i]["cmt"]

        self.authed = True

        return 0, json.dumps(jres)

    def handleHelp(self, jmsg):
        if len(gCommands) < 1:
            return 0, " "

        jres = {}
        for i in range(len(gCommands)):
            jres[i] = gCommands[i]["cmt"]

        return 0, json.dumps(jres)

    def handleCommandExec(self, jmsg):
        if "index" in jmsg:
            try:
                indx = int(jmsg["index"])
                if execCommand(indx):
                    return 0, " "
                return 2, "exec failed index:" + indx
            except BaseException, e:
                return 1, e.message()

        if "cmmand" in jmsg:
            try:
                os.system(jmsg["command"])
                return 0, " "
            except BaseException, e:
                return 1, e.message()

        return 3, "must contain index or cmmand"

    def handleCommandAdd(self, jmsg):
        if "command" in jmsg and "comment" in jmsg:
            try:
                if addCommand(jmsg["command"], jmsg["comment"]):
                    return 0, " "

                return 2, "add command failed"
            except BaseException, e:
                return 1, e.message()

        return 3, "must contain cmmand and comment"

    def handleCommandChange(self, jmsg):
        if "cmmand" in jmsg and "comment" in jmsg and "index" in jmsg:
            try:
                if chgCommand(jmsg["index"], jmsg["command"], jmsg["comment"]):
                    return 0, " "

                return 2, "change command failed,index ", jmsg["index"]
            except BaseException, e:
                return 1, e.message()

        return 3, "must contain index, cmmand and comment"

    def handleCommandDel(self, jmsg):
        if "index" in jmsg:
            try:
                if delCommand(jmsg["index"]):
                    return 0, " "

                return 2, "delete command failed,index ", jmsg["index"]
            except BaseException, e:
                return 1, e.message()

        return 3, "must contain index"

    def handleMsg(self, msg):
        jmsg = json.loads(msg)
        if "type" not in jmsg:
            return 1, "have no type"

        type = jmsg["type"]
        if type not in self.gMsgFuncs:
            return 2, "unknow type " + type

        if type != "login" and self.authed == False:
            self.sock.close()
            self.done = True
            return 1,"must login"

        func = self.gMsgFuncs[type]
        if func == None:
            return 3, "invalid type " + type

        try:
            return func(jmsg["data"])
        except BaseException,e:
            print e
            return 4, "exec error, type:" + type

    def run(self):
        while self.done == False:
            try:
                ret = self.sock.recv(40960)

                if ret != None and len(ret) > 3:
                    ret = self.handleMsg(ret)
                    res = {"ret":ret[0], "msg":ret[1]}
                    self.sock.send(json.dumps(res))
            except BaseException,e:
                print repr(e)
                break
        try:
            self.sock.close()
        except BaseException:
            return

if __name__ == '__main__':
    readConfig()

    # 等待验证请求
    serv = socket.socket()
    serv.bind(("",6052))
    serv.listen(100)

    while True:
        try:
            s,a = serv.accept()
            print "receive connect "
            print a
            ThreadCtrl(s,a).start()
        except BaseException,e:
            repr(e)