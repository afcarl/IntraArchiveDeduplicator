


import UniversalArchiveReader
import os
import os.path
import logging

import hashFile
import dbApi
import shutil
import traceback
import sql.operators as sqlo

import pyximport
print("Have Cython")
pyximport.install()

import deduplicator.cyHamDb as hamDb

PHASH_DISTANCE_THRESHOLD = 2


class TreeRoot(hamDb.BkHammingTree):

	def __init__(self):
		self.db       = dbApi.DbApi()
		self.log      = logging.getLogger("Main.Tree")
		super().__init__()

	def loadTree(self, treeRootPath):


		self.log.info("Loading contents of '%s' into BK tree", treeRootPath)
		items = self.db.getLike('fsPath', treeRootPath, wantCols=['dbId', 'pHash'])
		self.log.info("Found %s items in dir. Building tree", len(items))


		for dbId, pHash in items:
			if not pHash:
				continue
			pHash = pHash
			self.insert(pHash, dbId)

		self.rootPath = treeRootPath

		self.log.info("Tree loaded!")

	# We have to be careful, because if we try to remove a item outside the tree's
	# envelope, we'll get a KeyError. Therefore, we intercept calls to remove, require an
	# additional parameter (the path of the file containing the item we're removing),
	# and verify that the item that is being removed is valid to remove.
	# I'm doing this rather then just blindly catching KeyError because I want
	# any attempts to remove a key that /should/ be in the dict to still error.
	def remove(self, filePath, nodeHash, nodeData):
		if filePath.startswith(self.rootPath):
			super().remove(nodeHash, nodeData)






