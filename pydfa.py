from __future__ import absolute_import, division, print_function
from collections import OrderedDict
import re
import sys
import copy
import os


class dfa():
    def __init__(self):
        self.states = []
        self.alpha = []
        self.transfunc = []
        self.start = []
        self.final = []
        self.distinct = []

    def __str__(self):
        strstate = self.lstostr(self.states)
        stralpha = self.lstostr(self.alpha)
        strstart = self.lstostr(self.start)
        strfinal = self.lstostr(self.final)

        transcopy = copy.deepcopy(self.transfunc)
        pos = 0
        loop = 0
        while pos < (len(transcopy)):
            if loop == 2:
                transcopy.insert(pos, '\n')
                loop = -1
            pos += 1
            loop += 1
        strtrans = self.lstostr(transcopy)

        return (
            "(states, ({}))\n(alpha, ({}))\n(trans-func, ({}))\n(start, {})\n(final, ({}))\n".format(
                strstate, stralpha, strtrans, strstart, strfinal)
        )

    def lstostr(self, l):
        tostr = ""
        if l == []:
            return ""
        for i in range(len(l)):
            if isinstance(l[i], list) and l[i] in self.transfunc:
                if i == (len(l) - 1):
                    tostr = tostr + "({})".format(self.lstostr(l[i]))
                else:
                    tostr = tostr + "({}), ".format(self.lstostr(l[i]))                
            elif isinstance(l[i], list) and l[i] in self.states:
                if i == (len(l) - 1):
                    tostr = tostr + "[{}]".format(self.lstostr(l[i]))
                else:
                    tostr = tostr + "[{}], ".format(self.lstostr(l[i]))
            else:
                if l[i] == '\n':
                    tostr = tostr + '\n' + ' '*14
                elif i == (len(l) - 1):
                    tostr = tostr + "{}".format(l[i])
                else:
                    tostr = tostr + "{}, ".format(l[i])
        return tostr

    # Methods for main to call:
    def parsefile(self, filename):
        f = open(filename)
        file = f.read()
        f.close()
        self.chkparenths(file)
        self.chkfile(file)
        split_file = re.split(r'[ \(\),\n]', file)
        self.parse(split_file)

        # Turn partial DFA into full DFA:
        self.partialtofull()

        # Ensure DFA is valid:
        self.validate()

    def minimize(self):
        # Before anything, remove unreachable states to minimize run-time and simplify final dfa:
        unreach = self.findunreach()
        self.removeunreach(unreach)

        # Then, generate table distinct:
        self.genreduct()

        # Finally use distinct to join states:
        l1 = self.parsedistinct()
        l2 = self.uniononintersect(l1)
        self.swapstates(l2)
        self.swaptrans(l2)
        self.swapstart(l2)
        self.swapfinal(l2)

    # "Private" methods that are not directly called outside the wrapper methods:
    def chkparenths(self, s):
        # Checks to ensure parenths are matched before we strip/ignore them.
        depth = 0
        lineno = 1
        for char in s:
            if char == '(':
                depth += 1
            if char == ')':
                depth -= 1
                if depth == -1:
                    sys.exit(
                        "Syntax error: Mismatched right parenthesis.")
            if char == '\n':
                lineno += 1
        if depth >= 1:
            sys.exit(
                "Syntax error: Mismatched left parenthesis.")
                    
    def chkfile(self, s):
        patterns = [
            (r'\w+ +\w+', 'comma_error'),
            (r'\w+ *, *\)', 'eolcomma_error'),
            (r'\( *, *\w+', 'solcomma_error'),
            (r',,', 'cac_error')
        ]
        for pattern in patterns:
            pat, tag = pattern
            match = re.search(pat, s)
            if match:
                if tag == 'comma_error':
                    sys.exit(
                        "Syntax error: Missing comma.")
                if tag == 'eolcomma_error':
                    sys.exit(
                        "Syntax error: Comma at the end of an input list.")
                if tag == 'solcomma_error':
                    sys.exit(
                        "Syntax error: comma at the start of an input list.")
                if tag == 'cac_error':
                    sys.exit(
                        "Syntax error: comma directly after comma in input.")

        if not re.search(r'.*states.*alpha.*trans-func.*start.*final.*', s, re.DOTALL):
            sys.exit(
                "Syntax error: section header is missing, or order of sections is incorrect")
        if not re.search(r'.*states,.*alpha,.*trans-func,.*start,.*final,.*', s, re.DOTALL):
            sys.exit(
                "Syntax error: comma after section header is missing (ex: (states (...))).")

    def parse(self, file):
        translist = []
        reading = None
        for item in file:
            if item == '':
                continue
            elif re.match(r'states|alpha|trans-func|start|final', item):
                reading = item
                continue
            else:
                if reading == 'states':
                    if item == 'new_sink':
                        sys.exit(
                            'Definition error: State name "new_sink" reserved for use by partialtofull method.' 
                        )
                    if item in self.states:
                        sys.exit(
                            "Definition error: Improperly defined set. Duplicate state found.")
                    self.states.append(item)
                elif reading == 'alpha':
                    if self.states == []:
                        sys.exit(
                            "Definition Error: At least one state is required.")
                    if item in self.alpha:
                        sys.exit(
                            "Definition error: Improperly defined set. Duplicate alphabet symbol found.")
                    self.alpha.append(item)
                elif reading == 'trans-func':
                    translist.append(item)
                    if len(translist) == 3:
                        if translist in self.transfunc:
                            sys.exit(
                                "Definition error: Improperly defined set. Duplicate transition function found.")
                        self.transfunc.append(translist)
                        translist = []
                elif reading == 'start' and not len(translist) == 0:
                    sys.exit(
                        "Definition error: Transition function is defined improperly or is incomplete.")
                elif reading == 'start':
                    self.start.append(item)
                elif reading == 'final':
                    if self.start == []:
                        sys.exit(
                            "Definition error: Start state is required.")
                    if item in self.final:
                        sys.exit(
                            "Definition error: Improperly defined set. Duplicate final state found.")
                    self.final.append(item)
                else:
                    sys.exit("How did you get here?")                

    def partialtofull(self):
        sta = []
        for i in self.transfunc:
            sta.append((i[0], i[1]))
        for i in self.states:
            for a in self.alpha:
                if not (i, a) in sta and not 'new_sink' in self.states:
                    self.states.append('new_sink')
                    self.transfunc.append([i, a, 'new_sink'])
                elif not (i, a) in sta:
                    self.transfunc.append([i, a, 'new_sink'])

    def validate(self):
        # State names are assumed valid at this point.
        # Checking alpha to ensure only characters are defined
        for i in self.alpha:
            if len(i) > 1:
                sys.exit("Syntax error: alphabet must be composed of single characters.")

        # Checking that states in trans-func are in the list of states, and that the alpha
        # characters are in alpha.
        for i in self.transfunc:
            if not i[0] in self.states:
                sys.exit(
                    "Definition error: State input in a transition function not in list of states.")
            if not i[1] in self.alpha:
                sys.exit(
                    "Definition error: Alpha input in a transition function not in alphabet.")
            if not i[2] in self.states:
                sys.exit(
                    "Definition error: Result of a transition function not in list of states.")

        # Checking that transition is an actual function (each input is mapped to only one output).
        temp = []
        for i in self.transfunc:
            (x, y) = i[0], i[1]
            if (x, y) in temp:
                sys.exit(
                    "Definition error: Transition function not a function (same input goes to two different outputs)."
                )
            temp.append((x, y))

        # Checking that there is only one start state, and that it is in the set of states.
        if len(self.start) > 1:
            sys.exit("Definition error: More than one start state defined.")
        if not self.start[0] in self.states:
            sys.exit("Definition error: Start state not in the set of states.")

        # Checking that the set of final states is a subset of the set of states.
        for i in self.final:
            if not i in self.states:
                sys.exit("Definition error: a final state is not in the set of states.")

    def findunreach(self):
        reachable = set()
        reachable.add(self.start[0])
        new = set()
        new.add(self.start[0])
        while not len(new) == 0:
            temp = set()
            for i in new:
                for a in self.alpha:
                    temp.add(self.dotrans(i, a))
            new = temp - reachable
            reachable = reachable | new
        unreach = set(self.states) - reachable
        return list(unreach)
        
    def removeunreach(self, l):   
        for i in l:
            self.states.remove(i)
            j = 0
            while j < len(self.transfunc):
                if i in self.transfunc[j]:
                    self.transfunc.pop(j)
                    continue
                j += 1
            if i in self.final:
                self.final.remove(i)
        
    def genreduct(self):
        # Initializing reduction table.
        self.distinct = [[None for x in range(len(self.states))]
                         for y in range(len(self.states))]
        num = len(self.distinct)

        # Generates the reduction table in two steps. First step:
        for x in range(num):
            for y in range(num):
                if x >= y:
                    continue
                elif self.states[x] in self.final and not self.states[y] in self.final:
                    self.distinct[y][x] = 1
                elif not self.states[x] in self.final and self.states[y] in self.final:
                    self.distinct[y][x] = 1
                else:
                    self.distinct[y][x] = 0

        # Second step:
        equcont = False
        while not equcont:
            fakedistinct = copy.deepcopy(self.distinct)
            for x in range(num):
                for y in range(num):
                    if x >= y:
                        continue
                    else:
                        for a in self.alpha:
                            x1 = self.dotrans(self.states[x], a)
                            y1 = self.dotrans(self.states[y], a)
                            if self.states.index(x1) > self.states.index(y1):
                                x1, y1 = y1, x1
                            if self.distinct[y][x] == 0 and self.distinct[self.states.index(y1)][self.states.index(x1)] == 1:
                                self.distinct[y][x] = 1
            if fakedistinct == self.distinct:
                equcont = True

    def parsedistinct(self):
        l = []
        for x in range(len(self.distinct)):
            for y in range(len(self.distinct)):
                if self.distinct[y][x] == 1 or self.distinct[y][x] == None:
                    continue
                else:
                    i = [self.states[x], self.states[y]]
                    l.append(i)
        return l

    def uniononintersect(self, l):
        l2 = []
        while len(l) > 0:
            x, xs = l[0], l[1:]
            head = set(x)

            origlen = -1
            while len(head) > origlen:
                origlen = len(head)
                tail = []
                for i in xs:
                    if len(head.intersection(set(i))) > 0:
                        head = head | set(i)
                    else:
                        tail.append(i)
                xs = tail

            l2.append(list(head))
            l = xs
        for i in l2:
            i.sort()
        l2.sort()
        return l2

    def swapstates(self, l):
        for x in l:
            for x1 in x:
                pos = self.states.index(x1)
                self.states.remove(x1)
                if x not in self.states:
                    self.states.insert(pos, x)

    def swaptrans(self, l):
        for x in l:
            for x1 in x:
                for i in self.transfunc:
                    for j in i:
                        if not x1 == j or x1 == i[1]:
                            continue
                        pos = i.index(x1)
                        i.remove(x1)
                        i.insert(pos, x)
        self.removetransdupes()

    def swapstart(self, l):
        for x in l:
            for x1 in x:
                if x1 == self.start[0]:
                    self.start.pop()
                    self.start.append(x)

    def swapfinal(self, l):
        for x in l:
            for x1 in x:
                if not x1 in self.final:
                    continue
                pos = self.final.index(x1)
                self.final.remove(x1)
                if x not in self.final:
                    self.final.insert(pos, x)

    def dotrans(self, q, a):
        tf = self.transfunc
        for i in tf:
            if i[0] == q and i[1] == a:
                return i[2]
        return 'new_sink'

    def removestatedupes(self):
        prunedlist = []
        for i in self.states:
            if i not in prunedlist:
                prunedlist.append(i)
        self.states = prunedlist

    def removealphadupes(self):
        prunedlist = []
        for i in self.alpha:
            if i not in prunedlist:
                prunedlist.append(i)
        self.alpha = prunedlist

    def removetransdupes(self):
        prunedlist = []
        for i in self.transfunc:
            if i not in prunedlist:
                prunedlist.append(i)
        self.transfunc = prunedlist

    def removefinaldupes(self):
        prunedlist = []
        for i in self.final:
            if i not in prunedlist:
                prunedlist.append(i)
        self.final = prunedlist


def main(*args):
    if len(sys.argv) > 2:
        sys.exit(
            'Error: Pydfa only takes in one argument (filename). Syntax is "python -m pydfa <pathtofile>"')
    elif len(sys.argv) == 2:
        filepath = sys.argv[1]
    else:
        if sys.version_info[0] < 3:
            filepath = raw_input("Input filename: ")
        else:
            filepath = input("Input filename: ")

    if not os.path.isfile(filepath):
        sys.exit('File error: invalid file path or filename.')
    if not filepath.lower().endswith('.dfa'):
        sys.exit('File error: input file must have .dfa extension.')

    dfa1 = dfa()
    dfa1.parsefile(filepath)
    dfa1.minimize()
    print(dfa1)


if __name__ == '__main__':
    main(*sys.argv[1:])
