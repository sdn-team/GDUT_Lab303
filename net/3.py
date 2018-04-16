# !/usr/bin/python

"""
    This example create 7 sub-networks to connect 7  domain controllers.
    Each domain network contains at least 5 switches.
    For an easy test, we add 2 hosts for one switch.
    So, in our topology, we have at least 35 switches and 70 hosts.
    Hope it will work perfectly.
"""

from mininet.net import Mininet
from mininet.node import Controller, RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo
import logging
import os


def multiControllerNet(con_num=2, sw_num=7, host_num=3):
    "Create a network from semi-scratch with multiple controllers."

    controller_list = []
    switch_list = []
    host_list = []

    net = Mininet(controller=None, switch=OVSSwitch, link=TCLink)

    for i in xrange(con_num):
        name = 'controller%s' % str(i)
        c = net.addController(name, controller=RemoteController,
                                  port=6661 + i)
        controller_list.append(c)
        print "*** Creating %s" % name

    print "*** Creating switches"
    switch_list = [net.addSwitch('s%d' % n,protocols='OpenFlow13') for n in xrange(sw_num)]
    
    print "*** Creating hosts"
    host_list = [net.addHost('h%d' % n) for n in xrange(host_num)]

    print "*** Creating links of host2switch."
    
    net.addLink(switch_list[0], host_list[0])
    net.addLink(switch_list[5], host_list[2])
    net.addLink(switch_list[6], host_list[1])

    print "*** Creating intra links of switch2switch."
    for i in xrange(0, sw_num-1):
        net.addLink(switch_list[i], switch_list[i+1])




    print "*** Starting network"
    net.build()
    for c in controller_list:
        c.start()

    _No = 0
    for i in xrange(0, 3):
        switch_list[i].start([controller_list[_No]])

    _No = 1
    for j in xrange(3, 7):
         switch_list[j].start([controller_list[_No]])

        #print "*** Testing network"
        #net.pingAll()

    print "*** Running CLI"
    CLI(net)

    print "*** Stopping network"
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')  # for CLI output
    multiControllerNet(con_num=2, sw_num=7, host_num=3)
