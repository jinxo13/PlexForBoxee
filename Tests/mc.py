import urllib2, urllib
import xbmc
import os
from elementtree import ElementTree
import util
import time

def fileExists(f): return os.access(f, os.F_OK)

__ACTIVE_WINDOW = None
__WINDOWS = {}

class ListItem(object):
	MEDIA_UNKNOWN = 0
	MEDIA_AUDIO_MUSIC = 1
	MEDIA_VIDEO_CLIP = 2
	def __init__(self, type = 0):
		self.title = ''
		self.path = ''
		self.contentType = ''
		self.props = dict()

	def SetTitle(self, val): self.title = val
	def GetTitle(self): return self.title
	def SetPath(self, val): self.path = val
	def GetPath(self): return self.path
	def SetContentType(self, val): self.contentType = val
	def GetContentType(self): return self.contentType
	def SetImage(self, indx, path): pass
	def GetImage(self, indx): return ''
	def SetProperty(self, prop, value): self.props[prop] = value
	def GetProperty(self, prop):
		if prop in self.props:
			return self.props[prop]
		else:
			return ''
			
class Config:
	"""
	Alternate config to the mc config class
	Used when the mc config isn't working
	"""
	def __init__(self, filepath):
		self.__configFile = filepath
		self.__tree = None
		self.__isvalid = False
		self.__lastModified = -1
		try:
			if not fileExists(filepath):
				f = open(filepath, 'w')
				f.write('<registry/>')
				f.close()
				self.__lastModified = os.stat(filepath).st_mtime
			self.__tree = ElementTree.parse(filepath)
			self.__isvalid = True
		except IOError:
			#Error creating file.... permissions problem?
			util.logError("Failed to create settings file at %s" % filepath)

	def isValid(self): return self.__isvalid
	
	def GetValue(self, key):
		mt = os.stat(self.__configFile).st_mtime
		if mt != self.__lastModified:
			#File changed - reload
			self.__tree = ElementTree.parse(self.__configFile)
			self.__lastModified = mt
		for child in self.__tree.getroot():
			if child.attrib['id'] == key:
				result = child.text
				if result is None: return ''
				else: return result
		return ''

	def SetValue(self, key, value):
		#Update value in file
		found = False
		root = self.__tree.getroot()
		for child in root:
			if child.attrib['id'] == key:
				child.text = value
				found = True
				break
		if not found:
			e = ElementTree.Element('value', {'id':key})
			e.text = value
			root.append(e)
		self.__tree.write(self.__configFile)


class Control:
	def SetVisible(self, b): pass
	def SetFocus(self): pass

class Label(Control):
	def __init__(self): self.label = ''
	def SetLabel(self, l): self.label = l
	def GetLabel(self): return self.label

class Button(Control):
	pass

class List(Control):
	def __init__(self): self.items = []
	def SetItems(self, i): self.items = i
	def GetItems(self): return self.items

class Window:
	def __init__(self): self.controls = dict()
	def GetLabel(self, i): return self.GetControl(i, Label)
	def GetButton(self, i):	return self.GetControl(i, Button)
	def GetList(self, i):	return self.GetControl(i, List)
	def GetControl(self, i, type = Control):
		if i in self.controls: return self.controls[i]
		c = type()
		self.controls[i] = c
		return c

class Player:
	def __init__(self):
		self.__item = ListItem()
		self.__item_state = {'type': 'audio|video', 'state': 'playing|buffering|paused'}
		self.__vol = 100
	def IsPlaying(self):
		return self.__item_state['type'] == 'video' or self.__item_state['type'] == 'audio'
	def IsPlayingVideo(self):
		return self.__item_state['type'] == 'video'
	def IsPlayingAudio(self):
		return self.__item_state['type'] == 'audio'
	def GetPlayingItem(self):
		return self.__item
	def IsPaused(self):
		return self.__item_state['state'] == 'paused'
	def IsCaching(self):
		return self.__item_state['state'] == 'buffering'
	def GetTime(self):
		return 0
	def GetTotalTime(self):
		return 0
	def SeekTime(self, time):
		pass
	def PlayInBackground(self, li):
		self.__item = li
		self.__item_list = []
		self.__item_pos = 0
		self.__item_state['type'] == 'audio'
		self.__item_state['state'] == 'playing'
	def Stop(self):
		self.__item_state['type'] == 'none'
		self.__item_state['state'] == 'none'
	def Pause(self):
		self.__item_state['state'] == 'paused'
	def PlayList(self, type, items):
		if type == PlayList.PLAYLIST_MUSIC:
			self.__item_state['type'] == 'audio'
		else:
			self.__item_state['type'] == 'video'
		self.__item_state['state'] == 'playing'
		self.__item = items[0]
		self.__item_list = items
		self.__item_pos = 0
	def GetVolume(self):
		return self.__vol
	def SetVolume(self, vol):
		self.__vol = vol
	def PlayNext(self):
		if len(self.__item_list) == 0:
			return
		self.__item_pos = self.__item_pos+1
		if self.__item_pos > len(self.__item_list):
			self.__item_pos = 0
		self.__item = self.__item_list[self.__item_pos]
	def PlayPrevious(self):
		if len(self.__item_list) == 0:
			return
		self.__item_pos = self.__item_pos-1
		if self.__item_pos < 0:
			self.__item_pos = len(self.__item_list)-1
		self.__item = self.__item_list[self.__item_pos]