class TreeProcessor(object):

	def __init__(self, matchDir, removeDir, distanceThresh, callBack=None):
		self.log      = logging.getLogger("Main.Processor")

		print("Loading treestructure for path '%s'" % matchDir)
		self.root = TreeRoot()
		self.matchDir = matchDir

		# This doesn't seem to fit too well as a class attribute here, but I cannot
		# Think of anywhere else to put it.
		self.distance = distanceThresh

		# Items are moved to removeDir for manual deletion
		self.delProxyDir = removeDir
		self.root.loadTree(matchDir)

		self.callBack = callBack

	def convertToPath(self, inId):
		return self.root.db.getItems(wantCols=['fsPath', "internalPath"], dbId=inId).pop()

	def getMatches(self, item):

		# If the item doesn't have a phash (not an image?), check for binary duplicates
		if not item['pHash']:

			where = (sqlo.Like(self.root.db.table.fspath, self.matchDir+'%') & (self.root.db.table.itemhash == item['itemHash']))
			matches = self.root.db.getItems(wantCols=["dbId"], where=where)

			return matches

		# For items where we have a phash, look it up.
		matches = self.root.getWithinDistance(item['pHash'], self.distance)
		if item['dbId'] in matches:
			matches.remove(item['dbId'])

		ret = []
		for match in matches:
			itemPath, dummy_intpath = self.convertToPath(match)
			if itemPath != item["fsPath"]:
				if not os.path.exists(itemPath):
					self.log.warn("Item no longer exists!")
					continue
				ret.append(match)

		# print("phash matches", matches)
		return matches


	def trimTree(self, fileItems):
		for item in fileItems:
			self.root.remove(item['fsPath'], item['pHash'], item['dbId'])


	def scanItems(self, internalItems):

		pathMatches = {}
		seen = [0] * len(internalItems)
		offset = 0
		for item in internalItems:
			fMatches = self.getMatches(item)
			if not fMatches:
				self.log.info("Not duplicate: '%s'", item['fsPath'])
				return False
			for match in fMatches:
				seen[offset] += 1

				itemPath, intPath = self.convertToPath(match)
				if not os.path.exists(itemPath):
					self.log.error("Item has been deleted. Skipping match.")
					return False

				if itemPath not in pathMatches:
					pathMatches[itemPath] = set()

				pathMatches[itemPath].add(intPath)

			offset += 1
		if not all(seen):
			self.log.error("Wat? Not all items seen and yet loop is complete?")
			raise ValueError("Wat? Not all items seen and yet loop is complete?")

		return pathMatches

	# So this is rather confusing. We want to determine the "best" match, but we have
	# a lot of spurious matches.
	# As such, we count the number of distinct matches, then the total number of items in
	# the matching file, and sort using those parameters, and chose the one with the most distinct
	# matches, using the file quantities as the tie-breaker.
	# I have some ideas for using multiple
	def processMatches(self, filePath, pathMatches):

		items = []
		for archPath, intItemSet in pathMatches.items():

			# Build compound query so we can get only items where pHash is not NULL

			itemNum = self.root.db.getNumberOfPhashes(fsPath=archPath)

			items.append((len(intItemSet), itemNum, archPath))
			# print("archPath, intItemSet", archPath, len(intItemSet), itemNum)

		# Do the actual sort
		items.sort(reverse=True)
		baseItemNum = self.root.db.getNumberOfPhashes(fsPath=filePath)
		for commonSet, matchSize, matchFilePath in items[:5]:
			self.log.info("	Match: '%s', '%s', %s', '%s'", baseItemNum, commonSet, matchSize, matchFilePath)


		items.sort(reverse=True)
		return items[0][-1]


	# Called once for each distinct file on scanned path.
	# Fileitems are the contained files within the scanned file, if any
	def processFile(self, filePath, fileItems):
		self.log.info("Processing file '%s'", filePath)

		if not os.path.exists(filePath):
			self.log.error("Item no longer exists = '%s'", filePath)
			return

		# Only look at files where there are phashes contained
		if not any([item['pHash'] != None for item in fileItems]):
			return

		# There should only be one item with no internal path (the containing archive)
		# Check this to be sure
		if len([item for item in fileItems if not item['internalPath']]) != 1:
			self.log.error("Multiple no-path items?")
			return

		internalItems = [item for item in fileItems if item['internalPath']]

		pathMatches = self.scanItems(internalItems)
		if not pathMatches:
			return

		self.trimTree(internalItems)

		self.log.info("Item is NOT unique '%s'", filePath)
		bestMatch = self.processMatches(filePath, pathMatches)

		if self.callBack:
			self.callBack(filePath, bestMatch)
		self.handleDuplicate(filePath, bestMatch)

	def handleDuplicate(self, deletedFile, bestMatch):

		# When we have a callback, call the callback so it can do whatever it need to
		# with the information about the duplicate.


		dst = deletedFile.replace("/", ";")
		dst = os.path.join(self.delProxyDir, dst)
		self.log.info("Moving item from '%s'", deletedFile)
		self.log.info("	to '%s'", dst)
		try:
			shutil.move(deletedFile, dst)
		except KeyboardInterrupt:
			raise
		except OSError:
			self.log.error("ERROR - Could not move file!")
			self.log.error(traceback.format_exc())





	def trimFiles(self, targetDir):
		self.log.info("Trimming files on path '%s'", targetDir)
		delItems = self.root.db.getFileDictLikeBasePath(targetDir)
		self.log.info("Have %s items", len(delItems))



		# We want to scan items from the item with the least contained items to the item with the most contained items
		# Therefore, we convert the key array to a list of ({itemLen}, {itemKey}) 2-tuples, sort on that, and then use
		# that list for iterating
		items = list([(len(delItems[key]), key) for key in delItems.keys()])
		items.sort()


		processed = 0
		for dummy_len, filePath in items:
			self.processFile(filePath, delItems[filePath])

			processed += 1
			if processed % 100 == 0:
				print("Loop ", processed)


	@classmethod
	def phashScan(cls, args):

		import logSetup
		logSetup.initLogging()

		print("Scan settings:")
		print("targetDir    =", args.targetDir)
		print("removeDir    =", args.removeDir)
		print("scanEnv      =", args.scanEnv)
		print("compDistance =", args.compDistance)

		callback = None
		if 'callback' in args:
			callback = args['callback']



		tree = cls(args.scanEnv, args.removeDir, args.compDistance, callBack=callback)
		tree.trimFiles(args.targetDir)


def phashScan(args):
	TreeProcessor.phashScan(args)


def go():

	import logSetup
	logSetup.initLogging()

	checker = ArchChecker("/media/Storage/MP/Nanatsu no Taizai [++++]/Nanatsu no Taizai - Chapter 96 - Chapter 96[MangaJoy].zip")
	checker.isPhashUnique()
	# checker.addNewArch()


if __name__ == "__main__":
	go()
