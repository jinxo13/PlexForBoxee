import unittest
import util
import plexee

class utilTests(unittest.TestCase):

	if __name__ == '__main__':
		unittest.main('test_util')

	def testSsl(self):
		http = util.Http()
		data = http.Get('https://wrong.host.badssl.com/')
		self.assertTrue('<html>' in data)

	def testLogging(self):
		config = plexee.PlexeeConfig()
		config.setDebugOn()
		#Test logging numbers
		util.logDebug('Log a DEBUG number')
		util.logDebug(1)
		util.logInfo('Log an INFO number')
		util.logInfo(2)
		util.logError('Log an ERROR number')
		util.logError(3)
		self.assertEqual(1,1)
