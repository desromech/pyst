from abc import ABC, abstractmethod
from typing import Any
from .parsetree import SourcePosition, EmptySourcePosition
import copy
import struct

class ASGNodeDerivation(ABC):
    @abstractmethod
    def getSourcePosition(self) -> SourcePosition:
        pass

    def getSourceNodeDerivations(self):
        return ()

class ASGNodeSourceCodeDerivation(ASGNodeDerivation):
    def __init__(self, sourcePosition: SourcePosition) -> None:
        super().__init__()
        self.sourcePosition = sourcePosition

    def getSourcePosition(self) -> SourcePosition:
        return self.sourcePosition

class ASGNodeExpansionDerivation(ASGNodeDerivation):
    def __init__(self, algorithm, sourceNode) -> None:
        super().__init__()
        self.algorithm = algorithm
        self.sourceNode = sourceNode
        self.sourcePosition = None
        assert isinstance(self.sourceNode, ASGNode)

    def getSourcePosition(self) -> SourcePosition:
        if self.sourcePosition is None:
            self.sourcePosition = self.sourceNode.sourceDerivation.getSourcePosition()
        return self.sourcePosition

    def getSourceNodeDerivations(self):
        return (self.sourceNode,)

class ASGNodeUnificationDerivation(ASGNodeDerivation):
    def __init__(self, originalNode, unifiedNode) -> None:
        super().__init__()
        self.originalNode = originalNode
        self.unifiedNode = unifiedNode
        self.sourcePosition = None
        assert isinstance(self.originalNode, ASGNode)

    def getSourcePosition(self) -> SourcePosition:
        if self.sourcePosition is None:
            self.sourcePosition = self.originalNode.sourceDerivation.getSourcePosition()
        return self.sourcePosition

    def getSourceNodeDerivations(self):
        return (self.originalNode,)

class ASGNodeSyntaxExpansionDerivation(ASGNodeExpansionDerivation):
    pass

class ASGNodeCoercionExpansionDerivation(ASGNodeExpansionDerivation):
    pass

class ASGNodeMacroExpansionDerivation(ASGNodeExpansionDerivation):
    def __init__(self, algorithm, sourceNode, macro) -> None:
        super().__init__(algorithm, sourceNode)
        self.macro = macro

class ASGNodeReductionDerivation(ASGNodeExpansionDerivation):
    pass

class ASGNodeNoDerivation(ASGNodeDerivation):
    Singleton = None

    def getSourcePosition(self) -> SourcePosition:
        return EmptySourcePosition.getSingleton()

    @classmethod
    def getSingleton(cls):
        if cls.Singleton is None:
            cls.Singleton = cls()
        return cls.Singleton

class ASGNodeMirExpansionDerivation(ASGNodeExpansionDerivation):
    pass

class ASGNodeMirTypeExpansionDerivation(ASGNodeExpansionDerivation):
    pass

class ASGNodeAttributeDescriptor:
    def __init__(self) -> None:
        super().__init__()
        self.name: str = None

    def setName(self, name: str):
        self.name = name
        self.storageName = '_' + name

    def loadValueFrom(self, instance):
        return getattr(instance, self.storageName)
    
    def hasDefaultValueIn(self, instance) -> bool:
        return False
    
    def isFlag(self) -> bool:
        return False
    
    def storeValueIn(self, value, instance):
        setattr(instance, self.storageName, value)

    def initializeWithConstructorValueOn(self, constructorValue, instance):
        raise Exception("Cannot initialize attribute %s during construction." % str(self.name))
    
    def initializeWithDefaultConstructorValueOn(self, instance):
        raise Exception("Cannot initialize attribute %s with default value during construction." % str(self.name))

    def isConstructionAttribute(self) -> bool:
        return False

    def isSpecialAttribute(self) -> bool:
        return False
    
    def isSequencingPredecessorAttribute(self) -> bool:
        return False

    def isSyntacticPredecessorAttribute(self) -> bool:
        return False
    
    def isSourceDerivationAttribute(self) -> bool:
        return False
    
    def isDataAttribute(self) -> bool:
        return False

    def isDataInputPort(self) -> bool:
        return False

    def isSequencingDestinationPort(self) -> bool:
        return False
    
    def isInterpretationDependency(self) -> bool:
        return False
    
    def getNodeInputsOf(self, instance):
        return ()
    
    def getNodeDerivationsOf(self, instance):
        return ()
    
    def __get__(self, instance, owner):
        return self.loadValueFrom(instance)
    
    def __set__(self, instance, value):
        raise Exception('Not supported')

