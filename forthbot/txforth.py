import sys, re, string
from parsePythonValue import listItem
from pyparsing import OneOrMore, Word, pythonStyleComment

from twisted.protocols import basic
from twisted.internet import stdio, reactor


COLON = ':'
SCOLON = ';'
IF = 'if'
ELSE = 'else'
THEN = 'then'
BEGIN = 'begin'
UNTIL = 'until'

class Forth(basic.LineReceiver):

    punctuation = string.punctuation
    punctuation.replace('#', '')
    punctuation.replace('"', '')

    I = Word(string.letters + punctuation + string.digits) 
    D = listItem | I 
    S = OneOrMore(D).ignore(pythonStyleComment)

    delimiter = '\n' # unix terminal style newlines. remove this line

    def __init__(self):
        self.ds = []
        self.cStack   = []          # The control struct stack
        self.rStack   = []
        self.heap     = [0]*20      # The data heap
        self.heapNext =  0          # Next avail slot in heap
        self.words    = []          # The input stream of tokens

        self.ps = ["Forth> ", "...    "]


        self.cDict = {
            ':'    : self.cColon, ';'    : self.cSemi, 'if': self.cIf, 'else': self.cElse, 
            'then': self.cThen, 'begin': self.cBegin, 'until': self.cUntil,
        }

        self.rDict = {
        '+'  : self.rAdd, '-'   : self.rSub, '/' : self.rDiv, '*'    : self.rMul,   'over': self.rOver,
        'dup': self.rDup, 'swap': self.rSwap, '.': self.rDot, 'dump' : self.rDump,  'drop': self.rDrop,
        '='  : self.rEq,  '>'   : self.rGt,   '<': self.rLt,
        ','  : self.rComa,'@'   : self.rAt, '!'  : self.rBang,'allot': self.rAllot,

        'create': self.rCreate, 'does>': self.rDoes,
        }

    def rAdd (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(a+b)
    def rMul (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(a*b)
    def rSub (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(a-b)
    def rDiv (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(a/b)
    def rEq  (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(int(a==b))
    def rGt  (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(int(a>b))
    def rLt  (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(int(a<b))
    def rSwap(self, cod,p) : a=self.ds.pop(); b=self.ds.pop(); self.ds.append(a); self.ds.append(b)
    def rDup (self, cod,p) : self.ds.append(self.ds[-1])
    def rDrop(self, cod,p) : self.ds.pop()
    def rOver(self, cod,p) : self.ds.append(self.ds[-2])
    def rDump(self, cod,p) : self.sendLine("ds = "+ str(self.ds))
    def rDot (self, cod,p) : self.sendLine(str(self.ds.pop()))
    def rJmp (self, cod,p) : return cod[p]
    def rJnz (self, cod,p) : return (cod[p],p+1)[self.ds.pop()]
    def rJz  (self, cod,p) : return (p+1,cod[p])[self.ds.pop()==0]
    def rRun (self, cod,p) : self._runPcode(self.rDict[cod[p]]); return p+1
    def rPush(self, cod,p) : self.ds.append(cod[p])     ; return p+1

    def rCreate (self, pcode,p) :
        self.state = 'create'

    def state_create(self, label):
        self.lastCreate = label       # match next word (input) to next heap address
        self.rDict[label] = [self.rPush, self.heapNext]    # when created word is run, pushes its address
        while self.rStack:
            pcode, p = self.rStack.pop()
            print "resuming execution of %r at %d" % (pcode, p)
            self.p = p
            self._runPcode(pcode)
        return 'init'


    def rDoes (self, cod,p) :
        self.rDict[self.lastCreate] += cod[p:]        # rest of words belong to created words runtime
        return len(cod)                     # jump p over these

    def rAllot (self, cod,p) :
        self.heapNext += self.ds.pop()                # reserve n words for last create

    def rAt  (self, cod,p) : self.ds.append(self.heap[self.ds.pop()])       # get heap @ address
    def rBang(self, cod,p) : a=self.ds.pop(); self.heap[a] = self.ds.pop()  # set heap @ address
    def rComa(self, cod,p) :                                 # push tos into heap
        self.heap[self.heapNext]=self.ds.pop()
        self.heapNext += 1



    def fatal (self, mesg) : raise mesg

    def cColon (self, pcode) :
        return 'colon'

    def state_colon(self, label):
        if self.cStack : fatal(": inside Control stack: %s" % self.cStack)
        self.cStack.append(("COLON",label))  # flag for following ";"
        return 'compile'

    def cSemi (self, pcode) :
        if not self.cStack : fatal("No : for ; to match")
        code,label = self.cStack.pop()
        if code != "COLON" : fatal(": not balanced with ;")
        self.rDict[label] = pcode[:]       # Save word definition in rDict
        while pcode : pcode.pop()

    def cBegin (self, pcode) :
        self.cStack.append(("BEGIN",len(pcode)))  # flag for following UNTIL

    def cUntil (self, pcode) :
        if not self.cStack : fatal("No BEGIN for UNTIL to match")
        code,slot = self.cStack.pop()
        if code != "BEGIN" : fatal("UNTIL preceded by %s (not BEGIN)" % code)
        pcode.append(self.rJz)
        pcode.append(slot)

    def cIf (self, pcode) :
        pcode.append(self.rJz)
        self.cStack.append(("IF",len(pcode)))  # flag for following Then or Else
        pcode.append(0)                   # slot to be filled in

    def cElse (self, pcode) :
        if not self.cStack : fatal("No IF for ELSE to match")
        code,slot = self.cStack.pop()
        if code != "IF" : fatal("ELSE preceded by %s (not IF)" % code)
        pcode.append(self.rJmp)
        self.cStack.append(("ELSE",len(pcode)))  # flag for following THEN
        pcode.append(0)                     # slot to be filled in
        pcode[slot] = len(pcode)            # close JZ for IF

    def cThen (self, pcode) :
        if not self.cStack : fatal("No IF or ELSE for THEN to match")
        code,slot = self.cStack.pop()
        if code not in ("IF","ELSE") : fatal("THEN preceded by %s (not IF or ELSE)" % code)
        pcode[slot] = len(pcode)             # close JZ for IF or JMP for ELSE


   

    state = 'init'


    def connectionMade(self):
        self.sendLine(self.ps[0])

    def lineReceived(self, line):
        """
        """
        line = line.strip()
        if not line:
            return
        if line[0:1] == '#':
            return
        if line[0:1] == "@" : 
            lines = open(line[1:]).read()
            for line in lines.split('\n'):
                self.lineReceived(line)
        else:
            print "got line", line
            self.words = self.words + self.S.parseString(line).asList()
            while self.words:
                word = self.words.pop(0)
                self.wordReceived(word)
        if self.state == 'init':
            self.sendLine(self.ps[0])
        else:
            self.sendLine(self.ps[1])


    def wordReceived(self, word):
        print "doing word", word
        try:
            pto = 'state_'+self.state
            statehandler = getattr(self,pto)
        except AttributeError:
            log.msg('callback',self.state,'not found')
        else:
            self.state = statehandler(word)
            if self.state == 'done':
                print "DONE", self.pcode 
                


    def tokenizeWords(self, s) :
        global words 
        # clip comments, split to list of words
        self.words = self.S.parseString(s).asList()


    def state_init(self, word):
        self.pcode = []; self.prompt = self.ps[0]
        return self.state_compile(word)


    def state_compile(self, word):
        cAct = self.cDict.get(word, None)
        rAct = self.rDict.get(word, None)
        if cAct:
            z = self.do_cAct(cAct, word)
            if z is not None:
                return z

        elif rAct:
            self.do_rAct(rAct, word)

        else:
            self.pcode.append(self.rPush)
            res = self.fix_type(word)
            if res is None:
                self.pcode[-1] = self.rRun # change push to run
                self.pcode.append(word) # assume the word will be defined
            else:
                self.pcode.append(res)
        if self.cStack == []:
            self.p = 0
            v = self._runPcode(self.pcode)
            #self.p = 0
            #return self.pcodeReceived(self.pcode)
            return v
        return 'compile'


    def do_rAct(self, rAct, word):
        if type(rAct) == type([]) :
            self.pcode.append(self.rRun)# Compiled word.
            self.pcode.append(word)     # for now do dynamic lookup
        else : self.pcode.append(rAct)  # push builtin for runtime


    def do_cAct(self, cAct, word):
        return cAct(self.pcode)

    def _runPcode(self, pcode):
        gen = self.g_pcodeReceived(pcode).next
        ret = gen()
        return ret

    pstate = 'start'

    def pcodeReceived(self, pcode):
        try:
            pto = 'pstate_'+self.pstate
            statehandler = getattr(self,pto)
        except AttributeError:
            try:
                pto = 'state_'+self.state
                statehandler = getattr(self, pto)
            except AttributeError:
                log.msg('callback',self.pstate,'not found')
        else:
            self.pstate = statehandler(pcode)
            if self.pstate == 'done':
                print "pcodeReceived DONE"

    def pstate_start(self, pcode):
        self.p = 0
        return self.pstate_run(pcode)


    def pstate_run(self, pcode):
        while self.p < len(pcode):
            self.p = self.p_exec(pcode, self.p)
            if self.state == 'create':
                return 'create'
        return 'init'


 
    def g_pcodeReceived(self, pcode):
        while self.p < len(pcode):
            self.p = self.p_exec(pcode, self.p)
            if self.state == 'create':
                self.rStack.append((pcode, self.p))
                yield 'create'
        yield 'init'


    def p_exec(self, pcode, p):
        func = pcode[p]
        p +=1 
        newP = func(pcode, p)
        if newP != None: p = newP
        return p


    def execute (self, code) :
        p = 0
        while p < len(code) :
            func = code[p]
            p += 1
            newP = func(code,p)
            if newP != None : p = newP
            if self.state == 'create':
                return self.state
        return 'init'


    def _intlike(self, a):
        try:
            int(a)
            return True
        except:
            return False

    def _floatlike(self, a):
        if self._intlike(a):
            return False
        try:
            float(a)
            return True
        except:
            return False

    def fix_type(self, word):
        # Number to be pushed onto ds at runtime
        if self._intlike(word):
            return int(word)
        if self._floatlike(word):
            return float(word)
        if isinstance(word, list) or isinstance(word, dict):
            return word
        if word[0] in ["'", '"']:
            return word
        return None




if __name__ == "__main__":
    stdio.StandardIO(Forth())
    reactor.run()
