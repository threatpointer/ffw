from subprocess import Popen, PIPE, STDOUT
import logging

import serverutils
import verifycrashdata
import re


class StdoutQueue():
    """
    This is a Queue that behaves like stdout.

    Used to capture stdout events of the server/child.
    """

    def __init__(self, *args, **kwargs):
        self.q = args[0]

    def write(self, msg):
        self.q.put(msg)

    def flush(self):
        pass


class GdbServerManager(object):
    """The actual debug-server manager."""

    # copy from debugservermanager
    def __init__(self, config, queue_sync, queue_stdout, targetPort):
        self.config = config
        self.queue_sync = queue_sync
        self.queue_stdout = queue_stdout
        self.targetPort = targetPort

        self.pid = None
        self.dbg = None
        self.crashEvent = None
        self.proc = None

        self.stdoutQueue = StdoutQueue(queue_stdout)
        serverutils.setupEnvironment(config)

    # copy from debugservermanager
    def startAndWait(self):
        self.queue_stdout.put("Dummy")
        # do not remove print, parent excepts something
        logging.info("DebugServer: Start Server")
        #sys.stderr.write("Stderr")

        logging.info("Server PID: " + str(self.pid))

        # notify parent about the pid
        self.queue_sync.put( ("pid", self.pid) )

        crashData = self._waitForCrash()

        # _getCrashDetails could return None
        if crashData is not None:
            #logging.debug("DebugServer: send to queue_sync")
            self.queue_sync.put( ("data", crashData) )


    def _waitForCrash(self):
        logging.info("Wait for crash")

        # start gdb
        argsGdb = [ "/usr/bin/gdb", self.config["target_bin"], '-q' ]

        print "Start server: " + str(argsGdb)
        p = Popen(argsGdb, stdout=PIPE, stdin=PIPE, stderr=PIPE)

        data1 = "r " + self.config["target_args"] % ( { "port": self.targetPort } )
        data1 += "\nbt\n"
        ret = p.communicate(input=data1)[0]

        logging.info("get crash details, res: " + str(len(ret)))
        p = re.compile('#.*\(gdb\)', re.S)
        backtrace = re.search(p, ret, flags=0).group()
        self.queue_stdout.put(backtrace)
        backtraceFrames = backtrace.split('\n')
        i = 0
        res = []
        while(i < len(backtraceFrames)):
            if backtraceFrames[i].startswith("#"):
                res.append(backtraceFrames[i].rstrip("\n\r"))
            i += 1

        crashData = verifycrashdata.VerifyCrashData()
        crashData.setData(
            backtrace=res,
            output=ret,
            cause="GDBSERVERMANAGER: n/a"
        )
        gdbOutput = serverutils.getAsanOutput(self.config, self.pid)
        if gdbOutput is not None:
            crashData.setAsan(gdbOutput)

        return crashData
