import sys, re, string
from parsePythonValue import listItem
from pyparsing import OneOrMore, Word, pythonStyleComment

from twisted.protocols import basic
from twisted.internet import stdio, reactor
from twisted.python.filepath import FilePath
import os


class ForthWord(str):
    pass

class Forth(basic.LineReceiver):

    punctuation = string.punctuation
    punctuation.replace('#', '')
    punctuation.replace('"', '')

    I = Word(string.letters + punctuation + string.digits)
    I.setParseAction(lambda s,l,t: [ForthWord(t[0])])
    D = listItem | I
    S = OneOrMore(D).ignore(pythonStyleComment)

    def isForthWord(self, w):
        return w[0] == IDENT

    def isPyVal(self, w):
        return w[0] == PYVAL

    def tokenizeWords(self, s) :
        # clip comments, split to list of words
        res = self.S.parseString(s).asList()
        return res

    delimiter = '\n' # unix terminal style newlines. remove this line

    saveFile = FilePath(os.environ['HOME']).child('.forthbot.sav')

    def __init__(self, saveFile=None):
        if saveFile is not None:
            self.saveFile = saveFile 
        self.ds = []
        self.cStack   = []          # The control struct stack
        self.rStack   = []
        self.heap     = [0]*20      # The data heap
        self.heapNext =  0          # Next avail slot in heap

        self.ps = ["Forth> ", "...    "]
        self.p = 0


        self.cDict = {
            ':'    : self.cColon, ';'    : self.cSemi, 'if': self.cIf, 'else': self.cElse, 
            'then': self.cThen, 'begin': self.cBegin, 'until': self.cUntil,
        }

        self.rDict = {
        '+'  : self.rAdd, '-'   : self.rSub, '/' : self.rDiv, '*'    : self.rMul,   'over': self.rOver,
        'dup': self.rDup, 'swap': self.rSwap, '.': self.rDot, 'dump' : self.rDump,  'drop': self.rDrop,
        '='  : self.rEq,  '>'   : self.rGt,   '<': self.rLt,  's' : self.rSend, 'load': self.rLoad,
        'save': self.rSave, 'input': self.rInput,
        ','  : self.rComa,'@'   : self.rAt, '!'  : self.rBang,'allot': self.rAllot,

        'create': self.rCreate, 'does>': self.rDoes,
        }

    def saveState(self):
        import pickle
        fh = self.saveFile.open(mode='w')
        pickle.dump(self, fh, pickle.HIGHEST_PROTOCOL)
        fh.close()

    def loadState(self):
        import pickle
        import pprint
        fh = self.saveFile.open()
        n = pickle.load(fh)
        fh.close()
        n.sendLine = self.sendLine
        self.__dict__.update(n.__dict__)
  

    def __getstate__(self):
        v = self.__dict__.copy()
        v.pop('sendLine')
        return v


    def rSave(self, cod,p) : self.saveState()
    def rLoad(self, cod,p) : self.loadState()

    def rAdd (self, cod,p) : b=self.ds.pop(); a=self.ds.pop(); self.ds.append(a+b)
    def rSend(self, cod,p) : self.sendLine(self.ds.pop())
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
    def rRun (self, cod,p) :
        try:
            w = cod[p]
            self._runPcode(self.rDict[w]); return p+1
        except KeyError, e:
            self.fatal('Unknown command "%s"' % w)
        
    def rPush(self, cod,p) : 
        a = cod[p]
        self.ds.append(a)
        return p+1

    def rCreate (self, pcode,p) :
        self.state = 'create'

    def state_create(self, label):
        self.lastCreate = label       # match next word (input) to next heap address
        self.rDict[label] = [self.rPush, self.heapNext]    # when created word is run, pushes its address
        while self.rStack:
            pcode, p = self.rStack.pop()
            #self.p = p
            self._runPcode(pcode, p)
        return 'init'


    def rInput(self, cod, p) : 
        self.state = 'input'

    def state_input(self, w):
        self.ds.append(w)
        while self.rStack:
            pcode, p = self.rStack.pop()
            #self.p = p
            self._runPcode(pcode, p)
 
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



    def fatal (self, mesg) : raise Exception(mesg)

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
            words = self.tokenizeWords(line)
            while words:
                word = words.pop(0)
                self.wordReceived(word)
        if self.state == 'init':
            self.p = 0
        else:
            self.p = 1
        self.prompt()


    def prompt(self):
        if self.p == 0:
            return
        self.sendLine(self.ps[self.p])


    def wordReceived(self, word):
        try:
            pto = 'state_'+self.state
            statehandler = getattr(self,pto)
        except AttributeError:
            log.msg('callback',self.state,'not found')
        else:
            self.state = statehandler(word)
            if self.state == 'done':
                print "DONE", self.pcode 
                


    def state_init(self, word):
        self.pcode = []; 
        return self.state_compile(word)


    def _get_cAct(self, word):
        cAct = None
        try:
            cAct = self.cDict.get(word)
        except Exception, e:
            print e
        return cAct
 
    def _get_rAct(self, word):
        rAct = None
        try:
            rAct = self.rDict.get(word, None)
            if rAct is None:
                l = len(self.ds)
                if l > 1:
                    python_type = self.ds[-2]
                    args = self.ds[-1]
                    if word in dir(python_type):
                        print "found python type method"
                        def do_object_method(cod, p):
                            args = self.ds.pop()
                            python_type = self.ds.pop()
                            m = getattr(python_type, word)
                            res = m(*args)
                            if res == None:
                                self.ds.append(python_type)
                            else:
                                self.ds.append(res)
                        rAct = do_object_method
        except Exception, e:
            print e
        return rAct
 

    def state_compile(self, word):
        if isinstance(word, ForthWord):
            cAct = self._get_cAct(word)
            rAct = self._get_rAct(word)
            if cAct:
                z = self.do_cAct(cAct, word)
                if z is not None:
                    return z

            elif rAct:
                self.do_rAct(rAct, word)

            else:
                self.pcode.append(self.rRun) # change push to run
                self.pcode.append(word) # assume the word will be defined

        else:
            self.pcode.append(self.rPush)
            self.pcode.append(word)

        if self.cStack == []:
            return self._runPcode(self.pcode)
        return 'compile'


    def do_rAct(self, rAct, word):
        if type(rAct) == type([]) :
            self.pcode.append(self.rRun)# Compiled word.
            self.pcode.append(word)     # for now do dynamic lookup
        else : self.pcode.append(rAct)  # push builtin for runtime


    def do_cAct(self, cAct, word):
        return cAct(self.pcode)

    def _runPcode(self, pcode, p=0):
        while p < len(pcode):
            p = self.p_exec(pcode, p)
            if self.state == 'create':
                self.rStack.append((pcode, p))
                return 'create'
            if self.state == 'input':
                self.rStack.append((pcode, p))
                return 'input'
        return 'init'


    def p_exec(self, pcode, p):
        func = pcode[p]
        p +=1 
        newP = func(pcode, p)
        if newP != None: p = newP
        return p


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
