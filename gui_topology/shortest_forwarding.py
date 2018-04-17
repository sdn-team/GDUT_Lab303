# Copyright (C) 2016 Li Cheng at Beijing University of Posts
# and Telecommunications. www.muzixing.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# conding=utf-8
import logging
import json
import time
import struct
import networkx as nx
from operator import attrgetter
from ryu import cfg
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib import hub
from ryu.app.wsgi import ControllerBase, WSGIApplication, Response

from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link

import network_awareness
import network_monitor
import network_delay_detector

CONF = cfg.CONF

PATH_NO = CONF.k_paths
COOKIE_SHIFT = 100  # the 1-st path's 101 and 2-rd is 102 and so on
IDLE_TIMEOUT = 5
HARD_TIMEOUT = 5

REST_SRCIP = 'nw_src'
REST_DSTIP = 'nw_dst'

PRIORITY_FORWARD = 3

PERIOD = 0.1


class ShortestForwarding(app_manager.RyuApp):
    """
        ShortestForwarding is a Ryu app for forwarding packets in shortest
        path.
        The shortest path computation is done by module network awareness,
        network monitor and network delay detector.
    """

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        "network_awareness": network_awareness.NetworkAwareness,
        "network_monitor": network_monitor.NetworkMonitor,
        "network_delay_detector": network_delay_detector.NetworkDelayDetector,
        'wsgi': WSGIApplication}

    WEIGHT_MODEL = {'hop': 'weight', 'delay': "delay", "bw": "bw"}

    def __init__(self, *args, **kwargs):
        super(ShortestForwarding, self).__init__(*args, **kwargs)
        self.name = 'shortest_forwarding'
        self.awareness = kwargs["network_awareness"]
        self.monitor = kwargs["network_monitor"]
        self.delay_detector = kwargs["network_delay_detector"]
        self.datapaths = {}
        self.weight = self.WEIGHT_MODEL[CONF.weight]

        """modified here."""
        self.path_no = PATH_NO
        self.path_id = 0        # current path_id
        self.cookie = 0
        self.paths = []

        PathCalcu.set_logger(self.logger)
        self.data = {}
        self.data['shortest_fwd'] = self

        wsgi = kwargs['wsgi']
        mapper = wsgi.mapper
        wsgi.registory['PathCalcu'] = self.data

        path = '/routing/path'
        mapper.connect('routing_path', path, controller=PathCalcu,
                       # requirements=requirements,
                       action='get_path',
                       conditions=dict(method=['POST']))

        # Start a green thread to delete flow entries.
        # self.del_thread = hub.spawn(self._del)

        # time used to sleep when the controller receives
        # too many packet_in messages.
        self.time = time.clock()

    def _del(self):
        i = 0
        while True:
            # self.logger.info("_del is called.")
            if i == 5:
                """Modified here."""
                if len(self.paths):
                    path_info = self.paths[0]
                    self.logger.info("path_info is [%s]" % path_info)
                    self.del_shortest_forwarding(path_info)
                    self.logger.info("Delete flow entries.")
                    del self.paths[0]
                i = 0
            hub.sleep(2)
            i = i + 1

    def set_weight_mode(self, weight):
        """
            set weight mode of path calculating.
        """
        self.weight = weight
        if self.weight == self.WEIGHT_MODEL['hop']:
            self.awareness.get_shortest_paths(weight=self.weight)
        return True

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """
            Collect datapath information.
        """
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def add_flow(self, dp, p, match, actions, idle_timeout=0, hard_timeout=0,
                 cookie=0):
        """
            Send a flow entry to datapath.
        """
        ofproto = dp.ofproto
        parser = dp.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=p,
                                idle_timeout=idle_timeout,
                                hard_timeout=hard_timeout,
                                match=match, instructions=inst,
                                cookie=cookie)
        dp.send_msg(mod)

    def del_flow(self, dp, cookie, match={}):
        """Delete a flow entry to datapath."""
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        cmd = dp.ofproto.OFPFC_DELETE
        mod = parser.OFPFlowMod(datapath=dp, cookie=cookie,
                                out_port=ofp.OFPP_ANY,
                                out_group=ofp.OFPG_ANY,
                                flags=ofp.OFPFF_SEND_FLOW_REM,
                                command=cmd, match=match)

        # mod = parser.OFPFlowMod(datapath=dp, cookie=cookie,
        #                         command=cmd, priority=1, instructions=[])
        # self.logger.info("del_flow is called.")
        # self.logger.info("datapath = [%s], cookie = [%d]"
        #                  % (dp, cookie))
        dp.send_msg(mod)

    def send_flow_mod(self, datapath, flow_info, src_port, dst_port,
                      priority=1, cookie=0):
        """
            Build flow entry, and send it to datapath.
        """
        parser = datapath.ofproto_parser
        actions = []
        actions.append(parser.OFPActionOutput(dst_port))

        match = parser.OFPMatch(
            in_port=src_port, eth_type=flow_info[0],
            ipv4_src=flow_info[1], ipv4_dst=flow_info[2])

        self.add_flow(datapath, priority, match, actions,
                      idle_timeout=IDLE_TIMEOUT, hard_timeout=HARD_TIMEOUT,
                      cookie=cookie)

    def del_flow_mod(self, datapath, flow_info, src_port, dst_port, cookie=0):
        """
            Build flow entry, and send it to datapath.
        """
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(
            in_port=src_port, eth_type=flow_info[0],
            ipv4_src=flow_info[1], ipv4_dst=flow_info[2])

        self.del_flow(datapath, cookie, match=match)

    def _build_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
        """
            Build packet out object.
        """
        actions = []
        if dst_port:
            actions.append(datapath.ofproto_parser.OFPActionOutput(dst_port))

        msg_data = None
        if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
            if data is None:
                return None
            msg_data = data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath, buffer_id=buffer_id,
            data=msg_data, in_port=src_port, actions=actions)
        return out

    def send_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
        """
            Send packet out packet to assigned datapath.
        """
        out = self._build_packet_out(datapath, buffer_id,
                                     src_port, dst_port, data)
        if out:
            datapath.send_msg(out)

    def get_port(self, dst_ip, access_table):
        """
            Get access port if dst host.
            access_table: {(sw,port) :(ip, mac)}
        """
        if access_table:
            if isinstance(access_table.values()[0], tuple):
                for key in access_table.keys():
                    if dst_ip == access_table[key][0]:
                        dst_port = key[1]
                        return dst_port
        return None

    """Modified here."""
    def _get_cookie(self):
        cookie = self.path_id
        if cookie == 0:
            cookie = self.path_no
        return cookie

    def get_port_pair_from_link(self, link_to_port, src_dpid, dst_dpid):
        """
            Get port pair of link, so that controller can install flow entry.
        """
        if (src_dpid, dst_dpid) in link_to_port:
            return link_to_port[(src_dpid, dst_dpid)]
        else:
            self.logger.info("dpid:%s->dpid:%s is not in links" % (
                             src_dpid, dst_dpid))
            return None

    def flood(self, msg):
        """
            Flood ARP packet to the access port
            which has no record of host.
        """
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        for dpid in self.awareness.access_ports:
            for port in self.awareness.access_ports[dpid]:
                if (dpid, port) not in self.awareness.access_table.keys():
                    datapath = self.datapaths[dpid]
                    out = self._build_packet_out(
                        datapath, ofproto.OFP_NO_BUFFER,
                        ofproto.OFPP_CONTROLLER, port, msg.data)
                    datapath.send_msg(out)
        self.logger.debug("Flooding msg")

    def arp_forwarding(self, msg, src_ip, dst_ip):
        """ Send ARP packet to the destination host,
            if the dst host record is existed,
            else, flow it to the unknow access port.
        """
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        result = self.awareness.get_host_location(dst_ip)
        if result:  # host record in access table.
            datapath_dst, out_port = result[0], result[1]
            datapath = self.datapaths[datapath_dst]
            out = self._build_packet_out(datapath, ofproto.OFP_NO_BUFFER,
                                         ofproto.OFPP_CONTROLLER,
                                         out_port, msg.data)
            datapath.send_msg(out)
            self.logger.debug("Reply ARP to knew host")
        else:
            self.flood(msg)

    def _add_path_id(self):
        self.path_id += 1
        if self.path_id == self.path_no:
            self.path_id = 0
        return

    def get_path(self, src, dst, weight):
        """
            Get shortest path from network awareness module.
        """
        shortest_paths = self.awareness.shortest_paths
        graph = self.awareness.graph

        """Modified here."""
        self._add_path_id()
        path_id = self.path_id

        print("self.path_id is [%d]" % self.path_id)

        if weight == self.WEIGHT_MODEL['hop']:
            return shortest_paths.get(src).get(dst)[path_id]
        elif weight == self.WEIGHT_MODEL['delay']:
            # If paths existed, return it, else calculate it and save it.
            try:
                paths = shortest_paths.get(src).get(dst)

                """Modified here."""
                self.logger.info("path_id is [%d]" % path_id)
                return paths[path_id]
            except:
                paths = self.awareness.k_shortest_paths(graph, src, dst,
                                                        weight=weight)

                shortest_paths.setdefault(src, {})
                shortest_paths[src].setdefault(dst, paths)
                return paths[0]
        elif weight == self.WEIGHT_MODEL['bw']:
            # Because all paths will be calculate
            # when call self.monitor.get_best_path_by_bw
            # So we just need to call it once in a period,
            # and then, we can get path directly.
            try:
                # if path is existed, return it.
                path = self.monitor.best_paths.get(src).get(dst)
                return path
            except:
                # else, calculate it, and return.
                result = self.monitor.get_best_path_by_bw(graph,
                                                          shortest_paths)
                paths = result[1]
                best_path = paths.get(src).get(dst)
                return best_path

    def get_sw(self, dpid, in_port, src, dst):
        """
            Get pair of source and destination switches.
        """
        src_sw = dpid
        dst_sw = None

        src_location = self.awareness.get_host_location(src)
        if in_port in self.awareness.access_ports[dpid]:
            if (dpid,  in_port) == src_location:
                src_sw = src_location[0]
            else:
                return None

        dst_location = self.awareness.get_host_location(dst)
        if dst_location:
            dst_sw = dst_location[0]

        return src_sw, dst_sw

    def install_flow(self, datapaths, link_to_port, access_table, path,
                     flow_info, buffer_id, cookie=0, data=None):
        """
            Install flow entires for roundtrip: go and back.
            @parameter: path=[dpid1, dpid2...]
                        flow_info=(eth_type, src_ip, dst_ip, in_port)
        """
        if path is None or len(path) == 0:
            self.logger.info("Path error!")
            return
        in_port = flow_info[3]
        first_dp = datapaths[path[0]]
        out_port = first_dp.ofproto.OFPP_LOCAL
        back_info = (flow_info[0], flow_info[2], flow_info[1])
        p = PRIORITY_FORWARD

        # inter_link
        if len(path) > 2:
            # install flows into mid-switches
            for i in xrange(1, len(path)-1):
                port = self.get_port_pair_from_link(link_to_port,
                                                    path[i-1], path[i])
                port_next = self.get_port_pair_from_link(link_to_port,
                                                         path[i], path[i+1])
                if port and port_next:
                    src_port, dst_port = port[1], port_next[0]
                    datapath = datapaths[path[i]]
                    self.send_flow_mod(datapath, flow_info, src_port, dst_port,
                                       priority=p, cookie=cookie)
                    self.send_flow_mod(datapath, back_info, dst_port, src_port,
                                       priority=p, cookie=cookie)
                    self.logger.debug("inter_link flow install")
        if len(path) > 1:
            # the last flow entry: to dst host
            port_pair = self.get_port_pair_from_link(link_to_port,
                                                     path[-2], path[-1])
            if port_pair is None:
                self.logger.info("Port is not found")
                return
            src_port = port_pair[1]

            dst_port = self.get_port(flow_info[2], access_table)
            if dst_port is None:
                self.logger.info("Last port is not found.")
                return

            last_dp = datapaths[path[-1]]
            self.send_flow_mod(last_dp, flow_info, src_port, dst_port,
                               priority=p, cookie=cookie)
            self.send_flow_mod(last_dp, back_info, dst_port, src_port,
                               priority=p, cookie=cookie)

            # the first flow entry
            port_pair = self.get_port_pair_from_link(link_to_port,
                                                     path[0], path[1])
            if port_pair is None:
                self.logger.info("Port not found in first hop.")
                return
            out_port = port_pair[0]
            self.send_flow_mod(first_dp, flow_info, in_port, out_port,
                               priority=p, cookie=cookie)
            self.send_flow_mod(first_dp, back_info, out_port, in_port,
                               priority=p, cookie=cookie)
            self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)

        # src and dst on the same datapath
        else:
            out_port = self.get_port(flow_info[2], access_table)
            if out_port is None:
                self.logger.info("Out_port is None in same dp")
                return
            self.send_flow_mod(first_dp, flow_info, in_port, out_port,
                               priority=p, cookie=cookie)
            self.send_flow_mod(first_dp, back_info, out_port, in_port,
                               priority=p, cookie=cookie)
            self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)

    """Modified here."""
    def uninstall_flow(self, datapaths, link_to_port, access_table, path,
                       flow_info, cookie=0):
        """
            Uninstall flow entries for round trip: go and back.
            @parameter: path=[dpid1, dpid2...]
                        flow_info=(eth_type, src_ip, dst_ip, in_port)
        """
        self.logger.info("uninstall_flow is called.")
        if path is None or len(path) == 0:
            self.logger.info("Path error!")
            return
        in_port = flow_info[3]
        first_dp = datapaths[path[0]]
        out_port = first_dp.ofproto.OFPP_LOCAL
        back_info = (flow_info[0], flow_info[2], flow_info[1])

        # inter_link
        if len(path) > 2:
            # uninstall flows into mid-switches
            for i in xrange(1, len(path) - 1):
                port = self.get_port_pair_from_link(link_to_port,
                                                    path[i - 1], path[i])
                port_next = self.get_port_pair_from_link(link_to_port,
                                                         path[i], path[i + 1])
                if port and port_next:
                    src_port, dst_port = port[1], port_next[0]
                    datapath = datapaths[path[i]]
                    self.del_flow_mod(datapath, flow_info, src_port, dst_port,
                                      cookie=cookie)
                    self.del_flow_mod(datapath, back_info, dst_port, src_port,
                                      cookie=cookie)
                    self.logger.info("inter_link flow uninstall")
        if len(path) > 1:
            # the last flow entry: to dst host
            port_pair = self.get_port_pair_from_link(link_to_port,
                                                     path[-2], path[-1])
            if port_pair is None:
                self.logger.info("Port is not found")
                return
            src_port = port_pair[1]

            dst_port = self.get_port(flow_info[2], access_table)
            if dst_port is None:
                self.logger.info("Last port is not found.")
                return

            last_dp = datapaths[path[-1]]
            self.del_flow_mod(last_dp, flow_info, src_port, dst_port,
                              cookie=cookie)
            self.del_flow_mod(last_dp, back_info, dst_port, src_port,
                              cookie=cookie)

            # the first flow entry
            port_pair = self.get_port_pair_from_link(link_to_port,
                                                     path[0], path[1])
            if port_pair is None:
                self.logger.info("Port not found in first hop.")
                return
            out_port = port_pair[0]
            self.del_flow_mod(first_dp, flow_info, in_port, out_port,
                              cookie=cookie)
            self.del_flow_mod(first_dp, back_info, out_port, in_port,
                              cookie=cookie)

        # src and dst on the same datapath
        else:
            out_port = self.get_port(flow_info[2], access_table)
            if out_port is None:
                self.logger.info("Out_port is None in same dp")
                return
            self.del_flow_mod(first_dp, flow_info, in_port, out_port,
                              cookie=cookie)
            self.del_flow_mod(first_dp, back_info, out_port, in_port,
                              cookie=cookie)

    def shortest_forwarding(self, msg, eth_type, ip_src, ip_dst):
        """
            To calculate shortest forwarding path and install them into datapaths.
        """
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)
        if result:
            src_sw, dst_sw = result[0], result[1]
            if dst_sw:

                if time.clock() - self.time < PERIOD:
                    self.logger.info("Too many messages to handle!")
                    return
                else:
                    self.logger.info("I'm OK.")
                    self.time = time.clock()

                # Path has already calculated, just get it.
                path = self.get_path(src_sw, dst_sw, weight=self.weight)
                self.logger.info("[PATH]%s<-->%s: %s" % (ip_src, ip_dst, path))
                flow_info = (eth_type, ip_src, ip_dst, in_port)

                """Modified here."""
                cookie = self._get_cookie()
                self.paths.append(PathInfo(path, flow_info, cookie))

                # install flow entries to datapath along side the path.
                self.install_flow(self.datapaths,
                                  self.awareness.link_to_port,
                                  self.awareness.access_table, path,
                                  flow_info, msg.buffer_id,
                                  cookie=cookie, data=msg.data)
        return

    def del_shortest_forwarding(self, path_info):
        """
            To calculate shortest forwarding path and install them into datapaths.
        """
        if path_info:
            path = path_info.path
            flow_info = path_info.flow_info
            cookie = path_info.cookie
            self.uninstall_flow(self.datapaths,
                                self.awareness.link_to_port,
                                self.awareness.access_table, path,
                                flow_info, cookie=cookie)
        print("del_shortest_forwarding is called.")
        return

    def cal_sw(self, src, dst):
        """
            Get pair of source and destination switches.
        """
        src_sw = None
        dst_sw = None

        src_location = self.awareness.get_host_location(src)
        if src_location:
            src_sw = src_location[0]

        dst_location = self.awareness.get_host_location(dst)
        if dst_location:
            dst_sw = dst_location[0]

        return src_sw, dst_sw

    def cal_path(self, src_ip, dst_ip):
        result = self.cal_sw(src_ip, dst_ip)
        src = result[0]
        dst = result[1]
        path_id = self.path_id
        shortest_paths = self.awareness.shortest_paths

        return shortest_paths.get(src).get(dst)[path_id]

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        """
            In packet_in handler, we need to learn access_table by ARP.
            Therefore, the first packet from UNKOWN host MUST be ARP.
        """
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp.arp)
        ip_pkt = pkt.get_protocol(ipv4.ipv4)

        if isinstance(arp_pkt, arp.arp):
            self.logger.debug("ARP processing")
            self.arp_forwarding(msg, arp_pkt.src_ip, arp_pkt.dst_ip)

        if isinstance(ip_pkt, ipv4.ipv4):
            self.logger.debug("IPV4 processing")
            if len(pkt.get_protocols(ethernet.ethernet)):
                eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
                self.shortest_forwarding(msg, eth_type, ip_pkt.src, ip_pkt.dst)