class ASGNodeConstructionAttribute(ASGNodeAttributeDescriptor):
    def isConstructionAttribute(self) -> bool:
        return True

    def isNumberedConstructionAttribute(self) -> bool:
        return True
    
    def isPrinted(self) -> bool:
        return True

    def isComparedForUnification(self) -> bool:
        return True
    
    def hashFrom(self, instance) -> int:
        return hash(self.loadValueFrom(instance))
    
    def equalsFromAndFrom(self, first, second) -> bool:
        return self.loadValueFrom(first) == self.loadValueFrom(second)

    def initializeWithConstructorValueOn(self, constructorValue, instance):
        self.storeValueIn(constructorValue, instance)

class ASGNodeConstructionAttributeWithSourceDerivation(ASGNodeConstructionAttribute):
    def __init__(self, notInterpreted = False) -> None:
        super().__init__()
        self.sourceDerivationStorageName = None
        self.notInterpreted = notInterpreted

    def setName(self, name: str):
        super().setName(name)
        self.sourceDerivationStorageName = '_' + name + '_sourceDerivation'

    def loadSourceDerivationFrom(self, instance):
        return getattr(instance, self.sourceDerivationStorageName)

    def storeSourceDerivationIn(self, sourceDerivation, instance):
        return setattr(instance, self.sourceDerivationStorageName, sourceDerivation)

    def initializeWithConstructorValueOn(self, constructorValue, instance):
        self.storeValueIn(constructorValue.asASGNode(), instance)
        self.storeSourceDerivationIn(constructorValue.asASGNodeDerivation(), instance)

class ASGNodeDataAttribute(ASGNodeConstructionAttribute):
    def __init__(self, type, **kwArguments) -> None:
        super().__init__()
        self.type = type
        self.hasDefaultValue = False
        self.defaultValue = None
        self.isCompared = 'notCompared' not in kwArguments
        self.isPrinted_ = 'notPrinted' not in kwArguments
        if 'default' in kwArguments:
            self.hasDefaultValue = True
            self.defaultValue = kwArguments['default']

    def isPrinted(self) -> bool:
        return self.isPrinted_
    
    def isFlag(self) -> bool:
        return self.type is bool

    def isComparedForUnification(self) -> bool:
        return self.isCompared
    
    def hasDefaultValueIn(self, instance) -> bool:
        return self.hasDefaultValue and self.loadValueFrom(instance) == self.defaultValue

    def initializeWithDefaultConstructorValueOn(self, instance):
        if self.hasDefaultValue:
            self.storeValueIn(self.defaultValue, instance)
        else:
            super().initializeWithDefaultConstructorValueOn(instance)

    def isDataAttribute(self) -> bool:
        return True

class ASGNodeSourceDerivationAttribute(ASGNodeConstructionAttribute):
    def isConstructionAttribute(self) -> bool:
        return True

    def isSpecialAttribute(self) -> bool:
        return True

    def isSourceDerivationAttribute(self) -> bool:
        return True

    def isComparedForUnification(self) -> bool:
        return False

    def getNodeDerivationsOf(self, instance):
        return self.loadValueFrom(instance).getSourceNodeDerivations()
    
class ASGPredecessorAttribute(ASGNodeConstructionAttributeWithSourceDerivation):
    def isNumberedConstructionAttribute(self) -> bool:
        return False

    def initializeWithDefaultConstructorValueOn(self, instance):
        self.storeValueIn(None, instance)
        self.storeSourceDerivationIn(None, instance)

    def getNodeInputsOf(self, instance):
        value = self.loadValueFrom(instance)
        if value is None:
            return ()
        return (value,)
    
    def hashFrom(self, instance) -> int:
        return self.loadValueFrom(instance).unificationHash()
    
    def equalsFromAndFrom(self, first, second) -> bool:
        return self.loadValueFrom(first).unificationEquals(self.loadValueFrom(second))
    
class ASGSequencingPredecessorAttribute(ASGPredecessorAttribute):
    def isSequencingPredecessorAttribute(self) -> bool:
        return True

    def initializeWithConstructorValueOn(self, constructorValue, instance):
        if constructorValue is None:
            self.storeValueIn(None, instance)
            self.storeSourceDerivationIn(None, instance)
        else:
            self.storeValueIn(constructorValue.asASGSequencingNode(), instance)
            self.storeSourceDerivationIn(constructorValue.asASGSequencingNodeDerivation(), instance)
    
