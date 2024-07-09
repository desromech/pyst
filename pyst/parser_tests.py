import unittest
from .parsetree import *
from .parser import parseSourceString

class TestParser(unittest.TestCase):
    def parseSourceStringWithoutErrors(self, string: str) -> ParseTreeNode:
        ast = parseSourceString(string)
        self.assertTrue(ParseTreeErrorVisitor().checkAndPrintErrors(ast))
        return ast

    def testEmpty(self):
        ast = self.parseSourceStringWithoutErrors('')
        self.assertTrue(ast.isSequenceNode())

    def testLiteralInteger(self):
        node = self.parseSourceStringWithoutErrors('42')
        self.assertTrue(node.isLiteralIntegerNode())
        self.assertEqual(node.value, 42)

        node = self.parseSourceStringWithoutErrors('-42')
        self.assertTrue(node.isLiteralIntegerNode())
        self.assertEqual(node.value, -42)

if __name__ == '__main__':
    unittest.main()