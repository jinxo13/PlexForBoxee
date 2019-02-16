import constants
import unittest
import util
import plexee
import xbmc
import os
from plex import PlexManager
import time
import mc

class TestPlexee(unittest.TestCase):
	"""Tests Plexee functions"""

	if __name__ == '__main__':
		unittest.main('test_plexee')
	
	def setup(self):
		config = mc.GetApp().GetLocalConfig()
		config.SetValue('debug',1)

	def test_users(self):
		if (plexee.Plexee.Instance() is None):
			plx = plexee.Plexee()
		else:
			plx = plexee.Plexee.Instance()
		plexManager = plx.plexManager
		plexManager.clearMyPlex()
		self.assertTrue(plexManager.myPlexLogin(constants.USERNAME, constants.PASSWORD), 'Login succeeded')
		data, url = plexManager.myplex.getLocalUserData()
		users = plx.createUsers(data)
		util.logInfo('Users: %d' % len(users))
		self.assertNotEqual(0, len(users), "Users set up")
		plx.stopClientServices()

	def test_plex_config(self):
		#1. Mock Boxee settings file is good
		util.logInfo('#1. Boxee settings file is good')
		tempdir = '__zzz'
		filename = 'registry.xml'
		filepath = os.path.join(os.getcwd(),tempdir)
		fullfilename = os.path.join(filepath,filename)
		try:
			os.mkdir(filepath)
		except OSError:
			#Assume it exists already
			pass
		f = open(fullfilename,'w')
		f.write('<registry/>')
		f.close()
		xbmc.setMockProfilePath(filepath)
		config = plexee.PlexeeConfig()
		config.setManualHost('xxx')
		config.setManualHost('yyy')
		config.setManualPort('32400')
		config1 = plexee.PlexeeConfig()
		self.assertEqual('yyy',config1.getManualHost(), 'Use mock Boxee config - Test config reads and writes correctly')

		os.remove(fullfilename)
		time.sleep(2)
		os.rmdir(filepath)
		util.logInfo('#1. END - Boxee settings file is good')

		#2. Mock Boxee file not accessible
		util.logInfo('#2. Mock Boxee file not accessible')
		xbmc.setMockProfilePath('.')
		config = plexee.PlexeeConfig()
		config.setManualHost('zzz')
		config.setDebugOn()
		config1 = plexee.PlexeeConfig()
		self.assertEqual('zzz',config1.getManualHost(), 'Use alternate config - Test config reads and writes correctly')
		util.logInfo('#2. END - Mock Boxee file not accessible')

		#3. Mock Boxee file not accessible, get file again
		util.logInfo('#3. Mock Boxee file not accessible, get file again')
		config = plexee.PlexeeConfig()
		self.assertEqual('zzz',config.getManualHost(), 'Alternate config used again')
		util.logInfo('#3. END - Mock Boxee file not accessible, get file again')

	def testPlexeeInterface(self):
		config = plexee.PlexeeConfig()
		config.setMyPlexConnectOn()
		config.setMyPlexUser(constants.USERNAME)
		config.setMyPlexPassword(constants.PASSWORD)
		config.setMyPlexPIN(constants.PIN)
		config.setDebugOn()
		config.setPlexRemoteOff()

		if (plexee.Plexee.Instance() is None):
			plx = plexee.Plexee()
		else:
			plx = plexee.Plexee.Instance()
		plexManager = plx.plexManager

		homeWindow = plx.getHomeWindow()
		homeWindow.activate()
		homeWindow.load()

		connDlg = plx.getConnectionDialog()
		connDlg.activate()
		connDlg.load()

		#1. Get the library items
		util.logInfo('#1. Check library items were found')
		libraryItems = homeWindow.getMyLibraryItems()
		self.assertTrue(len(libraryItems) > 0)
		for i in libraryItems:
			util.logInfo(i.GetProperty('title'))

		#2. Try a search
		util.logInfo('#2. Check a search for "Guard" returned something')
		mc.SetDialogKeyboardText('Guard')
		homeWindow.searchClicked()
		items = homeWindow.searchList.GetItems()
		self.assertTrue(len(items) > 0)
		for i in items:
			util.logInfo(i.GetProperty('title'))

		#3. Click on first library item
		util.logInfo('#3. Click on first library item')
		homeWindow.handleItem(libraryItems[0])
		
		#4. Retry should use cache
		util.logInfo('--------------------------')
		util.logInfo('#4. Retry should use cache')
		homeWindow.handleItem(libraryItems[0])
		directoryWindow = plx.getDirectoryWindow()
		items = directoryWindow.getContentList().GetItems()
		for i in items:
			util.logInfo(i.GetProperty('title'))
		self.assertTrue(len(items) > 0)

		#5. Test the plex interface
		"""
		Retrieve data from Plex and load it into Plexee objects
		"""
		util.logInfo('#5. Test the Plex interface')
		servers = plexManager.getLocalServers()
		server = None
		for key in servers:
			server = servers[key]
			break

		data, url = plx.plexInterface.getChannelData(server)
		assert data is not None
		windowInformation = plx.createListItems(server, data, url, None)

		data, url = plx.plexInterface.getLibraryData(server)
		assert data is not None
		windowInformation = plx.createListItems(server, data, url, None)

		data, url = plx.plexInterface.getMyPlexQueueData()
		assert data is not None
		items = plx.createQueueItems(data)
		
		data, url = plx.plexInterface.getMyPlexUserData()
		assert data is not None
		users = plx.createUsers(data)

		data, url = plx.plexInterface.getOnDeckData(server)
		assert data is not None
		windowInformation = plx.createListItems(server, data, url, None)

		data, url = plx.plexInterface.getPlaylistData(server)
		assert data is not None
		windowInformation = plx.createListItems(server, data, url, None)

		data, url = plx.plexInterface.getRecentlyAddedData(server)
		assert data is not None
		windowInformation = plx.createListItems(server, data, url, None)

		#plx.stopClientServices()