class ASGSequencingPredecessorsAttribute(ASGPredecessorAttribute):
    def initializeWithConstructorValueOn(self, constructorValue, instance):
        self.storeValueIn(tuple(map(lambda x: x.asASGSequencingNode(), constructorValue)), instance)
        self.storeSourceDerivationIn(tuple(map(lambda x: x.asASGSequencingNodeDerivation(), constructorValue)), instance)

    def isSequencingPredecessorAttribute(self) -> bool:
        return True
    
    def getNodeInputsOf(self, instance):
        return self.loadValueFrom(instance)

    def hashFrom(self, instance) -> int:
        result = hash(tuple)
        for value in self.loadValueFrom(instance):
            result ^= value.unificationHash()

        return value.unificationHash()
    
    def equalsFromAndFrom(self, first, second) -> bool:
        firstValue = self.loadValueFrom(first)
        secondValue = self.loadValueFrom(second)
        if len(firstValue) != len(secondValue):
            return False

        for i in range(len(firstValue)):
            if not firstValue[i].unificationEquals(secondValue[i]):
                return False

        return True

class ASGSequencingDestinationPort(ASGNodeConstructionAttributeWithSourceDerivation):
    def isSequencingDestinationPort(self) -> bool:
        return True

    def initializeWithConstructorValueOn(self, constructorValue, instance):
        self.storeValueIn(constructorValue.asASGSequencingNode(), instance)
        self.storeSourceDerivationIn(constructorValue.asASGSequencingNodeDerivation(), instance)

    def isInterpretationDependency(self) -> bool:
        return not self.notInterpreted
    
    def getNodeInputsOf(self, instance):
        return [self.loadValueFrom(instance)]
    
    def hashFrom(self, instance) -> int:
        return self.loadValueFrom(instance).unificationHash()
    
    def equalsFromAndFrom(self, first, second) -> bool:
        return self.loadValueFrom(first).unificationEquals(self.loadValueFrom(second))
    
class ASGNodeDataInputPort(ASGNodeConstructionAttributeWithSourceDerivation):
    def initializeWithConstructorValueOn(self, constructorValue, instance):
        self.storeValueIn(constructorValue.asASGDataNode(), instance)
        self.storeSourceDerivationIn(constructorValue.asASGDataNodeDerivation(), instance)

    def isDataInputPort(self) -> bool:
        return True
    
    def isInterpretationDependency(self) -> bool:
        return not self.notInterpreted

    def getNodeInputsOf(self, instance):
        return [self.loadValueFrom(instance)]

    def hashFrom(self, instance) -> int:
        return self.loadValueFrom(instance).unificationHash()
    
    def equalsFromAndFrom(self, first, second) -> bool:
        return self.loadValueFrom(first).unificationEquals(self.loadValueFrom(second))
    
class ASGNodeOptionalDataInputPort(ASGNodeConstructionAttributeWithSourceDerivation):
    def initializeWithConstructorValueOn(self, constructorValue, instance):
        if constructorValue is None:
            self.storeValueIn(None, instance)
            self.storeSourceDerivationIn(None, instance)
        else:
            self.storeValueIn(constructorValue.asASGDataNode(), instance)
            self.storeSourceDerivationIn(constructorValue.asASGDataNodeDerivation(), instance)

    def isDataInputPort(self) -> bool:
        return True

    def isInterpretationDependency(self) -> bool:
        return not self.notInterpreted
    
    def getNodeInputsOf(self, instance):
        value =  self.loadValueFrom(instance)
        if value is None:
            return ()
        return (value,)

    def hashFrom(self, instance) -> int:
        value = self.loadValueFrom(instance)
        if value is None:
            return hash(None)
        return value.unificationHash()
    
    def equalsFromAndFrom(self, first, second) -> bool:
        firstValue = self.loadValueFrom(first)
        secondValue = self.loadValueFrom(second)
        if firstValue is secondValue:
            return True
        if firstValue is None:
            return False
        return firstValue.unificationEquals(secondValue)

class ASGNodeDataInputPorts(ASGNodeConstructionAttributeWithSourceDerivation):
    def initializeWithConstructorValueOn(self, constructorValue, instance) -> bool:
        self.storeValueIn(tuple(map(lambda x: x.asASGDataNode(), constructorValue)), instance)
        self.storeSourceDerivationIn(tuple(map(lambda x: x.asASGDataNodeDerivation(), constructorValue)), instance)

    def isDataInputPort(self) -> bool:
        return True

    def isInterpretationDependency(self) -> bool:
        return not self.notInterpreted
    
    def getNodeInputsOf(self, instance):
        return self.loadValueFrom(instance)

    def hashFrom(self, instance) -> int:
        result = hash(tuple)
        for value in self.loadValueFrom(instance):
            result ^= value.unificationHash()

        return result
    
    def equalsFromAndFrom(self, first, second) -> bool:
        firstValue = self.loadValueFrom(first)
        secondValue = self.loadValueFrom(second)
        if len(firstValue) != len(secondValue):
            return False

        for i in range(len(firstValue)):
            if not firstValue[i].unificationEquals(secondValue[i]):
                return False

        return True

