# fact1.4th

: fact                             #  n --- n!  replace TOS with its factorial
  0 swap                           # place a zero below n
  begin dup 1 - dup  1 = until     # make stack like 0 n ... 4 3 2 1
  begin dump *  over 0 = until     # multiply till see the zero below answer
  swap drop ;                      # delete the zero
