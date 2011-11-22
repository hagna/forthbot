# fact2.4th  Recursive factorial       # n --- n!

: fact  dup 1 > if                     # if 1 (or 0) just leave on stack
            dup 1 - fact               # next number down - get its factorial
    dump    * then                     # and mult - leavin ans on stack
  ;
