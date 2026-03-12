import sys
import re
import ast

def insertSubArray(mainArray, index, subArray):
    mainArray[index:index+1] = subArray
    return mainArray#[0:index] + subArray + mainArray[index+len(subArray)+1:len(mainArray)-1]

def findClosingCodeblock(program, startLine):
    count = 1
    for lineIndex, line in enumerate(program[startLine+1:]):
        if(re.fullmatch(r'.*\{', line)): count += 1
        if(re.fullmatch(r'\}', line)): count -= 1
        if(count == 0): return (startLine+lineIndex+1)
def findClosingBracket(line, startIndex):
    count = 1
    for index, char in enumerate(line[startIndex+1:]):
        if(char == "("): count += 1
        if(char == ")"): count -= 1
        if(count == 0): return index+startIndex

program = []

tvarsCounter = 0
codepointCounter = 1

preserveCodepoints = False
simplifyOnly = False

for index, arg in enumerate(sys.argv):
    if(arg == "--preserve-codepoints"):
        preserveCodepoints = True
        del sys.argv[index]
for index, arg in enumerate(sys.argv):
    if(arg == "--simplify-only"):
        simplifyOnly = True
        del sys.argv[index]

with open(sys.argv[1], "r", encoding="utf-8") as file:
    program = re.split(r'[\n;]', file.read())

#imports
for index, line in enumerate(program):
    if(re.fullmatch(r'import.*', line.replace(" ", ""))):
        with open(line.replace(" ", "")[6:], "r", encoding="utf-8") as importfile:
            importfilearr = re.split(r'[\n;]', importfile.read())
            program = insertSubArray(program, index, importfilearr)

for index, line in enumerate(program):
    if(line.replace(" ", "")[0:2] == "//"):
        del program[index]

CONSTANTS = [   ["DR_A_HI" , "*(65529)"], 
                [ "DR_A_LO" , "*(65530)"],
                [ "DR_DATA" , "*(65531)"],
                [ "DR_DONE" , "*(65532)"],
                [ "DW_E" , "*(65524)"],
                [ "DW_A_HI" , "*(65525)"],
                [ "DW_A_LO" , "*(65526)"],
                [ "DW_DATA" , "*(65527)"],
                [ "DW_DONE" , "*(65528)"]
            ]

for index, line in enumerate(program):
    for const in CONSTANTS:
        program[index] = program[index].replace(const[0], const[1])

#goto label assignment
for index, line in enumerate(program):
    if(re.fullmatch(r'.+\:', line.replace(" ", ""))):
        program[index] = f"e{codepointCounter:04}"
        for checkindex, check in enumerate(program):
            program[checkindex] = check.replace(f" {line.replace(" ", "")[:-1]}", f" e{codepointCounter:04}")
        codepointCounter += 1
#functions   
for index, line in enumerate(program):    
    if(line[0:8] == "function"):
        closeBracket = findClosingCodeblock(program, index)
        arguments = line.split("(")[1].split(")")[0].replace(" ", "").split(",")

        program[closeBracket] = ""

        program[index] = f"e{codepointCounter:04}"
        program.insert(index+1, line.split("{")[1])

        tCounter = 1

        for argIndex, arg in enumerate(arguments):
            program.insert(index+1, f"t{tCounter:04} = *(sp - {len(arguments)-argIndex})")
            for functionLineIndex, functionLine in enumerate(program[index:closeBracket]):
                program[index+functionLineIndex] = program[index+functionLineIndex].replace(arg, f"t{tCounter:04}")
            tCounter += 1
    
        functionName = re.split(r'[\s(]', line)[1]

        for checkindex, check in enumerate(program):
            program[checkindex] = program[checkindex].replace(functionName, f"e{codepointCounter:04}")

        codepointCounter += 1

        if(tCounter > tvarsCounter): tvarsCounter = tCounter
#arithmetic expansion
for index, line in enumerate(program): 
    if(re.search(r'[a-zA-Z\s0-9]=[a-zA-Z\s0-9]', line)):
        destName = line.split("=")[0]

        opCount = 0
        for charindex, char in enumerate(line):
            if(re.fullmatch(r'[+-]', char)): 
                opCount += 1
                if(opCount > 1):
                    program.insert(index+1, destName + " = " + destName + char + program[index][charindex+1:])
                    program[index] = program[index][:charindex] #continue
                    break
