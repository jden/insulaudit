
#
# TODO: move all constants to config module.
#

import serial 
from insulaudit.log import io, logger as log
from insulaudit import lib, config


# TODO: implement Buffer API and enable context manager.
class CommBuffer( object ):
  def __init__( self, port, timeout=config.settings.timeout ):
    self.timeout = timeout
    self.open( port )


  def open( self, newPort=False ):
    if newPort:
      self.port = newPort

    self.serial = serial.Serial( self.port, timeout=self.timeout )

    if self.serial.isOpen( ):
      log.info( '{agent} opened serial port: {serial}'\
         .format( serial = repr( self.serial ),
                  agent  =self.__class__.__name__ ) )

  def close( self ):
    io.info( 'closing serial port' )
    return self.serial.close( )
    
  def write( self, string ):
    r = self.serial.write( string )
    io.info( 'usb.write.len: %s\n%s' % ( len( string ),
                                         lib.hexdump( bytearray( string ) ) ) )
    return r

  def read( self, c ):
    r = self.serial.read( c )
    io.info( 'usb.read.len: %s'   % ( len( r ) ) )
    io.info( 'usb.read.raw: \n%s' % ( lib.hexdump( bytearray( r ) ) ) )
    return r
    
  def readline( self ):
    r = self.serial.readline( )
    io.info( 'usb.read.len: %s\n%s' % ( len( r ),
                                        lib.hexdump( r ) ) )
    return r
      
  def readlines( self ):
    r = self.serial.readlines( )
    io.info( 'usb.read.len: %s\n%s' % ( len( r ),
                                        lib.hexdump( r ) ) )
    return r

if __name__ == '__main__':
  import doctest
  doctest.testmost( )


#####
# EOF
