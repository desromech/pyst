import unittest
from .scanner import TokenKind, scanSourceString

class TestScanner(unittest.TestCase):
    def scanTokenKinds(self, string: str) -> list[TokenKind]:
        sourceCode, tokens = scanSourceString(string)
        return list(map(lambda t: t.kind, tokens))

    def test_empty(self):
        self.assertEqual(self.scanTokenKinds(''), [TokenKind.END_OF_SOURCE])

    def test_comment(self):
        self.assertEqual(self.scanTokenKinds('"A comment"'), [TokenKind.END_OF_SOURCE])

    def test_incompleteComment(self):
        self.assertEqual(self.scanTokenKinds('"A comment'), [TokenKind.ERROR, TokenKind.END_OF_SOURCE])

    def test_string(self):
        self.assertEqual(self.scanTokenKinds("'My String'"), [TokenKind.STRING, TokenKind.END_OF_SOURCE])

    def test_incompleteString(self):
        self.assertEqual(self.scanTokenKinds("'My String"), [TokenKind.ERROR, TokenKind.END_OF_SOURCE])

if __name__ == '__main__':
    unittest.main()