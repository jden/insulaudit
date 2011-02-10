import logging
from insulaudit.log import io, logger as log
from insulaudit import lib, core

import time


class FailedDataRead(Exception):
  pass

class ACK( object ):
  ACK         = 85  # U
  NAK         = 102 # f
  __ack__     = 'ACK'
  error       = -1
  readable    = -1
  __reason__  = 'UNKNOWN REASON'
  head        = ''
  REASONS     = [ "NO ERROR"
                , "CRC MISMATCH"
                , "COMMAND DATA ERROR"
                , "COMM BUSY AND/OR COMMAND CANNOT BE EXECUTED"
                , "COMMAND NOT SUPPORTED" ]
  def __init__( self, head ):
    self.head = head
    try:
      ( self.readable, self.error, self.code ) = head
    except ValueError, e:
      self.__reason__ = '%s:head.length:%s' % ( self.__reason__, len( head ) )
    print self.code
    self.__reason__ = '%s:%s' % ( self.error, self.REASONS[ self.code ] )
  
  def __repr__( self ):
    return (     self.readable == 1
             and self.error == self.ACK
           ) and self.__ack__  or self.__nak__( )

  def __nak__( self ):
    return '%s:raw:%s' % ( self.reason( ), lib.hexdump( self.head ) )

  def isACK( self ):
    return self.readable == 1 and self.error == self.ACK

  def isNAK( self ):
    return self.readable == 1 and self.error == self.NAK

  def isEmpty( readable ):
    return len( self.head ) == 0

  def reason( self ):
    return self.__reason__
    
class Reply( object ):
  
  log     = logging.getLogger( 'reply' )
  ack     = False
  info    = None
  __ACK__ = ACK

  def __init__( self, raw_reply ):
    self.log = logging.getLogger( self.__class__.__name__ )
    self.raw = raw_reply
    self.msg = bytearray( raw_reply )
    try:
      self.ack  = self.__ACK__( self.msg[ 0:3 ] )
      self.body = self.msg[ 3: len(self.msg) - 3 ]
    except IndexError, e:
      raise exceptions.NoReplyException( e )
    self.printable = str( self.msg ).encode( 'string_escape' )


  @staticmethod
  def dehex( S ):
    return [ dehex( l ) for l in S ]

  def __str__( self ):
    return pformat( { 'info' : repr( self.info )
                    , 'ack'  : self.ack
                    , 'body' : self.body } )

  def __repr__( self ):
    return "<{agent}:ack={ack}:{0}>".format( self.info,
                                   agent=self.__class__.__name__,
                                   ack=self.ack )

class CarelinkUsb( core.CommBuffer ):
  class ID:
    VENDOR  = 0x0a21
    PRODUCT = 0x8001
  timeout = .150

  #__response__ = core.Reply

  def radio( self, length, crc=True ):
    code = [ 12, 0 ]
    if crc:
      code.extend( [ lib.HighByte( length )
                   , lib.LowByte( length  ) ] )
      code.append( lib.CRC8.compute( code ) )
    self.write( str( bytearray( code ) ) )
    time.sleep( 0.200 )
    return bytearray( self.read( 64 ) )

  def __call__( self, command ):
    self.prevCommand = command
    x = str( command )
    self.serial.setTimeout( command.timeout )
    log.debug( 'setting timeout: %s' % command.timeout )
    io.info( 'carelink.command: %r\n%s' % ( command,
                                            command.hexdump( ) ) )
    self.write( x )
    self.write( x )
    log.debug( 'sent command, waiting' )
    time.sleep( command.sleep )
    reply = command( self )
    return reply
    response = self.read( 64 )
    # log.debug( 'response: %s' % bytearray( response ) )
    reply    = command( response )
    log.debug( 'command {0} inspects ACK{1}'.format(
                repr( command ),
                repr( reply.ack ) ) )
    #if reply.ack.isACK( ) or reply.ack.isNAK( ):
    reply    = command( reply, self )
    return reply


ERROR_LOOKUP = [ "NO ERROR",
  "CRC MISMATCH",
  "COMMAND DATA ERROR",
  "COMM BUSY AND/OR COMMAND CANNOT BE EXECUTED",
  "COMMAND NOT SUPPORTED" ]

class StickStatusStruct( object ):
  statmap = {
      'receiving.complete'      : 0x01,
      'receiving.progress'      : 0x02,
      'transmit.progress'       : 0x04,
      'interface.error'         : 0x08,
      'error.receiving.overflow': 0x10,
      'error.transmit.overflow' : 0x20
  }
  value = '????'
  flags = { }
  def __init__( self, status ):
    self.raw  = status
    flags = { }
    for k,v in self.statmap.iteritems( ):
      flags[ k ] = False
      if status & v > 0:
        flags[ k ] = True
        self.value = status & v
    self.flags = flags

  def __str__( self ):
    return '%s:%r' %( self.__class__.__name__, self.flags )

  def __repr__( self ):
    return '<{agent}:raw={raw}:flags={flags}>'.format(
                raw   = self.raw,
                flags = self.flags,
                agent = self.__class__.__name__ )



