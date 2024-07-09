from abc import ABC, abstractmethod

import os.path
import sys

class SourceCode:
    def __init__(self, directory: str | None, name: str, language: str, text: bytes) -> None:
        self.directory = directory
        self.name = name
        self.language = language
        self.text = text

    def __str__(self) -> str:
        if self.directory is None:
            return self.name
        return os.path.join(self.directory, self.name)

class SourcePosition:
    def __init__(self, sourceCode: SourceCode, startIndex: int, endIndex: int, startLine: int, startColumn: int, endLine: int, endColumn: int) -> None:
        self.sourceCode = sourceCode
        self.startIndex = startIndex
        self.endIndex = endIndex
        self.startLine = startLine
        self.startColumn = startColumn
        self.endLine = endLine
        self.endColumn = endColumn

    def getValue(self) -> bytes:
        return self.sourceCode.text[self.startIndex : self.endIndex]
    
    def getStringValue(self) -> str:
        return self.getValue().decode('utf-8')
    
    def until(self, endSourcePosition):
        return SourcePosition(self.sourceCode,
                self.startIndex, endSourcePosition.startIndex,
                self.startLine, self.startColumn,
                endSourcePosition.startLine, endSourcePosition.startColumn)

    def to(self, endSourcePosition):
        return SourcePosition(self.sourceCode,
                self.startIndex, endSourcePosition.endIndex,
                self.startLine, self.startColumn,
                endSourcePosition.endLine, endSourcePosition.endColumn)

    def __str__(self) -> str:
        return '%s:%d.%d-%d.%d' % (self.sourceCode, self.startLine, self.startColumn, self.endLine, self.endColumn)

class EmptySourcePosition:
    Singleton = None

    @classmethod
    def getSingleton(cls):
        if cls.Singleton is None:
            cls.Singleton = cls()
        return cls.Singleton

    def __str__(self) -> str:
        return '<no position>'


class ParseTreeVisitor(ABC):
    def visitNode(self, node):
        return node.accept(self)

    def visitOptionalNode(self, node):
        if node is not None:
            return self.visitNode(node)
        return None

    def visitNodes(self, nodes):
        for node in nodes:
            self.visitNode(node)

    def transformNodes(self, nodes):
        transformed = []
        for node in nodes:
            transformed.append(self.visitNode(node))
        return transformed

    @abstractmethod
    def visitErrorNode(self, node):
        pass

    @abstractmethod
    def visitAssignmentNode(self, node):
        pass

    @abstractmethod
    def visitCascadeMessageNode(self, node):
        pass

    @abstractmethod
    def visitIdentifierReferenceNode(self, node):
        pass

    @abstractmethod
    def visitLiteralCharacterNode(self, node):
        pass

    @abstractmethod
    def visitLiteralFloatNode(self, node):
        pass

    @abstractmethod
    def visitLiteralIntegerNode(self, node):
        pass

    @abstractmethod
    def visitLiteralSymbolNode(self, node):
        pass

    @abstractmethod
    def visitLiteralStringNode(self, node):
        pass

    @abstractmethod
    def visitMessageCascadeNode(self, node):
        pass

    @abstractmethod
    def visitMessageSendNode(self, node):
        pass

    @abstractmethod
    def visitSequenceNode(self, node):
        pass

class ParseTreeNode(ABC):
    def __init__(self, sourcePosition: SourcePosition) -> None:
        self.sourcePosition = sourcePosition

    @abstractmethod
    def accept(self, visitor: ParseTreeVisitor):
        pass

    def asMessageSendCascadeReceiverAndFirstMessage(self):
        return self, None

    def isAssignmentNode(self) -> bool:
        return False

    def isBinaryExpressionSequenceNode(self) -> bool:
        return False

    def isCascadeMessageNode(self) -> bool:
        return False

    def isErrorNode(self) -> bool:
        return False

    def isIdentifierReferenceNode(self) -> bool:
        return False

    def isLiteralNode(self) -> bool:
        return False

    def isLiteralCharacterNode(self) -> bool:
        return False

    def isLiteralFloatNode(self) -> bool:
        return False

    def isLiteralIntegerNode(self) -> bool:
        return False

    def isLiteralSymbolNode(self) -> bool:
        return False

    def isLiteralStringNode(self) -> bool:
        return False

    def isMessageCascadeNode(self) -> bool:
        return False

    def isMessageSendNode(self) -> bool:
        return False

    def isSequenceNode(self) -> bool:
        return False

class ParseTreeErrorNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, message: str, innerNodes: list[ParseTreeNode] = []) -> None:
        super().__init__(sourcePosition)
        self.message = message
        self.innerNodes = innerNodes
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitErrorNode(self)

    def isErrorNode(self) -> bool:
        return True

class ParseTreeApplicationNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, functional: ParseTreeNode, arguments: list[ParseTreeNode]) -> None:
        super().__init__(sourcePosition)
        self.functional = functional
        self.arguments = arguments
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitApplicationNode(self)

    def isApplicationNode(self) -> bool:
        return True
    
class ParseTreeAssignmentNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, variable: ParseTreeNode, value: ParseTreeNode) -> None:
        super().__init__(sourcePosition)
        self.variable = variable
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitAssignmentNode(self)

    def isAssignmentNode(self) -> bool:
        return True
    
class ParseTreeBinaryExpressionSequenceNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, elements: list[ParseTreeNode]) -> None:
        super().__init__(sourcePosition)
        self.elements = elements
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitBinaryExpressionSequenceNode(self)

    def isBinaryExpressionSequenceNode(self) -> bool:
        return True

    def asMessageSendCascadeReceiverAndFirstMessage(self):
        assert len(self.elements) >= 3
        if len(self.elements) == 3:
            return self.elements[0], ParseTreeCascadeMessageNode(self.sourcePosition, self.elements[1], [self.elements[2]])
        
        receiverSequence = ParseTreeBinaryExpressionSequenceNode(self.sourcePosition, self.elements[:-2])
        return receiverSequence, ParseTreeCascadeMessageNode(self.sourcePosition, self.elements[-2], [self.elements[-1]])

class ParseTreeMessageCascadeNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, receiver: ParseTreeNode, messages: list[ParseTreeNode]) -> None:
        super().__init__(sourcePosition)
        self.receiver = receiver
        self.messages = messages
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitMessageCascadeNode(self)

    def isMessageCascadeNode(self) -> bool:
        return True
    
class ParseTreeCascadeMessageNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, selector: ParseTreeNode, arguments: list[ParseTreeNode]) -> None:
        super().__init__(sourcePosition)
        self.selector = selector
        self.arguments = arguments
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitCascadeMessageNode(self)

    def isCascadeMessageNode(self) -> bool:
        return True
    
class ParseTreeIdentifierReferenceNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, value: str) -> None:
        super().__init__(sourcePosition)
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitIdentifierReferenceNode(self)

    def isIdentifierReferenceNode(self) -> bool:
        return True

class ParseTreeLiteralNode(ParseTreeNode):
    def isLiteralNode(self) -> bool:
        return True

class ParseTreeLiteralCharacterNode(ParseTreeLiteralNode):
    def __init__(self, sourcePosition: SourcePosition, value: int) -> None:
        super().__init__(sourcePosition)
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitLiteralCharacterNode(self)

    def isLiteralCharacterNode(self) -> bool:
        return True

class ParseTreeLiteralFloatNode(ParseTreeLiteralNode):
    def __init__(self, sourcePosition: SourcePosition, value: float) -> None:
        super().__init__(sourcePosition)
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitLiteralFloatNode(self)

    def isLiteralFloatNode(self) -> bool:
        return True

class ParseTreeLiteralIntegerNode(ParseTreeLiteralNode):
    def __init__(self, sourcePosition: SourcePosition, value: int) -> None:
        super().__init__(sourcePosition)
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitLiteralIntegerNode(self)

    def isLiteralIntegerNode(self) -> bool:
        return True

