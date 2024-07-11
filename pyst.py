#!/usr/bin/env python3

import sys
import json
import os.path

class FrontEndDriver:
    def __init__(self) -> None:
        self.module = None
        self.moduleName = None
        self.topFolder = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
        self.inputSourceFiles = []
        self.includeDirectories = [
            os.path.join(self.topFolder, 'module-sources')
        ]
        self.analyzedSources = []
        self.outputFileName = 'a.out'
        self.verbose = False
        self.isDone = False

    def printHelp(self):
        print(
"""pyst.py [options] <input files>* [-- <evaluation args> ]
-h -help --help             Prints this message.
-version --version          Prints the version information.
-v                          Enable the verbosity in the output.
-o                          Sets the output file name.
"""
        )

    def printVersion(self):
        print("sysmelbc.py version 0.1")

    def parseCommandLineArguments(self, argv):
        i = 1
        while i < len(argv):
            arg = argv[i]
            i += 1
            if len(arg) > 0 and arg[0] == '-':
                if arg in ['-h', '-help', '--help']:
                    self.printHelp()
                    self.isDone = True
                    return True
                elif arg in ['-version', '--version']:
                    self.printVersion()
                    self.isDone = True
                    return True
                elif arg in ['-v']:
                    self.verbose = True
                elif arg in ['-o']:
                    if i >= len(argv):
                        self.printHelp()
                        return False

                    self.outputFileName = argv[i]
                    i += 1
            else:
                self.inputSourceFiles.append(arg)
        return True

    def parseAndAnalyzeSourceFile(self, sourceFile):
        from pyst.parser import parseFileNamed
        from pyst.parsetree import ParseTreeErrorVisitor
        from pyst.syntax import ASGParseTreeFrontEnd
        from pyst.analysis import expandAndAnalyze
        from pyst.visualizations import asgToDotFileNamed, asgWithDerivationsToDotFileNamed
        from pyst.environment import makeScriptAnalysisEnvironment
        from pyst.mop import asgPredecessorTopoSortDo

        parseTree = parseFileNamed(sourceFile)
        if not ParseTreeErrorVisitor().checkAndPrintErrors(parseTree):
            return False

        asgSyntax = ASGParseTreeFrontEnd().visitNode(parseTree)
        asgToDotFileNamed(asgSyntax, 'asgSyntax.dot')

        asgAnalyzed, asgAnalysisErrors = expandAndAnalyze(makeScriptAnalysisEnvironment(asgSyntax.sourceDerivation.getSourcePosition(), sourceFile), asgSyntax)
        asgToDotFileNamed(asgAnalyzed, 'asgAnalyzed.dot')
        asgWithDerivationsToDotFileNamed(asgAnalyzed, 'asgAnalyzedWithDerivation.dot')
        for error in asgAnalysisErrors:
            sys.stderr.write('%s\n' % error.prettyPrintError())
        self.analyzedSources.append(asgAnalyzed)
        return len(asgAnalysisErrors) == 0

    def parseAndAnalyzeSourceFiles(self):
        success = True
        for inputSource in self.inputSourceFiles:
            if not self.parseAndAnalyzeSourceFile(inputSource):
                success = False
        return success

    def evaluateAnalyzedSource(self, analyzedSource):
        from pyst.gcm import topLevelScriptGCM
        gcm = topLevelScriptGCM(analyzedSource)
        interpretableScript = gcm.asInterpretableInstructions()
        #print('Toplevel script', interpretableScript.dump())
        interpretableScript.dumpDotToFileNamed('toplevelGCM.dot')
        scriptResult = interpretableScript.evaluateWithArguments()
        return scriptResult

    def evaluateAnalyzedSources(self):
        for analyzedSource in self.analyzedSources:
            evalResult = self.evaluateAnalyzedSource(analyzedSource)
            if self.verbose and evalResult is not None:
                print(evalResult)
        return True
    
    def runPipeline(self):
        if not self.parseAndAnalyzeSourceFiles():
            return False

        if not self.evaluateAnalyzedSources():
            return False
        
        return True
    
    def main(self, argv):
        if not self.parseCommandLineArguments(argv):
            return False
        if len(self.inputSourceFiles) == 0:
            self.printHelp()
            return True
        return self.runPipeline()    

if __name__ == "__main__":
    if not FrontEndDriver().main(sys.argv):
        sys.exit(1)