class ASGNodeDataAndSequencingInputPorts(ASGNodeConstructionAttributeWithSourceDerivation):
    def initializeWithConstructorValueOn(self, constructorValue, instance) -> bool:
        self.storeValueIn(tuple(map(lambda x: x.asASGNode(), constructorValue)), instance)
        self.storeSourceDerivationIn(tuple(map(lambda x: x.asASGNodeDerivation(), constructorValue)), instance)

    def isDataInputPort(self) -> bool:
        return True

    def isSequencingPredecessorAttribute(self) -> bool:
        return True

    def getNodeInputsOf(self, instance):
        return self.loadValueFrom(instance)

    def hashFrom(self, instance) -> int:
        result = hash(tuple)
        for value in self.loadValueFrom(instance):
            result ^= value.unificationHash()

        return value.unificationHash()
    
    def equalsFromAndFrom(self, first, second) -> bool:
        firstValue = self.loadValueFrom(first)
        secondValue = self.loadValueFrom(second)
        if len(firstValue) != len(secondValue):
            return False

        for i in range(len(firstValue)):
            if not firstValue[i].unificationEquals(secondValue[i]):
                return False

        return True
    
class ASGNodeMetaclass(type):
    def __new__(cls, name, bases, attributes):
        descriptors = []
        for base in bases:
            baseDescriptors = getattr(base, '__asgAttributeDescriptors__', None)
            if baseDescriptors is not None:
                descriptors += baseDescriptors

        for attributeName, attributeDescriptor in attributes.items():
            if not isinstance(attributeDescriptor, ASGNodeAttributeDescriptor):
                continue

            attributeDescriptor.setName(attributeName)
            descriptors.append(attributeDescriptor)

        specialAttributes: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isSpecialAttribute(), descriptors))
        syntacticPredecessors: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isSyntacticPredecessorAttribute(), descriptors))
        sequencingPredecessors: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isSequencingPredecessorAttribute(), descriptors))
        dataAttributes: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isDataAttribute(), descriptors))
        dataInputPorts: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isDataInputPort(), descriptors))
        destinationPorts: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isSequencingDestinationPort(), descriptors))
        interpretationDependencies: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isInterpretationDependency(), descriptors))

        numberedConstructionAttributes: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isConstructionAttribute() and desc.isNumberedConstructionAttribute(), descriptors))
        unnumberedConstructionAttributes: list[ASGNodeAttributeDescriptor] = list(filter(lambda desc: desc.isConstructionAttribute() and not desc.isNumberedConstructionAttribute(), descriptors))
        constructionAttributes = numberedConstructionAttributes + unnumberedConstructionAttributes

        constructionAttributeDictionary = {}
        for attr in constructionAttributes:
            constructionAttributeDictionary[attr.name] = attr
            
        nodeClass = super().__new__(cls, name, bases, attributes)
        nodeClass.__asgKindName__ = name.removeprefix('ASG').removesuffix('Node')
        nodeClass.__asgAttributeDescriptors__ = descriptors
        nodeClass.__asgSpecialAttributes__ = specialAttributes
        nodeClass.__asgSyntacticPredecessors__ = syntacticPredecessors
        nodeClass.__asgSequencingPredecessors__ = sequencingPredecessors
        nodeClass.__asgConstructionAttributes__ = constructionAttributes
        nodeClass.__asgConstructionAttributeDictionary__ = constructionAttributeDictionary
        nodeClass.__asgDataAttributes__ = dataAttributes
        nodeClass.__asgDataInputPorts__ = dataInputPorts
        nodeClass.__asgDestinationPorts__ = destinationPorts
        nodeClass.__asgInterpretationDependency__ = interpretationDependencies
        return nodeClass

