#!/usr/bin/env python

import struct
import argparse
import uinput   #https://github.com/tuomasjjrasanen/python-uinput
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
log= logging.getLogger(__name__)

EVENT_AXIS, EVENT_BUTTON= 2,1 #joystick event type

class JoystickSender(object):
    def __init__( self, receiver ):
        self.receiver= receiver
    
    def send(self, event_type, ctrl_id, value):
        self.receiver( event_type, ctrl_id, value )

class JoystickMapper(JoystickSender):
    def receive( self, event_type, ctrl_id, value ):
        args= self.map( event_type, ctrl_id, value )
        if args is not None:
            self.send( *args )
    
    def map(self, event_type, ctrl_id, value):
        return event_type, ctrl_id, value

class ShiftMapper( JoystickMapper ):
    '''"Shifts" the joystick using one of its buttons - similar to the
    shift key on the keyboard. '''
    
    def __init__(self, 
            receiver, 
            buttons_to_shift, 
            axes_to_shift, 
            button_offset, 
            axes_offset, 
            shift_button, 
            toggle=False,
            output_shift_key_events=False):
        '''buttons_to_shift and axes_to_shift are lists of numbers of which elements to shift
        offsets are integers added to axes/buttons number when they are shifted
        shift_button is the number of the button to act as the shift "key" 
        toggle makes this act "as CAPS LOCK", instead of shift (toggle key)
        output_shift_key_events indicates if we want the shift button presses to be output (instead of suppressed)
        '''
        JoystickMapper.__init__(self, receiver)
        assert not shift_button in buttons_to_shift #I don't even want to think about it
        self.shift_elements= (set(buttons_to_shift), set(axes_to_shift))
        self.offsets= (button_offset, axes_offset)
        self.shift_button= shift_button
        self.type_dict= {EVENT_BUTTON:0, EVENT_AXIS:1}
        self.shift_state= 0
        self.output_shift_key_events= output_shift_key_events
        self.toggle= toggle
    
    def map( self, event_type, ctrl_id, value ):
        if event_type==EVENT_BUTTON and ctrl_id==self.shift_button:
            if not self.toggle or (self.toggle and value==1):
                self.shift_state= 1-self.shift_state #0->1, 1->0
                log.info("shift key at {}".format(self.shift_state))
                if not self.output_shift_key_events:
                    return None
        i= self.type_dict[event_type]
        if self.shift_state and ctrl_id in self.shift_elements[i]:
            ctrl_id+= self.offsets[i]
        return event_type, ctrl_id, value
        

class VirtualJoystick(object):
    def __init__(self, num_axes, num_buttons):
        #see https://github.com/tuomasjjrasanen/python-uinput/blob/master/examples/joystick.py
        self.num_axes, self.num_buttons= num_axes, num_buttons
        self.events= \
            [(uinput.ABS_X[0], uinput.ABS_X[1]+i, -128, 127, 0, 0) for i in range(num_axes)] + \
            [(uinput.BTN_0[0], uinput.BTN_0[1]+i) for i in range(num_buttons)] 
        self.device= uinput.Device( self.events, name="joystick_shift")


    def send( self, event_type, ctrl_id, value ):
        '''the signature of this function follows event_loop.event_receiver'''
        log.debug("Emmiting {} {} {}".format(event_type, ctrl_id, value))
        i= ctrl_id
        if event_type==EVENT_BUTTON:
            
            self.device.emit( (uinput.BTN_0[0], uinput.BTN_0[1]+i), value )
        if event_type==EVENT_AXIS:
            self.device.emit( (uinput.ABS_X[0], uinput.ABS_X[1]+i), value )

    def destroy(self):
        self.device.destroy()
        
        
def event_loop( dev_filename, event_receiver ):
    '''event loop that reads events from the physical joystick'''
    joystick_file= open(dev_filename)
    while True:
        data= joystick_file.read(8)
        d1,time,ignore1,ignore2,d2,d3,event_type,ctrl_id= data
        axis_value= d3
        button_value= ord(d2)
        event_type= ord(event_type)
        ctrl_id= ord(ctrl_id)
        axis_value= struct.unpack('b', axis_value)[0]
        if not event_type in (EVENT_AXIS, EVENT_BUTTON):
            continue #event_type contains some strange stuff on the beggining of file
        value= axis_value if event_type==EVENT_AXIS else button_value
        log.debug("joystick received {} {} {}".format(event_type, ctrl_id, value))
        event_receiver( event_type, ctrl_id, value)

def argument_parser():
    parser = argparse.ArgumentParser(description= \
        '''Shift joystick keys. Creates a virtual joystick with twice as many '''
        '''axes and buttons as your real one, and allows you to control the '''
        '''new ones using a "shift-button", much like your keyboard shift key. \n'''
        '''\n'''
        '''Don't forget to mv the original /dev/jsX out of the way if your game '''
        '''accepts input from ALL joysticks (otherwise you'll get repeated events).'''
        )
    parser.add_argument('-d', '--debug', action='store_true',       help='print debug messages')
    parser.add_argument('-t', '--toggle', action='store_true',      help='Act as CAPS LOCK instead of shift')
    parser.add_argument('-a', '--n_axes', type=int, default=6,      help='number of axes of the physical joystick')
    parser.add_argument('-b', '--n_buttons', type=int, default=16,  help='number of buttons of the physical joystick')
    parser.add_argument('device', type=str,                         help='joystick device file')
    parser.add_argument('shiftbtn', type=int,                       help='Number of the button acting as shift')
    
    
    return parser

if __name__=="__main__":
    parser= argument_parser()
    args= parser.parse_args()
    
    log.setLevel( logging.DEBUG if args.debug else logging.WARNING)

    buttons_to_shift= set(range(args.n_buttons+1)) - set((args.shiftbtn,))
    axes_to_shift=    set(range(args.n_axes+1))
    
    log.info("Creating virtual joystick")
    vj= VirtualJoystick( args.n_axes*2, args.n_buttons*2 )
    mapper= ShiftMapper( 
        receiver= vj.send, 
        buttons_to_shift= buttons_to_shift, 
        axes_to_shift=  axes_to_shift, 
        button_offset=  args.n_buttons, 
        axes_offset=    args.n_axes,
        shift_button=   args.shiftbtn,
        toggle=         args.toggle,
        output_shift_key_events= False)
    try:
        log.info("Entering event loop")
        event_loop(args.device, mapper.receive)
    except KeyboardInterrupt:
        log.info("Received KeyboardInterrupt. Exiting...")
        vj.destroy()
        exit()

