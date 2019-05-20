# Project 1: DFA Parser and Minimizer


## How to use:

 1. Install [python](https://www.python.org/downloads/) (should work on any version above 2.7, tested on versions 2.7, 3.6 and 3.7).
 2. Download pydfa.py script.
 3. Run the script in a shell with following command: `python -m pydfa <pathtofile>`  
    Alternatively, you can run the command without the filepath argument, and the script will  
    prompt you for it.
 4. Enjoy your minimized DFA!

## Syntax rules for file parser:
 1. File must have the following syntax:
    ```
    (states, (0,1,2,3,4,5))
    (alpha, (1,2))
    (trans-func, ((0,1,3),(0,2,4),(1,2,3),(2,1,5),(3,1,2),(4,2,1),(5,1,4)))
    (start, 0)
    (final, (1))
    ```
    Headers states, alpha, trans-func, start, and final are reserved words and cannot be state names.
 2. Repeated states, alphabet symbols, transition functions and final states will result in an error.
 3. Commas, parenthesis and whitespace are split on and should not be used in state names.  
    Most other symbols are allowed.
 4. Partially defined DFA's are converted to be fully defined. The current implementation of this  
    makes use of the reserved state name **"new_sink"**. If the file read contains a state with this name,  
    an error message will be displayed.


## Note about minimization implementation:
The minimization algorithm employed removes states that cannot be reached from the given start state  
prior to generating the table for reduction. If you expected a disconnected state to be represented  
in a tuple in the list of minimized states but did not see it, this is why.