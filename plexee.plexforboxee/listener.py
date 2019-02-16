import re
import traceback
import time
import util
import plexee
import plex
import mc
import xbmc
import threading
import socket
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import urlparse
from cgi import parse_qsl

def jsonrpc(cmd, params=None):
	return ''

def getXMLHeader():
	return '<?xml version="1.0" encoding="utf-8"?>'+"\r\n"
def getOKMsg():
	return getXMLHeader() + '<Response code="200" status="OK" />'

def getPlexHeaders():
	plexManager = plex.PlexManager.Instance()
	h = {
		"Content-type": "application/x-www-form-urlencoded",
		"Access-Control-Allow-Origin": "*",
		"X-Plex-Version": plexManager.xPlexVersion,
		"X-Plex-Client-Identifier": plexManager.xPlexClientIdentifier,
		"X-Plex-Provides": "player",
		"X-Plex-Product": plexManager.xPlexProduct,
		"X-Plex-Device-Name": plexManager.xPlexProduct,
		"X-Plex-Platform": plexManager.xPlexPlatform,
		"X-Plex-Model": plexManager.xPlexPlatform,
		"X-Plex-Device": plexManager.xPlexDevice,
	}
	if plexManager.myplex.isAuthenticated():
		h["X-Plex-Username"] = plexManager.myplex.authenticationToken
	return h