class USBStatus( core.Command ):
  """
  """
  __retries__ = 3
  code  = [ 3 ]
  ACK   = 85  # U
  NAK   = 102 # f
  label = 'usb.status'
  __info__ = { 'error.fatal'     : 0x00
             , 'status'          : 0x00
             , 'rfBytesAvailable': 0x00
             }

  def rfByteCount( self, count ):
    return lib.BangInt( count )

  def onACK(self):
    """Called by decode on success."""
    reply = self.reply
    info = { 'error.fatal'     : reply.body[ 3 ]
           , 'status'          : StickStatusStruct( reply.body[ 5 ] )
           , 'rfBytesAvailable': self.rfByteCount( reply.body[ 6:8 ] )
           }
    self.__dict__.update( info )
    reply.info = info
    self.info  = info
    
  def decode(self):
    """Should set self.info"""
    self.reply    = Reply( self.response )
    self.info = self.__info__
    if self.reply.ack.isACK( ):
      self.onACK()
    else:
      log.info('nonack:%s' % self.reply.ack)
    self.reply.info = self.info

  def read(self, port):
    response = None
    for i in xrange(self.__retries__):
      io.debug( 'retry %s' % i )
      port.read(0)
      #port.write('')
      #port.read(0)
      response = port.read( 64 )
      if len(response) > 0: break;
    return response

  def __call__( self, port ):
    """Should read from the port as needed by the command, set, self.response,
    call self.decode, and return self.  Returns an object with an info to be
    set. (returns self)"""
    #time.sleep( .2 )
    self.response = self.read(port)
    if self.response == '':
      raise FailedDataRead(repr(self))
    self.decode( )
    log.debug( 'status reply: %r' % self.info )
    return self
   

class USBProductInfo( USBStatus ):
  """Get product info from the usb device."""
  code   = [ 4, 0, 0 ]
  SW_VER = 16
  label  = 'usb.productInfo'
  rf_table  = { 001: '868.35Mhz' ,
                000: '916.5Mhz'  ,
                255: '916.5Mhz'  }
  iface_key = { 3: 'USB',
                1: 'Paradigm RF' }

  @classmethod
  def decodeInterfaces( klass, L ):
    n, tail    = L[ 0 ], L[ 1: ]
    interfaces = [ ]
    for x in xrange( n ):
      i    = x*2
      k, v = tail[i], tail[i+1]
      interfaces.append( ( k, klass.iface_key.get( v, 'UNKNOWN'  ) ) )
    return interfaces

  def onACK(self):
    reply = self.reply
    self.info = {
      'rf.freq'          : self.rf_table.get( reply.body[ 5 ], 'UNKNOWN' )
    , 'serial'           : (reply.body[ 0:3 ],
                           str( reply.body[ 0:3 ]).encode( 'hex'  ) )
    , 'product.version'  : '{0}.{1}'.format( *reply.body[ 3:5 ] )
    , 'description'      : str( reply.body[ 06:16 ] )
    , 'software.version' : '{0}.{1}'.format( *reply.body[ 16:18 ] )
    , 'interfaces'       : self.decodeInterfaces( reply.body[ 18: ] )
    }


class InterfaceStats( USBStatus ):
  code          = [ 5 ]
  INTERFACE_IDX = 19
  label         = 'usb.interfaceStats'
  def onACK(self):
    b = self.reply.body
    self.reply.info = {
      'errors.crc'      : b[ 0 ]
    , 'errors.sequence' : b[ 1 ]
    , 'errors.naks'     : b[ 2 ]
    , 'errors.timeouts' : b[ 3 ]
    , 'packets.received': lib.BangLong( b[ 4: 8 ] )
    , 'packets.transmit': lib.BangLong( b[ 8:12 ] )
    }

class USBInterfaceStats( InterfaceStats ):
  code          = [ 5, 1 ]
  label         = 'usb.interfaceStats'

class RadioInterfaceStats( InterfaceStats ):
  code          = [ 5, 0 ]
  label         = 'usb.interfaceStats'

class USBSignalStrength( USBStatus ):
  code  = [ 6, 0 ]
  label = 'usb.signalStrength'
  value = '??'

  def decode(self):
    self.info = self.response[ 0 ]
    log.info( '{0}: {1}dBm'.format( self.label, self.info ) )
    

  def __repr__( self ):
    return '<{agent}:code={code}, label={label} {signal}dBm>'\
           .format( code   = repr( self.code ),
                    agent  = self.__class__.__name__,
                    signal = self.info,
                    label  = self.label )
    
if __name__ == '__main__':
  import doctest
  doctest.testmod( )

#####
# EOF
