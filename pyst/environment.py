from .mop import *
from .syntax import *
from .asg import *
import sys

class PystMetaclass(type):
    def __new__(cls, name, bases, attributes):
        assert len(bases) <= 1
        methodDictionary = {}
        metaMethodDictionary = {}
        superclass = None
        if len(bases) > 0:
            superclass = bases[0]

        for key, value in attributes.items():
            if hasattr(value, '__pystSelector__'):
                methodDictionary[value.__pystSelector__] = value
            if hasattr(value, '__pystMetaSelector__'):
                metaMethodDictionary[value.__pystMetaSelector__] = value

        pystClass = super().__new__(cls, name, bases, attributes)
        pystClass.__pystMethodDictionary__ = methodDictionary
        pystClass.__pystMetaMethodDictionary__ = metaMethodDictionary
        pystClass.__pystSuperclass__ = superclass
        return pystClass

    def lookupMetaSelector(cls, selector):
        found = cls.__pystMethodDictionary__.get(selector, None)
        if found is not None:
            return found
        if cls.__pystSuperclass__ is not None:
            return cls.__pystSuperclass__.lookupMetaSelector(selector)
        return None

    def metaPerformWithArguments(cls, selector, arguments):
        method = cls.lookupMetaSelector(selector)
        if method is None:
            if hasattr(cls, selector):
                return getattr(cls, selector)
        assert False

    def lookupSelector(cls, selector):
        found = cls.__pystMethodDictionary__.get(selector, None)
        if found is not None:
            return found
        if cls.__pystSuperclass__ is not None:
            return cls.__pystSuperclass__.lookupSelector(selector)
        return None
    
def pystSelector(selector: str):
    def decorator(func):
        func.__pystSelector__ = selector
        return func
    return decorator

def pystMetaSelector(selector: str):
    def decorator(func):
        func.__pystMetaSelector__ = selector
        return func
    return decorator

class PystObject(metaclass=PystMetaclass):
    @pystSelector('doesNotUnderstand:')
    def doesNotUnderstand(self, message):
        raise MessageNotUnderstood(self, message)

    def performWithArguments(self, selector, arguments):
        method = self.__class__.lookupSelector(selector)
        if method is not None:
            return method(self, *arguments)
        
        if len(arguments) == 0 and hasattr(self, selector):
            return getattr(self, selector)

        if selector == 'doesNotUnderstand:' and len(arguments) == 1:
            raise MessageNotUnderstood(self, arguments[0])

        return self.performWithArguments('doesNotUnderstand:', [Message(selector, arguments)])

class Message:
    def __init__(self, selector: str, arguments):
        self.selector = selector
        self.arguments = arguments

    def __str__(self) -> str:
        return '#' + repr(self.selector)

class MessageNotUnderstood(Exception):
    def __init__(self, receiver, message, *args: object) -> None:
        super().__init__(*args)
        self.receiver = receiver
        self.message = message

    def __str__(self) -> str:
        return 'MessageNotUnderstood: %s >> %s' % (repr(self.receiver), str(self.message))

ValueSelectors = set(['value', 'value:', 'value:value:', 'value:value:value:', 'value:value:value:value:'])

def performInWithArguments(receiver, selector: str, arguments):
    if hasattr(receiver, 'metaPerformWithArguments'):
        return receiver.metaPerformWithArguments(selector, arguments)
    if hasattr(receiver, 'performWithArguments'):
        return receiver.performWithArguments(selector, arguments)

    if hasattr(receiver, selector):
        return getattr(receiver, selector)
    
    if callable(receiver) and selector in ValueSelectors:
        return receiver(*arguments)
    if selector == 'doesNotUndertand:':
        raise MessageNotUnderstood(receiver, arguments[0])
    return performInWithArguments(receiver, 'doesNotUndertand:', (Message(selector, arguments),))

class FileStream(PystObject):
    def __init__(self, handle) -> None:
        self.handle = handle

    @pystSelector('nextPutAll:')
    def nextPutAll(self, data):
        self.handle.write(data)

    @pystSelector('nl')
    def nl(self):
        self.nextPutAll('\n')

    @pystSelector('print:')
    def print(self, object):
        self.nextPutAll(str(object))

class Stdio(PystObject):
    stdout = FileStream(sys.stdout)

class ASGEnvironment(ABC):
    @abstractmethod
    def getTopLevelTargetEnvironment(self):
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
        self.capturedValues = []
        self.captureBindings = []
        self.symbolTable = {}
        self.capturedSymbolTable = {}
        self.capturedValueTable = {}

    def addArgumentBinding(self, argument: ASGArgumentNode):
        self.arguments.append(argument)
        if argument.name is not None:
            self.symbolTable[argument.name] = [argument] + self.symbolTable.get(argument.name, [])

    def getValidCaptureBindingFor(self, capturedValue):
        if capturedValue in self.capturedValueTable:
            return self.capturedValueTable[capturedValue]
        
        binding = ASGCapturedValueNode(capturedValue.sourceDerivation, len(self.capturedValues))
        self.capturedValues.append(capturedValue)
        self.captureBindings.append(binding)
        self.capturedValueTable[capturedValue] = binding
        return binding

    def lookSymbolBindingRecursively(self, symbol: str):
        if symbol in self.symbolTable:
            return self.symbolTable[symbol][0]
        
        if symbol in self.capturedSymbolTable:
            return self.capturedSymbolTable[symbol]

        parentBinding = self.parent.lookSymbolBindingRecursively(symbol)
        if parentBinding is None:
            return None
        
        if parentBinding.isBetaReplaceableNode():
            captureBinding = self.getValidCaptureBindingFor(parentBinding)
            self.capturedSymbolTable[symbol] = captureBinding
            return captureBinding
        
        return parentBinding

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
