#!/usr/bin/python

"""
This example shows how to create an empty Mininet object
(without a topology object) and add nodes to it manually.
"""

from mininet.net import Mininet
from mininet.node import RemoteController, Controller
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def emptyNet():

    """"Create an empty network and add nodes to it."""

    net = Mininet( controller=RemoteController )

    info('*** Adding controller\n')
    c0 = net.addController('c0')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.1.1/24',
                     mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.1.2/24',
                     mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.1.3/24',
                     mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.1.4/24',
                     mac='00:00:00:00:00:04')
    h5 = net.addHost('h5', ip='10.0.1.5/24',
                     mac='00:00:00:00:00:05')
    h6 = net.addHost('h6', ip='10.0.1.6/24',
                     mac='00:00:00:00:00:06')

    info('*** Adding switch\n')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    s3 = net.addSwitch('s3', protocols='OpenFlow13')
    s4 = net.addSwitch('s4', protocols='OpenFlow13')
    s5 = net.addSwitch('s5', protocols='OpenFlow13')

    info('*** Creating links\n')
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    net.addLink(h3, s1)
    net.addLink(h4, s5)
    net.addLink(h5, s5)
    net.addLink(h6, s5)
    net.addLink(s1, s2)
    net.addLink(s1, s3)
    net.addLink(s1, s4)
    net.addLink(s2, s5)
    net.addLink(s3, s5)
    net.addLink(s4, s5)

    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    s3.start([c0])
    s4.start([c0])
    s5.start([c0])

    info('*** Running CLI\n')
    CLI(net)

    info('*** Stopping network')
    net.stop()


if __name__ == '__main__':
    setLogLevel( 'info' )
    emptyNet()
