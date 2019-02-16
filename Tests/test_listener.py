import plexee
from listener import ClientListener, ThreadedHTTPServer, MyHandler
import unittest
import time
import constants
import util

class remoteTests(unittest.TestCase):
	"""Tests Plexee functions"""

	if __name__ == '__main__':
		unittest.main('test_listener')

	def testListener_BROKEN(self):
		config = plexee.PlexeeConfig()
		#config.setMyPlexConnectOn()
		config.setMyPlexUser(constants.USERNAME)
		config.setMyPlexPassword(constants.PASSWORD)
		config.setMyPlexPIN(constants.PIN)
		config.setPlexRemoteOn()
		config.setDebugOn()

		if plexee.Plexee.Instance() is None:
			plx = plexee.Plexee()
		else:
			plx = plexee.Plexee.Instance()
			
		lis = plx.clientListener
		self.assertTrue(lis.isRunning())
		plx.stopClientServices()
		util.logInfo('Stopped')
		self.assertFalse(lis.isRunning())