class ASGNode(metaclass = ASGNodeMetaclass):
    def __init__(self, *positionalArguments, **kwArguments) -> None:
        super().__init__()

        self.__hashValueCache__ = None
        self.__betaReplaceableDependencies__ = None
        self.__dominanceTreeDepth__ = None
        self.__constantDataNodeCache__ = None

        constructionAttributes = self.__class__.__asgConstructionAttributes__
        constructionAttributeDictionary = self.__class__.__asgConstructionAttributeDictionary__
        if len(positionalArguments) > len(constructionAttributes):
            raise Exception('Excess number of construction arguments.')
        
        for i in range(len(positionalArguments)):
            constructionAttributes[i].initializeWithConstructorValueOn(positionalArguments[i], self)
        for i in range(len(positionalArguments), len(constructionAttributes)):
            constructionAttributes[i].initializeWithDefaultConstructorValueOn(self)

        for key, value in kwArguments.items():
            if key not in constructionAttributeDictionary:
                raise Exception('Failed to find attribute %s in %s' % (str(key), repr(self.__class__)))
            constructionAttributeDictionary[key].initializeWithConstructorValueOn(value, self)

    def unificationHash(self) -> int:
        if self.__hashValueCache__ is not None:
            return self.__hashValueCache__

        self.__hashValueCache__ = hash(self.__class__)
        constructionAttributes = self.__class__.__asgConstructionAttributes__
        for attribute in constructionAttributes:
            if attribute.isComparedForUnification():
                self.__hashValueCache__ ^= attribute.hashFrom(self)
        return self.__hashValueCache__
    
    def unificationEquals(self, other) -> bool:
        if self is other: return True
        if self.__class__ != other.__class__:
            return False

        constructionAttributes = self.__class__.__asgConstructionAttributes__
        for attribute in constructionAttributes:
            if attribute.isComparedForUnification():
                if not attribute.equalsFromAndFrom(self, other):
                    return False

        return True

    def isSatisfiedAsTypeBy(self, otherType) -> bool:
        if otherType.isBottomTypeNode():
            return True
        return self.unificationEquals(otherType)

    def asASGNode(self):
        return self

    def asASGNodeDerivation(self):
        return ASGNodeNoDerivation.getSingleton()

    def asASGDataNode(self):
        return self.asASGNode()

    def asASGDataNodeDerivation(self):
        return self.asASGNodeDerivation()

    def isBetaReplaceableNode(self) -> bool:
        return False

    def isTypeNode(self) -> bool:
        return False

    def isTypeUniverseNode(self) -> bool:
        return False
    
    def isBottomTypeNode(self) -> bool:
        return False

    def isPureDataNode(self) -> bool:
        raise Exception("Subclass responsibility isPureDataNode")
    
    def isSyntaxNode(self) -> bool:
        return False

    def isSequencingNode(self) -> bool:
        return False

    def isLiteralNode(self) -> bool:
        return False
    
    def asASGSequencingNode(self):
        if self.isPureDataNode():
            return None

        return self.asASGNode()

    def asASGSequencingNodeDerivation(self):
        if self.isPureDataNode():
            return None

        return self.asASGNodeDerivation()

    def explicitDestinations(self):
        for port in self.__class__.__asgDestinationPorts__:
            for predecessor in port.getNodeInputsOf(self):
                yield predecessor

    def sequencingDependencies(self):
        for port in self.__class__.__asgSequencingPredecessors__:
            for predecessor in port.getNodeInputsOf(self):
                yield predecessor

    def syntacticDependencies(self):
        for port in self.__class__.__asgSyntacticPredecessors__:
            for predecessor in port.getNodeInputsOf(self):
                yield predecessor

    def effectDependencies(self):
        return []
    
    def interpretationDependencies(self):
        for port in self.__class__.__asgInterpretationDependency__:
            for dep in port.getNodeInputsOf(self):
                yield dep

    def dataDependencies(self):
        for port in self.__class__.__asgDataInputPorts__:
            for dataInput in port.getNodeInputsOf(self):
                yield dataInput

    def typeDependencies(self):
        for port in self.__class__.__asgTypeInputPorts__:
            for typeInput in port.getNodeInputsOf(self):
                yield typeInput

    def scheduledDataDependencies(self):
        return self.dataDependencies()

    def allDerivationNodes(self):
        for port in self.__class__.__asgConstructionAttributes__:
            for derivation in port.getNodeDerivationsOf(self):
                yield derivation

    def allDependencies(self):
        for dependency in self.sequencingDependencies():
            yield dependency
        for dependency in self.syntacticDependencies():
            yield dependency
        for dependency in self.effectDependencies():
            yield dependency
        for dependency in self.dataDependencies():
            yield dependency

    def divergenceDestinations(self):
        return ()
    
    def printNameWithDataAttributes(self) -> str:
        result = self.__class__.__asgKindName__
        attributes: list[ASGNodeAttributeDescriptor] = self.__class__.__asgDataAttributes__
        destIndex = 0;
        for attribute in attributes:
            if not attribute.isPrinted():
                continue

            if attribute.hasDefaultValueIn(self):
                continue

            if attribute.isFlag():
                if not attribute.loadValueFrom(self):
                    continue

            if destIndex == 0:
                result += '('
            else:
                result += ', '

            result += attribute.name
            if not attribute.isFlag():
                result += ' = '
                result += repr(attribute.loadValueFrom(self))
            destIndex += 1

        if destIndex != 0:
            result += ')'
                
        return result

    def getAllConstructionAttributes(self) -> list:
        return list(map(lambda attr: attr.loadValueFrom(self), self.__class__.__asgConstructionAttributes__))

    def printNameWithComparedAttributes(self) -> str:
        result = self.__class__.__asgKindName__
        attributes: list[ASGNodeAttributeDescriptor] = self.__class__.__asgConstructionAttributes__
        destIndex = 0;
        for attribute in attributes:
            if not attribute.isPrinted():
                continue

            if not attribute.isComparedForUnification():
                continue

            if attribute.hasDefaultValueIn(self):
                continue

            if destIndex == 0:
                result += '('
            else:
                result += ', '

            result += attribute.name
            result += ' = '
            attributeValue = attribute.loadValueFrom(self)
            if isinstance(attributeValue, tuple):
                result += '('
                for i in range(len(attributeValue)):
                    if i > 0:
                        result += ', '
                    result += str(attributeValue[i])
                result += ')'
            else:
                result += str(attributeValue)
            result += ('@%x' % attribute.hashFrom(self))
            destIndex += 1

        if destIndex != 0:
            result += ')'
                
        return result

    def prettyPrintNameWithDataAttributes(self) -> str:
        return self.printNameWithDataAttributes()
    
    def __str__(self) -> str:
        return self.printNameWithDataAttributes()
    
    def isKindOf(self, kind):
        return isinstance(self, kind)

    def betaReplaceableDependencies(self):
        if self.__betaReplaceableDependencies__ is not None:
            return self.__betaReplaceableDependencies__
        
        self.__betaReplaceableDependencies__ = set()
        if self.isBetaReplaceableNode():
            self.__betaReplaceableDependencies__.add(self)

        for dependency in self.allDependencies():
            if dependency not in self.__betaReplaceableDependencies__:
                for element in dependency.betaReplaceableDependencies():
                    self.__betaReplaceableDependencies__.add(element)
        return self.__betaReplaceableDependencies__

    def appendInFlattenedList(self, list: list):
        list.append(self)

    def directImmediateDominator(self):
        return None

    def dominanceTreeDepth(self):
        if self.__dominanceTreeDepth__ is None:
            idom = self.immediateDominator()
            if idom is not None:
                self.__dominanceTreeDepth__ = idom.dominanceTreeDepth() + 1
            else:
                self.__dominanceTreeDepth__ = 0

        return self.__dominanceTreeDepth__
    
    def isActivationContextParameterDataNode(self):
        return False

    def isConstructionDataNode(self):
        return False

    def isConstantDataNode(self):
        if self.__constantDataNodeCache__ is not None:
            return self.__constantDataNodeCache__
        
        if not self.isConstructionDataNode():
            self.__constantDataNodeCache__ = False;
            return False
        
        self.__constantDataNodeCache__ = True
        for dataDependency in self.dataDependencies():
            if not dataDependency.isConstantDataNode():
                self.__constantDataNodeCache__ = False
                break

        return self.__constantDataNodeCache__

    def interpretInContext(self, context, parameters):
        raise Exception('Cannot interpret %s.' % self.printNameWithDataAttributes())

