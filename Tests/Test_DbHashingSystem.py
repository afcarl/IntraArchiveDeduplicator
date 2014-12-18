
import unittest
import scanner.logSetup as logSetup

import os.path

import Tests.basePhashTestSetup


import pyximport
pyximport.install()
import deduplicator.cyHamDb as hamDb

CONTENTS = [

		[1,  '{cwd}/test_ptree/allArch.zip',         '',                                 '9d7d02a6bff693737904c5d1a35c89cc', None,                  None,                None, None, None ],
		[2,  '{cwd}/test_ptree/allArch.zip',         'Lolcat_this_is_mah_job.jpg',       'd9ceeb6b43c2d7d096532eabfa6cf482', 27427800275512429, -   4504585791368671746, None, 493,  389  ],
		[3,  '{cwd}/test_ptree/allArch.zip',         'Lolcat_this_is_mah_job.png',       '1268e704908cc39299d73d6caafc23a0', 27427800275512429, -   4504585791368671746, None, 493,  389  ],
		[4,  '{cwd}/test_ptree/allArch.zip',         'Lolcat_this_is_mah_job_small.jpg', '40d39c436e14282dcda06e8aff367307', 27427800275512429, -   4504585791368671746, None, 300,  237  ],
		[5,  '{cwd}/test_ptree/allArch.zip',         'dangerous-to-go-alone.jpg',        'dcd6097eeac911efed3124374f44085b', -149413575039568585,   4576150637722077151, None, 325,  307  ],
		[6,  '{cwd}/test_ptree/allArch.zip',         'lolcat-crocs.jpg',                 '6d0a977694630ac9d1d33a7f068e10f8', -5569898607211671279,  167400391896309758,  None, 500,  363  ],
		[7,  '{cwd}/test_ptree/allArch.zip',         'lolcat-oregon-trail.jpg',          '7227289a017988b6bdcf61fd4761f6b9', -4955310669995365332, -8660145558008088574, None, 501,  356  ],
		[8,  '{cwd}/test_ptree/notQuiteAllArch.zip', '',                                 'd3c2108bfc69602cfbf2f821eb874ccd', None,                  None,                None, None, None ],
		[9,  '{cwd}/test_ptree/notQuiteAllArch.zip', 'Lolcat_this_is_mah_job.jpg',       'd9ceeb6b43c2d7d096532eabfa6cf482', 27427800275512429, -   4504585791368671746, None, 493,  389  ],
		[10, '{cwd}/test_ptree/notQuiteAllArch.zip', 'Lolcat_this_is_mah_job.png',       '1268e704908cc39299d73d6caafc23a0', 27427800275512429, -   4504585791368671746, None, 493,  389  ],
		[11, '{cwd}/test_ptree/notQuiteAllArch.zip', 'Lolcat_this_is_mah_job_small.jpg', '40d39c436e14282dcda06e8aff367307', 27427800275512429, -   4504585791368671746, None, 300,  237  ],
		[12, '{cwd}/test_ptree/notQuiteAllArch.zip', 'lolcat-crocs.jpg',                 '6d0a977694630ac9d1d33a7f068e10f8', -5569898607211671279,  167400391896309758,  None, 500,  363  ],
		[13, '{cwd}/test_ptree/notQuiteAllArch.zip', 'lolcat-oregon-trail.jpg',          '7227289a017988b6bdcf61fd4761f6b9', -4955310669995365332, -8660145558008088574, None, 501,  356  ],
		[14, '{cwd}/test_ptree/testArch.zip',        '',                                 '86975a1f7fca8d520fb0bd4a29b1e953', None,                  None,                None, None, None ],
		[15, '{cwd}/test_ptree/testArch.zip',        'Lolcat_this_is_mah_job.png',       '1268e704908cc39299d73d6caafc23a0', 27427800275512429, -   4504585791368671746, None, 493,  389  ],
		[16, '{cwd}/test_ptree/testArch.zip',        'Lolcat_this_is_mah_job_small.jpg', '40d39c436e14282dcda06e8aff367307', 27427800275512429, -   4504585791368671746, None, 300,  237  ],
		[17, '{cwd}/test_ptree/testArch.zip',        'dangerous-to-go-alone.jpg',        'dcd6097eeac911efed3124374f44085b', -149413575039568585,   4576150637722077151, None, 325,  307  ],
]

# Patch in current script directory so the CONTENTS paths work.
import os.path
cwd = os.path.dirname(os.path.realpath(__file__))
for x in range(len(CONTENTS)):
	CONTENTS[x][1] = CONTENTS[x][1].format(cwd=cwd)
	CONTENTS[x] = tuple(CONTENTS[x])



