from .mop import *
from .asg import *
from .interpreter import ASGNodeWithInterpretableInstructions

class ASGNodeWithInstructionScheduling:
    def __init__(self, functionalNode, activationParameters, constants, serializedInstructions) -> None:
        self.functionalNode = functionalNode
        self.activationParameters = activationParameters
        self.constants = constants
        self.serializedInstructions = serializedInstructions

    def enumerateForInterpretation(self):
        for node in self.constants:
            yield node
        for node in self.activationParameters:
            yield node
        for node in self.serializedInstructions:
            yield node

    def enumerateForTargetCompilation(self):
        for node in self.activationParameters:
            yield node 
        for node in self.constants:
            yield node 
        for node in self.serializedInstructions:
            yield node 

    def asInterpretableInstructions(self):
        return ASGNodeWithInterpretableInstructions(self.functionalNode, list(self.enumerateForInterpretation()), len(self.constants), len(self.activationParameters))

class InstructionUserList:
    def __init__(self) -> None:
        self.users = []
        self.usersSet = set()
    
    def addUser(self, user):
        if user in self.usersSet:
            return

        self.users.append(user)
        self.usersSet.add(user)

class GlobalCodeMotionAlgorithm:
    """
    Global Code Motion algorithm implementation. See
    Cliff Click "Global Code Motion. Global Value Numbering." for a detailed description of the algorithm.
    """
    def __init__(self, functionalNode) -> None:
        self.functionalNode = functionalNode
        self.regions = []
        self.regionToIndexDictionary = {}
        self.loopNestingLevels = []
        self.activationContextParameterInstructions = []
        self.dataInstructions = []
        self.dataInstructionUserLists = []
        self.dataInstructionIndexDictionary = {}
        self.pinnedDataInstructions = []
        self.idoms = []
        self.dominanceTreeDepths = []
        self.earlySchedule = []
        self.scheduleRegions = []

    def computeForBlock(self):
        blockNode: ASGBlockDefinitionNode = self.functionalNode
        self.computeForRegions(blockNode.captures + blockNode.arguments, asgPredecessorTopo(blockNode.exitPoint))
        return self.serializeInstructions()

    def computeForTopLevelScript(self):
        topLevelScript: ASGTopLevelScriptNode = self.functionalNode
        self.computeForRegions([], asgPredecessorTopo(topLevelScript.exitPoint))
        return self.serializeInstructions()

    def dependenciesOf(self, instruction):
        for dep in instruction.scheduledDataDependencies():
            yield dep

    def computeForRegions(self, activationParameters, regions):
        self.regions = regions
        self.findDataInstructions(activationParameters)
        self.computeUserLists()
        for i in range(len(regions)):
            region = regions[i]
            self.regionToIndexDictionary[region] = i

        # The direct immediate dominators are missing the divergence destinations.
        self.idoms = list(map(lambda r: self.regionToIndexDictionary.get(r.directImmediateDominator(), None), regions))
        for regionIndex in range(len(regions)):
            region = regions[regionIndex]
            for divergenceDestination in region.divergenceDestinations():
                destinationIndex = self.regionToIndexDictionary[divergenceDestination]
                assert self.idoms[destinationIndex] is None
                self.idoms[destinationIndex] = regionIndex

        # Dominance tree depths.
        self.dominanceTreeDepths = [None] * len(regions)
        for i in range(len(regions)):
            self.computeDominanceTreeDepthAtIndex(i)

        # Compute the loop nesting levels.
        self.computeLoopNestingLevels()

        # Early and late schedule the instructions
        self.earlyScheduleInstructions()
        self.lateScheduleInstructions()

    def findDataInstructions(self, activationParameters):
        visited = set()
        self.dataInstructions = []
        self.dataInstructionIndexDictionary = {}
        self.constantDataInstructions = []
        
        def traverseNode(node):
            if node in visited:
                return
            
            visited.add(node)
            if not node.isConstantDataNode():
                for dependency in self.dependenciesOf(node):
                    if dependency in visited:
                        continue

                    traverseNode(dependency)

            if node.isPureDataNode() or node.isStatefullDataNode():
                if node.isActivationContextParameterDataNode():
                    self.activationContextParameterInstructions.append(node)
                elif node.isConstantDataNode():
                    self.constantDataInstructions.append(node)
                else:
                    self.dataInstructionIndexDictionary[node] = len(self.dataInstructions)
                    self.dataInstructions.append(node)

        for activationParameter in activationParameters:
            traverseNode(activationParameter)
        for region in self.regions:
            traverseNode(region)

    def computeUserLists(self):
        self.dataInstructionUserLists = []
        for i in range(len(self.dataInstructions)):
            self.dataInstructionUserLists.append(InstructionUserList())

        def visitNode(user):
            for dependency in user.dataDependencies():
                if dependency in self.dataInstructionIndexDictionary:
                    self.dataInstructionUserLists[self.dataInstructionIndexDictionary[dependency]].addUser(user)

        for region in self.regions:
            visitNode(region)

        for dataInstruction in self.dataInstructions:
            visitNode(dataInstruction)

    def computeDominanceTreeDepthAtIndex(self, index):
        if self.dominanceTreeDepths[index] is None:
            idom = self.idoms[index]
            if idom is None:
                self.dominanceTreeDepths[index] = 0
            else:
                self.dominanceTreeDepths[index] = self.computeDominanceTreeDepthAtIndex(idom) + 1
        
        return self.dominanceTreeDepths[index]
    
    def computeLoopNestingLevels(self):
        self.loopNestingLevels = [0] * len(self.regions)
    
    def earlyScheduleInstructions(self):
        self.earlySchedule = [0] * len(self.dataInstructions)
        self.pinnedDataInstructions = [False] * len(self.dataInstructions)
        visited = [False] * len(self.dataInstructions)

        # Pin the phi instructions
        def pinInstructionToRegion(instruction, region):
            assert region is not None
            regionIndex = self.regionToIndexDictionary[region]
            instructionIndex = self.dataInstructionIndexDictionary[instruction]
            assert not self.pinnedDataInstructions[instructionIndex]
            self.earlySchedule[instructionIndex] = regionIndex
            self.pinnedDataInstructions[instructionIndex] = True

        for instruction in self.dataInstructions:
            if not instruction.isPhiNode():
                continue
            
            phi: ASGPhiNode = instruction
            region = phi.predecessor
            pinInstructionToRegion(phi, region)
            for incomingValue in phi.values:
                pinInstructionToRegion(incomingValue, incomingValue.predecessor)

        def visitInstruction(instructionIndex):
            if visited[instructionIndex]:
                return True
            
            visited[instructionIndex] = True
            instruction = self.dataInstructions[instructionIndex]

            for dependency in instruction.dataDependencies():
                if dependency not in self.dataInstructionIndexDictionary:
                    continue

                dependencyIndex = self.dataInstructionIndexDictionary[dependency]
                visitInstruction(dependencyIndex)

                if not self.pinnedDataInstructions[instructionIndex]:
                    dependencyRegion = self.earlySchedule[dependencyIndex]
                    dependencyRegionDepth = self.dominanceTreeDepths[dependencyRegion]

                    instructionRegion = self.earlySchedule[instructionIndex]
                    instructionRegionDepth = self.dominanceTreeDepths[instructionRegion]
                    if instructionRegionDepth < dependencyRegionDepth:
                        self.earlySchedule[instructionIndex] = self.earlySchedule[dependencyIndex]

        for i in range(len(self.dataInstructions)):
            visitInstruction(i)

    def lateScheduleInstructions(self):
        self.scheduleRegions = list(self.earlySchedule)
        visited = [False] * len(self.dataInstructions)

        def blockIndexOfInstructionUserOf(instructionOrRegion, usedValue):
            instructionIndex = self.dataInstructionIndexDictionary.get(instructionOrRegion, None)
            if instructionIndex is not None:
                return self.scheduleRegions[instructionIndex]
            
            userRegion = instructionOrRegion.getRegionOfUsedValue(usedValue)
            assert userRegion is not None
            return self.regionToIndexDictionary[userRegion]

        def visitInstruction(instruction):
            instructionIndex = self.dataInstructionIndexDictionary.get(instruction, None)
            if instructionIndex is None or visited[instructionIndex]:
                return
            visited[instructionIndex] = True

            lca = None
            for user in self.dataInstructionUserLists[instructionIndex].users:
                visitInstruction(user)
                userBlockIndex = blockIndexOfInstructionUserOf(user, instruction)
                lca = self.computeBlockLCA(lca, userBlockIndex)

            assert lca is not None
            bestBlock = lca
            while lca != self.scheduleRegions[instructionIndex]:
                if self.loopNestingLevels[lca] < bestBlock:
                    bestBlock = lca
                lca = self.idoms[lca]
            self.scheduleRegions[instructionIndex] = bestBlock
        
        for i in range(len(self.dataInstructions)):
            if self.pinnedDataInstructions[i]:
                visited[i] = True
                for user in self.dataInstructionUserLists[i].users:
                    visitInstruction(user)

        # Visit the remaining data instructions
        for i in range(len(self.dataInstructions)):
            if not visited[i]:
                visitInstruction(self.dataInstructions[i])

    def computeBlockLCA(self, a, b):
        if a is None:
            return b

        # Climb until the same level
        while self.dominanceTreeDepths[a] > self.dominanceTreeDepths[b]:
            a = self.idoms[a]
        while self.dominanceTreeDepths[b] > self.dominanceTreeDepths[a]:
            b = self.idoms[b]

        # Climb until the same
        while a != b:
            a = self.idoms[a]
            b = self.idoms[b]
        return a
    
    def serializeInstructions(self):
        # Group the instructions by region
        perRegionInstructions = []
        for i in range(len(self.regions)):
            perRegionInstructions.append([])

        for i in range(len(self.scheduleRegions)):
            perRegionInstructions[self.scheduleRegions[i]].append(self.dataInstructions[i])

        # Sort the region instructions
        perRegionSortedInstructions = list(map(self.sortRegionInstructions, perRegionInstructions))

        # Serialize the instructions themselves
        serializedInstructions = []
        for i in range(len(self.regions)):
            serializedInstructions.append(self.regions[i])
            serializedInstructions += perRegionSortedInstructions[i]
            
        return ASGNodeWithInstructionScheduling(self.functionalNode, self.activationContextParameterInstructions, self.constantDataInstructions, serializedInstructions)
    
    def sortRegionInstructions(self, instructions):
        sortedPhiInstructions = []
        sortedInstructions = []
        sortedPhiValueInstructions = []
        instructionsSet = set(instructions)
        visitedSet = set(sortedInstructions)

        def visitInstruction(instruction):
            if instruction in visitedSet or instruction not in instructionsSet:
                return
            visitedSet.add(instruction)
            
            for dependency in instruction.dataDependencies():
                visitInstruction(dependency)

            if instruction.isPhiNode():
                sortedPhiInstructions.append(instruction)
            elif instruction.isPhiValueNode():
                sortedPhiValueInstructions.append(instruction)
            else:
                sortedInstructions.append(instruction)


        for instruction in instructions:
            visitInstruction(instruction)

        return sortedPhiInstructions + sortedInstructions + sortedPhiValueInstructions

def blockGCM(node: ASGBlockDefinitionNode):
    blockWithGcm = GlobalCodeMotionAlgorithm(node).computeForBlock()
    return blockWithGcm

def topLevelScriptGCM(node: ASGTopLevelScriptNode):
    topLevelScriptGCM = GlobalCodeMotionAlgorithm(node).computeForTopLevelScript()
    return topLevelScriptGCM