#string expansion
for index, line in enumerate(program):
    if(re.search(r'.*\s*\=\s*[\'\"].*[\'\"]', line)):
        destName = line.split("=")[0]
        program[index] = f'{destName} = {str([*ast.literal_eval(line.split("=")[1])])}'

#char conversion
for index, line in enumerate(program):
    while(re.search(r'[\'\"][^\'\"]*[\'\"]', line)):
        char = re.search(r'[\'\"][^\'\"]*[\'\"]', line)
        line = line.replace(line[char.start():char.end()], str(ord(ast.literal_eval(line[char.start():char.end()]))))

    program[index] = line
#array expansion
for index, line in enumerate(program):
    if(re.search(r'.*\s*\=\s*\[.*\]', line)):
        destName = line.split("=")[0]

        program.append(f"e{codepointCounter:04}")
        for itemindex, item in enumerate(ast.literal_eval(line.split("=")[1])):
            program.append("~" + str(item))
        program[index] = f"{destName} = &e{codepointCounter:04} + 2"

        codepointCounter += 1
#bracket expansion
for index, line in enumerate(program):
    start = re.search(r'[\s\*\&\(\!]\(', program[index])
    while(start):
        #for l in program:
        #    print(l)
        end = findClosingBracket(program[index], start.end())+1
        simplified = program[index].replace(program[index][start.end()-1:end+1], "t0000")
        program.insert(index+1, simplified)

        program[index] = f"t0000 = {program[index][start.end():end]}"

        if(1 > tvarsCounter): tvarsCounter = 1
        start = re.search(r'[\s\*\&\(\!]\(', program[index])
#tvar init lines
for i in range(0, tvarsCounter+1):
    program.insert(0, f"t{i:04}")
#var initing
for index, line in enumerate(program):
    if(re.fullmatch(r'[^e\{\}\~][a-zA-Z0-9]*', line.strip()) and not line.strip() == "NOP"):
        program.append(f"e{codepointCounter:04}")
        for checkindex, check in enumerate(program):
            while(re.search(r'[\s\=\-\+\(\)\*\&\!]' + line.replace(" ", "") + r'[\s\=\-\+\(\)]', program[checkindex]) or re.fullmatch(r'.*[\s\=\-\+\)\*\&\!]' + line.replace(" ", ""), program[checkindex]) or re.fullmatch(r'.*\s' + line.replace(" ", ""), program[checkindex])) or re.fullmatch(line.replace(" ", "") + r'\s*[\=].*', program[checkindex]):
                program[checkindex] = check.replace(line.replace(" ", ""), f"e{codepointCounter:04}")
        
        codepointCounter += 1
        program[index] = ""
        
#if jump signage
for index, line in enumerate(program):
    if(line.strip()[0:2] == "if"):
        closeBracket = findClosingCodeblock(program, index)
        
        program[closeBracket] = f"e{codepointCounter:04}"
        program[index] = line.replace("{", f" e{codepointCounter:04}")

        codepointCounter += 1
#function expansion
for index, line in enumerate(program):
    fcheck = re.search(r'.+\=[^\+\-\*\&]+\([^\(\)]*\)', line)
    if(fcheck):
        program[index] = line.split("=")[1]
        program.insert(index+1, line.split("=")[0] + "= fretv")