class ParseTreeLiteralStringNode(ParseTreeLiteralNode):
    def __init__(self, sourcePosition: SourcePosition, value: str) -> None:
        super().__init__(sourcePosition)
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitLiteralStringNode(self)    

    def isLiteralStringNode(self) -> bool:
        return True

class ParseTreeLiteralSymbolNode(ParseTreeLiteralNode):
    def __init__(self, sourcePosition: SourcePosition, value: str) -> None:
        super().__init__(sourcePosition)
        self.value = value
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitLiteralSymbolNode(self)

    def isLiteralSymbolNode(self) -> bool:
        return True

class ParseTreeMessageSendNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, receiver: ParseTreeNode, selector: ParseTreeNode, arguments: list[ParseTreeNode]) -> None:
        super().__init__(sourcePosition)
        self.receiver = receiver
        self.selector = selector
        self.arguments = arguments
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitMessageSendNode(self)    

    def asMessageSendCascadeReceiverAndFirstMessage(self):
        return self.receiver, ParseTreeCascadeMessageNode(self.sourcePosition, self.selector, self.arguments)

    def isMessageSendNode(self) -> bool:
        return True

class ParseTreeSequenceNode(ParseTreeNode):
    def __init__(self, sourcePosition: SourcePosition, elements: list[ParseTreeNode]) -> None:
        super().__init__(sourcePosition)
        self.elements = elements
    
    def accept(self, visitor: ParseTreeVisitor):
        return visitor.visitSequenceNode(self)

    def isSequenceNode(self) -> bool:
        return True

class ParseTreeSequentialVisitor(ParseTreeVisitor):
    def visitErrorNode(self, node: ParseTreeErrorNode):
        self.visitNodes(node.innerNodes)

    def visitApplicationNode(self, node: ParseTreeMessageSendNode):
        self.visitNode(node.functional)
        self.visitNodes(node.arguments)

    def visitAssignmentNode(self, node: ParseTreeAssignmentNode):
        self.visitNode(node.variable)
        self.visitNode(node.value)

    def visitBinaryExpressionSequenceNode(self, node: ParseTreeBinaryExpressionSequenceNode):
        self.visitNodes(node.elements)

    def visitCascadeMessageNode(self, node: ParseTreeCascadeMessageNode):
        self.visitNode(node.selector)
        self.visitNodes(node.arguments)

    def visitIdentifierReferenceNode(self, node: ParseTreeIdentifierReferenceNode):
        pass

    def visitLiteralNode(self, node: ParseTreeLiteralNode):
        pass

    def visitLiteralCharacterNode(self, node: ParseTreeLiteralCharacterNode):
        self.visitLiteralNode(node)

    def visitLiteralFloatNode(self, node: ParseTreeLiteralFloatNode):
        self.visitLiteralNode(node)

    def visitLiteralIntegerNode(self, node: ParseTreeLiteralIntegerNode):
        self.visitLiteralNode(node)

    def visitLiteralSymbolNode(self, node: ParseTreeLiteralSymbolNode):
        self.visitLiteralNode(node)

    def visitLiteralStringNode(self, node: ParseTreeLiteralStringNode):
        self.visitLiteralNode(node)

    def visitMessageSendNode(self, node: ParseTreeMessageSendNode):
        self.visitOptionalNode(node.receiver)
        self.visitNode(node.selector)
        self.visitNodes(node.arguments)

    def visitMessageCascadeNode(self, node: ParseTreeMessageCascadeNode):
        self.visitOptionalNode(node.receiver)
        self.visitNodes(node.messages)

    def visitSequenceNode(self, node: ParseTreeSequenceNode):
        self.visitNodes(node.elements)

class ParseTreeErrorVisitor(ParseTreeSequentialVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.errorNodes: list[ParseTreeErrorNode] = []
    
    def visitErrorNode(self, node: ParseTreeErrorNode):
        self.errorNodes.append(node)
        super().visitErrorNode(node)

    def checkAndPrintErrors(self, node: ParseTreeNode):
        self.visitNode(node)
        for errorNode in self.errorNodes:
            sys.stderr.write('%s: %s\n' % (str(errorNode.sourcePosition), errorNode.message))
        return len(self.errorNodes) == 0
    