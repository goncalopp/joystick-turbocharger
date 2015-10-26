import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
log= logging.getLogger(__name__)

def set_level( is_debug ):
    log.setLevel( logging.DEBUG if is_debug else logging.WARNING)
