from twisted.trial.unittest import TestCase, SkipTest

from forthbot.forth import compile, execute
from forthbot import txforth as forth
from subprocess import Popen, PIPE
from twisted.python import procutils
from twisted.python.filepath import FilePath




class ForthRunner(TestCase):
    def fakeSendLine(self, s):
        self.sentLines.append(s)

    def setUp(self):
        self.f = forth.Forth()
        self.f.sendLine = self.fakeSendLine
        self.sentLines = []

    def _runforth(self, s):
        for line in s.split('\n'):
            self.f.lineReceived(line)


class ImprovedForth(ForthRunner):

    def test_dir(self):
        i = "'a' dir"
        self._runforth(i)
        self.assertTrue(isinstance(self.f.ds[0], list))
        for a in ['find', 'index', 'isalpha']:
            self.assertTrue(a in self.f.ds[0])

    def test_split(self):
        i = '"a b c d e" [] split'
        self._runforth(i)
        self.assertEquals(self.f.ds, [['a', 'b', 'c', 'd', 'e']])

    def test_input(self):
        i = ": test_input input 100 + ;"
        self._runforth(i)
        self.f.lineReceived('test_input')
        self.assertTrue('...    ' in self.sentLines)
        self.f.lineReceived('99')
        self.assertEquals(self.f.ds, [199])

    def test_append_strings(self):
        i = '"abc" "def" + .'
        c = 'abcdef'
        self._runforth(i)
        o = self.sentLines
        self.assertTrue(c in self.sentLines, "%s did not contain %s" % (o, c))

    def test_append_lists(self):
        i = '[1, 2, 3] [4, 5, 6] + .'
    	c = '[1, 2, 3, 4, 5, 6]'
        self._runforth(i)
        o = self.sentLines
        self.assertTrue(c in self.sentLines, "%s did not contain %s" % (o, c))


    def test_persist(self):
        fp = FilePath(self.mktemp())
        f = forth.Forth(saveFile=fp)
        f.sendLine = self.f.sendLine
        f.lineReceived(": question 99 1 + . ;")
        f.lineReceived("question")
        f.saveState()
        self.f.saveFile = fp
        self.f.loadState()
        self.f.sendLine('foobar')
        self._runforth("question")
        self.assertTrue("100" in self.sentLines)

    def test_get_state(self):
        """
        get_state returns everything but sendLine
        """
        v = self.f.__getstate__()
        self.assertTrue('sendLine' not in v)


class TestForth(TestCase):
    def setUp(self):
        self.f = forth.Forth()

    def test_tokenizeWords(self):
        res = self.f.tokenizeWords('a b c d e 1 2 34')
        self.assertEquals(res, ['a', 'b', 'c', 'd', 'e', 1, 2, 34])

    def test_tokenizeWords_comments(self):
        res = self.f.tokenizeWords('a b c d e 1 2 # 34')
        self.assertEquals(res, ['a', 'b', 'c', 'd', 'e', 1, 2])

    def test_toklists(self):
        res = self.f.tokenizeWords('["a", "b"] 1 2 3 c d e')
        self.assertEquals(res, [['a', 'b'], 1, 2, 3, 'c', 'd', 'e'])

    def test_tokdict(self):
        res = self.f.tokenizeWords("{'foo':2} 1 2 3 c d e")
        self.assertEquals(res, [{'foo':2}, 1, 2, 3, 'c', 'd', 'e'])

    def test_tokstrings(self):
        res = self.f.tokenizeWords("'abc' 'def' 1 2 3")
        self.assertEquals(res, ['abc', 'def', 1, 2, 3])



    def test_tokenizeWords_strings(self):
        res = self.f.tokenizeWords('"nate test" "this" \'out\' 1 2')
        self.assertEquals(res, ['nate test', 'this', "out", 1, 2])


class TestDoc(ForthRunner):
    """
    A few test cases from http://openbookproject.net/py4fun/forth/forth.html
    """

    def test_add_mult(self):
        p = '5 6 + 7 8 + * .'
        self._runforth(p)
        self.assertTrue('165' in self.sentLines)

    def test_create(self):
        p = 'create v1 1 allot v1 .'
        self._runforth(p)
        self.assertTrue('0' in self.sentLines)

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

15 fact 
'''
        self._runforth(p)
        self.assertEquals(self.f.ds, [])


    def test_dump(self):
        p = '5 dump 6 dump + dump 7 dump 8 dump + dump * dump'
        self._runforth(p)
        self.assertEquals(self.sentLines, ['ds = [5]', 'ds = [5, 6]', 'ds = [11]', 'ds = [11, 7]', 'ds = [11, 7, 8]', 'ds = [11, 15]', 'ds = [165]' ])

    def test_square_dup(self):
        p = '25 dup * .'
        self._runforth(p)
        self.assertTrue('625' in self.sentLines)

    def test_swap_minus(self):
        p = '42 0 swap - .'
        self._runforth(p)
        self.assertTrue('-42' in self.sentLines)

    def test_comment(self):
        p = "5 6 + .  # this is a comment"
        self._runforth(p)
        self.assertTrue('11' in self.sentLines)

    def test_newword(self):
        p = ': negate 0 swap - ; 5 negate .'
        self._runforth(p)
        self.assertTrue('-5' in self.sentLines)

    def test_begin_until(self):
        p = '5 begin dup . 1 - dup 0 = until'
        self._runforth(p)
        self.assertTrue(self.sentLines,  ['5', '4', '3', '2', '1', 'Forth> '])

    def test_load_factorial(self):
        p = "@%s\n 5 fact ." % FilePath(__file__).sibling('fact1.4th').path
        self._runforth(p)
        self.assertTrue('120' in self.sentLines)

    def test_load_factorial2(self):
        p = "@%s\n 5 fact ." % FilePath(__file__).sibling('fact2.4th').path
        self._runforth(p)
        self.assertTrue('120' in self.sentLines)


    def test_load_factorial3(self):
        p = "@%s" % FilePath(__file__).sibling('fact3.4th').path
        self._runforth(p)
        self.assertTrue('1307674368000' in self.sentLines)


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



    def test_does(self):
        p = ': constant create , does> @ ;\n2009 constant thisYear\nthisYear .'
        self._runforth(p)
        self.assertTrue('2009' in self.sentLines)





