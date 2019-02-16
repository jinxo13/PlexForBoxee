import constants
import unittest
import urllib2
import mc
from plex import PlexServer, MyPlexService, PlexManager
from plexee import PlexeeConfig
import util
import time
from plexgdm import PlexGDM

class plexTests(unittest.TestCase):
	"""Tests the Plex python interface"""

	if __name__ == '__main__':
		unittest.main('test_plex')
	
	def setup(self):
		config = mc.GetApp().GetLocalConfig()
		config.SetValue('debug','1')

	def testConfigs(self):
		config = mc.GetApp().GetLocalConfig()
		config.SetValue('debug','1')
		config.SetValue('test','fred')
		config.SetValue('test2','1.234')

		config2 = util.Config(PlexeeConfig.getUserSettingsFile())
		config2.SetValue('debug','2')
		self.assertEqual(config2.GetValue('debug'), config.GetValue('debug'))
		self.assertEqual(config2.GetValue('test'), config.GetValue('test'))
		self.assertEqual(config2.GetValue('test2'), config.GetValue('test2'))

	#Server connection settings
	#1. Unencrypted
	#2. Users setup on unencrypted
	#3. Encrypted - no users
	#4. Encrypted - users
	# AND GDM on or off
	# Direct connection or via myPlex

	#Encrypted try ip and bypass certificate?

	def getCurrentDateTime(self):
		return time.strftime("%d/%m/%Y %H:%M:%S")

	def testDirectConnection(self):
		"""Test connect"""
		#self.setup()
		#1. Connect to local plex server
		server = PlexServer.Manual(constants.HOST, constants.PORT)
		server.connect()

		if not server.isTokenRequired:
			self.assertTrue(server.isConnected)
			data, url = server.getLibraryData()
			util.logInfo(data)
			assert data is not None
		else:
			self.assertFalse(server.isConnected)

		#2. Connect to an invalid server
		server = PlexServer.Manual('10.1.3.1', 32400)
		self.assertFalse(server.isConnected)

		#3. Connect to a non-plex server
		server = PlexServer.Manual('www.google.com', 80)
		self.assertFalse(server.isConnected)


	def testMyPlexConnection(self):
		self.setup()
		util.logInfo(self.getCurrentDateTime() + "1. Create PlexManager")

		plexManager = PlexManager({
			'platform':'Linux',
			'port': '32500',
			'platformversion':'Linux boxeebox 2.6.28 #6 PREEMPT Thu Aug 12 11:39:42 CST 2010 i686 unknown',
			'provides':'player,timeline',
			'product':'Plexee',
			#'product':'Plexee',
			'version':'1.0',
			'device':'DLink Boxeebox',
			'deviceClass':'pc',
			'deviceid':'test_plexee'			
		})
		util.logInfo(self.getCurrentDateTime() + "1. END PlexManager")

		util.logInfo(self.getCurrentDateTime() + "2. Do Plex Login")
		plexManager.clearMyPlex()
		self.assertEqual(plexManager.myPlexLogin('x', 'x'), plexManager.ERR_MPLEX_AUTH_FAILED,'Login should fail')
		self.assertEqual(plexManager.myPlexLogin(constants.USERNAME, constants.PASSWORD), plexManager.SUCCESS,'Login succeeded')
		token = plexManager.myplex.authenticationToken
		util.logInfo('TOKEN: %s' % token)
		assert token is not None
		util.logInfo(self.getCurrentDateTime() + "2. END Plex Login")

		util.logInfo(self.getCurrentDateTime() + "3. Connect to server")
		server = PlexServer.Manual(constants.HOST, constants.PORT, token) #token
		server.connect()

		util.logInfo(self.getCurrentDateTime() + "3. END Connect to server")
		util.logInfo(self.getCurrentDateTime() + "4. Get data")
		data, url = server.getLibraryData()
		util.logInfo(data)
		assert data is not None
		util.logInfo(self.getCurrentDateTime() + "4. END Get data")

	def testMyPlexUsers(self):
		self.setup()
		util.logInfo(self.getCurrentDateTime() + "1. Create PlexManager")
		if (PlexManager.Instance() is None):
			plexManager = PlexManager({
				'platform':'Linux',
				'port': '32500',
				'platformversion':'Linux boxeebox 2.6.28 #6 PREEMPT Thu Aug 12 11:39:42 CST 2010 i686 unknown',
				'provides':'player,timeline',
				'product':'Plexee',
				#'product':'Plexee',
				'version':'1.0',
				'device':'DLink Boxeebox',
				'deviceClass':'pc',
				'deviceid':'test_plexee'			
			})
		else:
			plexManager = PlexManager.Instance()
		util.logInfo(self.getCurrentDateTime() + "1. END PlexManager")

		util.logInfo(self.getCurrentDateTime() + "2. Do Plex Login")
		plexManager.clearMyPlex()
		self.assertTrue(plexManager.myPlexLogin(constants.USERNAME, constants.PASSWORD), 'Login succeeded')
		token = plexManager.myplex.authenticationToken
		util.logInfo('TOKEN: %s' % token)
		assert token is not None
		util.logInfo(self.getCurrentDateTime() + "2. END Plex Login")
		
		result = plexManager.switchUser('1311516',constants.PIN)
		self.assertEqual(result, PlexManager.SUCCESS)
		result = plexManager.switchUser('1311516','abc')
		self.assertEqual(result, PlexManager.ERR_USER_PIN_FAILED)
