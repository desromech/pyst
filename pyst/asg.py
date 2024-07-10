from .mop import *
from .syntax import *

class ASGAnalyzedNode(ASGNode):
    sourceDerivation = ASGNodeSourceDerivationAttribute()

    def asASGNodeDerivation(self):
        return self.sourceDerivation

class ASGSequencingNode(ASGAnalyzedNode):
    def isPureDataNode(self) -> bool:
        return False

    def isSequencingNode(self) -> bool:
        return True
    
class ASGSequenceEntryNode(ASGSequencingNode):
    def isBasicBlockStart(self) -> bool:
        return True
    
    def isSequenceEntryNode(self) -> bool:
        return True
    
    def interpretInContext(self, context, parameterList):
        pass

class ASGSequenceDivergenceNode(ASGSequencingNode):
    predecessor = ASGSequencingPredecessorAttribute()

    def directImmediateDominator(self):
        return self.predecessor

class ASGConditionalBranchNode(ASGSequenceDivergenceNode):
    condition = ASGNodeDataInputPort()
    trueDestination = ASGSequencingDestinationPort()
    falseDestination = ASGSequencingDestinationPort()

    def getRegionOfUsedValue(self, usedValue):
        return self.predecessor

    def divergenceDestinations(self):
        yield self.trueDestination
        yield self.falseDestination

class ASGSequenceBranchEndNode(ASGSequencingNode):
    predecessor = ASGSequencingPredecessorAttribute()
    divergence = ASGSequencingPredecessorAttribute()

    def getRegionOfUsedValue(self, usedValue):
        return self.predecessor

    def isBasicBlockEnd(self) -> bool:
        return True

    def directImmediateDominator(self):
        return self.predecessor
    
class ASGSequenceConvergenceNode(ASGSequencingNode):
    divergence = ASGSequencingPredecessorAttribute()
    predecessors = ASGSequencingPredecessorsAttribute()

    def isBasicBlockStart(self) -> bool:
        return True

    def isSequenceConvergenceNode(self) -> bool:
        return True

    def directImmediateDominator(self):
        return self.divergence

class ASGSequenceReturnNode(ASGSequencingNode):
    value = ASGNodeDataInputPort()
    predecessor = ASGSequencingPredecessorAttribute()

    def isSequenceReturnNode(self) -> bool:
        return True

    def directImmediateDominator(self):
        return self.predecessor

    def getRegionOfUsedValue(self, usedValue):
        return self
    
    def interpretInContext(self, context, parameters):
        context.returnValue(context[parameters[0]])

class ASGAnalyzedDataExpressionNode(ASGAnalyzedNode):
    def isPureDataNode(self) -> bool:
        return True

class ASGAnalyzedStatefullExpressionNode(ASGAnalyzedNode):
    def isPureDataNode(self) -> bool:
        return False
    
    def isStatefullDataNode(self) -> bool:
        return True

class ASGSequencingAndDataNode(ASGAnalyzedNode):
    predecessor = ASGSequencingPredecessorAttribute()

    def isPureDataNode(self) -> bool:
        return False

    def isSequencingNode(self) -> bool:
        return True

    def directImmediateDominator(self):
        return self.predecessor

    def getRegionOfUsedValue(self, usedValue):
        return self.predecessor
    
class ASGErrorNode(ASGAnalyzedDataExpressionNode):
    message = ASGNodeDataAttribute(str)
    innerNodes = ASGNodeDataInputPorts()

    def prettyPrintError(self) -> str:
        return '%s: %s' % (str(self.sourceDerivation.getSourcePosition()), self.message)

class ASGLiteralNode(ASGAnalyzedDataExpressionNode):
    def isLiteralNode(self) -> bool:
        return True
    
    def isConstantDataNode(self) -> bool:
        return True
    
class ASGLiteralCharacterNode(ASGLiteralNode):
    value = ASGNodeDataAttribute(int)

class ASGLiteralIntegerNode(ASGLiteralNode):
    value = ASGNodeDataAttribute(int)

class ASGLiteralFloatNode(ASGLiteralNode):
    value = ASGNodeDataAttribute(float)

class ASGLiteralSymbolNode(ASGLiteralNode):
    value = ASGNodeDataAttribute(str)

    def isLiteralSymbolNode(self) -> bool:
        return True

class ASGLiteralStringNode(ASGLiteralNode):
    value = ASGNodeDataAttribute(str)