class ASGUnificationComparisonNode:
    def __init__(self, node) -> None:
        self.node = node

    def __eq__(self, other: object) -> bool:
        return self.node.unificationEquals(other.node)
    
    def __hash__(self) -> int:
        return self.node.unificationHash()

class ASGPatternMatchingPattern(ABC):
    @abstractmethod
    def matchesNode(self, node: ASGNode):
        pass

    @abstractmethod
    def getExpectedKind(self) -> type:
        pass

    @abstractmethod
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        pass

class ASGPatternMatchingNodeKindPattern(ASGPatternMatchingPattern):
    def __init__(self, kind: type, function) -> None:
        super().__init__()
        self.kind = kind
        self.function = function

    def getExpectedKind(self) -> type:
        return self.kind

    def matchesNode(self, node):
        return True

    def __call__(self, algorithm, expansionResult, *args: Any, **kwArguments) -> Any:
        return self.function(algorithm, *args, **kwArguments)

class ASGPatternMatchingNodeKindPatternWithPredicate(ASGPatternMatchingNodeKindPattern):
    def __init__(self, kind: type, predicate, function) -> None:
        super().__init__(kind, function)
        self.predicate = predicate

    def matchesNode(self, node):
        return self.predicate(node)

class ASGRecursivePatternMatchingNodeKindPattern(ASGPatternMatchingNodeKindPattern):
    def __call__(self, algorithm, expansionResult, *args: Any, **kwArguments) -> Any:
        return self.function(algorithm, expansionResult, *args, **kwArguments)

class ASGRecursivePatternMatchingNodeKindPatternWithPredicate(ASGPatternMatchingNodeKindPatternWithPredicate):
    def __call__(self, algorithm, expansionResult, *args: Any, **kwArguments) -> Any:
        return self.function(algorithm, expansionResult, *args, **kwArguments)
    
