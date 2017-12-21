import urllib2
from urllib2 import *

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import config

def build_opener(*handlers):
    if not config.get_ucsm_https_verify():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib2.build_opener(urllib2.HTTPSHandler(context=ctx), *handlers)
    else:
        return urllib2.build_opener(*handlers)