class ASGLiteralObjectNode(ASGLiteralNode):
    value = ASGNodeDataAttribute(object)

class ASGLiteralNilNode(ASGLiteralNode):
    pass

class ASGLiteralFalseNode(ASGLiteralNode):
    pass

class ASGLiteralTrueNode(ASGLiteralNode):
    pass

class ASGLiteralPrimitiveFunctionNode(ASGLiteralNode):
    name = ASGNodeDataAttribute(str)
    compileTimeImplementation = ASGNodeDataAttribute(object, default = None, notCompared = True, notPrinted = True)

    pure = ASGNodeDataAttribute(bool, default = False)
    compileTime = ASGNodeDataAttribute(bool, default = False)
    alwaysInline = ASGNodeDataAttribute(bool, default = False)

    def isLiteralPrimitiveFunction(self) -> bool:
        return True

    def isPureCompileTimePrimitive(self) -> bool:
        return self.pure and self.compileTime

    def isAlwaysReducedPrimitive(self) -> bool:
        return self.alwaysInline

    def reduceApplicationWithAlgorithm(self, node, algorithm):
        arguments = list(map(algorithm, node.arguments))
        return self.compileTimeImplementation(ASGNodeReductionDerivation(algorithm, node), node.type, *arguments)

class ASGBetaReplaceableNode(ASGAnalyzedDataExpressionNode):
    def isBetaReplaceableNode(self) -> bool:
        return True

class ASGArgumentNode(ASGBetaReplaceableNode):
    index = ASGNodeDataAttribute(int, default = 0)
    name = ASGNodeDataAttribute(str, default = None, notCompared = True)
    isImplicit = ASGNodeDataAttribute(bool, default = False)

    def isArgumentNode(self) -> bool:
        return True

    def isActivationContextParameterDataNode(self):
        return True

class ASGCapturedValueNode(ASGBetaReplaceableNode):
    def isCapturedValueNode(self) -> bool:
        return True

    def isActivationContextParameterDataNode(self):
        return True

class ASGArrayNode(ASGAnalyzedDataExpressionNode):
    elements = ASGNodeDataInputPorts()

class ASGBlockNode(ASGAnalyzedDataExpressionNode):
    arguments = ASGNodeDataInputPorts(notInterpreted = True)
    entryPoint = ASGSequencingDestinationPort(notInterpreted = True)
    exitPoint = ASGSequencingPredecessorAttribute(notInterpreted = True)
    name = ASGNodeDataAttribute(str, default = None, notCompared = True)

    def scheduledDataDependencies(self):
        return ()

    def isConstantDataNode(self) -> bool:
        return self.type.isConstantDataNode()

    def isBlock(self) -> bool:
        return True

class ASGApplicationNode(ASGAnalyzedDataExpressionNode):
    functional = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

    def isLiteralPureCompileTimePrimitiveApplication(self):
        return self.functional.isPureCompileTimePrimitive() and all(argument.isLiteralNode() for argument in self.arguments)

    def isLiteralAlwaysReducedPrimitiveApplication(self):
        return self.functional.isAlwaysReducedPrimitive()

class ASGFxApplicationNode(ASGSequencingAndDataNode):
    functional = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()
    
    def interpretInContext(self, context, parameters):
        functional = context[parameters[0]]
        arguments = list(map(lambda x: context[x], parameters[1:]))
        return functional(*arguments)

class ASGMessageSendNode(ASGAnalyzedDataExpressionNode):
    receiver = ASGNodeDataInputPort()
    selector = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

class ASGFxMessageSendNode(ASGSequencingAndDataNode):
    receiver = ASGNodeDataInputPort()
    selector = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

class ASGMutableArrayNode(ASGAnalyzedStatefullExpressionNode):
    elements = ASGNodeDataInputPorts()

class ASGTopLevelScriptNode(ASGAnalyzedDataExpressionNode):
    entryPoint = ASGSequencingDestinationPort()
    exitPoint = ASGSequencingPredecessorAttribute()

class ASGPhiValueNode(ASGAnalyzedDataExpressionNode):
    value = ASGNodeDataInputPort()
    predecessor = ASGSequencingPredecessorAttribute()

    def isPhiValueNode(self) -> bool:
        return True

class ASGPhiNode(ASGAnalyzedDataExpressionNode):
    values = ASGNodeDataInputPorts()
    predecessor = ASGSequencingPredecessorAttribute()

    def isPhiNode(self) -> bool:
        return True