def asgPatternMatchingOnNodeKind(kind: type, when = None):
    def makePattern(function):
        if when is not None:
            return ASGPatternMatchingNodeKindPatternWithPredicate(kind, when, function)
        else:
            return ASGPatternMatchingNodeKindPattern(kind, function)
    return makePattern

def asgRecursivePatternMatchingOnNodeKind(kind: type, when = None):
    def makePattern(function):
        if when is not None:
            return ASGRecursivePatternMatchingNodeKindPatternWithPredicate(kind, when, function)
        else:
            return ASGRecursivePatternMatchingNodeKindPattern(kind, function)
    return makePattern

class ASGUnifiedNodeValue:
    def __init__(self, node: ASGNode, derivation: ASGNodeDerivation) -> None:
        self.node = node
        self.derivation = derivation

    def asASGNode(self) -> ASGNode:
        return self.node
    
    def asASGNodeDerivation(self) -> ASGNodeDerivation:
        return self.derivation

    def asASGDataNode(self):
        return self.node.asASGDataNode()

    def asASGDataNodeDerivation(self):
        return self.node.asASGDataNodeDerivation()
    
    def asASGSequencingNode(self):
        return self.node.asASGSequencingNode()

    def asASGSequencingNodeDerivation(self):
        return self.node.asASGSequencingNodeDerivation()
    
    def asASGTypeNode(self):
        return self.node.asASGTypeNode()

    def asASGTypeNodeDerivation(self):
        return self.node.asASGTypeNodeDerivation()
    
    def isSequencingNode(self):
        return self.node.isSequencingNode()


class ASGDynamicProgrammingAlgorithmMetaclass(type):
    def __new__(cls, name, bases, attributes):
        patterns: list[ASGPatternMatchingNodeKindPattern] = []
        for base in bases:
            patterns += base.__asgDPAPatterns__

        for value in attributes.values():
            if isinstance(value, ASGPatternMatchingPattern):
                patterns.append(value)

        patternKindDictionary = {}
        for pattern in patterns:
            patternKind = pattern.getExpectedKind()
            if patternKind not in patternKindDictionary:
                patternKindDictionary[patternKind] = []
            patternKindDictionary[patternKind].append(pattern)

        algorithm = super().__new__(cls, name, bases, attributes)
        algorithm.__asgDPAPatterns__ = patterns
        algorithm.__asgDPAPatternKindDictionary__ = patternKindDictionary
        return algorithm

class ASGDynamicProgrammingAlgorithmNodeExpansionResult:
    def __init__(self, incomingDelegatingExpansion, node: ASGNode) -> None:
        self.incomingDelegatingExpansion: ASGDynamicProgrammingAlgorithmNodeExpansionResult = incomingDelegatingExpansion
        self.node = node
        self.hasFinished = False
        self.result = None

    def finishWithValue(self, resultValue):
        if self.hasFinished:
            if resultValue != self.result:
                raise Exception("Expansion of %s has diverging result values." % (self.node))
            return self.result

        self.hasFinished = True
        self.result = resultValue
        if self.incomingDelegatingExpansion is not None:
            self.incomingDelegatingExpansion.finishWithValue(resultValue)
        return resultValue
    
