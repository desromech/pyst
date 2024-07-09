import unittest
from .scanner import TokenKind, scanSourceString

class TestScanner(unittest.TestCase):
    def scanTokenKinds(self, string: str) -> list[TokenKind]:
        sourceCode, tokens = scanSourceString(string)
        return list(map(lambda t: t.kind, tokens))

    def testEmpty(self):
        self.assertEqual(self.scanTokenKinds(''), [TokenKind.END_OF_SOURCE])

    def testComment(self):
        self.assertEqual(self.scanTokenKinds('"A comment"'), [TokenKind.END_OF_SOURCE])

    def testIncompleteComment(self):
        self.assertEqual(self.scanTokenKinds('"A comment'), [TokenKind.ERROR, TokenKind.END_OF_SOURCE])

    def testString(self):
        self.assertEqual(self.scanTokenKinds("'My String'"), [TokenKind.STRING, TokenKind.END_OF_SOURCE])

    def testIncompleteString(self):
        self.assertEqual(self.scanTokenKinds("'My String"), [TokenKind.ERROR, TokenKind.END_OF_SOURCE])

    def testIdentifier(self):
        self.assertEqual(self.scanTokenKinds("helloIdentifier"), [TokenKind.IDENTIFIER, TokenKind.END_OF_SOURCE])

    def testSymbol(self):
        self.assertEqual(self.scanTokenKinds("#symbol"), [TokenKind.SYMBOL, TokenKind.END_OF_SOURCE])

    def testKeyword(self):
        self.assertEqual(self.scanTokenKinds("keyword:"), [TokenKind.KEYWORD, TokenKind.END_OF_SOURCE])

    def testMultiKeyword(self):
        self.assertEqual(self.scanTokenKinds("keyword:with:"), [TokenKind.MULTI_KEYWORD, TokenKind.END_OF_SOURCE])

    def testKeywordSymbol(self):
        self.assertEqual(self.scanTokenKinds("#keyword:"), [TokenKind.SYMBOL, TokenKind.END_OF_SOURCE])

    def testOperator(self):
        self.assertEqual(self.scanTokenKinds("#<"), [TokenKind.SYMBOL, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("#|"), [TokenKind.SYMBOL, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("#+"), [TokenKind.SYMBOL, TokenKind.END_OF_SOURCE])

    def testStringSymbol(self):
        self.assertEqual(self.scanTokenKinds("#'Hello Symbol'"), [TokenKind.SYMBOL, TokenKind.END_OF_SOURCE])

    def testInteger(self):
        self.assertEqual(self.scanTokenKinds("1234"), [TokenKind.INTEGER, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("+1234"), [TokenKind.INTEGER, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("-1234"), [TokenKind.INTEGER, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("2r01010"), [TokenKind.INTEGER, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("16rC0DE"), [TokenKind.INTEGER, TokenKind.END_OF_SOURCE])

    def testCharacter(self):
        self.assertEqual(self.scanTokenKinds("$a"), [TokenKind.CHARACTER, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("$$"), [TokenKind.CHARACTER, TokenKind.END_OF_SOURCE])

    def testFloat(self):
        self.assertEqual(self.scanTokenKinds("42.5"), [TokenKind.FLOAT, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("42.5e+12"), [TokenKind.FLOAT, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("42.5E+12"), [TokenKind.FLOAT, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("42.5e-12"), [TokenKind.FLOAT, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("42.5E-12"), [TokenKind.FLOAT, TokenKind.END_OF_SOURCE])

    def testPunctuations(self):
        self.assertEqual(self.scanTokenKinds("( )"), [TokenKind.LEFT_PARENT, TokenKind.RIGHT_PARENT, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("[ ]"), [TokenKind.LEFT_BRACKET, TokenKind.RIGHT_BRACKET, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("{ }"), [TokenKind.LEFT_CURLY_BRACKET, TokenKind.RIGHT_CURLY_BRACKET, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds(". ; : |"), [TokenKind.DOT, TokenKind.SEMICOLON, TokenKind.COLON, TokenKind.BAR, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("< > ^"), [TokenKind.LESS_THAN, TokenKind.GREATER_THAN, TokenKind.CARET, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("`' `` `, `@"), [TokenKind.QUOTE, TokenKind.QUASI_QUOTE, TokenKind.QUASI_UNQUOTE, TokenKind.SPLICE, TokenKind.END_OF_SOURCE])

    def testOperator(self):
        self.assertEqual(self.scanTokenKinds("+"), [TokenKind.OPERATOR, TokenKind.END_OF_SOURCE])
        self.assertEqual(self.scanTokenKinds("-"), [TokenKind.OPERATOR, TokenKind.END_OF_SOURCE])

if __name__ == '__main__':
    unittest.main()