#!/usr/bin/env python
import pyforms
from pyforms import BaseWidget
from pyforms.Controls import ControlCheckBoxList, ControlButton, ControlNumber, ControlLabel
from pyforms.gui.Controls.ControlImage import ControlImage

import requests
import threading
import urllib
import xmltodict

from zeroconf import ServiceBrowser, Zeroconf

class STListener( object ):

    def __init__( self, device_added_cb, device_removed_cb ):
        self.device_added_cb = device_added_cb
        self.device_removed_cb = device_removed_cb

    def remove_service( self, zeroconf, type, name ):
        print "service name: %s - remove called" % name
        self.device_removed_cb( "don't have ip" )

    def add_service( self, zeroconf, type, name ):
        info = zeroconf.get_service_info( type, name )
        ip = '%d.%d.%d.%d' % ( ord( info.address[0] ), ord( info.address[1] ), ord( info.address[2]  ), ord( info.address[3] ) )
        self.device_added_cb( ip )


class UI( BaseWidget ):

    def __init__( self ):
        super( UI, self ).__init__( "Bose SoundTouch UI" )

        self.ip = None
        self.speakers = {}

        self._speakers = ControlCheckBoxList( "Speakers" )
        self._speakers.selection_changed_event = self.speaker_selected

        self._remove = ControlButton( "Remove" )
        self._set = ControlButton( "Set" )
        self._add = ControlButton( "Add" )
        self._volume = ControlNumber()
        self._volume.decimals = 0
        self._volume_set = ControlButton( "Set Volume" )
        self._volume_get = ControlButton( "Get Volume" )
        self._volume_value = ControlLabel()
        self._bass = ControlNumber()
        self._bass.decimals = 0
        self._bass_set = ControlButton( "Set Bass (neg)" )
        self._bass_get = ControlButton( "Get Bass" )
        self._bass_value = ControlLabel()
        self._power = ControlButton( "Power" )
        self._mute = ControlButton( "Mute" )
        self._now_playing = ControlButton( "Now Playing" )
        self._prev = ControlButton( "Prev" )
        self._play_pause = ControlButton( "Play/Pause" )
        self._next = ControlButton( "Next" )
        self._p1 = ControlButton( "P1" )
        self._p2 = ControlButton( "P2" )
        self._p3 = ControlButton( "P3" )
        self._p4 = ControlButton( "P4" )
        self._p5 = ControlButton( "P5" )
        self._p6 = ControlButton( "P6" )

        self._zone = ControlCheckBoxList( "Zone Info" )
        self._info = ControlCheckBoxList( "Speaker Info" )
        self._np = ControlCheckBoxList( "Now Playing" )
        self._art = ControlImage()

        self.formset = ( [ '_zone', '_info' ],
            [ ( '_speakers' ),
              ( '_remove', '_set', '_add' ),
              ( '_volume', '_volume_set', '_volume_get', '_volume_value' ),
              ( '_bass', '_bass_set', '_bass_get', '_bass_value' ),
              ( '_power', '_mute', '_now_playing' ),
              ( '_prev', '_play_pause', '_next' ),
              ( '_p1', '_p2', '_p3' ),
              ( '_p4', '_p5', '_p6' ) ],
              [ '_np', '_art' ] )

        self._add.value = self.__add
        self._set.value = self.__set
        self._remove.value = self.__remove
        self._volume_get.value = self.__volume_get
        self._volume_set.value = self.__volume_set
        self._bass_get.value = self.__bass_get
        self._bass_set.value = self.__bass_set
        self._power.value = self.__power
        self._mute.value = self.__mute
        self._now_playing.value = self.set_now_playing
        self._prev.value = self.__prev
        self._play_pause.value = self.__play_pause
        self._next.value = self.__next
        self._p1.value = self.__preset1
        self._p2.value = self.__preset2
        self._p3.value = self.__preset3
        self._p4.value = self.__preset4
        self._p5.value = self.__preset5
        self._p6.value = self.__preset6

        self.zeroconf = Zeroconf()
        self.st_listener = STListener( self.device_added, self.device_removed )
        self.browser = ServiceBrowser( self.zeroconf, "_soundtouch._tcp.local.", self.st_listener )

        self.select_device_timer = threading.Timer( 10.0, self.select_device )

    def before_close_event( self ):
        self.zeroconf.close()

    def device_added( self, ip ):
        r = requests.get( "http://" + ip + ":8090/info" )
        d = xmltodict.parse( r.text )
        self._speakers.__add__( d['info']['name'] + " (" + ip + ")" )
        self.select_device_timer.cancel()
        self.select_device_timer = threading.Timer( 2.0, self.select_device )
        self.select_device_timer.start()

    def select_device( self ):
        #self.speaker_selected()
        pass

    def device_removed( self, ip ):
        print "device removed: %s" % ip

    def __add( self):
        z = '<zone master="' + self.deviceId + '">'
        ip = self._zone.items[ self._zone.selected_row_index ][0].split('(')[-1].split(')')[0]
        id = self.ipDeviceId( ip )
        z += '<member ipaddress="' + ip + '">' + id + '</member>'
        z += '</zone>'
        requests.post( self.url + "/addZoneSlave", z )
        self.set_zone()

    def __remove( self):
        z = '<zone master="' + self.deviceId + '">'
        ip = self._zone.items[ self._zone.selected_row_index ][0].split('(')[-1].split(')')[0]
        id = self.ipDeviceId( ip )
        z += '<member ipaddress="' + ip + '">' + id + '</member>'
        z += '</zone>'
        requests.post( self.url + "/removeZoneSlave", z )
        self.set_zone()

    def __set( self ):
        z = '<zone master="' + self.deviceId + '">'
        devices = self._zone.items
        for device in devices:
            ip = device[0].split('(')[-1].split(')')[0]
            slave = device[1]
            id = self.ipDeviceId( ip )
            if slave:
                z += '<member ipaddress="' + ip + '">' + id + '</member>'
        z += '</zone>'
        requests.post( self.url + "/setZone", z )
        self.set_zone()

    def __volume_get( self ):
        r = requests.get( self.url + "/volume" )
        d = xmltodict.parse( r.text )
        v = d['volume']['actualvolume']
        self._volume_value.value = v
        self._volume.value = int(v)

    def __volume_set( self ):
        d = '<volume>' + str( self._volume.value ).split('.')[0] + '</volume>'
        requests.post( self.url + "/volume", d )
        self.__volume_get()

    def __bass_get( self ):
        r = requests.get( self.url + "/bass" )
        d = xmltodict.parse( r.text )
        v = d['bass']['actualbass']
        self._bass_value.value = v
        self._bass.value = -int(v)

    def __bass_set( self ):
        d = '<bass>-' + str( self._bass.value ).split('.')[0] + '</bass>'
        requests.post( self.url + "/bass", d )
        self.__bass_get()

    def __power( self ):
        self.send_key( "POWER", "release" )

    def __mute( self ):
        self.send_key( "MUTE", "press" )

    def __prev( self ):
        self.send_key( "PREV_TRACK", "press" )

    def __play_pause( self ):
        self.send_key( "PLAY_PAUSE", "press" )

    def __next( self ):
        self.send_key( "NEXT_TRACK", "press" )

    def __preset1( self ):
        self.send_key( "PRESET_1", "release" )

    def __preset2( self ):
        self.send_key( "PRESET_2", "release" )

    def __preset3( self ):
        self.send_key( "PRESET_3", "release" )

    def __preset4( self ):
        self.send_key( "PRESET_4", "release" )

    def __preset5( self ):
        self.send_key( "PRESET_5", "release" )

    def __preset6( self ):
        self.send_key( "PRESET_6", "release" )

    def send_key( self, key, action ):
        data = '<key state="' + action + '" sender="Gabbo">' + key + '</key>'
        requests.post( self.url + "/key", data )

    def speaker_selected( self ):
        selected = self._speakers.selected_row_index
        if( selected == -1):
            selected = 0

        ip = self._speakers.items[ selected ][0].split('(')[-1].split(')')[0]
        self.url = "http://" + ip + ":8090"

        r = requests.get( self.url + "/info" )
        d = xmltodict.parse( r.text )
        self._info.clear()
        self._info.__add__( "Name: " + d['info']['name'] )
        deviceId = d['info']['@deviceID']
        self.deviceId = deviceId
        self._info.__add__( "ID: " + deviceId )
        self._info.__add__( "Type: " + d['info']['type'] )
        self._info.__add__( "MargeID: " + d['info']['margeAccountUUID'] )
        self._info.__add__( "MargeURL: " + d['info']['margeURL'] )
        self._info.__add__( "IP: " + d['info']['networkInfo'][0]['ipAddress'] )
        ver = d['info']['components']['component'][0]['softwareVersion']
        self._info.__add__( "Version: " + ver.split(' ')[0] )
        self._info.__add__( "Firmware Date: " + ver.split(' ')[1].split('.')[-1] )
        self._info.__add__( "Firmware Author: " + ver.split(' ')[1].split('.')[0] )
        self._info.__add__( "Firmware Branch: " + ver.split(' ')[1].split('.')[1] )
        self._info.__add__( "Firmware BuildMachine: " + ver.split(' ')[1].split('.')[2] )

        self.set_now_playing()
        self.set_zone()
        self.__volume_get()
        self.__bass_get()

    def set_zone( self ):
        self._zone.clear()
        r = requests.get( self.url + "/getZone" )
        d = xmltodict.parse( r.text )

        master = None
        try:
            master = d['zone']['@master']
        except:
            pass

        if( master and not master == self.deviceId ):
            self._zone.__add__( "Device is slave" )
            return

        devices = self._speakers.items
        for device in devices:
            ip = device[0].split('(')[-1].split(')')[0]
            id = self.ipDeviceId( ip )
            if( ( not id == self.deviceId ) and ( not id == master ) ):
                member = False
                try:
                    m = d['zone']['member']['#text']
                    if( m == id ):
                        member = True
                    self._zone.__add__( ( device[0], member ) )
                    continue
                except:
                    pass
                try:
                    members = d['zone']['member']
                    for m in members:
                        if( m['#text'] == id ):
                            member = True
                            break
                except:
                    pass
                self._zone.__add__( ( device[0], member ) )

    def ipDeviceId( self, ip ):
        r = requests.get( "http://" + ip + ":8090/info" )
        d = xmltodict.parse( r.text )
        return d['info']['@deviceID']

    def set_now_playing( self ):
        self._np.clear()
        r = requests.get( self.url + "/now_playing" )
        d = xmltodict.parse( r.text )
        self.set_track_info( d, "Play Status", "playStatus" )
        self._np.__add__( "Music Service: " + d['nowPlaying']['@source'] )
        try:
          self._np.__add__( "Account: " + d['nowPlaying']['@sourceAccount'] )
        except:
            pass
        self.set_track_info( d, "Track Name", "track" )
        self.set_track_info( d, "Track Artist", "artist" )
        self.set_track_info( d, "Track Album", "album" )
        self.set_track_info( d, "Track Station", "stationName" )
        self.set_track_info( d, "Track Time Total", "time", "@total" )
        self.set_track_info( d, "Track Time into", "time", "#text" )

        try:
            art = d['nowPlaying']['art']['#text']
            urllib.urlretrieve( art, "/tmp/art" )
            self._art.value = "/tmp/art"
        except:
            try:
                art = d['nowPlaying']['ContentItem']['containerArt']
                urllib.urlretrieve( art, "/tmp/art" )
                self._art.value = "/tmp/art"
            except:
                pass

    def set_track_info( self, d, name, key, subkey=None ):
        try:
          if subkey:
              v = d['nowPlaying'][key][subkey]
          else:
              v = d['nowPlaying'][key]

          self._np.__add__( name + ": " + v )
        except:
            pass


if __name__ == "__main__":
    pyforms.start_app( UI )

