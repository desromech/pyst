from enum import Enum
from .parsetree import SourceCode, SourcePosition
import copy
import os.path

TokenKind = Enum('TokenKind', [
    'END_OF_SOURCE', 'ERROR',

    'CHARACTER', 'FLOAT', 'IDENTIFIER', 'INTEGER', 'KEYWORD', 'MULTI_KEYWORD', 'OPERATOR', 'STRING', 'SYMBOL',
    'LEFT_PARENT', 'RIGHT_PARENT', 'LEFT_BRACKET', 'RIGHT_BRACKET', 'LEFT_CURLY_BRACKET', 'RIGHT_CURLY_BRACKET',
    'LESS_THAN', 'GREATER_THAN',
    'COLON', 'COLON_COLON', 'BAR',
    'ASSIGNMENT', 'SEMICOLON', 'COMMA', 'DOT', 'CARET',
    'QUOTE', 'QUASI_QUOTE', 'QUASI_UNQUOTE', 'SPLICE',
    'LITERAL_ARRAY_START', 'BYTE_ARRAY_START'
])

class Token:
    def __init__(self, kind: TokenKind, sourcePosition: SourcePosition, errorMessage: str = None):
        self.kind = kind
        self.sourcePosition = sourcePosition
        self.errorMessage = errorMessage

    def getValue(self) -> bytes:
        return self.sourcePosition.getValue()

    def getStringValue(self) -> str:
        return self.sourcePosition.getStringValue()

    def __repr__(self) -> str:
        if self.errorMessage is not None:
            return '%s: %s: %s' % (str(self.sourcePosition), repr(self.kind), self.errorMessage)
        else:
            return '%s: %s' % (str(self.sourcePosition), repr(self.kind))

class ScannerState:
    def __init__(self, sourceCode: SourceCode):
        self.sourceCode = sourceCode
        self.position = 0
        self.line = 1
        self.column = 1
        self.isPreviousCR = False
    
    def atEnd(self) -> bool:
        return self.position >= len(self.sourceCode.text)

    def peek(self, peekOffset: int = 0) -> int:
        peekPosition = self.position + peekOffset
        if peekPosition < len(self.sourceCode.text):
            return self.sourceCode.text[peekPosition]
        else:
            return -1
        
    def advance(self) -> None:
        assert self.position < len(self.sourceCode.text)
        c = self.sourceCode.text[self.position]
        self.position += 1
        if c == b'\r'[0]: 
            self.line += 1
            self.column = 1
            self.isPreviousCR = True
        elif c == b'\n'[0]: 
            if not self.isPreviousCR:
                self.line += 1
                self.column = 1
            self.isPreviousCR = False
        elif c == b'\t'[0]: 
            self.column = (self.column + 4) % 4 * 4 + 1
            self.isPreviousCR = False
        else:
            self.column += 1

    def advanceCount(self, count: int) -> None:
        for i in range(count):
            self.advance()
        
    def makeToken(self, kind: TokenKind) -> Token:
        sourcePosition = SourcePosition(self.sourceCode, self.position, self.position, self.line, self.column, self.line, self.column)
        return Token(kind, sourcePosition)
    
    def makeTokenStartingFrom(self, kind: TokenKind, initialState) -> Token:
        sourcePosition = SourcePosition(self.sourceCode, initialState.position, self.position, initialState.line, initialState.column, self.line, self.column)
        return Token(kind, sourcePosition)

    def makeErrorTokenStartingFrom(self, errorMessage: str, initialState):
        sourcePosition = SourcePosition(self.sourceCode, initialState.position, self.position, initialState.line, initialState.column, self.line, self.column)
        return Token(TokenKind.ERROR, sourcePosition, errorMessage)

def skipWhite(state: ScannerState) -> tuple[ScannerState, Token]:
    hasSeenComment = True
    while hasSeenComment:
        hasSeenComment = False
        while not state.atEnd() and state.peek() <= b' '[0]:
            state.advance()

        if state.peek() == b'"'[0]:
            commentInitialState = copy.copy(state)
            state.advanceCount(1)
            hasCommentEnd = False
            while not state.atEnd():
                hasCommentEnd = state.peek() == b'"'[0]
                if hasCommentEnd:
                    state.advanceCount(1)
                    break

                state.advance()
            if not hasCommentEnd:
                return state, state.makeErrorTokenStartingFrom('Incomplete multiline comment.', commentInitialState)

            hasSeenComment = True

    return state, None

def isDigit(c: int) -> bool:
    return (b'0'[0] <= c and c <= b'9'[0])

def isIdentifierStart(c: int) -> bool:
    return (b'A'[0] <= c and c <= b'Z'[0]) or \
        (b'a'[0] <= c and c <= b'z'[0]) or \
        (b'_'[0] == c)

