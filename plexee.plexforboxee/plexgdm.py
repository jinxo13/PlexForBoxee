import sys
import struct
import time
import util
import urllib2
import socket
import plex
import threading

##
#Implements the Plex G'day Mate service
#Borrowed from PlexAPI.py at:
#https://github.com/iBaa/PlexConnect
class PlexGDM:

	def __init__(self):
		#self.IP_PlexGDM = '<broadcast>'
		self.multicastAddress = '239.0.0.250'
		#self.multicastAddress = '<broadcast>'
		#self._multicast_address = '239.0.0.250'
        #self.discover_group = (self._multicast_address, 32414)
        #self.client_register_group = (self._multicast_address, 32413)
        #self.client_update_port = 32412

		self.gdmReceivePort = 32414
		self.gdmDestPort = 32413
		self.clientUpdatePort = 32412
		self.clientRegisterGroup = (self.multicastAddress, 32413)
		self.discoverGroup = ('<broadcast>', 32414)

		self.searchHeader = 'M-SEARCH * HTTP/1.0'
		self.clientHeader = '* HTTP/1.0'
		self.clientData = ''
		self.clientId = ''

	##
	#	Returns a list of the plex.PlexServer's found
	#
	def getServers(self, timeoutsec):
		util.logDebug("***")
		util.logDebug("Looking up Plex Media Server")
		util.logDebug("***")
		
		# setup socket for discovery -> multicast message
		GDM = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		GDM.settimeout(timeoutsec)
		
		# Set the time-to-live for messages to 1 for local network
		GDM.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		
		returnData = []
		try:
			# Send data to the multicast group
			util.logDebug("Sending discovery message: %s" % self.searchHeader)
			GDM.sendto(self.searchHeader, self.discoverGroup)

			# Look for responses from all recipients
			while True:
				try:
					data, server = GDM.recvfrom(1024)
					returnData.append( { 'from' : server,
										 'data' : data } )
				except socket.timeout:
					break
		finally:
			GDM.close()

		discovery_complete = True

		PMS_list = {}
		if returnData:
			for response in returnData:
				update = { 'ip' : response.get('from')[0] }
				
				# Check if we had a positive HTTP response						  
				if "200 OK" in response.get('data'):
					for each in response.get('data').split('\n'): 
						# decode response data
						update['discovery'] = "auto"
						#update['owned']='1'
						#update['master']= 1
						#update['role']='master'
						
						if "Content-Type:" in each:
							update['content-type'] = each.split(':')[1].strip()
						elif "Resource-Identifier:" in each:
							update['uuid'] = each.split(':')[1].strip()
						elif "Name:" in each:
							update['serverName'] = each.split(':')[1].strip().decode('utf-8', 'replace')  # store in utf-8
						elif "Port:" in each:
							update['port'] = each.split(':')[1].strip()
						elif "Updated-At:" in each:
							update['updated'] = each.split(':')[1].strip()
						elif "Version:" in each:
							update['version'] = each.split(':')[1].strip()
						
				PMS_list[update['uuid']] = update
		
		if PMS_list=={}:
			util.logDebug("GDM: No servers discovered")
		else:
			util.logDebug("GDM: Servers discovered: %i" % len(PMS_list))
			for uuid in PMS_list:
				msg = "%s %s:%s" % (PMS_list[uuid]['serverName'], PMS_list[uuid]['ip'], PMS_list[uuid]['port'])
				util.logDebug(msg)
		
		return PMS_list

	def clientDetails(self, c_id, c_name, c_post, c_product, c_version):
		self.clientId = c_id
	
	def startClientAdvertising(self):
		self.registerThread = threading.Thread(target=self.registerClient)
		self.registerThread.start()
		util.logInfo('Plexee GDM advertising started')

	def stopClientAdvertising(self):
		self.registerThreadActive = False
		util.logInfo('Plexee GDM advertising ending...')
		self.registerThread.join(5.0)
		util.logInfo('Plexee GDM advertising ended')
					
	def registerClient (self):
		self.registerThreadActive = False
		plexManager = plex.PlexManager.Instance()
		self.clientData = "Content-Type: plex/media-player\r\n" + \
				"Name: %s\r\n" + \
				"Port: %s\r\n" + \
				"Product: %s\r\n" + \
				"Version: %s\r\n" + \
				"Device-Class: %s\r\n" + \
				"Protocol: plex\r\n" + \
				"Protocol-Version: 1\r\n" + \
				"Protocol-Capabilities: %s\r\n" + \
				"Resource-Identifier: %s\r\n"
		self.clientData = self.clientData % (
				plexManager.xPlexDevice,
				plexManager.xPlexClientPort,
				plexManager.xPlexProduct,
				plexManager.xPlexVersion,
				plexManager.xPlexDeviceClass,
				plexManager.xPlexProvides,
				plexManager.xPlexClientIdentifier)

		update_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		
		#Set socket reuse, may not work on all OSs.
		try:
			update_sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		except:
			pass
		
		#Attempt to bind to the socket to recieve and send data.  If we can;t do this, then we cannot send registration
		try:
			update_sock.bind(('0.0.0.0',self.clientUpdatePort))
		except:
			util.logError("Client GDM Advertising: Unable to bind to port [%s] - client will not be registered" % str(self.clientUpdatePort))
			return	  
		
		update_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
		status = update_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.multicastAddress) + socket.inet_aton('0.0.0.0'))
		update_sock.setblocking(0)

		#Now, listen for client discovery reguests and respond.
		self.registerThreadActive = True
		while self.registerThreadActive:
			try:
				update_sock.sendto("HELLO %s\r\n%s" % (self.clientHeader, self.clientData), self.clientRegisterGroup)
			except:
				util.logDebug("Error: Unable to send registeration message")
			try:
				data, addr = update_sock.recvfrom(1024)
			except socket.error, e:
				pass
			else:
				if "M-SEARCH * HTTP/1." in data:
					try:
						update_sock.sendto("HTTP/1.0 200 OK\r\n%s" % self.clientData, addr)
					except:
						util.logDebug("Error: Unable to send client update message")
					
					self.registerThreadActive = True
			time.sleep(15.0)
			#self.clientRegistered = self.isClientRegistered(server)

		util.logDebug("Client Update loop stopped")
		#When we are finished, then send a final goodbye message to deregister cleanly.
		try:
			update_sock.sendto("BYE %s\r\n%s" % (self.clientHeader, self.clientData), self.clientRegisterGroup)
			util.logDebug("BYE sent...")
		except:
			util.logError("Error: Unable to send client update message")

	def isClientRegistered(self, server):
		try:
			data, url = server.getClientData()
			if self.clientId in data:
				util.logInfo("Client registration successful")
				util.logDebug("Client data is: %s" % data)
				return True
			else:
				util.logDebug("Client registration not found")
				util.logDebug("Client data is: %s" % data)

		except:
			util.logDebug("Unable to check status")
			pass

		return False