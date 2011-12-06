import sys, re, string
from parsePythonValue import listItem
from pyparsing import OneOrMore, Word, pythonStyleComment
from ircLogBot import LogBot


class Forth:
    ds = []
    cStack   = []          # The control struct stack
    heap     = [0]*20      # The data heap
    heapNext =  0          # Next avail slot in heap
    words    = []          # The input stream of tokens

    punctuation = string.punctuation
    punctuation.replace('#', '')
    punctuation.replace('"', '')

    I = Word(string.letters + punctuation + string.digits) 
    D = listItem | I 
    S = OneOrMore(D).ignore(pythonStyleComment)

    def __init__(self):
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
    def rDup (self, cod,p) : self.ds.append(ds[-1])
    def rDrop(self, cod,p) : self.ds.pop()
    def rOver(self, cod,p) : self.ds.append(ds[-2])
    def rDump(self, cod,p) : self.sendLine("ds = "+ str(self.ds))
    def rDot (self, cod,p) : self.sendLine(self.ds.pop())
    def rJmp (self, cod,p) : return cod[p]
    def rJnz (self, cod,p) : return (cod[p],p+1)[self.ds.pop()]
    def rJz  (self, cod,p) : return (p+1,cod[p])[self.ds.pop()==0]
    def rRun (self, cod,p) : self.execute(self.rDict[cod[p]]); return p+1
    def rPush(self, cod,p) : self.ds.append(cod[p])     ; return p+1

    def rCreate (self, pcode,p) :
        self.lastCreate = label = self.getWord()      # match next word (input) to next heap address
        self.rDict[label] = [self.rPush, self.heapNext]    # when created word is run, pushes its address

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
        if self.cStack : fatal(": inside Control stack: %s" % self.cStack)
        label = self.getWord()
        cStack.append(("COLON",label))  # flag for following ";"

    def cSemi (self, pcode) :
        if not cStack : fatal("No : for ; to match")
        code,label = cStack.pop()
        if code != "COLON" : fatal(": not balanced with ;")
        rDict[label] = pcode[:]       # Save word definition in rDict
        while pcode : pcode.pop()

    def cBegin (self, pcode) :
        cStack.append(("BEGIN",len(pcode)))  # flag for following UNTIL

    def cUntil (self, pcode) :
        if not cStack : fatal("No BEGIN for UNTIL to match")
        code,slot = cStack.pop()
        if code != "BEGIN" : fatal("UNTIL preceded by %s (not BEGIN)" % code)
        pcode.append(rJz)
        pcode.append(slot)

    def cIf (self, pcode) :
        pcode.append(rJz)
        cStack.append(("IF",len(pcode)))  # flag for following Then or Else
        pcode.append(0)                   # slot to be filled in

    def cElse (self, pcode) :
        if not cStack : fatal("No IF for ELSE to match")
        code,slot = cStack.pop()
        if code != "IF" : fatal("ELSE preceded by %s (not IF)" % code)
        pcode.append(rJmp)
        cStack.append(("ELSE",len(pcode)))  # flag for following THEN
        pcode.append(0)                     # slot to be filled in
        pcode[slot] = len(pcode)            # close JZ for IF

    def cThen (self, pcode) :
        if not cStack : fatal("No IF or ELSE for THEN to match")
        code,slot = cStack.pop()
        if code not in ("IF","ELSE") : fatal("THEN preceded by %s (not IF or ELSE)" % code)
        pcode[slot] = len(pcode)             # close JZ for IF or JMP for ELSE


   

    state = 'init'

    def lineReceived(self, string):
        """
        """
        try:
            pto = 'state_'+self.state
            statehandler = getattr(self,pto)
        except AttributeError:
            log.msg('callback',self.state,'not found')
        else:
            self.state = statehandler(string)
            if self.state == 'done':
                pass


    def tokenizeWords(self, s) :
        global words 
        # clip comments, split to list of words
        self.words = self.S.parseString(s).asList()


    def getWord (self, prompt="... ") :
        try:
            word = self.words[0]
            self.words = self.words[1:]
            return word
        except:
            return None


    def state_init(self, line):
        self.pcode = []; self.prompt = "Forth> "
        self.sendLine(self.prompt)
        if line[0:1] == "@" : line = open(line[1:-1]).read()
        self.tokenizeWords(line)
        while 1:
            pcode = self.compile(line)
            if pcode == None:
                return 'init'
            self.execute(pcode)


    def execute (self, code) :
        p = 0
        while p < len(code) :
            func = code[p]
            p += 1
            newP = func(code,p)
            if newP != None : p = newP


    def compile(self, line):
        while 1:
            word = self.getWord(self.prompt)  # get next word
            print "doing word", word
            if word == None : return None
            cAct = None
            rAct = None
            if type(word) not in [type(['list'])]:
                cAct = self.cDict.get(word)  # Is there a compile time action ?
                rAct = self.rDict.get(word)  # Is there a runtime action ?

            if cAct : cAct(self.pcode)   # run at compile time
            elif rAct :
                if type(rAct) == type([]) :
                    self.pcode.append(rRun)     # Compiled word.
                    self.pcode.append(word)     # for now do dynamic lookup
                else : self.pcode.append(rAct)  # push builtin for runtime
            else :
                # Number to be pushed onto ds at runtime
                self.pcode.append(self.rPush)
                try : self.pcode.append(int(word))
                except :
                    try: self.pcode.append(float(word))
                    except : 
                        if type(word) == type(['list']):
                            self.pcode.append(word)
                        if type(word) == type("string"):
                            c = word[0]
                            if c == '"' or c == "'":
                                self.pcode.append(word[1:-1])
                            else:
                                self.pcode[-1] = self.rRun     # Change rPush to rRun
                                self.pcode.append(word)   # Assume word will be defined
            if not self.cStack :
                return self.pcode
            self.prompt = "...    "
            self.sendLine(self.prompt)


class ForthBot(LogBot):
    """A logging IRC bot."""
    
    nickname = "joanie"
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" % 
                        time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.logger.close()


    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))
        
        # Check to see if they're sending me a private message
        if channel == self.nickname:
            msg = "It isn't nice to whisper!  Play nice with the group."
            self.msg(user, msg)
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            msg = "%s: I am a log bot" % user
            self.msg(channel, msg)
            self.logger.log("<%s> %s" % (self.nickname, msg))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'