class ASGBuilderWithGVN:
    def __init__(self, parentBuilder) -> None:
        self.parentBuilder: ASGBuilderWithGVN = parentBuilder
        self.builtNodes = {}
        self.currentPredecessor = None

    def memento(self):
        return self.currentPredecessor

    def restoreMemento(self, memento):
        self.currentPredecessor = memento

    def unifyWithPreviousBuiltNode(self, node: ASGNode):
        if node is None:
            return None
        
        if not node.isPureDataNode():
            return node
        
        comparisonNode = ASGUnificationComparisonNode(node)
        unifiedNode = self.unifyChildNode(comparisonNode)
        if unifiedNode is not None:
            return ASGUnifiedNodeValue(unifiedNode.node, ASGNodeUnificationDerivation(node, unifiedNode.node))
        
        self.builtNodes[comparisonNode] = comparisonNode
        return node
    
    def unifyChildNode(self, node: ASGNode):
        unified = self.builtNodes.get(node, None)
        if unified is not None:
            return unified

        if self.parentBuilder is not None:
            return self.parentBuilder.unifyChildNode(node)
        return None
    
    def updatePredecessorWith(self, node: ASGNode):
        if node.asASGNode().isSequencingNode():
            self.currentPredecessor = node
        return node

    def build(self, kind, *arguments, **kwArguments) -> ASGNode | ASGUnifiedNodeValue:
        builtNode = kind(*arguments, **kwArguments)
        return self.updatePredecessorWith(self.unifyWithPreviousBuiltNode(builtNode))
    
    def forSyntaxExpansionBuild(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.build(kind, ASGNodeSyntaxExpansionDerivation(expansionAlgorithm, syntaxNode), *arguments, **kwArguments)

    def forSyntaxExpansionBuildAndSequence(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.updatePredecessorWith(self.forSyntaxExpansionBuild(expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments))

    def forCoercionExpansionBuild(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.build(kind, ASGNodeCoercionExpansionDerivation(expansionAlgorithm, syntaxNode), *arguments, **kwArguments)

    def forCoercionExpansionBuildAndSequence(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.updatePredecessorWith(self.forSyntaxExpansionBuild(expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments))

    def forMirExpansionBuild(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.build(kind, ASGNodeMirExpansionDerivation(expansionAlgorithm, syntaxNode), *arguments, **kwArguments)

    def forMirTypeExpansionBuild(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.build(kind, ASGNodeMirTypeExpansionDerivation(expansionAlgorithm, syntaxNode), *arguments, **kwArguments)

    def forMirExpansionBuildAndSequence(self, expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments):
        return self.updatePredecessorWith(self.forMirExpansionBuild(expansionAlgorithm, syntaxNode, kind, *arguments, **kwArguments))
        
class ASGDynamicProgrammingAlgorithm(metaclass = ASGDynamicProgrammingAlgorithmMetaclass):
    def __init__(self) -> None:
        self.processedNodes = {}

    def setValueForNodeExpansion(self, node, result):
        expansionResult = self.processedNodes.get(node, None)
        if expansionResult is not None:
            expansionResult.finishWithValue(result)
        else:
            expansionResult = ASGDynamicProgrammingAlgorithmNodeExpansionResult(None, node)
            expansionResult.finishWithValue(result)
            self.processedNodes[node] = expansionResult

    def postProcessResult(self, result):
        return result

    def fromNodeContinueExpanding(self, incomingDelegatingNode: ASGNode, node: ASGNode):
        expansionResult = self.processedNodes.get(node, None)
        if expansionResult is not None:
            if not expansionResult.hasFinished:
                raise Exception('Circular dependency in expansion of node %s' % str(node))

            return expansionResult.result

        patternKindDictionary = self.__class__.__asgDPAPatternKindDictionary__
        currentClass = node.__class__
        while currentClass is not None:
            patterns: list[ASGPatternMatchingNodeKindPattern] | None = patternKindDictionary.get(currentClass, None)
            if patterns is not None:
                for pattern in patterns:
                    if pattern.matchesNode(node):
                        incomingExpansion = None
                        if incomingDelegatingNode is not None:
                            incomingExpansion = self.processedNodes[incomingDelegatingNode]

                        expansionResult = ASGDynamicProgrammingAlgorithmNodeExpansionResult(incomingExpansion, node)
                        self.processedNodes[node] = expansionResult

                        patternResult = pattern(self, expansionResult, node)
                        patternResult = self.postProcessResult(patternResult)
                        return expansionResult.finishWithValue(patternResult)

            if len(currentClass.__bases__) != 0:
                currentClass = currentClass.__bases__[0]
            else:
                currentClass = None
        raise Exception("Failed to find matching pattern for %s in %s." % (str(node), str(self)))
    
    def __call__(self, node: ASGNode) -> Any:
        return self.fromNodeContinueExpanding(None, node)

class ASGDynamicProgrammingReductionAlgorithm(ASGDynamicProgrammingAlgorithm):
    def reduceNode(self, node: ASGNode):
        return self(node)
    
    def reduceAttribute(self, attribute):
        if isinstance(attribute, ASGNode):
            return self.reduceNode(attribute)
        else:
            return attribute

    @asgPatternMatchingOnNodeKind(ASGNode)
    def reduceGenericNode(self, node: ASGNode) -> ASGNode:
        return self.reduceGenericNodeRecursively(node)
    
    def reduceGenericNodeRecursively(self, node: ASGNode):
        nodeAttributes = node.getAllConstructionAttributes()
        reducedAttributes = []
        hasReducedAttribute = False
        for attribute in nodeAttributes:
            reducedAttribute = self.reduceAttribute(attribute)
            hasReducedAttribute = hasReducedAttribute or reducedAttribute is not attribute
            reducedAttributes.append(reducedAttribute)

        if hasReducedAttribute:
            return self.fromNodeContinueExpanding(node, node.__class__(*reducedAttributes))
        else:
            return node
        
def asgPredecessorTopoSortDo(startingNode, aBlock):
    visited = set()
    def visitNode(node):
        if node in visited:
            return
        
        visited.add(node)
        for pred in node.sequencingDependencies():
            visitNode(pred)
        aBlock(node)

    visitNode(startingNode)

def asgPredecessorTopo(startingNode):
    topoSort = []
    asgPredecessorTopoSortDo(startingNode, topoSort.append)
    return topoSort