class TestSequenceFunctions(unittest.TestCase):

	def __init__(self, *args, **kwargs):
		logSetup.initLogging()
		super().__init__(*args, **kwargs)

	def setUp(self):

		self.addCleanup(self.dropDatabase)

		self.db = Tests.basePhashTestSetup.TestDb()

		# Check the table is set up
		self.assertEqual(self.db.getItemNum(), (len(CONTENTS), ),
				'Setup resulted in an incorrect number of items in database!')

	def dropDatabase(self):
		self.db.tearDown()

	def test_treeExists(self):
		self.assertIsInstance(self.db.tree, hamDb.BkHammingTree)


	def test_loadFromDb(self):
		self.db.tree.dropTree()
		self.db.doLoad()


	# Verify the structure of the tree
	# does not change across reloading.
	def test_testLoadingDeterminsm(self):
		loadedTree = list(self.db.tree.root)

		self.db.tree.root = None
		self.db.tree.nodes = 0

		self.db.doLoad()

		self.assertEqual(list(self.db.tree.root), loadedTree)


	def test_getItemsSimple(self):

		expect = list(CONTENTS)
		expect.sort()
		items = list(self.db.getItems())
		items.sort()

		self.assertEqual(items, expect)


	def test_searchByPhash1(self):

		expect = {
			(2,  '/media/Storage/Scripts/Deduper/Tests/test_ptree/allArch.zip',          'Lolcat_this_is_mah_job.jpg',       'd9ceeb6b43c2d7d096532eabfa6cf482', 27427800275512429, -4504585791368671746, None, 493, 389),
			(3,  '/media/Storage/Scripts/Deduper/Tests/test_ptree/allArch.zip',          'Lolcat_this_is_mah_job.png',       '1268e704908cc39299d73d6caafc23a0', 27427800275512429, -4504585791368671746, None, 493, 389),
			(4,  '/media/Storage/Scripts/Deduper/Tests/test_ptree/allArch.zip',          'Lolcat_this_is_mah_job_small.jpg', '40d39c436e14282dcda06e8aff367307', 27427800275512429, -4504585791368671746, None, 300, 237),
			(9,  '/media/Storage/Scripts/Deduper/Tests/test_ptree/notQuiteAllArch.zip',  'Lolcat_this_is_mah_job.jpg',       'd9ceeb6b43c2d7d096532eabfa6cf482', 27427800275512429, -4504585791368671746, None, 493, 389),
			(10, '/media/Storage/Scripts/Deduper/Tests/test_ptree/notQuiteAllArch.zip',  'Lolcat_this_is_mah_job.png',       '1268e704908cc39299d73d6caafc23a0', 27427800275512429, -4504585791368671746, None, 493, 389),
			(11, '/media/Storage/Scripts/Deduper/Tests/test_ptree/notQuiteAllArch.zip',  'Lolcat_this_is_mah_job_small.jpg', '40d39c436e14282dcda06e8aff367307', 27427800275512429, -4504585791368671746, None, 300, 237),
			(15, '/media/Storage/Scripts/Deduper/Tests/test_ptree/testArch.zip',         'Lolcat_this_is_mah_job.png',       '1268e704908cc39299d73d6caafc23a0', 27427800275512429, -4504585791368671746, None, 493, 389),
			(16, '/media/Storage/Scripts/Deduper/Tests/test_ptree/testArch.zip',         'Lolcat_this_is_mah_job_small.jpg', '40d39c436e14282dcda06e8aff367307', 27427800275512429, -4504585791368671746, None, 300, 237),
		}


		expect = set(expect)

		# Distance of 0 from results
		ret = self.db.getWithinDistance(27427800275512429)
		ret = set(ret)

		self.assertEqual(ret, expect)

		# Distance of 1 from results
		ret = self.db.getWithinDistance(27427800275512428)
		ret = set(ret)
		self.assertEqual(ret, expect)

		# Distance of 2 from results
		ret = self.db.getWithinDistance(27427800275512424)
		ret = set(ret)
		self.assertEqual(ret, expect)


	def test_searchByPhash2(self):
		ret = self.db.getWithinDistance(27427800275512426)
		self.assertEqual(ret, [])

		ret = self.db.getWithinDistance(507)
		self.assertEqual(ret, [])

		ret = self.db.getWithinDistance(-5569898607211671251)
		self.assertEqual(ret, [])


	def test_searchByPhash3(self):


		expect = [
			(6, '/media/Storage/Scripts/Deduper/Tests/test_ptree/allArch.zip',          'lolcat-crocs.jpg',                 '6d0a977694630ac9d1d33a7f068e10f8', -5569898607211671279, 167400391896309758,   None, 500,  363),
			(12, '/media/Storage/Scripts/Deduper/Tests/test_ptree/notQuiteAllArch.zip', 'lolcat-crocs.jpg',                 '6d0a977694630ac9d1d33a7f068e10f8', -5569898607211671279, 167400391896309758,   None, 500,  363),
		]

		expect = set(expect)
		# Distance of 2 from results
		ret = self.db.getWithinDistance(-5569898607211671279)
		ret = set(ret)


		self.assertEqual(ret, expect)



