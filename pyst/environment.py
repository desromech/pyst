from .mop import *
from .syntax import *
from .asg import *

class Stdio:
    pass

class ASGEnvironment(ABC):
    @abstractmethod
    def getTopLevelTargetEnvironment(self):
        pass

    @abstractmethod
    def lookSymbolBindingListRecursively(self, symbol: str):
        pass

    @abstractmethod
    def lookSymbolBindingRecursively(self, symbol: str):
        pass

    def isLexicalEnvironment(self):
        return False

    def isScriptEnvironment(self):
        return False
    
    def childWithSymbolBinding(self, symbol: str, binding: ASGNode):
        return ASGChildEnvironmentWithBindings(self).childWithSymbolBinding(symbol, binding)

class ASGMacroContext(ASGNode):
    derivation = ASGNodeDataAttribute(ASGNodeDerivation)
    expander = ASGNodeDataAttribute(object)

class ASGTopLevelTargetEnvironment(ASGEnvironment):
    uniqueInstance_ = None

    def __init__(self) -> None:
        super().__init__()
        self.symbolTable = {}
        topLevelDerivation = ASGNodeNoDerivation.getSingleton()
        self.topLevelUnificationTable = {}
        self.addSymbolValue('nil', ASGLiteralNilNode(topLevelDerivation))
        self.addSymbolValue('false', ASGLiteralFalseNode(topLevelDerivation))
        self.addSymbolValue('true', ASGLiteralTrueNode(topLevelDerivation))

        self.addSymbolValue('Stdio', ASGLiteralObjectNode(topLevelDerivation, Stdio))

        self.addPrimitiveFunctions()
        self.gcmCache = {}
        self.interpreterCache = {}

    def addUnificationValue(self, value: ASGNode):
        comparisonValue = ASGUnificationComparisonNode(value)
        if comparisonValue in self.topLevelUnificationTable:
            return self.topLevelUnificationTable[comparisonValue]
        else:
            self.topLevelUnificationTable[comparisonValue] = value
            return value

    def addSymbolValue(self, name: str, value: ASGNode):
        if name is not None:
            self.symbolTable[name] = [value] + self.symbolTable.get(name, [])

    def lookLastBindingOf(self, name: str):
        if not name in self.symbolTable:
            return None
        return self.symbolTable[name][0]
    
    def lookValidLastBindingOf(self, name: str):
        if not name in self.symbolTable:
            raise Exception('Missing required binding for %s.' % name)
        return self.symbolTable[name][0]

    def getTopLevelTargetEnvironment(self):
        return self
    
    def lookSymbolBindingListRecursively(self, symbol: str):
        return self.symbolTable.get(symbol, [])

    def lookSymbolBindingRecursively(self, symbol: str):
        result = self.symbolTable.get(symbol, None)
        if result is not None:
            return result[0]
        else:
            return None

    @classmethod
    def uniqueInstance(cls):
        if cls.uniqueInstance_ is None:
            cls.uniqueInstance_ = cls()

        return cls.uniqueInstance_
    
    def addPrimitiveFunctions(self):
        pass

class ASGChildEnvironment(ASGEnvironment):
    def __init__(self, parent: ASGEnvironment, sourcePosition: SourcePosition = None) -> None:
        super().__init__()
        self.parent = parent
        self.sourcePosition = sourcePosition
        self.topLevelTargetEnvironment = parent.getTopLevelTargetEnvironment()
    
    def getTopLevelTargetEnvironment(self):
        return self.topLevelTargetEnvironment

    def lookSymbolBindingListRecursively(self, symbol: str):
        return self.parent.lookSymbolBindingListRecursively(symbol)

    def lookSymbolBindingRecursively(self, symbol: str):
        return self.parent.lookSymbolBindingRecursively(symbol)

class ASGChildEnvironmentWithBindings(ASGChildEnvironment):
    def __init__(self, parent: ASGEnvironment, sourcePosition: SourcePosition = None) -> None:
        super().__init__(parent, sourcePosition)
        self.symbolTable = {}

    def postCopy(self):
        self.symbolTable = dict(self.symbolTable)

    def addSymbolBinding(self, symbol: str, binding: ASGNode):
        if symbol is not None:
            self.symbolTable[symbol] = [binding] + self.symbolTable.get(symbol, [])

    def childWithSymbolBinding(self, symbol: str, binding: ASGNode):
        child = copy.copy(self)
        child.postCopy()
        child.addSymbolBinding(symbol, binding)
        return child

    def lookSymbolBindingListRecursively(self, symbol: str):
        return self.symbolTable.get(symbol, []) + self.parent.lookSymbolBindingListRecursively(symbol)

    def lookSymbolBindingRecursively(self, symbol: str):
        if symbol in self.symbolTable:
            return self.symbolTable[symbol][0]
        return self.parent.lookSymbolBindingRecursively(symbol)

class ASGLexicalEnvironment(ASGChildEnvironment):
    def isLexicalEnvironment(self):
        return True

class ASGFunctionalAnalysisEnvironment(ASGLexicalEnvironment):
    def __init__(self, parent: ASGEnvironment, sourcePosition: SourcePosition = None) -> None:
        super().__init__(parent, sourcePosition)
        self.arguments = []
        self.symbolTable = {}

    def addArgumentBinding(self, argument: ASGArgumentNode):
        self.arguments.append(argument)
        if argument.name is not None:
            self.symbolTable[argument.name] = [argument] + self.symbolTable.get(argument.name, [])

    def lookSymbolBindingListRecursively(self, symbol: str):
        return self.symbolTable.get(symbol, []) + self.parent.lookSymbolBindingListRecursively(symbol)

class ASGScriptEnvironment(ASGLexicalEnvironment):
    def __init__(self, parent: ASGEnvironment, sourcePosition: SourcePosition = None, scriptDirectory = '', scriptName = 'script') -> None:
        super().__init__(parent, sourcePosition)
        self.scriptDirectory = scriptDirectory
        self.scriptName = scriptName

    def isScriptEnvironment(self):
        return True

class ASGBuilderWithGVNAndEnvironment(ASGBuilderWithGVN):
    def __init__(self, parentBuilder, topLevelEnvironment: ASGTopLevelTargetEnvironment) -> None:
        super().__init__(parentBuilder)
        self.topLevelEnvironment = topLevelEnvironment

    def topLevelIdentifier(self, name: str):
        if self.parentBuilder is not None:
            return self.parentBuilder.topLevelIdentifier(name)

        value = self.topLevelEnvironment.lookLastBindingOf(name)
        return self.unifyWithPreviousBuiltNode(value)

def makeScriptAnalysisEnvironment(sourcePosition: SourcePosition, scriptPath: str) -> ASGEnvironment:
    topLevelEnvironment = ASGTopLevelTargetEnvironment.uniqueInstance()
    scriptDirectory = os.path.dirname(scriptPath)
    scriptName = os.path.basename(scriptPath)
    return ASGScriptEnvironment(topLevelEnvironment, sourcePosition, scriptDirectory, scriptName)
