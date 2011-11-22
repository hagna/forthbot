# fact3.4th

: variable create 1 allot ;            #   ---     create var and init to TOS
  variable m
  variable answer

: fact                                 #  n --- n!  replace TOS with factorial
     m !                               # set m to TOS
  1 answer !                           # set answer = 1
  begin
    answer @ m @ dump * answer !       # set answer = answer * m
    m @ 1 - m !                        # set m = m-1
    m @ 0 = until                      # repeat until m == 0
  answer @                             # return answer
  ;

 15 fact .                             # compute 15! and print
