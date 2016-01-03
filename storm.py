# -*- coding: utf-8 -*-

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import traceback
from collections import deque

try:
    import simplejson as json
except ImportError:
    import json

json_encode = lambda x: json.dumps(x)
json_decode = lambda x: json.loads(x)


# reads lines and reconstructs newlines appropriately
def readMsg():
    msg = ""
    while True:
        line = sys.stdin.readline()
        if not line:
            raise Exception('Read EOF from stdin')
        if line[0:-1] == "end":
            break
        msg = msg + line
    return json_decode(msg[0:-1])


MODE = None
ANCHOR_TUPLE = None

# queue up commands we read while trying to read taskids
pending_commands = deque()


def readTaskIds():
    if pending_taskids:
        return pending_taskids.popleft()
    else:
        msg = readMsg()
        while type(msg) is not list:
            pending_commands.append(msg)
            msg = readMsg()
        return msg


# queue up taskids we read while trying to read commands/tuples
pending_taskids = deque()


def readCommand():
    if pending_commands:
        return pending_commands.popleft()
    else:
        msg = readMsg()
        while type(msg) is list:
            pending_taskids.append(msg)
            msg = readMsg()
        return msg


def readTuple():
    cmd = readCommand()
    return Tuple(cmd["id"], cmd["comp"], cmd["stream"], cmd["task"], cmd["tuple"])


def sendMsgToParent(msg):
    print json_encode(msg)
    print "end"
    sys.stdout.flush()


def sync():
    sendMsgToParent({'command': 'sync'})


def sendpid(heartbeatdir):
    pid = os.getpid()
    sendMsgToParent({'pid': pid})
    open(heartbeatdir + "/" + str(pid), "w").close()


def emitBolt(tup, stream=None, anchors=[], directTask=None):
    global ANCHOR_TUPLE
    if ANCHOR_TUPLE is not None:
        anchors = [ANCHOR_TUPLE]
    m = {"command": "emit"}
    if stream is not None:
        m["stream"] = stream
    m["anchors"] = map(lambda a: a.id, anchors)
    if directTask is not None:
        m["task"] = directTask
    m["tuple"] = tup
    sendMsgToParent(m)


def ack(tup):
    sendMsgToParent({"command": "ack", "id": tup.id})


def fail(tup):
    sendMsgToParent({"command": "fail", "id": tup.id})


def reportError(msg):
    sendMsgToParent({"command": "error", "msg": msg})


def log(msg, level=2):
    sendMsgToParent({"command": "log", "msg": msg, "level": level})


def logTrace(msg):
    log(msg, 0)


def logDebug(msg):
    log(msg, 1)


def logInfo(msg):
    log(msg, 2)


def logWarn(msg):
    log(msg, 3)


def logError(msg):
    log(msg, 4)


def rpcMetrics(name, params):
    sendMsgToParent({"command": "metrics", "name": name, "params": params})


def initComponent():
    setupInfo = readMsg()
    sendpid(setupInfo['pidDir'])
    return [setupInfo['conf'], setupInfo['context']]


class Tuple(object):
    def __init__(self, id, component, stream, task, values):
        self.id = id
        self.component = component
        self.stream = stream
        self.task = task
        self.values = values

    def __repr__(self):
        return '<%s%s>' % (
            self.__class__.__name__,
            ''.join(' %s=%r' % (k, self.__dict__[k]) for k in sorted(self.__dict__.keys())))

    def is_heartbeat_tuple(self):
        return self.task == -1 and self.stream == "__heartbeat"


class Bolt(object):
    def initialize(self, stormconf, context):
        pass

    def process(self, tuple):
        pass

    def run(self):
        global MODE
        MODE = Bolt
        conf, context = initComponent()
        try:
            self.initialize(conf, context)
            while True:
                tup = readTuple()
                if tup.is_heartbeat_tuple():
                    sync()
                else:
                    try:
                        self.process(tup)
                    except Exception, e:
                        reportError(traceback.format_exc(e))
                        fail(tup)
        except BaseException, e:
            reportError(traceback.format_exc(e))
            raise e


class BasicBolt(object):
    def initialize(self, stormconf, context):
        pass

    def process(self, tuple):
        pass

    def run(self):
        global MODE
        MODE = Bolt
        global ANCHOR_TUPLE
        conf, context = initComponent()
        try:
            self.initialize(conf, context)
            while True:
                tup = readTuple()
                if tup.is_heartbeat_tuple():
                    sync()
                else:
                    ANCHOR_TUPLE = tup
                    try:
                        self.process(tup)
                        ack(tup)
                    except Exception, e:
                        error_formatted = "sessionId:[{}] ERROR: {}".format(extract_session_id(tup),
                                                                            traceback.format_exc(e))
                        reportError(error_formatted)
                        fail(tup)
        except BaseException, e:
            reportError(traceback.format_exc(e))
            raise e


class BenchmarkBolt(BasicBolt):
    def process(self, tuple):
        emitBolt(tuple.values, anchors=[tuple])

if __name__ == '__main__':
    bolt = BenchmarkBolt()
    bolt.run()

