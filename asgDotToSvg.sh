#!/bin/sh
set -ex

dot -Tsvg asgSyntax.dot > asgSyntax.svg
dot -Tsvg asgAnalyzed.dot > asgAnalyzed.svg
dot -Tsvg asgAnalyzedWithDerivation.dot > asgAnalyzedWithDerivation.svg
dot -Tsvg toplevelGCM.dot > toplevelGCM.svg
