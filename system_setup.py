import subprocess

from my_logging import log

def run_command( l, catch=None ):
     try:
        msg= subprocess.check_output(l, stderr=subprocess.STDOUT)
        return msg
     except subprocess.CalledProcessError as e:
        if catch:
            catch( e.output )
        else:
            raise

def setup_system1( phy_joystick_dev ):
    log.info("Loading kernel module")
    run_command(["modprobe","uinput"])

    log.info("Making physical joystick unusable by other programs")
    #block physical joystick device file so that other processes don't grab (repeated) events from it
    msg= run_command(
        ["chmod", "ugo-rwx", phy_joystick_dev], 
        catch= lambda e: log.warning("Failed to make physical joystick unusable by other programs. You'll have to mv the device file yourself, or risk receiving duplicate joystick events. Error: " + e ) )

def setup_system2( device_name ):
    #prevent X from using virtual joystick as mouse
    log.debug("Preventing X from using the virtual joystick as a mouse")
    run_command(
        ["xinput", "set-prop", device_name, "Device Enabled", "0"],
        catch= lambda e: log.warning("xinput set-prop failed: "+e) )

def unsetup_system( phy_joystick_dev ):
    #unblock physical joystick device file to its original location
    log.info("Making physical joystick usable by other programs")
    run_command(
        ["chmod", "ugo-rwx", phy_joystick_dev],
        #a error can happen because we no longer have permissions after drop_privileges
        catch= lambda e: log.warning("Due to technical limitations, your physical joystick is unusable from other programs until you re-plug it") )

def drop_privileges(uid_name='nobody', gid_name='nogroup'):
    '''drop root privileges, to avoid security issues'''
    import os, pwd, grp
    if os.getuid() != 0:
        return
    log.info("dropping root privileges")
    running_uid = pwd.getpwnam(uid_name).pw_uid
    running_gid = grp.getgrnam(gid_name).gr_gid
    os.setgroups([])
    os.setgid(running_gid)
    os.setuid(running_uid)
    old_umask = os.umask(077)
 
