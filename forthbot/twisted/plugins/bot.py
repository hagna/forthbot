# -*- test-case-name: ircbot.test.test_twistd_plugin -*-

"""
Plugin hook module for twistd service.
"""

from os.path import join

from zope.interface import implements

from twisted.application.service import IServiceMaker
from twisted.application.internet import TCPClient
from twisted.plugin import IPlugin
from twisted.python.usage import Options, portCoerce

class _IrcBotPlugin(object):
    """
    Trivial glue class to expose a twistd service.
    """
    implements(IPlugin, IServiceMaker)

    class options(Options):
        """
        IrcBot twistd command line options.
        """
        optParameters = [
            ('port', 'p', 6667, 'TCP port to connect to.', portCoerce),
			('server', 's', '10.1.2.209', 'IRC server'),
			('channel', 'c', 'test', 'channel to join'),
             ]

    description = "ircbot log bot"

    tapname = "ircbot"

    def makeService(self, options):
        """
        Create a service which will run a IrcBot server.

        @param options: mapping of configuration
        """
        from pygame.image import load

        from forthbot.ircLogBot import LogBotFactory
        from twisted.python.filepath import FilePath
        from twisted.internet import reactor
        from twisted.application.service import MultiService
        from twisted.protocols.policies import TrafficLoggingFactory
        port = options['port']
        server = options['server']
        channel = options['channel']
        logfile = channel + '.log'
        f = LogBotFactory(channel, logfile)

        service = MultiService()
        tcp = TCPClient(server, port, f)
        tcp.setName('TCP_SERVICE_ircbot')
        tcp.setServiceParent(service)

        return service

ircbotplugin = _IrcBotPlugin()
