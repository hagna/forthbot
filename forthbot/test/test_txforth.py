from twisted.trial.unittest import TestCase, SkipTest

from forthbot.txforth import Forth
from forthbot import forth
from twisted.python import procutils
from twisted.python.filepath import FilePath


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


class TestForth(TestCase):
    def setUp(self):
        self.f = Forth()

    def tearDown(self):
        pass

    def test_tokenizeWords(self):
        self.f.tokenizeWords('a b c d e 1 2 34')
        self.assertEquals(self.f.words, ['a', 'b', 'c', 'd', 'e', 1, 2, 34])

    def test_tokenizeWords_comments(self):
        self.f.tokenizeWords('a b c d e 1 2 # 34')
        self.assertEquals(self.f.words, ['a', 'b', 'c', 'd', 'e', 1, 2])

    def test_tokenizeWords_strings(self):
        self.f.tokenizeWords('"nate test" "this" \'out\' 1 2')
        self.assertEquals(self.f.words, ['"nate test"', '"this"', "'out'", 1, 2])


class TestDoc(TestCase):
    """
    A few test cases from http://openbookproject.net/py4fun/forth/forth.html
    """
    def fakeSendLine(self, s):
        self.sentLines.append(s)

    def setUp(self):
        self.sentLines = []
        self.f = Forth()
        self.f.sendLine = self.fakeSendLine

    def tearDown(self):
        pass

    def _runforth(self, s):
        for line in s.split('\n'):
            self.f.lineReceived(line)

    def _cmpforth(self, p, output):
        z = self._runforth(p)
        s = output.split('\n')
        for i, line in enumerate(z.split('\n')):
            self.assertEquals(s[i].strip(), line.strip(), "error on line %d of output" % i)

    def expect_this(self, s):
        self.assertEquals(self.sentLines[0], s)

    def test_add_mult(self):
        p = '5 6 + 7 8 + * .'
        self._runforth(p)
        g = self.expect_this(165)
        self._cmpforth(p, g)

    def test_dump(self):
        p = '5 dump 6 dump + dump 7 dump 8 dump + dump * dump'
        g = self.expect_this('''\
ds =  [5]
ds =  [5, 6]
ds =  [11]
ds =  [11, 7]
ds =  [11, 7, 8]
ds =  [11, 15]
ds =  [165]''')
        self._cmpforth(p, g)

    def test_square_dup(self):
        p = '25 dup * .'
        g = self.expect_this(625)
        self._cmpforth(p, g)

    def test_swap_minus(self):
        p = '42 0 swap - .'
        g = self.expect_this(-42)
        self._cmpforth(p, g)

    def test_comment(self):
        p = "5 6 + .  # this is a comment"
        g = self.expect_this(11)
        self._cmpforth(p, g)

    def test_newword(self):
        p = ': negate 0 swap - ; 5 negate .'
        g = '''\
Forth> -5
Forth> 
'''
        self._cmpforth(p, g)


    def test_begin_until(self):
        p = '5 begin dup . 1 - dup 0 = until'
        g = '''\
Forth> 5
4
3
2
1
Forth> 
'''
        self._cmpforth(p, g) 


    def test_load_factorial(self):
        p = "@%s\n 5 fact ." % FilePath(__file__).sibling('fact1.4th').path
        g = '''\
Forth> ds =  [0, 5, 4, 3, 2, 1]
ds =  [0, 5, 4, 3, 2]
ds =  [0, 5, 4, 6]
ds =  [0, 5, 24]
120'''
        self._cmpforth(p, self.expect_this(g))

    def test_load_factorial2(self):
        p = "@%s\n 5 fact ." % FilePath(__file__).sibling('fact2.4th').path
        g = '''\
Forth> ds =  [5, 4, 3, 2, 1]
ds =  [5, 4, 3, 2]
ds =  [5, 4, 6]
ds =  [5, 24]
120'''
        self._cmpforth(p, self.expect_this(g))

    def test_load_factorial3(self):
        p = "@%s" % FilePath(__file__).sibling('fact3.4th').path
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
        g = "Forth> " * 2 + self.expect_this(2009)
        self._cmpforth(p, g)

