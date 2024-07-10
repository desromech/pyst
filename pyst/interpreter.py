from .mop import *
from .asg import *

class ASGNodeWithInterpretableInstructions:
    def __init__(self, functionalNode, instructions, constantCount, activationParameterCount) -> None:
        self.functionalNode = functionalNode
        self.instructions = instructions
        self.constantCount = constantCount
        self.activationParameterCount = activationParameterCount
        self.startpc = constantCount + activationParameterCount
        self.activationContextSize = len(self.instructions) - self.constantCount
        self.parametersLists = None
        self.constants = []
        self.buildParametersLists()

    def buildParametersLists(self):
        self.parametersLists = []
        instructionIndexTable = {}
        for i in range(len(self.instructions)):
            instructionIndexTable[self.instructions[i]] = i - self.constantCount
        for i in range(self.constantCount):
            constantInstruction = self.instructions[i]
            self.constants.append(constantInstruction.evaluateAsConstantValue())
        for i in range(self.constantCount, len(self.instructions)):
            instruction = self.instructions[i]
            parameterList = tuple(map(lambda dep: instructionIndexTable[dep], instruction.interpretationDependencies()))
            self.parametersLists.append(parameterList)

    def evaluateWithArguments(self, *args):
        activationContext = ASGNodeInterpreterActivationContext(self.startpc, args, self)
        return activationContext.execute()

    def dump(self) -> str:
        result = ''
        for i in range(len(self.instructions)):
            result += '%d: %s' % (i - self.constantCount, self.instructions[i].prettyPrintNameWithDataAttributes())
            if i >= self.constantCount:
                parameters = self.parametersLists[i - self.constantCount]
                if len(parameters) > 0:
                    result += '('
                    for i in range(len(parameters)):
                        if i > 0:
                            result += ', '
                        result += str(parameters[i])
                    result += ')'
            else:
                result += ' := '
                result += repr(self.constants[i])

            result += '\n'

        return result

    def dumpDot(self) -> str:
        result = 'digraph {\n'

        def formatId(id) -> str:
            if id < 0:
                return 'C%d' % abs(id)
            else:
                return 'N%d' % id

        for i in range(len(self.instructions)):
            result += '  %s [label="%s"]\n' % (formatId(i - self.constantCount), self.instructions[i].prettyPrintNameWithDataAttributes().replace('\\', '\\\\'.replace('\"', '\\"')))

        for i in range(self.constantCount, len(self.instructions)):
            if i > self.startpc:
                result += '  %s -> %s [color = blue]\n' % (formatId(i - self.constantCount - 1), formatId(i - self.constantCount))

            parameters = self.parametersLists[i - self.constantCount]
            for param in parameters:
                result += '  %s -> %s\n' % (formatId(i - self.constantCount), formatId(param))

        result += '}'
        return result
    
    def dumpDotToFileNamed(self, filename):
        with open(filename, "w") as f:
            f.write(self.dumpDot())

class ASGNodeInterpreterActivationContext:
    def __init__(self, pc, activationParameters, instructions: ASGNodeWithInterpretableInstructions) -> None:
        self.pc = pc
        self.data = [None] * instructions.activationContextSize
        self.instructions = instructions
        self.result = None
        self.shouldReturn = None

        for i in range(len(activationParameters)):
            self.data[i] = activationParameters[i]

    def execute(self):
        self.shouldReturn = False
        constantCount = self.instructions.constantCount
        while not self.shouldReturn:
            pc = self.pc
            instruction = self.instructions.instructions[pc]
            parameters = self.instructions.parametersLists[pc - constantCount]
            self.pc += 1
            self.data[pc - constantCount] = instruction.interpretInContext(self, parameters)

        return self.result

    def returnValue(self, value):
        self.result = value
        self.shouldReturn = True

    def __getitem__(self, index: int):
        if index < 0:
            return self.instructions.constants[self.instructions.constantCount + index]
        else:
            return self.data[index]
