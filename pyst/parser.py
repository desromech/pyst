from .scanner import Token, TokenKind, scanFileNamed, scanSourceString
from .parsetree import *
import copy

class ParserState:
    def __init__(self, sourceCode: SourceCode, tokens: list[Token]) -> None:
        self.sourceCode = sourceCode
        self.tokens = tokens
        self.position = 0

    def atEnd(self) -> bool:
        return self.position >= len(self.tokens) or self.peekKind() == TokenKind.END_OF_SOURCE

    def peekKind(self, offset: int = 0) -> TokenKind:
        peekPosition = self.position + offset
        if peekPosition < len(self.tokens):
            return self.tokens[peekPosition].kind
        else:
            return TokenKind.END_OF_SOURCE

    def peek(self, offset: int = 0) -> Token:
        peekPosition = self.position + offset
        if peekPosition < len(self.tokens):
            return self.tokens[peekPosition]
        else:
            return None
        
    def advance(self) -> None:
        assert self.position < len(self.tokens)
        self.position += 1

    def next(self) -> Token:
        token = self.tokens[self.position]
        self.position += 1
        return token

    def expectAddingErrorToNode(self, expectedKind: TokenKind, node: ParseTreeNode) -> ParseTreeNode:
        if self.peekKind() == expectedKind:
            self.advance()
            return node
        
        errorPosition = self.currentSourcePosition()
        errorNode = ParseTreeErrorNode(errorPosition, "Expected token of kind %s." % str(expectedKind))
        return ParseTreeSequenceNode(node.sourcePosition.to(errorPosition), [node, errorNode])

    def currentSourcePosition(self) -> SourcePosition:
        if self.position < len(self.tokens):
            return self.tokens[self.position].sourcePosition

        assert self.tokens[-1].kind == TokenKind.END_OF_SOURCE 
        return self.tokens[-1].sourcePosition

    def previousSourcePosition(self) -> SourcePosition:
        assert self.position > 0
        return self.tokens[self.position - 1].sourcePosition

    def sourcePositionFrom(self, startingPosition: int) -> SourcePosition:
        assert startingPosition < len(self.tokens)
        startSourcePosition = self.tokens[startingPosition].sourcePosition
        if self.position > 0:
            endSourcePosition = self.previousSourcePosition()
            return startSourcePosition.to(endSourcePosition)
        else:
            endSourcePosition = self.currentSourcePosition()
            return startSourcePosition.until(endSourcePosition)
    
    def advanceWithExpectedError(self, message: str):
        if self.peekKind() == TokenKind.ERROR:
            errorToken = self.next()
            return self, ParseTreeErrorNode(errorToken.sourcePosition, errorToken.errorMessage)
        elif self.atEnd():
            return self, ParseTreeErrorNode(self.currentSourcePosition(), message)
        else:
            errorPosition = self.currentSourcePosition()
            self.advance()
            return self, ParseTreeErrorNode(errorPosition, message, [])

def parseEscapedString(string: str) -> str:
    unescaped = ''
    i = 0
    stringLength = len(string)
    while i < len(string):
        c = string[i]
        if c == "'" and i + 1 < stringLength and string[i + 1] == "'":
            i += 1
        unescaped += c
        i += 1
    return unescaped

def parseIntegerConstant(string: str) -> str:
    if b'r' in string:
        radixIndex = string.index(b'r')
    elif b'R' in string:
        radixIndex = string.index(b'R')
    else:
        return int(string)
    
    radix = int(string[0:radixIndex])
    radixedInteger = int(string[radixIndex + 1:], abs(radix))
    if radix < 0:
        return -radixedInteger
    else:
        return radixedInteger

