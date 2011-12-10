from twisted.trial.unittest import TestCase, SkipTest

from forthbot.forth import compile, execute, tokenizeWords
from forthbot import txforth as forth
from subprocess import Popen, PIPE
from twisted.python import procutils
from twisted.python.filepath import FilePath



def _runforth(s):
    forthproc = forth.__file__
    p = procutils.which('python')[0]
    p2 = Popen([p, forthproc], stdin=PIPE, stdout=PIPE)
    output = p2.communicate(input=s)[0]
    return output


class ImprovedForth(TestCase):
    def setUp(self):
        pass

    def test_append_strings(self):
        i = '"abc" "def" + .'
        c = 'abcdef'
        o = _runforth(i)
        self.assertTrue(c in o, "%s did not contain %s" % (o, c))

    def test_append_lists(self):
        i = '[1, 2, 3] [4, 5, 6] + .'
        o = _runforth(i)
        e = '[1, 2, 3, 4, 5, 6]'
        self.assertTrue(e in o, "%s did not contain %s" % (o, e))

class TestPcode(TestCase):
    def setUp(self):
        self.f = forth.Forth()

    def test_pcode(self):
        def fake(pcode):
            for p in pcode:
                self.f.pcodeReceived([p])



        self.f._runPcode = fake
        self.f.lineReceived('5 5 + .')


class TestForth(TestCase):
    def setUp(self):
        forth.words = []

    def tearDown(self):
        forth.words = []

    def test_tokenizeWords(self):
        tokenizeWords('a b c d e 1 2 34')
        self.assertEquals(forth.words, ['a', 'b', 'c', 'd', 'e', 1, 2, 34])

    def test_tokenizeWords_comments(self):
        tokenizeWords('a b c d e 1 2 # 34')
        self.assertEquals(forth.words, ['a', 'b', 'c', 'd', 'e', 1, 2])

    def test_tokenizeWords_strings(self):
        tokenizeWords('"nate test" "this" \'out\' 1 2')
        self.assertEquals(forth.words, ['"nate test"', '"this"', "'out'", 1, 2])


class TestDoc(TestCase):
    """
    A few test cases from http://openbookproject.net/py4fun/forth/forth.html
    """
    def fakeSendLine(self, s):
        self.sentLines.append(s)

    def setUp(self):
        self.f = forth.Forth()
        self.f.sendLine = self.fakeSendLine
        self.sentLines = []

    def tearDown(self):
        pass


    def _runforth(self, s):
        for line in s.split('\n'):
            self.f.lineReceived(line)

    def test_add_mult(self):
        p = '5 6 + 7 8 + * .'
        self._runforth(p)
        self.assertEquals(self.sentLines[-2], '165')

    def test_create(self):
        p = 'create v1 1 allot v1 .'
        self._runforth(p)
        print self.sentLines
        self.assertEquals(self.sentLines[-2], '0')

    def test_two_vars(self):
        p = '''\
# fact3.4th

: variable create 1 allot ;            #   ---     create var and init to TOS
  variable m
  variable answer

: fact                                 #  n --- n!  replace TOS with factorial
     m !                               # set m to TOS
  1 answer !                           # set answer = 1
;

15 fact .
'''
        self._runforth(p)
        self.assertEquals(self.f.ds, [])


    def test_dump(self):
        p = '5 dump 6 dump + dump 7 dump 8 dump + dump * dump'
        self._runforth(p)
        self.assertEquals(self.sentLines, ['ds = [5]', 'ds = [5, 6]', 'ds = [11]', 'ds = [11, 7]', 'ds = [11, 7, 8]', 'ds = [11, 15]', 'ds = [165]', 'Forth> '])

    def test_square_dup(self):
        p = '25 dup * .'
        self._runforth(p)
        self.assertEquals(self.sentLines[-2], '625')

    def test_swap_minus(self):
        p = '42 0 swap - .'
        self._runforth(p)
        self.assertEquals(self.sentLines[-2], '-42')

    def test_comment(self):
        p = "5 6 + .  # this is a comment"
        self._runforth(p)
        self.assertEquals(self.sentLines[-2], '11')

    def test_newword(self):
        p = ': negate 0 swap - ; 5 negate .'
        self._runforth(p)
        self.assertEquals(self.sentLines[-2], '-5')

    def test_begin_until(self):
        p = '5 begin dup . 1 - dup 0 = until'
        self._runforth(p)
        self.assertEquals(self.sentLines,  ['5', '4', '3', '2', '1', 'Forth> '])

    def test_load_factorial(self):
        p = "@%s\n 5 fact ." % FilePath(__file__).sibling('fact1.4th').path
        self._runforth(p)
        print self.sentLines
        self.assertEquals(self.sentLines[-2], '120')

    def test_load_factorial2(self):
        p = "@%s\n 5 fact ." % FilePath(__file__).sibling('fact2.4th').path
        self._runforth(p)
        print self.sentLines
        self.assertEquals(self.sentLines[-2], '120')


        g = '''\
Forth> ds =  [5, 4, 3, 2, 1]
ds =  [5, 4, 3, 2]
ds =  [5, 4, 6]
ds =  [5, 24]
120'''
        self._cmpforth(p, self.expect_this(g))

    def test_load_factorial3(self):
        p = "@%s" % FilePath(__file__).sibling('fact3.4th').path
        self._runforth(p)
        print self.sentLines
        self.assertEquals(self.sentLines[-2], '1307674368000')


        g = '''\
ds =  [1, 15]
ds =  [15, 14]
ds =  [210, 13]
ds =  [2730, 12]
ds =  [32760, 11]
ds =  [360360, 10]
ds =  [3603600, 9]
ds =  [32432400, 8]
ds =  [259459200, 7]
ds =  [1816214400, 6]
ds =  [10897286400L, 5]
ds =  [54486432000L, 4]
ds =  [217945728000L, 3]
ds =  [653837184000L, 2]
ds =  [1307674368000L, 1]
1307674368000'''
        self._cmpforth(p, self.expect_this(g))



    def test_does(self):
        p = ': constant create , does> @ ;\n2009 constant thisYear\nthisYear .'
        self._runforth(p)
        self.assertEquals(self.sentLines[-2], '2009')





