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

        node = self.parseSourceStringWithoutErrors('+42')
        self.assertTrue(node.isLiteralIntegerNode())
        self.assertEqual(node.value, 42)

        node = self.parseSourceStringWithoutErrors('-42')
        self.assertTrue(node.isLiteralIntegerNode())
        self.assertEqual(node.value, -42)

        node = self.parseSourceStringWithoutErrors('2r1010')
        self.assertTrue(node.isLiteralIntegerNode())
        self.assertEqual(node.value, 0b1010)

        node = self.parseSourceStringWithoutErrors('16rC0DE')
        self.assertTrue(node.isLiteralIntegerNode())
        self.assertEqual(node.value, 0xC0DE)

    def testLiteralCharacter(self):
        node = self.parseSourceStringWithoutErrors('$A')
        self.assertTrue(node.isLiteralCharacterNode())
        self.assertEqual(node.value, ord('A'))

    def testLiteralFloat(self):
        node = self.parseSourceStringWithoutErrors('42.5')
        self.assertTrue(node.isLiteralFloatNode())
        self.assertEqual(node.value, 42.5)

        node = self.parseSourceStringWithoutErrors('42.5e3')
        self.assertTrue(node.isLiteralFloatNode())
        self.assertEqual(node.value, 42.5e3)

    def testLiteralString(self):
        node = self.parseSourceStringWithoutErrors("'Hello World'")
        self.assertTrue(node.isLiteralStringNode())
        self.assertEqual(node.value, 'Hello World')

        node = self.parseSourceStringWithoutErrors("'Hello ''World'''")
        self.assertTrue(node.isLiteralStringNode())
        self.assertEqual(node.value, "Hello 'World'")

    def testLiteralSymbolIdentifier(self):
        node = self.parseSourceStringWithoutErrors("#symbol")
        self.assertTrue(node.isLiteralSymbolNode())
        self.assertEqual(node.value, 'symbol')

    def testLiteralSymbolKeyword(self):
        node = self.parseSourceStringWithoutErrors("#keyword:")
        self.assertTrue(node.isLiteralSymbolNode())
        self.assertEqual(node.value, 'keyword:')

        node = self.parseSourceStringWithoutErrors("#keyword:with:")
        self.assertTrue(node.isLiteralSymbolNode())
        self.assertEqual(node.value, 'keyword:with:')

    def testLiteralSymbolString(self):
        node = self.parseSourceStringWithoutErrors("#'Hello World'")
        self.assertTrue(node.isLiteralSymbolNode())
        self.assertEqual(node.value, 'Hello World')

        node = self.parseSourceStringWithoutErrors("#'Hello ''World'''")
        self.assertTrue(node.isLiteralSymbolNode())
        self.assertEqual(node.value, "Hello 'World'")

    def testIdentifierReference(self):
        node = self.parseSourceStringWithoutErrors("identifier")
        self.assertTrue(node.isIdentifierReferenceNode())
        self.assertEqual(node.value, 'identifier')

    def testBinaryExpressionSequence(self):
        node = self.parseSourceStringWithoutErrors("1 + 2")
        self.assertTrue(node.isBinaryExpressionSequenceNode())
        self.assertEqual(len(node.elements), 3)

        term: ParseTreeNode = node.elements[0]
        self.assertTrue(term.isLiteralIntegerNode())
        self.assertEqual(term.value, 1)

        operator: ParseTreeNode = node.elements[1]
        self.assertTrue(operator.isLiteralSymbolNode())
        self.assertEqual(operator.value, '+')

        term: ParseTreeNode = node.elements[2]
        self.assertTrue(term.isLiteralIntegerNode())
        self.assertEqual(term.value, 2)

    def testBinaryExpressionSequence(self):
        node = self.parseSourceStringWithoutErrors("1 + 2 * 4")
        self.assertTrue(node.isBinaryExpressionSequenceNode())
        self.assertEqual(len(node.elements), 5)

        term: ParseTreeNode = node.elements[0]
        self.assertTrue(term.isLiteralIntegerNode())
        self.assertEqual(term.value, 1)

        operator: ParseTreeNode = node.elements[1]
        self.assertTrue(operator.isLiteralSymbolNode())
        self.assertEqual(operator.value, '+')

        term: ParseTreeNode = node.elements[2]
        self.assertTrue(term.isLiteralIntegerNode())
        self.assertEqual(term.value, 2)

        operator: ParseTreeNode = node.elements[3]
        self.assertTrue(operator.isLiteralSymbolNode())
        self.assertEqual(operator.value, '*')

        term: ParseTreeNode = node.elements[4]
        self.assertTrue(term.isLiteralIntegerNode())
        self.assertEqual(term.value, 4)

    def testUnaryMessageSend(self):
        node = self.parseSourceStringWithoutErrors("a negated")
        self.assertTrue(node.isMessageSendNode())
        self.assertTrue(node.receiver.isIdentifierReferenceNode())
        self.assertEqual(node.receiver.value, 'a')

        self.assertTrue(node.selector.isLiteralSymbolNode())
        self.assertEqual(node.selector.value, 'negated')

        self.assertEqual(len(node.arguments), 0)

    def testKeywordMessageSend(self):
        node = self.parseSourceStringWithoutErrors("a perform: #yourself")
        self.assertTrue(node.isMessageSendNode())
        self.assertTrue(node.receiver.isIdentifierReferenceNode())
        self.assertEqual(node.receiver.value, 'a')

        self.assertTrue(node.selector.isLiteralSymbolNode())
        self.assertEqual(node.selector.value, 'perform:')

        self.assertEqual(len(node.arguments), 1)
        argument: ParseTreeNode = node.arguments[0]

        self.assertTrue(argument.isLiteralSymbolNode())
        self.assertEqual(argument.value, 'yourself')

    def testKeywordMessageSend2(self):
        node = self.parseSourceStringWithoutErrors("a perform: #doSomethingWith: with: 42")
        self.assertTrue(node.isMessageSendNode())
        self.assertTrue(node.receiver.isIdentifierReferenceNode())
        self.assertEqual(node.receiver.value, 'a')

        self.assertTrue(node.selector.isLiteralSymbolNode())
        self.assertEqual(node.selector.value, 'perform:with:')

        self.assertEqual(len(node.arguments), 2)

        argument: ParseTreeNode = node.arguments[0]
        self.assertTrue(argument.isLiteralSymbolNode())
        self.assertEqual(argument.value, 'doSomethingWith:')

        argument: ParseTreeNode = node.arguments[1]
        self.assertTrue(argument.isLiteralIntegerNode())
        self.assertEqual(argument.value, 42)

if __name__ == '__main__':
    unittest.main()