class MyHandler(BaseHTTPRequestHandler):
	"""
	Modified from listener.py at: https://github.com/hippojay/script.plexbmc.helper
	"""

	protocol_version = 'HTTP/1.1'
	def log_message(self, format, *args):
		# I have my own logging, suppressing BaseHTTPRequestHandler's
		#util.logDebug(format % args)
		return True
	def do_HEAD(self):
		util.logDebug("Serving HEAD request...", util.Constants.DEBUG_CLIENT_GROUP)
		self.answer_request(0)

	def do_GET(self):
		util.logDebug("Serving GET request...", util.Constants.DEBUG_CLIENT_GROUP)
		self.answer_request(1)

	def do_OPTIONS(self):
		self.send_response(200)
		self.send_header('Content-Length', '0')
		self.send_header('X-Plex-Client-Identifier', plex.PlexManager.Instance().xPlexClientIdentifier)
		self.send_header('Content-Type', 'text/plain')
		self.send_header('Connection', 'close')
		self.send_header('Access-Control-Max-Age', '1209600')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE, PUT, HEAD')
		self.send_header('Access-Control-Allow-Headers', 'x-plex-version, x-plex-platform-version, x-plex-username, x-plex-client-identifier, x-plex-target-client-identifier, x-plex-device-name, x-plex-platform, x-plex-product, accept, x-plex-device')
		self.end_headers()
		self.wfile.close()

	def response(self, body, headers = {}, code = 200):
		try:
			self.send_response(code)
			for key in headers:
				self.send_header(key, headers[key])
			self.send_header('Content-Length', len(body))
			self.send_header('Connection', "close")
			self.end_headers()
			self.wfile.write(body)
			self.wfile.close()
		except:
			pass

	"""
	def updateCommandID(self, uuid, commandID):
		if commandID and self.subscriberself.get(uuid, False):
			self.subscribers[uuid].commandID = int(commandID)			 
	"""

	def getLocation(self):
		#navigation,fullScreenVideo,fullScreenPhoto,fullScreenMusic
		plx = plexee.Plexee.Instance()
		boxeePlayer = plx.player.mcPlayer
		windowId = False
		try:
			w = mc.GetActiveWindow()
			if w:
				windowId = w.GetLabel(1).GetLabel()
				util.logInfo("Current Window: %s" % windowId)
		except:
			pass

		if boxeePlayer.IsPlayingVideo():
			return "fullScreenVideo"
		if boxeePlayer.IsPlayingAudio() and not windowId:
			return "fullScreenMusic"
		if plx.getPhotoDialog().isShowing():
			return "fullScreenPhoto"
		return 'navigation'

	def getPlayerState(self, type):
		plx = plexee.Plexee.Instance()
		boxeePlayer = plx.player.mcPlayer
		info = dict()
		info['state'] = 'stopped'
		info['type'] = type

		isPlaying = False
		item = None
		if type in ['video','music']:
			if type == 'video':
				isPlaying = boxeePlayer.IsPlayingVideo()
			else:
				isPlaying = boxeePlayer.IsPlayingAudio()
			if isPlaying:
				item = boxeePlayer.GetPlayingItem()
				info['state'] = 'playing'
				if boxeePlayer.IsPaused():
					info['state'] = 'paused'
				if boxeePlayer.IsCaching():
					info['state'] = 'buffering'

		elif type == 'photo':
			isPlaying = plx.getPhotoDialog().isShowing()
			if isPlaying:
				dlg = plx.getPhotoDialog()
				item = dlg.getFocusedPhoto()
				if dlg.isSlideShowActive():
					info['state'] = 'playing'
				else:
					info['state'] = 'paused'

		#stopped, paused, playing, buffering and error
		if not isPlaying or item is None:
			return info

		if type == 'music':
			info['controllable'] = "playPause,play,stop,skipPrevious,skipNext,volume"
		elif type == 'video':
			info['controllable'] = "playPause,play,stop,skipPrevious,skipNext,volume,stepBack,stepForward,seekTo"
		elif type == 'photo':
			info['controllable'] = "playPause,play,stop,skipPrevious,skipNext"

		#ratingKey is the corresponding rating key attribute in the media.
		#key is the corresponding key attributre in the media.
		#containerKey is the key for the container, if appropriate.
		info['key'] = item.GetProperty('key')
		info['ratingKey'] = item.GetProperty('ratingKey')
		info['containerKey'] = item.GetProperty('containerKey')

		if type != 'photo':
			#duration is the duration of the media, in millisecondself.
			#time is the current playback position, in millisecondself.
			info['time'] = str(int(boxeePlayer.GetTime() * 1000))
			info['duration'] = str(int(boxeePlayer.GetTotalTime() * 1000))
			info['mediaIndex'] = item.GetProperty("mediaIndex")
			info['partIndex'] = item.GetProperty("partIndex")
			info['partCount'] = item.GetProperty("partCount")

			#playQueueID=XXX Sent if the player is currently playing a playQueue.
			#playQueueItemID=XXX Sent if the player is currently playing a playQueue.
			#playQueueVersion=XXX
			info['playQueueItemID'] = item.GetProperty('playQueueItemID')
			#seekRange=X-Y is optionally sent to specify the specific subrange that is seekable, in milliseconds
			info['seekRange']="0-%s" % info['duration']
			#volume=[0,100], shuffle=0/1, repeat=0/1/2 (where 1 = repeat one, 2 = repeat all)
			info['volume'] = str(boxeePlayer.GetVolume())
			info['shuffle'] = '0'
			#TODO: Track repeat status and report here
			info['repeat'] = '0'

		info['machineIdentifier'] = item.GetProperty('machineIdentifier')
		server = plex.PlexManager.Instance().getServer(info['machineIdentifier'])
		info['address'] = ''
		info['port'] = ''
		info['protocol'] = ''
			
		if server:
			info['address'] = server.host
			info['port'] = server.port
			info['protocol'] = server.protocol

		return info

	def getTimelineXML(self, ptype):
		info = self.getPlayerState(ptype)
		# save this info off so the server update can use it too
		#self.playerprops[ptype] = info;
		ret = "\r\n"+'<Timeline state="%s" type="%s"' % (info['state'], ptype)
		if info['state'] != 'stopped':
			ret += ' controllable="%s"' % info['controllable']
			ret += ' machineIdentifier="%s"' % info['machineIdentifier']
			ret += ' protocol="%s"' % info['protocol']
			ret += ' address="%s"' % info['address']
			ret += ' port="%s"' % info['port']
			#ret += ' guid="%s"' % info['guid']
			ret += ' containerKey="%s"' % info['containerKey']
			ret += ' key="%s"' % info['key']
			ret += ' ratingKey="%s"' % info['ratingKey']
			if ptype != 'photo':
				ret += ' time="%s"' % info['time']
				ret += ' duration="%s"' % info['duration']
				ret += ' seekRange="0-%s"' % info['duration']
				ret += ' mediaIndex="%s"' % info['mediaIndex']
				ret += ' partIndex="%s"' % info['partIndex']
				ret += ' partCount="%s"' % info['partCount']
				ret += ' playQueueItemID="%s"' % info['playQueueItemID']
				ret += ' volume="%s"' % info['volume']
				ret += ' shuffle="%s"' % info['shuffle']
				ret += ' repeat="%s"' % info['repeat']
		ret += '/>'
		return ret

	def msg(self):
		plexManager = plex.PlexManager.Instance()
		msg = getXMLHeader()
		msg += '<MediaContainer commandID="INSERTCOMMANDID"'
		msg += ' machineIdentifier="%s"' % plexManager.xPlexClientIdentifier
		msg += ' location="%s">' % self.getLocation()

		msg += self.getTimelineXML('music')
		msg += self.getTimelineXML('photo')
		msg += self.getTimelineXML('video')
		msg += "\r\n</MediaContainer>"
		return msg

	def answer_request(self, sendData):
		try:
			plx = plexee.Plexee.Instance()
			plexManager = plex.PlexManager.Instance()
			request_path=self.path[1:]
			url_parts = list(urlparse(request_path))
			paramarrays = dict(parse_qsl(url_parts[4]))
			request_path=re.sub(r"\?.*","",request_path)
			params = {}
			for key in paramarrays:
				params[key] = paramarrays[key]
			util.logDebug ("request path is: [%s]" % ( request_path,), util.Constants.DEBUG_CLIENT_GROUP)
			util.logDebug ("params are: %s" % params, util.Constants.DEBUG_CLIENT_GROUP)

			if 'X-Plex-Target-Client-Identifier' in params:
				if params['X-Plex-Target-Client-Identifier'] != plexManager.xPlexClientIdentifier:
					self.response('Bad X-Plex-Target-Client-Identifier value', code=404)
					return

			#self.updateCommandID(self,headers.get('X-Plex-Client-Identifier', plexManager.xPlexClientIdentifier), params.get('commandID', False))
			if request_path=="version":
				self.response("PleXBMC Helper Remote Redirector: Running\r\nVersion: %s" % plexManager.xPlexVersion)

			elif request_path=="verify":
				result = jsonrpc("ping")
				self.response("XBMC JSON connection test:\r\n" + result)

			elif "resources" == request_path:
				resp = getXMLHeader()
				resp += "<MediaContainer>"
				resp += "<Player"
				resp += ' title="%s"' % plexManager.xPlexDevice
				resp += ' protocol="plex"'
				resp += ' protocolVersion="1"'
				resp += ' protocolCapabilities="%s"' % plexManager.xPlexProvides
				resp += ' machineIdentifier="%s"' % plexManager.xPlexClientIdentifier
				resp += ' product="%s"' % plexManager.xPlexProduct
				resp += ' platform="%s"' % plexManager.xPlexPlatform
				resp += ' platformVersion="%s"' % plexManager.xPlexPlatformVersion
				resp += ' deviceClass="%s"' % plexManager.xPlexDeviceClass
				resp += "/>"
				resp += "</MediaContainer>"
				util.logDebug("crafted resources response: %s" % resp, util.Constants.DEBUG_CLIENT_GROUP)
				self.response(resp, getPlexHeaders())

			elif "/poll" in request_path:
				if params.get('wait', False) == '1':
					#hold request until next notification to requester
					time.sleep(1)
				commandID = params.get('commandID', 0)
				msg = re.sub(r"INSERTCOMMANDID", str(commandID), self.msg())
				self.response(msg, {
				  'X-Plex-Client-Identifier': plexManager.xPlexClientIdentifier,
				  'Access-Control-Expose-Headers': 'X-Plex-Client-Identifier',
				  'Access-Control-Allow-Origin': '*',
				  'Content-Type': 'text/xml'
				})

			elif request_path == "player/playback/setParameters":
				self.response(getOKMsg(), getPlexHeaders())
				if 'volume' in params:
					try:
						volume = int(params['volume'])
						util.logInfo("WebClient: Adjusting the volume to %s" % volume)
						plx.player.mcPlayer.SetVolume(volume)
					except:
						pass
			
			elif "/playMedia" in request_path:
				self.response(getOKMsg(), getPlexHeaders())
				server = plexManager.getServer(params.get('machineIdentifier'))
				fullurl = server.getUrl(params['key'])
				util.logInfo("WebClient: playMedia command -> fullurl: %s" % fullurl)
				data = plexManager.getData(fullurl, {'X-Plex-Token':params.get('token','')})
				item = None
				#Stop player
				plx.player.mcPlayer.Stop()
				for childListItem in plx.createVideoListItems(server, data, fullurl):
					item = childListItem
					break
				itemType = item.GetProperty("itemtype")
				playDialog = plx.getPlayDialog()
				if itemType == 'Photo':
					#Show picture
					playDialog.handleItem(item)
				else:
					resume = params.get('offset', '0')
					#player/playback/playMedia?key=%2Flibrary%2Fmetadata%2F53402&offset=597000&machineIdentifier=9a35df949e05bc86d0aa792c56e3db68c0c36250&protocol=http&address=10.1.3.201&port=32400&containerKey=%2FplayQueues%2F1004%3Fown%3D1%26window%3D200&token=transient-736bfb60-e43c-4946-b987-a0c4f25bd2e0&commandID=1
					item.SetProperty('webviewOffset', resume)
					item.SetProperty('skipResume', '1')
					playDialog.handleItem(item)
					if not itemType == 'Track':
						playDialog.play()

			elif request_path == "player/mirror/details":
				#Can be called from the remote to show the pre-play screen for a specific item
				self.response(getOKMsg(), getPlexHeaders())
				resume = params.get('viewOffset', params.get('offset', "0"))
				server = plexManager.getServer(params.get('machineIdentifier'))
				fullurl = server.getUrl(params['key'])
				util.logDebug("playMedia command -> fullurl: %s" % fullurl, util.Constants.DEBUG_CLIENT_GROUP)
				
				#player/playback/playMedia?key=%2Flibrary%2Fmetadata%2F53402&offset=597000&machineIdentifier=9a35df949e05bc86d0aa792c56e3db68c0c36250&protocol=http&address=10.1.3.201&port=32400&containerKey=%2FplayQueues%2F1004%3Fown%3D1%26window%3D200&token=transient-736bfb60-e43c-4946-b987-a0c4f25bd2e0&commandID=1
				data = plexManager.getData(fullurl, {'X-Plex-Token':params.get('token','')})
				item = None
				for childListItem in plx.createVideoListItems(server, data, fullurl):
					item = childListItem
					break
				item.SetProperty('viewOffset', resume)
				item.SetProperty('skipResume', '1')
				playDialog = plx.getPlayDialog()
				playDialog.handleItem(item)

			elif request_path == "player/playback/play":
				self.response(getOKMsg(), getPlexHeaders())
				type = params['type']
				if type == 'photo':
					plx.getPhotoDialog().startSlideShow()
				else:
					if plx.player.mcPlayer.IsPaused():
						plx.player.mcPlayer.Pause()
						util.logInfo('WebClient: Unpausing player')

			elif request_path == "player/playback/pause":
				self.response(getOKMsg(), getPlexHeaders())
				type = params['type']
				if type == 'photo':
					plx.getPhotoDialog().stopSlideShow()
				else:
					if not plx.player.mcPlayer.IsPaused():
						plx.player.mcPlayer.Pause()
						util.logInfo('WebClient: Pausing player')

			elif request_path == "player/playback/stop":
				self.response(getOKMsg(), getPlexHeaders())
				type = params['type']
				if type == 'photo':
					plx.getPhotoDialog().close()
				else:
					plx.player.mcPlayer.Stop()
					util.logInfo('WebClient: Stop Player')

			elif request_path == "player/playback/seekTo":
				self.response(getOKMsg(), getPlexHeaders())
				offset = int(long(params.get('offset', 0))/1000)
				plx.player.mcPlayer.SeekTime(offset)
				util.logInfo('WebClient: Seek to %s' % str(offset))

			elif request_path == "player/playback/stepForward":
				self.response(getOKMsg(), getPlexHeaders())
				if plx.player.mcPlayer.IsPlayingVideo() or plx.player.mcPlayer.IsPlayingAudio():
					durationSec = plx.player.mcPlayer.GetTotalTime()
					currentPosSec = plx.player.mcPlayer.GetTime()
					stepSec = int(durationSec/100)
					offset = currentPosSec + stepSec
					plx.player.mcPlayer.SeekTime(offset)
					util.logInfo('WebClient: Step forward 1%')

			elif request_path == "player/playback/stepBack":
				self.response(getOKMsg(), getPlexHeaders())
				if plx.player.mcPlayer.IsPlayingVideo() or plx.player.mcPlayer.IsPlayingAudio():
					durationSec = plx.player.mcPlayer.GetTotalTime()
					currentPosSec = plx.player.mcPlayer.GetTime()
					stepSec = int(durationSec/100)
					offset = currentPosSec - stepSec
					plx.player.mcPlayer.SeekTime(offset)
					util.logInfo('WebClient: Step back 1%')

			elif request_path == "player/playback/skipNext":
				self.response(getOKMsg(), getPlexHeaders())
				util.logInfo('WebClient: Play next...')
				type = params['type']
				if type == 'photo':
					plx.getPhotoDialog().showNextImage()
				else:
					plx.player.mcPlayer.PlayNext()

			elif request_path == "player/playback/skipPrevious":
				self.response(getOKMsg(), getPlexHeaders())
				util.logInfo('WebClient: Play previouself...')
				type = params['type']
				if type == 'photo':
					plx.getPhotoDialog().showPrevImage()
				else:
					plx.player.mcPlayer.PlayPrevious()

			elif request_path == "player/navigation/moveUp":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Up")

			elif request_path == "player/navigation/moveDown":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Down")

			elif request_path == "player/navigation/moveLeft":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Left")

			elif request_path == "player/navigation/moveRight":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Right")

			elif request_path == "player/navigation/select":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Select")

			elif request_path == "player/navigation/home":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Home")

			elif request_path == "player/navigation/back":
				self.response(getOKMsg(), getPlexHeaders())
				jsonrpc("Input.Back")

			else:
				self.response('No implemented', code=500)

		except:
			traceback.print_exc()
	