#assemblification
if not simplifyOnly:
    for index, line in enumerate(program):
        #e0000 = a
        if(re.fullmatch(r'.+\=[^\-\+]+', line.replace(" ", ""))):
            splitLine = re.split(r'\=', line.replace(" ", ""))

            if(re.fullmatch(r'[0-9]+', splitLine[1])):
                loadingInstructions = [f"REG R6 {splitLine[1]}"]
            if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', splitLine[1])):
                loadingInstructions = [f"LDI R6 {splitLine[1]}"]
            if(re.fullmatch(r'fretv', splitLine[1])):
                loadingInstructions = [f"ADD R6 R9 R15"]
            if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', splitLine[1])):
                loadingInstructions = [f"LDI R6 {splitLine[1][1:]}",
                                    f"LDR R6 R6"]
            if(re.fullmatch(r'\&e[0-9][0-9][0-9][0-9]', splitLine[1])):
                loadingInstructions = [f"REG R6 {splitLine[1][1:]}"]
            
            if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', splitLine[0])):
                dWriteInstructions = [f"STI {splitLine[0]} R6"]
            if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', splitLine[0])):
                dWriteInstructions = [f"LDI R5 {splitLine[0][1:]}",
                                    f"STR R5 R6"]
                
            program = insertSubArray(program, index, loadingInstructions+dWriteInstructions)

        #e0000 = a + b
        if(re.fullmatch(r'[^*&].+\=.+[\+\-].+', line.replace(" ", ""))):
            splitLine = re.split(r'[\+\-\=]', line.replace(" ", ""))

            loadingInstructions = []
            for opindex, operand in enumerate(splitLine[1:]):
                if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', splitLine[1+opindex])):
                    loadingInstructions.append(f"LDI R{7+opindex} {splitLine[1+opindex]}")
                if(re.fullmatch(r'\&e[0-9][0-9][0-9][0-9]', splitLine[1+opindex])):
                    loadingInstructions.append(f"REG R{7+opindex} {splitLine[1+opindex][1:]}")
                if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', splitLine[1+opindex])):
                    loadingInstructions.append(f"LDI R{7+opindex} {splitLine[1+opindex][1:]}")
                    loadingInstructions.append(f"LDR R{7+opindex} R{7+opindex}")
                if(re.fullmatch(r'[0-9]+', splitLine[1+opindex])):
                    loadingInstructions.append(f"REG R{7+opindex} {splitLine[1+opindex]}")
                if(re.fullmatch(r'sp', splitLine[1+opindex])):
                    loadingInstructions.append(f"ADD R{7+opindex} R4 R15")
            program = insertSubArray(program, index, loadingInstructions + [
                f"{"ADD" if re.search(r'\+', line.replace(" ", "")) else "SUB"} R6 R7 R8",
                f"STI {splitLine[0]} R6"
            ])
        #if((!)a) e0000
        if(re.fullmatch(r'if\(.*\)e[0-9][0-9][0-9][0-9]', line.replace(" ", ""))):
            splitLine = re.split(r'[\(\)]', line.replace(" ", ""))
            negated = splitLine[1][0] == "!"

            if(not negated):
                checkInstructions = [f"LDI R6 {splitLine[1]}",
                                    "ADD R6 R6 R6",
                                    f"JZI {splitLine[2]}"]
                
            #to the absolutely nobody who is going to read this,
            #there used to be !negation functionality...

            program = insertSubArray(program, index, checkInstructions)
        #e0001(e0003, e0004)
        if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]\(.*\)', line.replace(" ", ""))):
            splitLine = re.split(r'[\(\)]', line.replace(" ", ""))
            arguments = splitLine[1].split(",")

            argPushInstructions = []
            for argument in arguments:
                if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', argument)):
                    argPushInstructions.append("ADD R4 R4 R14")
                    argPushInstructions.append(f"LDI R6 {argument}")
                    argPushInstructions.append("STR R4 R6")
                if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', argument)):
                    argPushInstructions.append("ADD R4 R4 R14")
                    argPushInstructions.append(f"LDI R6 {argument[1:]}")
                    argPushInstructions.append("LDR R6 R6")
                    argPushInstructions.append("STR R4 R6")
                if(re.fullmatch(r'\&e[0-9][0-9][0-9][0-9]', argument)):
                    argPushInstructions.append("ADD R4 R4 R14")
                    argPushInstructions.append(f"MEM R4 {argument[1:]}")
                if(re.fullmatch(r'[0-9]+', argument)):
                    argPushInstructions.append("ADD R4 R4 R14")
                    argPushInstructions.append(f"MEM R4 {argument}")

            program = insertSubArray(program, index, argPushInstructions + [
                "ADD R4 R4 R14",
                f"MEM R4 e{codepointCounter:04}",
                f"JUCI {splitLine[0]}",
                f"e{codepointCounter:04}",
                f"REG R6 {len(arguments)+1}",
                "SUB R4 R4 R6"
            ])
            codepointCounter += 1
        #cout(a)
        if(re.fullmatch(r'cout\(.*\)', line.replace(" ", ""))):
            value = re.split(r'[\(\)]', line.replace(" ", ""))[1]
            
            if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', value)):
                logInstructions = [f"LDI R3 {value}"]
            if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', value)):
                logInstructions = [f"LDI R5 {value[1:]}",
                                "LDR R3 R5"]
            if(re.fullmatch(r'\&e[0-9][0-9][0-9][0-9]', value)):
                logInstructions = [f"REG R3 {value[1:]}"]
            if(re.fullmatch(r'[0-9]+', value)):
                logInstructions = [f"REG R3 {value}"]
            
            program = insertSubArray(program, index, logInstructions)
        #tmrs(a)
        if(re.fullmatch(r'tmrs\(.*\)', line.replace(" ", ""))):
            value = re.split(r'[\(\)]', line.replace(" ", ""))[1]
            
            if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', value)):
                logInstructions = [f"LDI R1 {value}"]
            if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', value)):
                logInstructions = [f"LDI R5 {value[1:]}",
                                "LDR R1 R5"]
            if(re.fullmatch(r'\&e[0-9][0-9][0-9][0-9]', value)):
                logInstructions = [f"REG R1 {value[1:]}"]
            if(re.fullmatch(r'[0-9]+', value)):
                logInstructions = [f"REG R1 {value}"]
            
            program = insertSubArray(program, index, logInstructions)
        #tmrh(a())
        if(re.fullmatch(r'tmrh\(.*\)', line.replace(" ", ""))):
            addr = re.split(r'[\(\)]', line.replace(" ", ""))[1]

            program = insertSubArray(program, index, [
                "REG R5 65533",
                f"MEM R5 {addr}"
            ])
        #cin()
        if(re.fullmatch(r'cin\(\s*\)', line.replace(" ", ""))):
            program = insertSubArray(program, index, [
                "REG R5 65535",
                f"MEM R5 e{codepointCounter:04}",
                f"e{codepointCounter+1:04}",
                f"JUCI e{codepointCounter+1:04}",
                f"e{codepointCounter:04}",
                "ADD R9 R2 R15"
            ])
            codepointCounter += 2
        #return a
        if(re.fullmatch(r'return.*', line.replace(" ", ""))):
            value = line.replace(" ", "").split("return")[1]

            if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]', value)):
                retLoadInstructions = [f"LDI R9 {value}"]
            if(re.fullmatch(r'\*e[0-9][0-9][0-9][0-9]', value)):
                retLoadInstructions = [f"LDI R5 {value[1:]}",
                                "LDR R9 R5"]
            if(re.fullmatch(r'\&e[0-9][0-9][0-9][0-9]', value)):
                retLoadInstructions = [f"REG R9 {value[1:]}"]
            if(re.fullmatch(r'[0-9]+', value)):
                retLoadInstructions = [f"REG R9 {value}"]

            program = insertSubArray(program, index, retLoadInstructions + ["LDR R6 R4", "JUCR R6"])
        #goto e0000
        if(re.fullmatch(r'goto.*', line.replace(" ", ""))):
            program = insertSubArray(program, index, ["JUCI " + line.replace(" ", "").split("goto")[1]])
        #exit()
        if(re.fullmatch(r'exit\(\)', line.replace(" ", ""))):
            program = insertSubArray(program, index, ["HLT"])

    program = ["REG R14 1", f"REG R4 e{codepointCounter:04}"] + program + [f"e{codepointCounter:04}"]

program = [line+"\n" for line in program if line]

#codepoint assignment
for index, line in enumerate(program):
    if(re.fullmatch(r'e[0-9][0-9][0-9][0-9]\n', line.replace(" ", "")) and not preserveCodepoints):
        for checkindex, check in enumerate(program):
            program[checkindex] = check.replace(line.replace(" ", "")[:-1], str(index*2))
        program[index] = "NOP"

for index, line in enumerate(program):
    if not "\n" in line:
        program[index] = line+"\n"
    if line[0] == "~":
        program[index] = line[1:]

with open(sys.argv[2], "w") as file:
    file.writelines(program)