class PathInfo(object):
    def __init__(self, path, flow_info, cookie):
        self.path = path
        self.flow_info = flow_info
        self.cookie = cookie


class PathCalcu(ControllerBase):

    _LOGGER = None

    def __init__(self, req, link, data, **config):
        super(PathCalcu, self).__init__(req, link, data, **config)
        self.shortest_forwarding = data['shortest_fwd']

    @classmethod
    def set_logger(cls, logger):
        cls._LOGGER = logger
        cls._LOGGER.propagate = False
        hdlr = logging.StreamHandler()
        fmt_str = '[PC][%(levelname)s] %(message)s'
        hdlr.setFormatter(logging.Formatter(fmt_str))
        cls._LOGGER.addHandler(hdlr)

    # POST '/routing/path'
    def get_path(self, req, **kwargs):
        return self._get_path(req)

    def _get_path(self, req):
        try:
            rest = req.json if req.body else {}
        except ValueError:
            return Response(status=400)

        try:
            src_ip = rest[REST_SRCIP]
            dst_ip = rest[REST_DSTIP]
            return self._cal_path(src_ip, dst_ip)
        except ValueError:
            return Response(status=400)

    def _cal_path(self, src_ip, dst_ip):
        shortest_fwd = self.shortest_forwarding
        result = shortest_fwd.cal_path(src_ip, dst_ip)
        PathCalcu._LOGGER.info('result is [%s]' % result)

        body = json.dumps(result)
        return Response(content_type='application/json', body=body)