class ClientListener(object):
	def __init__(self, port):
		self.port = port
		self.clientListener = None
		self.thread = None
		self.__running = False

	def isRunning(self):
		return self.__running

	def start(self):
		if self.clientListener:
			util.logWarn('Plexee client listener already started')
			return #Already started
		for i in range(3):
			try:
				self.clientListener = ThreadedHTTPServer(('localhost', self.port), MyHandler)
				self.clientListener.timeout = 0.95
				break
			except:
				#Probably address in use
				time.sleep(1)
				util.logError('Plexee client failed to start. Attempt %s of 3' % str(i))
		if self.clientListener is None:
			util.logError('Plexee client failed to start.')
			return

		self.thread = threading.Thread(target=self.__serve)
		self.thread.start()
		util.logInfo('Plexee client listener started')

	def __serve(self):
		self.__running = True
		while self.__running:
			self.clientListener.handle_request()

	def stop(self):
		if not self.clientListener:
			return #Not running
		try:
			self.__running = False
			mc.Http().Get('http://localhost:%i' % self.port)
			util.logDebug('Close server...')
			self.clientListener.server_close()
			util.logDebug('Wait for thread to end...')
			self.thread.join(5.0)
			util.logInfo('Plexee client listener stopped')
			self.clientListener = None
		except:
			util.logError('Error stopping Plexee client listener')
			traceback.print_exc()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	daemon_threads = True

	def server_bind(self):
		HTTPServer.server_bind(self)
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		util.logDebug('Server bound...')
