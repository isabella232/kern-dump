import os, sys
#import inspect
from fontTools import ttLib

'''
Gets all possible kerning pairs within font.
Supports RTL.

2013-01-22:
Working with Bickham Script pro 3 and its many subtables, it was discovered that 
the script reports many more pairs than actually exist. Investigate!

'''

kKernFeatureTag = 'kern'
kGPOStableName = 'GPOS'
finalList = []
# AFMlist = []


class myLeftClass:
    def __init__(self):
        self.glyphs = []
        self.class1Record = 0


class myRightClass:
    def __init__(self):
        self.glyphs = []
        self.class2Record = 0


def collectUniqueKernLookupListIndexes(featureRecord):
    uniqueKernLookupIndexList = []
    for featRecItem in featureRecord:
        # print featRecItem.FeatureTag  
        # GPOS feature tags (e.g. kern, mark, mkmk, size) of each ScriptRecord
        if featRecItem.FeatureTag == kKernFeatureTag:
            feature = featRecItem.Feature

            for featLookupItem in feature.LookupListIndex:
                if featLookupItem not in uniqueKernLookupIndexList:
                    uniqueKernLookupIndexList.append(featLookupItem)
    
    return uniqueKernLookupIndexList


class Analyze(object):
    def __init__(self, fontPath):
        self.font = ttLib.TTFont(fontPath)
        self.kerningPairs = {}
        self.singlePairs = {}
        # self.firstGlyphsList = []
        # self.firstGlyphsDict = {} # contains the first glyph of the pair, has two pairPosFormat keys, one for class kerning, the other for pair kerning
        self.pairPosList = []

        if kGPOStableName not in self.font:
            print "The font has no %s table" % kGPOStableName
            self.goodbye()

        self.analyzeFont()
        self.findKerningLookups()
        self.getPairPos()
        self.getSinglePairs()
        self.getClassPairs()


    def goodbye(self):
        print 'Aborted.'
        return


    def analyzeFont(self):
        self.gposTable = self.font[kGPOStableName].table

        'ScriptList:'
        self.scriptList = self.gposTable.ScriptList
        'FeatureList:'
        self.featureList = self.gposTable.FeatureList

        self.featureCount = self.featureList.FeatureCount
        self.featureRecord = self.featureList.FeatureRecord

        self.uniqueKernLookupIndexList = collectUniqueKernLookupListIndexes(self.featureRecord)


    def findKerningLookups(self):
        if not len(self.uniqueKernLookupIndexList):
            print "The font has no %s feature" % kKernFeatureTag
            self.goodbye()

        'LookupList:'
        self.lookupList = self.gposTable.LookupList
        self.lookups = []
        for kernLookupIndex in sorted(self.uniqueKernLookupIndexList):
            lookup = self.lookupList.Lookup[kernLookupIndex]

            # Confirm this is a GPOS LookupType 2; or using an extension table (GPOS LookupType 9):

            '''
            Lookup types:
            1   Single adjustment           Adjust position of a single glyph
            2   Pair adjustment             Adjust position of a pair of glyphs
            3   Cursive attachment          Attach cursive glyphs
            4   MarkToBase attachment       Attach a combining mark to a base glyph
            5   MarkToLigature attachment   Attach a combining mark to a ligature
            6   MarkToMark attachment       Attach a combining mark to another mark
            7   Context positioning         Position one or more glyphs in context
            8   Chained Context positioning Position one or more glyphs in chained context
            9   Extension positioning       Extension mechanism for other positionings
            10+ Reserved                    For future use
            '''

            if lookup.LookupType not in [2, 9]:
                print "This is not a pair adjustment positioning lookup (GPOS LookupType 2); or using an extension table (GPOS LookupType 9)."
                continue
            self.lookups.append(lookup)


    def getPairPos(self):
        for lookup in self.lookups:
            for subtableItem in lookup.SubTable:

                if subtableItem.LookupType == 2: # normal case, not using extension table
                    pairPos = subtableItem

                elif subtableItem.LookupType == 9: # extension table
                    if subtableItem.ExtensionLookupType == 8: # contextual
                        print 'Contextual Kerning not (yet?) supported.'
                        continue
                    elif subtableItem.ExtensionLookupType == 2:
                        pairPos = subtableItem.ExtSubTable
                
                # print pairPos, pairPos.Format, pairPos.Coverage.Format 

                # if pairPos.Coverage.Format not in [1, 2]:
                if pairPos.Coverage.Format not in [1, 2]:
                    print "WARNING: Coverage format %d is not yet supported" % pairPos.Coverage.Format
                
                if pairPos.ValueFormat1 not in [0, 4, 5]:
                    print "WARNING: ValueFormat1 format %d is not yet supported" % pairPos.ValueFormat1
                
                if pairPos.ValueFormat2 not in [0]:
                    print "WARNING: ValueFormat2 format %d is not yet supported" % pairPos.ValueFormat2


                self.pairPosList.append(pairPos)
                
                # Each glyph in this list will have a corresponding PairSet which will
                # contain all the second glyphs and the kerning value in the form of PairValueRecord(s)
                # self.firstGlyphsDict[pairPos.Format] = pairPos.Coverage.glyphs

                # self.firstGlyphsList.extend(pairPos.Coverage.glyphs)


    def getSinglePairs(self):
        for pairPos in self.pairPosList:
            if pairPos.Format == 1: 
                # single pair adjustment

                firstGlyphsList = pairPos.Coverage.glyphs

                # This iteration is done by index so that we have a way to reference the firstGlyphsList list
                for pairSetIndex, pairSetInstance in enumerate(pairPos.PairSet):
                    for pairValueRecordItem in pairPos.PairSet[pairSetIndex].PairValueRecord:
                        secondGlyph = pairValueRecordItem.SecondGlyph
                        valueFormat = pairPos.ValueFormat1
                        if valueFormat == 5: # RTL kerning
                            kernValue = "<%d 0 %d 0>" % (pairValueRecordItem.Value1.XPlacement, pairValueRecordItem.Value1.XAdvance)
                        elif valueFormat == 0: # RTL pair with value <0 0 0 0>
                            kernValue = "<0 0 0 0>"
                        elif valueFormat == 4: # LTR kerning
                            kernValue = pairValueRecordItem.Value1.XAdvance
                        else:
                            print "\tValueFormat1 = %d" % valueFormat
                            continue # skip the rest
                        
                        self.kerningPairs[(firstGlyphsList[pairSetIndex], secondGlyph)] = kernValue
                        self.singlePairs[(firstGlyphsList[pairSetIndex], secondGlyph)] = kernValue

                        # self.kerningPairs[(self.firstGlyphsDict[pairPos.Format][pairSetIndex], secondGlyph)] = kernValue
                        # self.singlePairs[(self.firstGlyphsDict[pairPos.Format][pairSetIndex], secondGlyph)] = kernValue


    def getClassPairs(self):
        for loop, pairPos in enumerate(self.pairPosList):
            if pairPos.Format == 2: 
                # class pair adjustment

                firstGlyphsList = pairPos.Coverage.glyphs

                firstGlyphs = {}
                secondGlyphs = {}

                leftClasses = {}
                rightClasses = {}
                

                # Find left class with the Class1Record index="0".
                # This first class is mixed into the "Coverage" table (e.g. all left glyphs)
                # and has no class="X" property, that is why we have to find them that way. 
                
                lg0 = myLeftClass()
                # list of all glyphs kerned to the left of a pair, including all glyphs contained within kerning classes:
                allLeftGlyphs = firstGlyphsList
                # list of all glyphs contained within left-sided kerning classes:
                allLeftClassGlyphs = pairPos.ClassDef1.classDefs.keys()

                allLeftGlyphs.sort()
                allLeftClassGlyphs.sort()
                lg0.glyphs = list(set(allLeftGlyphs) - set(allLeftClassGlyphs))
                lg0.glyphs.sort()

                leftClasses[lg0.class1Record] = lg0

                # Find all the remaining left classes:
                for leftGlyph in pairPos.ClassDef1.classDefs:
                    class1Record = pairPos.ClassDef1.classDefs[leftGlyph]
                    lg = myLeftClass()
                    lg.class1Record = class1Record
                    if class1Record != 0: # this was the crucial line.
                        leftClasses.setdefault(class1Record, lg).glyphs.append(leftGlyph)

                    # if class1Record in leftClasses:
                    #     leftClasses[class1Record].glyphs.append(leftGlyph)
                    # else:
                    #     lg = myLeftClass()
                    #     lg.class1Record = class1Record
                    #     leftClasses[class1Record] = lg
                    #     leftClasses[class1Record].glyphs.append(leftGlyph)

                # Same for the right classes:
                for rightGlyph in pairPos.ClassDef2.classDefs:                    
                    class2Record = pairPos.ClassDef2.classDefs[rightGlyph]
                    if class2Record in rightClasses:
                        rightClasses[class2Record].glyphs.append(rightGlyph)
                    else:
                        rg = myRightClass()
                        rg.class2Record = class2Record
                        rightClasses[class2Record] = rg
                        rightClasses[class2Record].glyphs.append(rightGlyph)
                
                # for cl in leftClasses:
                #     print cl, leftClasses[cl].glyphs
                #     print loop
                #     print


                for record_l in leftClasses:
                    for record_r in rightClasses:
                        if pairPos.Class1Record[record_l].Class2Record[record_r]:
                            valueFormat = pairPos.ValueFormat1
                            
                            if valueFormat in [4, 5]:
                                kernValue = pairPos.Class1Record[record_l].Class2Record[record_r].Value1.XAdvance
                            elif valueFormat == 0: # valueFormat zero is caused by a value of <0 0 0 0> on a class-class pair; skip these
                                continue
                            else:
                                print "\tValueFormat1 = %d" % valueFormat
                                continue # skip the rest
                            
                            if kernValue != 0:
                                for l in leftClasses[record_l].glyphs:
                                    for r in rightClasses[record_r].glyphs:
                                        if (l, r) in self.kerningPairs:
                                            # if the kerning pair has already been assigned in pair-to-pair kerning
                                            continue
                                        else:
                                            if valueFormat == 5: # RTL kerning
                                                kernValue = "<%d 0 %d 0>" % (pairPos.Class1Record[record_l].Class2Record[record_r].Value1.XPlacement, pairPos.Class1Record[record_l].Class2Record[record_r].Value1.XAdvance)
                                            

                                            self.kerningPairs[(l, r)] = kernValue
                            
                        else:
                            print 'ERROR'





if __name__ == "__main__":
    if len(sys.argv) == 2:
        if os.path.exists(sys.argv[1]):
            fontPath = sys.argv[1]
            f = Analyze(fontPath)

            # for c in f.leftClasses:
            #     print 'leftClass:', c, f.leftClasses[c].glyphs

            # for c in f.rightClasses:
            #     print 'rightClass:', c, f.rightClasses[c].glyphs


            # for x in f.lookups:
            #     print x

            finalList = []
            for pair, value in f.kerningPairs.items():
                finalList.append('/%s /%s %s' % ( pair[0], pair[1], value ))

            finalList.sort()

            output = '\n'.join(finalList)
            # print output

            print len(f.kerningPairs)
            # print len(f.singlePairs)

    else:
        print "No valid font provided."