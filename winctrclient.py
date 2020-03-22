#-*- coding: UTF-8 -*-
import socket
import json
import time
import os
import re

# str = '  1   "command1   "'
# strs = re.findall(r'(.+?) "(.+?)" "(.+?)"', str)
# print strs
gServerAddr = "127.0.0.1:6052"
gConfigFile= "wincc.ini"
gUserName = "cdc"
gPassWord = "123456"
gDone = False

def readConfig():
    global gUserName,gPassWord,gConfigFile,gServerAddr
    try:
        f = open(gConfigFile, "r+")
        jrec = json.load(f)
        f.close()

        if jrec == None:
            return

        if "server" in jrec:
            gServerAddr = jrec["server"]

        if "username" in jrec:
            gUserName = jrec["username"]

        if "password" in jrec:
            gPassWord = jrec["password"]

    except BaseException,e:
        repr(e)

def saveConfig():
    global gServerAddr, gUserName, gPassWord, gConfigFile
    try:
        jrec = {"username":gUserName,"password":gPassWord,"server":gServerAddr}
        str = json.dumps(jrec)

        f = open(gConfigFile, "w+")
        f.write(str)
        f.close()
    except BaseException,e:
        repr(e)

def waitRes(s):
    trys = 0
    while trys < 10:
        try:
            res = s.recv(4096)
            if res != None and len(res) > 3:
                jres = json.loads(res)
                return jres["ret"],jres["msg"]
        except BaseException,e:
            repr(e)
        trys+=1
        time.sleep(1)

    return 1,"timeout"

def login(s):
    req = {"type":"login","data":{"username":gUserName,"password":gPassWord}}
    s.send(json.dumps(req))
    return waitRes(s)

def help(sck, str):
    req = {"type": "help","data":" "}
    sck.send(json.dumps(req))
    ret, msg = waitRes(sck)
    if ret == 0:
        print "h:help\nu:change user configure\na:add command\nc:change command\nd:delete command\ne:exec command\nq:exit"
    print msg

def changeConfigure(sck, str):
    global gUserName,gPassWord,gServerAddr

    strs = re.findall(r'u "(.+?)" "(.+?)" "(.+?)"', str)
    if len(strs) < 1 or len(strs[0]) < 3:
        print "usage:u <\"username\"> <\"password\"> <\"server ip:port\">"
        return

    params = []
    strs = strs[0]

    for s in strs:
        s.strip(" ")
        if len(s) > 0:
            params.append(s)

    if len(params) < 3 or ":" not in params[2]:
        print "usage:a <\"command string\"> <\"comment string\">"
        return

    if gUserName == params[0] and gPassWord == params[1] and gServerAddr == params[2]:
        return

    gUserName = params[0]
    gPassWord = params[1]
    gServerAddr = params[2]

    saveConfig()
    gDone = True

def addCommand(sck, str):
    strs = re.findall(r'a "(.+?)" "(.+?)"', str)
    if len(strs) < 1:
        print "usage:a <\"command string\"> <\"comment string\">"
        return

    params = []
    strs = strs[0]

    for s in strs:
        s.strip(" ")
        if len(s) > 0:
            params.append(s)

    if len(params) < 2:
        print "usage:a <\"command string\"> <\"comment string\">"
        return

    req = {"type":"add","data":{"command":params[0],"comment":params[1]}}
    sck.send(json.dumps(req))
    ret,msg = waitRes(sck)
    if ret != 0:
        print msg
    else:
        print "success"

def chgCommand(sck, indx, commandstr, comment):
    strs = re.findall(r'c (.+?) "(.+?)" "(.+?)"', str)
    if len(strs) < 1:
        print "usage:c <number> <\"command string\"> <\"comment string\">"
        return

    params = []
    strs = strs[0]

    for s in strs:
        s.strip(" ")
        s.strip("\"")
        if len(s) > 0:
            params.append(s)

    if len(params) < 3:
        print "usage:c <number> <\"command string\"> <\"comment string\">"
        return

    try:
        number = int(params[0])
        req = {"type": "change", "data":{"index":number,"command": params[1], "comment": params[2]}}
        sck.send(json.dumps(req))
        ret, msg = waitRes(sck)
        if ret != 0:
            print msg
        else:
            print "success"
    except BaseException,e:
        print "usage:c <number> <\"command string\"> <\"comment string\">"

def delCommand(sck, str):
    strs = re.findall(r'd (.+?)', str)
    if len(strs) < 1:
        print "usage:d <number>"
        return

    str = strs[0][0]

    try:
        number = int(str)
        req = {"type": "del", "data":{"index": number}}
        sck.send(json.dumps(req))
        ret, msg = waitRes(sck)
        if ret != 0:
            print msg
        else:
            print "success"
    except BaseException,e:
        print "usage:c <number> <\"command string\"> <\"comment string\">"

def execCommandIndex(sck, str):
    try:
        number = int(str)
        req = {"type": "exec", "data":{"index": number}}
        sck.send(json.dumps(req))
        ret, msg = waitRes(sck)
        if ret != 0:
            print msg
        else:
            print "success"
    except BaseException, e:
        print "usage:<number>"

def execCommandCustom(sck, str):
    try:
        strs = re.findall(r'e "(.+?)"',str)
        if len(strs) > 0:
            req = {"type": "exec", "data":{"command": strs[0][0]}}
            sck.send(json.dumps(req))
            ret, msg = waitRes(sck)
            if ret != 0:
                print msg
            else:
                print "success"
    except BaseException, e:
        print "usage:e <\"command string\">"

gCommands = {
    "a":addCommand,
    "c":chgCommand,
    "d":delCommand,
    "e":execCommandCustom,
    "h":help,
    "u":changeConfigure
}

def handleCommand(sck, str):
    strs = str.split(" ")
    if len(strs) < 1:
        print "invalid input"
        return

    cmd = strs[0].strip(" ")
    if cmd in gCommands:
        gCommands[cmd](sck, str)
    else:
        execCommandIndex(sck,str)

if __name__ == '__main__':
    readConfig()

    while True:
        if len(gUserName) < 3 or len(gPassWord) < 3:
            gUserName = input("username:")
            gPassWord = input("password")
            saveConfig()
            continue

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # sock.connect(("3s.net579.com", 12009))
            s.connect(("127.0.0.1", 6052))
        except BaseException:
            print u"连接远程服务器失败"
            time.sleep(1)
            continue
        s.settimeout(1)
        ret,msg = login(s)
        print msg
        if ret != 0:
            s.close()
            print "u:change user configure\nq:exit"
            str = raw_input(">>")
            changeConfigure(s,str)
            continue

        print "h:help\nu:change user configure\na:add command\nc:change command\nd:delete command\ne:exec command\nq:exit"
        print msg

        while gDone == False:
            str = raw_input(">>")
            handleCommand(s, str)
            if str == "q":
                os.abort()

        gDone = False
        s.close()