def isIdentifierMiddle(c: int) -> bool:
    return isIdentifierStart(c) or isDigit(c)

def isOperatorCharacter(c: int) -> bool:
    return c >= 0 and c in b'+-/\\*~<>=@,%|&?!^'

def scanAdvanceKeyword(state: ScannerState) -> tuple[ScannerState, Token]:
    if not isIdentifierStart(state.peek()):
        return state, False
    
    initialState = copy.copy(state)
    while isIdentifierMiddle(state.peek()):
        state.advance()

    if state.peek() != b':'[0]:
        return initialState, False

    state.advance()
    return state, True

def scanNextToken(state: ScannerState) -> tuple[ScannerState, Token]:
    state, whiteErrorToken = skipWhite(state)
    if whiteErrorToken is not None: return state, whiteErrorToken

    if state.atEnd():
        return state, state.makeToken(TokenKind.END_OF_SOURCE)
    
    initialState = copy.copy(state)
    c = state.peek()

    ## Identifiers, keywords and multi-keywords
    if isIdentifierStart(c):
        state.advance()
        while isIdentifierMiddle(state.peek()):
            state.advance()

        if state.peek() == b':'[0]:
            state.advance()
            isMultiKeyword = False
            hasAdvanced = True
            while hasAdvanced:
                state, hasAdvanced = scanAdvanceKeyword(state)
                isMultiKeyword = isMultiKeyword or hasAdvanced

            if isMultiKeyword:
                return state, state.makeTokenStartingFrom(TokenKind.MULTI_KEYWORD, initialState)
            else:
                return state, state.makeTokenStartingFrom(TokenKind.KEYWORD, initialState)
        
        return state, state.makeTokenStartingFrom(TokenKind.IDENTIFIER, initialState)
    
    ## Numbers
    if isDigit(c) or ((state.peek() == b'+'[0] or state.peek() == b'-'[0]) and isDigit(state.peek(1))):
        state.advance()
        while isDigit(state.peek()):
            state.advance()

        ## Parse the radix.
        if not state.atEnd() and state.peek() in b'rR':
            state.advance()
            while isIdentifierMiddle(state.peek()):
                state.advance()
            return state, state.makeTokenStartingFrom(TokenKind.INTEGER, initialState)
        
        ## Decimal point.
        if state.peek() == b'.'[0] and isDigit(state.peek(1)):
            state.advanceCount(2)
            while isDigit(state.peek()):
                state.advance()

            if (state.peek() == b'e'[0] or state.peek() == b'E'[0]):
                if isDigit(state.peek(1)) or ((state.peek(1) == b'+'[0] or state.peek(1) == b'-'[0]) and isDigit(state.peek(2))):
                    state.advanceCount(2)
                    while isDigit(state.peek()):
                        state.advance()

            return state, state.makeTokenStartingFrom(TokenKind.FLOAT, initialState)
        
        return state, state.makeTokenStartingFrom(TokenKind.INTEGER, initialState)

    ## Symbols
    if c == b'#'[0]:
        c1 = state.peek(1)
        if isIdentifierStart(c1):
            state.advanceCount(2)
            while isIdentifierMiddle(state.peek()):
                state.advance()

            if state.peek() == b':'[0]:
                state.advance()
                isMultiKeyword = False
                hasAdvanced = True
                while hasAdvanced:
                    state, hasAdvanced = scanAdvanceKeyword(state)
                    isMultiKeyword = isMultiKeyword or hasAdvanced

                if isMultiKeyword:
                    return state, state.makeTokenStartingFrom(TokenKind.SYMBOL, initialState)
                else:
                    return state, state.makeTokenStartingFrom(TokenKind.SYMBOL, initialState)
            
            return state, state.makeTokenStartingFrom(TokenKind.SYMBOL, initialState)

        elif c1 == b"'"[0]:
            state.advanceCount(2)
            while not state.atEnd() and (state.peek() != b"'"[0] or (state.peek() == b"'"[0] and state.peek(1) == b"'"[0])):
                if state.peek() == b"'"[0] and state.peek(1) == b"'"[0]:
                    state.advanceCount(2)
                else:
                    state.advance()

            if state.peek() != b"'"[0]:
                return state, state.makeErrorTokenStartingFrom("Incomplete symbol string literal.", initialState)
            state.advance()

            return state, state.makeTokenStartingFrom(TokenKind.SYMBOL, initialState)
        elif isOperatorCharacter(c1):
            state.advanceCount(2)
            while isOperatorCharacter(state.peek()):
                state.advance()
            return state, state.makeTokenStartingFrom(TokenKind.SYMBOL, initialState)
        elif c1 == b'['[0]:
            state.advanceCount(2)
            return state, state.makeTokenStartingFrom(TokenKind.BYTE_ARRAY_START, initialState)
        elif c1 == b'('[0]:
            state.advanceCount(2)
            return state, state.makeTokenStartingFrom(TokenKind.LITERAL_ARRAY_START, initialState)

    ## Strings
    if c == b"'"[0]:
        state.advance()
        while not state.atEnd() and (state.peek() != b"'"[0] or (state.peek() == b"'"[0] and state.peek(1) == b"'"[0])):
            if state.peek() == b"'"[0] and state.peek(1) == b"'"[0]:
                state.advanceCount(2)
            else:
                state.advance()

        if state.peek() != b"'"[0]:
            return state, state.makeErrorTokenStartingFrom("Incomplete string literal.", initialState)
        state.advance()

        return state, state.makeTokenStartingFrom(TokenKind.STRING, initialState)

    ## Characters
    if c == b"$"[0]:
        state.advance()
        if state.atEnd():
            return state, state.makeErrorTokenStartingFrom("Incomplete character literal.", initialState)
        state.advance()

        return state, state.makeTokenStartingFrom(TokenKind.CHARACTER, initialState)

    if c == b'('[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.LEFT_PARENT, initialState)
    elif c == b')'[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.RIGHT_PARENT, initialState)
    elif c == b'['[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.LEFT_BRACKET, initialState)
    elif c == b']'[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.RIGHT_BRACKET, initialState)
    elif c == b'{'[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.LEFT_CURLY_BRACKET, initialState)
    elif c == b'}'[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.RIGHT_CURLY_BRACKET, initialState)
    elif c == b';'[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.SEMICOLON, initialState)
    elif c == b'.'[0]:
        state.advance()
        return state, state.makeTokenStartingFrom(TokenKind.DOT, initialState)
    elif c == b':'[0]:
        state.advance()
        if state.peek(0) == b'='[0]:
            state.advance()
            return state, state.makeTokenStartingFrom(TokenKind.ASSIGNMENT, initialState)
        return state, state.makeTokenStartingFrom(TokenKind.COLON, initialState)
    elif c == b'`'[0]:
        if state.peek(1) == b'\''[0]:
            state.advanceCount(2)
            return state, state.makeTokenStartingFrom(TokenKind.QUOTE, initialState)
        elif state.peek(1) == b'`'[0]:
            state.advanceCount(2)
            return state, state.makeTokenStartingFrom(TokenKind.QUASI_QUOTE, initialState)
        elif state.peek(1) == b','[0]:
            state.advanceCount(2)
            return state, state.makeTokenStartingFrom(TokenKind.QUASI_UNQUOTE, initialState)
        elif state.peek(1) == b'@'[0]:
            state.advanceCount(2)
            return state, state.makeTokenStartingFrom(TokenKind.SPLICE, initialState)
    elif c == b'|'[0]:
        state.advance()
        if isOperatorCharacter(state.peek()):
            while isOperatorCharacter(state.peek()):
                state.advance()
            return state, state.makeTokenStartingFrom(TokenKind.OPERATOR, initialState)
        return state, state.makeTokenStartingFrom(TokenKind.BAR, initialState)
    elif isOperatorCharacter(c):
        while isOperatorCharacter(state.peek()):
            state.advance()
        token = state.makeTokenStartingFrom(TokenKind.OPERATOR, initialState)
        tokenValue = token.getValue()
        if tokenValue == b'<':
            token.kind = TokenKind.LESS_THAN
        elif tokenValue == b'>':
            token.kind = TokenKind.GREATER_THAN
        elif tokenValue == b'^':
            token.kind = TokenKind.CARET
        return state, token

    state.advance()
    errorToken = state.makeErrorTokenStartingFrom("Unexpected character.", initialState)
    return state, errorToken

def scanSourceCode(sourceCode: SourceCode) -> list[Token]:
    state = ScannerState(sourceCode)
    tokens = []
    while True:
        state, token = scanNextToken(state)
        tokens.append(token)
        if token.kind == TokenKind.END_OF_SOURCE:
            break
    return tokens

def scanSourceString(sourceText: str, sourceName: str = '<string>') -> tuple[SourceCode, list[Token]]:
    sourceCode = SourceCode(None, sourceName, 'smalltalk', sourceText.encode('utf-8'))
    tokens = scanSourceCode(sourceCode)
    return sourceCode, tokens

def scanFileNamed(fileName: str) -> tuple[SourceCode, list[Token]]:
    with open(fileName, "rb") as f:
        sourceText = f.read()
        sourceDirectory = os.path.dirname(fileName)
        sourceName = os.path.basename(fileName)
        sourceCode = SourceCode(sourceDirectory, sourceName, 'smalltalk', sourceText)
        tokens = scanSourceCode(sourceCode)
        return sourceCode, tokens
