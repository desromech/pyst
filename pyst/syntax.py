from .mop import *
from .parsetree import *

class ASGSyntaxNode(ASGNode):
    sourceDerivation = ASGNodeSourceDerivationAttribute()

    def isSyntaxNode(self) -> bool:
        return True

    def isPureDataNode(self) -> bool:
        return True

    def asASGNodeDerivation(self):
        return self.sourceDerivation

class ASGSyntaxErrorNode(ASGSyntaxNode):
    message = ASGNodeDataAttribute(int)
    innerNodes = ASGNodeDataInputPorts()

class ASGSyntaxArgumentNode(ASGSyntaxNode):
    name = ASGNodeDataAttribute(str)

class ASGSyntaxArrayNode(ASGSyntaxNode):
    elements = ASGNodeDataInputPorts()

class ASGSyntaxBlockNode(ASGSyntaxNode):
    arguments = ASGNodeDataInputPorts()
    body = ASGNodeDataInputPort()

class ASGSyntaxCascadeMessageNode(ASGSyntaxNode):
    selector = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

class ASGSyntaxLexicalSequenceNode(ASGSyntaxNode):
    locals = ASGNodeDataInputPorts()
    pragmas = ASGNodeDataInputPorts()
    elements = ASGNodeDataInputPorts()

class ASGSyntaxLocalVariableNode(ASGSyntaxNode):
    name = ASGNodeDataAttribute(str)

class ASGSyntaxLiteralNode(ASGSyntaxNode):
    pass

class ASGSyntaxLiteralCharacterNode(ASGSyntaxLiteralNode):
    value = ASGNodeDataAttribute(int)

class ASGSyntaxLiteralIntegerNode(ASGSyntaxLiteralNode):
    value = ASGNodeDataAttribute(int)

class ASGSyntaxLiteralFloatNode(ASGSyntaxLiteralNode):
    value = ASGNodeDataAttribute(float)

class ASGSyntaxLiteralStringNode(ASGSyntaxLiteralNode):
    value = ASGNodeDataAttribute(str)

class ASGSyntaxLiteralSymbolNode(ASGSyntaxLiteralNode):
    value = ASGNodeDataAttribute(str)

class ASGSyntaxApplicationNode(ASGSyntaxNode):
    functional = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

class ASGSyntaxAssignmentNode(ASGSyntaxNode):
    store = ASGNodeDataInputPort()
    value = ASGNodeDataInputPort()

class ASGSyntaxBinaryExpressionSequenceNode(ASGSyntaxNode):
    elements = ASGNodeDataInputPorts()

class ASGSyntaxIdentifierReferenceNode(ASGSyntaxNode):
    value = ASGNodeDataAttribute(str)

class ASGSyntaxPragmaNode(ASGSyntaxNode):
    selector = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

class ASGSyntaxMessageSendNode(ASGSyntaxNode):
    receiver = ASGNodeOptionalDataInputPort()
    selector = ASGNodeDataInputPort()
    arguments = ASGNodeDataInputPorts()

class ASGSyntaxMessageCascadeNode(ASGSyntaxNode):
    receiver = ASGNodeDataInputPort()
    messages = ASGNodeDataInputPorts()

class ASGSyntaxDictionaryNode(ASGSyntaxNode):
    elements = ASGNodeDataInputPorts()

class ASGSyntaxSequenceNode(ASGSyntaxNode):
    elements = ASGNodeDataInputPorts()

class ASGParseTreeFrontEnd(ParseTreeVisitor):

    def visitErrorNode(self, node: ParseTreeErrorNode):
        return ASGSyntaxErrorNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.message, self.transformNodes(node.innerNodes))

    def visitApplicationNode(self, node: ParseTreeApplicationNode):
        return ASGSyntaxApplicationNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitNode(node.functional), self.transformNodes(node.arguments))

    def visitArrayNode(self, node: ParseTreeArrayNode):
        return ASGSyntaxSequenceNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.transformNodes(node.elements))

    def visitAssignmentNode(self, node: ParseTreeAssignmentNode):
        return ASGSyntaxAssignmentNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitNode(node.store), self.visitNode(node.value))

    def visitArgumentNode(self, node: ParseTreeArgumentNode):
        return ASGSyntaxArgumentNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.name)

    def visitBinaryExpressionSequenceNode(self, node: ParseTreeBinaryExpressionSequenceNode):
        return ASGSyntaxBinaryExpressionSequenceNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.transformNodes(node.elements))

    def visitBlockNode(self, node: ParseTreeBlockNode):
        return ASGSyntaxBlockNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitNode(node.arguments), self.visitNode(node.body))

    def visitCascadeMessageNode(self, node: ParseTreeCascadeMessageNode):
        return ASGSyntaxCascadeMessageNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitNode(node.selector), self.transformNodes(node.arguments))

    def visitIdentifierReferenceNode(self, node: ParseTreeIdentifierReferenceNode):
        return ASGSyntaxIdentifierReferenceNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.value)

    def visitLexicalSequenceNode(self, node: ParseTreeLexicalSequenceNode):
        return ASGSyntaxLexicalSequenceNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.transformNodes(node.locals), self.transformNodes(node.pragmas), self.transformNodes(node.elements))

    def visitLocalVariableNode(self, node: ParseTreeLocalVariableNode):
        return ASGSyntaxLocalVariableNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.name)

    def visitLiteralCharacterNode(self, node: ParseTreeLiteralCharacterNode):
        return ASGSyntaxLiteralCharacterNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.value)

    def visitLiteralFloatNode(self, node: ParseTreeLiteralFloatNode):
        return ASGSyntaxLiteralFloatNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.value)

    def visitLiteralIntegerNode(self, node: ParseTreeLiteralIntegerNode):
        return ASGSyntaxLiteralIntegerNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.value)

    def visitLiteralSymbolNode(self, node: ParseTreeLiteralSymbolNode):
        return ASGSyntaxLiteralSymbolNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.value)

    def visitLiteralStringNode(self, node: ParseTreeLiteralStringNode):
        return ASGSyntaxLiteralStringNode(ASGNodeSourceCodeDerivation(node.sourcePosition), node.value)

    def visitMessageSendNode(self, node: ParseTreeMessageSendNode):
        return ASGSyntaxMessageSendNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitOptionalNode(node.receiver), self.visitNode(node.selector), self.transformNodes(node.arguments))

    def visitMessageCascadeNode(self, node: ParseTreeMessageSendNode):
        return ASGSyntaxMessageCascadeNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitNode(node.receiver), self.transformNodes(node.messages))

    def visitPragmaNode(self, node: ParseTreePragmaNode):
        return ASGSyntaxPragmaNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.visitNode(node.selector), self.transformNodes(node.arguments))

    def visitSequenceNode(self, node: ParseTreeSequenceNode):
        return ASGSyntaxSequenceNode(ASGNodeSourceCodeDerivation(node.sourcePosition), self.transformNodes(node.elements))
