#!/bin/sh

#please run this before AND after starting joystick_shift

#load userspace input kernel module
sudo modprobe uinput

#allow the current user to fake input events (he has sudo, anyway...)
sudo chown $(whoami) /dev/uinput

#prevent X from using joystick as a mouse
xinput set-prop 'joystick_shift' "Device Enabled" 0