class App:
	def GetLocalConfig(self): return _config
	def GetId(self): return 'plexee.plexforboxee'

class Http(object):
	def __init__(self):
		self.opener = urllib2.build_opener(urllib2.HTTPHandler)
		self.headers = dict()
		self.code = 0

	def GetHttpResponseCode(self):
		return self.code

	def Get(self, url):
		util.logDebug('MC: GET %s' % url)
		request = urllib2.Request(url)
		for p in self.headers:
			request.add_header(p, self.headers[p])
		try:
			resp = self.opener.open(request)
			self.code = resp.code
			return resp.read()
		except urllib2.HTTPError, e:
			self.code = e.code
			util.logDebug('MC: POST error %d' % e.code)
			if e.code == 201:
				return e.read()
			return None

	def Reset(self):
		self.code = 0
		self.headers.clear()

	def Post(self, url, data):
		util.logDebug('MC: POST %s' % url)
		request = urllib2.Request(url, data)
		for p in self.headers:
			request.add_header(p, self.headers[p])
		request.get_method = lambda: 'POST'
		try:
			resp = self.opener.open(request)
			self.code = resp.code
			return resp.read()
		except urllib2.HTTPError, e:
			self.code = e.code
			util.logDebug('MC: POST error %d' % e.code)
			if e.code == 201:
				return e.read()
			return None

	def SetHttpHeader(self, prop, value):
		self.headers[prop] = value

def GetInfoString(prop):
	if prop == "System.BuildVersion":
		return 1

# Do not change DeviceId - used in actual logging code
def GetDeviceId():
	return "unittest"

def GetApp():
	return _app

def ActivateWindow(i):
	__ACTIVE_WINDOW = GetWindow(i)

def GetActiveWindow():
	return __ACTIVE_WINDOW

def GetWindow(i):
	if not __WINDOWS.has_key(i):
		__WINDOWS[i] = Window()
	return __WINDOWS[i]

def GetPlayer():
	return _player

def ShowDialogWait():
	util.logInfo('DialogWait...')
def HideDialogWait():
	util.logInfo('...DialogWait Ended')
def ShowDialogNotification(msg):
	util.logInfo('DialogNotification: %s' % msg)

class State:
	DIALOG_TEXT = ''

def SetDialogKeyboardText(text): State.DIALOG_TEXT = text
def ShowDialogKeyboard(title, text, bool):
	if State.DIALOG_TEXT == '': return text
	return State.DIALOG_TEXT

def __getCurrentDateTime():
	return time.strftime("%d/%m/%Y %H:%M:%S")

def LogInfo(msg): print(__getCurrentDateTime() + ' LogInfo: %s' % msg)
def LogError(msg): print(__getCurrentDateTime() + ' LogError: %s' % msg)
def LogDebug(msg): print(__getCurrentDateTime() + ' LogDebug: %s' % msg)

_app = App()
_player = Player()
_config = Config(os.path.join(xbmc.translatePath('special://profile'),'apps',GetApp().GetId(),'registry.xml'))

def ListItems(): return []

class PlayList(object):
	PLAYLIST_MUSIC = 0
	PLAYLIST_VIDEO = 1
	
	def __init__(self, type):
		self.__list = []
		self.type = type
	def Clear(self): self.__list = []
	def Add(self, val): self.__list.append(val)
	def Play(self):
		GetPlayer().PlayList(self.type, self.__list)