def parseLiteralInteger(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.INTEGER
    return state, ParseTreeLiteralIntegerNode(token.sourcePosition, parseIntegerConstant(token.getValue()))

def parseLiteralFloat(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.FLOAT
    return state, ParseTreeLiteralFloatNode(token.sourcePosition, float(token.getValue()))

def parseLiteralString(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.STRING
    return state, ParseTreeLiteralStringNode(token.sourcePosition, parseEscapedString(token.getStringValue()[1:-1]))

def parseLiteralCharacter(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.CHARACTER
    return state, ParseTreeLiteralCharacterNode(token.sourcePosition, ord(token.getStringValue()[1]))

def parseLiteralSymbol(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.SYMBOL
    symbolValue = token.getStringValue()[1:]
    if symbolValue[0] == "'":
        assert symbolValue[0] == "'" and symbolValue[-1] == "'"
        symbolValue = parseEscapedString(symbolValue[1:-1])
    return state, ParseTreeLiteralSymbolNode(token.sourcePosition, symbolValue)

def parseLiteral(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    if   state.peekKind() == TokenKind.INTEGER: return parseLiteralInteger(state)
    elif state.peekKind() == TokenKind.FLOAT: return parseLiteralFloat(state)
    elif state.peekKind() == TokenKind.STRING: return parseLiteralString(state)
    elif state.peekKind() == TokenKind.CHARACTER: return parseLiteralCharacter(state)
    elif state.peekKind() == TokenKind.SYMBOL: return parseLiteralSymbol(state)
    else: return state.advanceWithExpectedError("Literal")

def parseIdentifier(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.IDENTIFIER
    return state, ParseTreeIdentifierReferenceNode(token.sourcePosition, token.getStringValue())

def parseLiteralArrayIdentifier(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    assert token.kind == TokenKind.IDENTIFIER
    tokenValue = token.getStringValue()
    if tokenValue in ['nil', 'false', 'true']:
        return state, ParseTreeIdentifierReferenceNode(token.sourcePosition, tokenValue)
    else:
        return state, ParseTreeLiteralSymbolNode(token.sourcePosition, tokenValue)

def parseTokenAsSymbol(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    token = state.next()
    return state, ParseTreeLiteralSymbolNode(token.sourcePosition, token.getStringValue())

def parseTerm(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    if state.peekKind() == TokenKind.IDENTIFIER: return parseIdentifier(state)
    elif state.peekKind() == TokenKind.LEFT_PARENT: return parseParenthesis(state)
    elif state.peekKind() == TokenKind.LEFT_BRACKET: return parseBlock(state)
    elif state.peekKind() == TokenKind.LEFT_CURLY_BRACKET: return parseArray(state)
    elif state.peekKind() == TokenKind.LITERAL_ARRAY_START: return parseLiteralArray(state)
    elif state.peekKind() == TokenKind.CARET: return parseReturn(state)
    else: return parseLiteral(state)

def parseLiteralArrayElement(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    if state.peekKind() == TokenKind.IDENTIFIER: return parseLiteralArrayIdentifier(state)
    elif state.peekKind() == TokenKind.LEFT_PARENT: return parseLiteralArray(state)
    elif state.peekKind() == TokenKind.LITERAL_ARRAY_START: return parseLiteralArray(state)
    elif state.peekKind() in [
        TokenKind.LEFT_BRACKET, TokenKind.RIGHT_BRACKET,
        TokenKind.LEFT_CURLY_BRACKET, TokenKind.RIGHT_CURLY_BRACKET,
        TokenKind.LESS_THAN, TokenKind.GREATER_THAN, 
        TokenKind.COLON, TokenKind.BAR,
        TokenKind.CARET, 
        TokenKind.ASSIGNMENT, TokenKind.SEMICOLON, TokenKind.DOT, TokenKind.COMMA,
        TokenKind.QUOTE, TokenKind.QUASI_QUOTE, TokenKind.QUASI_UNQUOTE, TokenKind.SPLICE,
    ]: return parseTokenAsSymbol(state)
    else: return parseLiteral(state)

def parseParenthesis(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    # (
    startPosition = state.position
    assert state.peekKind() == TokenKind.LEFT_PARENT
    state.advance()

    if isBinaryExpressionOperator(state.peekKind()) and state.peekKind(1) == TokenKind.RIGHT_PARENT:
        token = state.next()
        state.advance()
        return state, ParseTreeIdentifierReferenceNode(token.sourcePosition, token.getStringValue())

    state, expression = parseSequenceUntilEndOrDelimiter(state, TokenKind.RIGHT_PARENT)

    # )
    expression = state.expectAddingErrorToNode(TokenKind.RIGHT_PARENT, expression)
    return state, expression

def parseArray(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    # {
    startPosition = state.position
    assert state.peekKind() == TokenKind.LEFT_CURLY_BRACKET
    state.advance()

    state, elements = parseExpressionListUntilEndOrDelimiter(state, TokenKind.RIGHT_CURLY_BRACKET)

    # }
    if state.peekKind() == TokenKind.RIGHT_CURLY_BRACKET:
        state.advance()
    else:
        elements.append(ParseTreeErrorNode(state.currentSourcePosition(), "Expected right parenthesis."))

    return state, ParseTreeArrayNode(state.sourcePositionFrom(startPosition), elements)

def parseLiteralArray(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    # #( | ()
    startPosition = state.position
    assert state.peekKind() == TokenKind.LITERAL_ARRAY_START or state.peekKind() == TokenKind.LEFT_PARENT
    state.advance()

    elements = []
    while not state.atEnd() and state.peekKind() != TokenKind.RIGHT_PARENT:
        state, element = parseLiteralArrayElement(state)
        elements.append(element)

    # )
    if state.peekKind() == TokenKind.RIGHT_PARENT:
        state.advance()
    else:
        elements.append(ParseTreeErrorNode(state.currentSourcePosition(), "Expected right parenthesis."))

    return state, ParseTreeLiteralArrayNode(state.sourcePositionFrom(startPosition), elements)

def parseReturn(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    # ^
    startPosition = state.position
    assert state.peekKind() == TokenKind.CARET
    state.advance()

    state, expression = parseExpression(state)
    return state, ParseTreeReturnNode(state.sourcePositionFrom(startPosition), expression)

def parseLocalVariable(state: ParserState) -> tuple[ParserState, list[ParseTreeNode]]:
    if state.peekKind() == TokenKind.IDENTIFIER:
        sourcePosition = state.currentSourcePosition()
        token = state.next()
        return state, ParseTreeLocalVariableNode(sourcePosition, token.getStringValue())
    else: return state.advanceWithExpectedError("Local variable")

def parseLocalVariables(state: ParserState) -> tuple[ParserState, list[ParseTreeNode]]:
    # |
    assert state.peekKind() == TokenKind.BAR
    state.advance()

    locals = []
    while not state.atEnd() and state.peekKind() != TokenKind.BAR:
        state, local = parseLocalVariable(state)
        locals.append(local)

    # |
    if state.peekKind() == TokenKind.BAR:
        state.advance()
    else:
        locals.append(ParseTreeErrorNode(state.currentSourcePosition(), 'Expected a bar after the local variable declarations.'))
    return state, locals

def parseArgument(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    assert state.peekKind() == TokenKind.COLON
    state.advance()
    if state.peekKind() == TokenKind.IDENTIFIER:
        nameToken = state.next()
        return state, ParseTreeArgumentNode(state.sourcePositionFrom(startPosition), nameToken.getStringValue())
    else:
        return state, ParseTreeErrorNode(state.currentSourcePosition(), 'Expected an argument name.')

def parseBlock(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    # {
    startPosition = state.position
    assert state.peekKind() == TokenKind.LEFT_BRACKET
    state.advance()

    arguments = []
    while state.peekKind() == TokenKind.COLON:
        state, argument = parseArgument(state)
        arguments.append(argument)

    hasBar = False
    if len(arguments) != 0 and state.peekKind() == TokenKind.BAR:
        hasBar = True
        state.advance()

    body = None
    if len(arguments) == 0 or hasBar:
        state, body = parseLexicalSequenceUntilEndOrDelimiter(state, TokenKind.RIGHT_BRACKET)

    # }
    body = state.expectAddingErrorToNode(TokenKind.RIGHT_BRACKET, body)
    return state, ParseTreeBlockNode(state.sourcePositionFrom(startPosition), arguments, body)

def parseUnaryPostfixExpression(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    state, receiver = parseTerm(state)
    while state.peekKind() in [TokenKind.IDENTIFIER, TokenKind.LEFT_PARENT, TokenKind.LEFT_BRACKET]:
        token = state.peek()
        if token.kind == TokenKind.IDENTIFIER:
            state.advance()
            selector = ParseTreeLiteralSymbolNode(token.sourcePosition, token.getStringValue())
            receiver = ParseTreeMessageSendNode(receiver.sourcePosition.to(selector.sourcePosition), receiver, selector, [])
        elif token.kind == TokenKind.LEFT_PARENT:
            state.advance()
            state, arguments = parseExpressionListUntilEndOrDelimiter(state, TokenKind.RIGHT_PARENT)
            if state.peekKind() == TokenKind.RIGHT_PARENT:
                state.advance()
            else:
                arguments.append(ParseTreeErrorNode(state.currentSourcePosition(), "Expected right parenthesis."))
            receiver = ParseTreeApplicationNode(state.sourcePositionFrom(startPosition), receiver, arguments)
    return state, receiver

def isBinaryExpressionOperator(kind: TokenKind) -> bool:
    return kind in [TokenKind.OPERATOR, TokenKind.LESS_THAN, TokenKind.GREATER_THAN, TokenKind.BAR]

def parseBinaryExpressionSequence(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    state, operand = parseUnaryPostfixExpression(state)
    if not isBinaryExpressionOperator(state.peekKind()):
        return state, operand
    
    elements = [operand]
    while isBinaryExpressionOperator(state.peekKind()):
        operatorToken = state.next()
        operator = ParseTreeLiteralSymbolNode(operatorToken.sourcePosition, operatorToken.getStringValue())
        elements.append(operator)

        state, operand = parseUnaryPostfixExpression(state)
        elements.append(operand)

    return state, ParseTreeBinaryExpressionSequenceNode(state.sourcePositionFrom(startPosition), elements)
    
def parseKeywordApplication(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    assert state.peekKind() == TokenKind.KEYWORD
    startPosition = state.position

    symbolValue = ""
    arguments = []
    firstKeywordSourcePosition = state.peek(0).sourcePosition
    lastKeywordSourcePosition = firstKeywordSourcePosition
    while state.peekKind() == TokenKind.KEYWORD:
        keywordToken = state.next()
        lastKeywordSourcePosition = keywordToken.sourcePosition
        symbolValue += keywordToken.getStringValue()
        
        state, argument = parseBinaryExpressionSequence(state)
        arguments.append(argument)

    functionIdentifier = ParseTreeLiteralSymbolNode(firstKeywordSourcePosition.to(lastKeywordSourcePosition), symbolValue)
    return state, ParseTreeMessageSendNode(state.sourcePositionFrom(startPosition), None, functionIdentifier, arguments)

def parseKeywordMessageSend(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    state, receiver = parseBinaryExpressionSequence(state)
    if state.peekKind() != TokenKind.KEYWORD:
        return state, receiver

    symbolValue = ""
    arguments = []
    firstKeywordSourcePosition = state.peek(0).sourcePosition
    lastKeywordSourcePosition = firstKeywordSourcePosition
    while state.peekKind() == TokenKind.KEYWORD:
        keywordToken = state.next()
        lastKeywordSourcePosition = keywordToken.sourcePosition
        symbolValue += keywordToken.getStringValue()
        
        state, argument = parseBinaryExpressionSequence(state)
        arguments.append(argument)

    selector = ParseTreeLiteralSymbolNode(firstKeywordSourcePosition.to(lastKeywordSourcePosition), symbolValue)
    return state, ParseTreeMessageSendNode(state.sourcePositionFrom(startPosition), receiver, selector, arguments)

def parsePragma(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    assert state.peekKind() == TokenKind.LESS_THAN
    state.advance()

    arguments = []
    if state.peekKind() == TokenKind.IDENTIFIER:
        selectorStartPosition = state.position
        token = state.next()
        selector = ParseTreeLiteralSymbolNode(state.sourcePositionFrom(selectorStartPosition), token.getStringValue())
    elif state.peekKind() == TokenKind.KEYWORD:
        symbolValue = ""
        firstKeywordSourcePosition = state.peek(0).sourcePosition
        lastKeywordSourcePosition = firstKeywordSourcePosition
        while state.peekKind() == TokenKind.KEYWORD:
            keywordToken = state.next()
            lastKeywordSourcePosition = keywordToken.sourcePosition
            symbolValue += keywordToken.getStringValue()
            
            state, argument = parseUnaryPostfixExpression(state)
            arguments.append(argument)

        selector = ParseTreeLiteralSymbolNode(firstKeywordSourcePosition.to(lastKeywordSourcePosition), symbolValue)
    else:
        return state, ParseTreeErrorNode(state.sourcePositionFrom(startPosition), 'Expected a pragma.')
    
    if state.peekKind() == TokenKind.GREATER_THAN:
        state.advance()
        return state, ParseTreePragmaNode(state.sourcePositionFrom(startPosition), selector, arguments)
    else:
        pragma = ParseTreePragmaNode(state.sourcePositionFrom(startPosition), selector, arguments)
        return state, state.expectAddingErrorToNode(TokenKind.GREATER_THAN, pragma)

def parsePragmas(state: ParserState) -> tuple[ParserState, list[ParseTreeNode]]:
    pragmas = []
    while state.peekKind() == TokenKind.LESS_THAN:
        state, pragma = parsePragma(state)
        pragmas.append(pragma)
    return state, pragmas

def parseCascadedMessage(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    token = state.peek()
    if state.peekKind() == TokenKind.IDENTIFIER:
        state.advance()
        selector = ParseTreeLiteralSymbolNode(token.sourcePosition, token.getStringValue())
        return state, ParseTreeCascadeMessageNode(state.sourcePositionFrom(startPosition), selector, [])
    elif state.peekKind() == TokenKind.KEYWORD:
        symbolValue = ""
        arguments = []
        firstKeywordSourcePosition = state.peek(0).sourcePosition
        lastKeywordSourcePosition = firstKeywordSourcePosition
        while state.peekKind() == TokenKind.KEYWORD:
            keywordToken = state.next()
            lastKeywordSourcePosition = keywordToken.sourcePosition
            symbolValue += keywordToken.getStringValue()
            
            state, argument = parseBinaryExpressionSequence(state)
            arguments.append(argument)

        selector = ParseTreeLiteralSymbolNode(firstKeywordSourcePosition.to(lastKeywordSourcePosition), symbolValue)
        return state, ParseTreeCascadeMessageNode(state.sourcePositionFrom(startPosition), selector, arguments)
    elif isBinaryExpressionOperator(state.peekKind()):
        state.advance()
        selector = ParseTreeLiteralSymbolNode(token.sourcePosition, token.getStringValue())
        state, argument = parseUnaryPostfixExpression(state)
        return state, ParseTreeCascadeMessageNode(state.sourcePositionFrom(startPosition), selector, [argument])
    else:
        return state, ParseTreeErrorNode(state.currentSourcePosition(), 'Expected a cascaded message send.')

def parseMessageSendCascade(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    state, firstMessage = parseKeywordMessageSend(state)
    if state.peekKind() != TokenKind.SEMICOLON:
        return state, firstMessage
    
    cascadeReceiver, firstCascadedMessage  = firstMessage.asMessageSendCascadeReceiverAndFirstMessage()
    cascadedMessages = []
    if firstCascadedMessage is not None:
        cascadedMessages.append(firstCascadedMessage)

    while state.peekKind() == TokenKind.SEMICOLON:
        state.advance()
        state, cascadedMessage = parseCascadedMessage(state)
        cascadedMessages.append(cascadedMessage)
    return state, ParseTreeMessageCascadeNode(state.sourcePositionFrom(startPosition), cascadeReceiver, cascadedMessages)

def parseLowPrecedenceExpression(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    if state.peekKind() == TokenKind.KEYWORD:
        return parseKeywordApplication(state)
    return parseMessageSendCascade(state)

def parseAssignmentExpression(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    startPosition = state.position
    state, assignedStore = parseLowPrecedenceExpression(state)
    if state.peekKind() == TokenKind.ASSIGNMENT:
        operatorToken = state.next()
        state, assignedValue = parseAssignmentExpression(state)
        return state, ParseTreeAssignmentNode(state.sourcePositionFrom(startPosition), assignedStore, assignedValue)
    else:
        return state, assignedStore

def parseExpression(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    return parseAssignmentExpression(state)

def parseExpressionListUntilEndOrDelimiter(state: ParserState, delimiter: TokenKind) -> tuple[ParserState, list[ParseTreeNode]]:
    elements = []

    # Chop the initial dots
    while state.peekKind() == TokenKind.DOT:
        state.advance()

    # Parse the next expression
    expectsExpression = True
    while not state.atEnd() and state.peekKind() != delimiter:
        if not expectsExpression:
            elements.append(ParseTreeErrorNode(state.currentSourcePosition(), "Expected dot before expression.", []))

        state, expression = parseExpression(state)
        elements.append(expression)

        expectsExpression = False
        # Chop the next dot sequence
        while state.peekKind() == TokenKind.DOT:
            expectsExpression = True
            state.advance()

    return state, elements

def parseSequenceUntilEndOrDelimiter(state: ParserState, delimiter: TokenKind) -> tuple[ParserState, ParseTreeNode]:
    initialPosition = state.position
    state, elements = parseExpressionListUntilEndOrDelimiter(state, delimiter)
    if len(elements) == 1:
        return state, elements[0]
    return state, ParseTreeSequenceNode(state.sourcePositionFrom(initialPosition), elements)

def parseLexicalSequenceUntilEndOrDelimiter(state: ParserState, delimiter: TokenKind) -> tuple[ParserState, ParseTreeNode]:
    initialPosition = state.position
    locals = []
    state, pragmas = parsePragmas(state)

    if state.peekKind() == TokenKind.BAR:
        state, locals = parseLocalVariables(state)

    state, morePragmas = parsePragmas(state)
    pragmas += morePragmas

    state, elements = parseExpressionListUntilEndOrDelimiter(state, delimiter)
    if len(locals) == 0 and len(pragmas) == 0 and len(elements) == 1:
        return state, elements[0]
    return state, ParseTreeLexicalSequenceNode(state.sourcePositionFrom(initialPosition), locals, pragmas, elements)

def parseTopLevelExpression(state: ParserState) -> tuple[ParserState, ParseTreeNode]:
    state, node = parseLexicalSequenceUntilEndOrDelimiter(state, TokenKind.END_OF_SOURCE)
    return node

def parseSourceString(sourceText: str, sourceName: str = '<string>') -> ParseTreeNode:
    sourceCode, tokens = scanSourceString(sourceText, sourceName)
    state = ParserState(sourceCode, tokens)
    return parseTopLevelExpression(state)

def parseFileNamed(fileName: str) -> ParseTreeNode:
    sourceCode, tokens = scanFileNamed(fileName)
    state = ParserState(sourceCode, tokens)
    return parseTopLevelExpression(state)
    