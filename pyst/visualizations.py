from .mop import *

def asgTopoSortTraversal(aBlock, node: ASGNode):
    visited = set()
    def visitNode(node):
        if node in visited:
            return
        
        visited.add(node)
        for dependency in node.allDependencies():
            visitNode(dependency)
        aBlock(node)

    visitNode(node)

def asgTopoSort(node: ASGNode):
    sorted = []
    if node is not None:
        asgTopoSortTraversal(sorted.append, node)
    return sorted

def asgToDot(node: ASGNode):
    sortedNodes = asgTopoSort(node)
    nodeToNameDictionary = {}
    nodeCount = 0
    result = 'digraph {\n'
    for node in sortedNodes:
        nodeName = 'N%d' % nodeCount
        nodeToNameDictionary[node] = nodeName
        result += '  N%d [label="%s"]\n' % (nodeCount, node.prettyPrintNameWithDataAttributes().replace('\\', '\\\\').replace('"', '\\"'))
        nodeCount += 1

    for node in sortedNodes:
        nodeName = nodeToNameDictionary[node]
        for dependency in node.sequencingDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = blue]\n' % (nodeName, dependencyName)
        for dependency in node.syntacticDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = blue]\n' % (nodeName, dependencyName)
        for dependency in node.effectDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = red]\n' % (nodeName, dependencyName)
        for dependency in node.dataDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = green]\n' % (nodeName, dependencyName)

        for destination in node.explicitDestinations():
            destinationName = nodeToNameDictionary[destination]
            result += '  %s -> %s [color = cyan]\n' % (nodeName, destinationName)

    result += '}\n'
    return result

def asgToDotFileNamed(node: ASGNode, filename: str):
    dotData = asgToDot(node)
    with open(filename, "w") as f:
        f.write(dotData)

def asgTopoSortTraversalWithDerivations(aBlock, node: ASGNode):
    visited = set()
    def visitNode(node):
        if node in visited:
            return
        
        visited.add(node)
        for derivation in node.allDerivationNodes():
            visitNode(derivation)
        for dependency in node.allDependencies():
            visitNode(dependency)
        aBlock(node)

    visitNode(node)

def asgTopoSortWithDerivations(node: ASGNode):
    sorted = []
    if node is not None:
        asgTopoSortTraversalWithDerivations(sorted.append, node)
    return sorted

def asgWithDerivationsToDot(node: ASGNode):
    sortedNodes = asgTopoSortWithDerivations(node)
    nodeToNameDictionary = {}
    nodeCount = 0
    result = 'digraph {\n'
    for node in sortedNodes:
        nodeName = 'N%d' % nodeCount
        nodeToNameDictionary[node] = nodeName
        result += '  N%d [label="%s"]\n' % (nodeCount, node.prettyPrintNameWithDataAttributes().replace('\\', '\\\\').replace('"', '\\"'))
        nodeCount += 1

    for node in sortedNodes:
        nodeName = nodeToNameDictionary[node]
        for derivation in node.allDerivationNodes():
            derivationName = nodeToNameDictionary[derivation]
            result += '  %s -> %s [color = gray]\n' % (nodeName, derivationName)

        for dependency in node.sequencingDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = blue]\n' % (nodeName, dependencyName)
        for dependency in node.syntacticDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = blue]\n' % (nodeName, dependencyName)
        for dependency in node.effectDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = red]\n' % (nodeName, dependencyName)
        for dependency in node.dataDependencies():
            dependencyName = nodeToNameDictionary[dependency]
            result += '  %s -> %s [color = green]\n' % (nodeName, dependencyName)
        for destination in node.explicitDestinations():
            destinationName = nodeToNameDictionary[destination]
            result += '  %s -> %s [color = cyan]\n' % (nodeName, destinationName)

    result += '}\n'
    return result

def asgWithDerivationsToDotFileNamed(node: ASGNode, filename: str):
    dotData = asgWithDerivationsToDot(node)
    with open(filename, "w") as f:
        f.write(dotData)