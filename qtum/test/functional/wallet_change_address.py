#!/usr/bin/env python3
# Copyright (c) 2023 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test wallet change address selection"""

import re

from test_framework.blocktools import COINBASE_MATURITY
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
)


class WalletChangeAddressTest(BitcoinTestFramework):
    def set_test_params(self):
        self.setup_clean_chain = True
        self.num_nodes = 3
        # discardfee is used to make change outputs less likely in the change_pos test
        self.extra_args = [
            [],
            ["-discardfee=1"],
            ["-avoidpartialspends", "-discardfee=1"]
        ]

    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    def assert_change_index(self, node, tx, index):
        change_index = None
        for vout in tx["vout"]:
            info = node.getaddressinfo(vout["scriptPubKey"]["address"])
            if (info["ismine"] and info["ischange"]):
                change_index = int(re.findall(r'\d+', info["hdkeypath"])[-1])
                break
            
        assert_equal(change_index, index)

    def assert_change_pos(self, wallet, tx, pos):
        change_pos = None
        for index, output in enumerate(tx["vout"]):
            info = wallet.getaddressinfo(output["scriptPubKey"]["address"])
            if (info["ismine"] and info["ischange"]):
                change_pos = index
                break
        assert_equal(change_pos, pos)

    def run_test(self):
        self.log.info("Setting up")
        # Mine some coins
        self.generate(self.nodes[0], COINBASE_MATURITY + 1)

        # Get some addresses from the two nodes
        addr1 = [self.nodes[1].getnewaddress() for _ in range(3)]
        addr2 = [self.nodes[2].getnewaddress() for _ in range(3)]
        addrs = addr1 + addr2

        # Send 1 + 0.5 coin to each address
        [self.nodes[0].sendtoaddress(addr, 100.0) for addr in addrs]
        [self.nodes[0].sendtoaddress(addr, 50) for addr in addrs]
        self.generate(self.nodes[0], 1)

        for i in range(20):
            for n in [1, 2]:
                self.log.debug(f"Send transaction from node {n}: expected change index {i}")
                txid = self.nodes[n].sendtoaddress(self.nodes[0].getnewaddress(), 2)
                tx = self.nodes[n].getrawtransaction(txid, True)
                # find the change output and ensure that expected change index was used
                self.assert_change_index(self.nodes[n], tx, i)

        # Start next test with fresh wallets and new coins
        self.nodes[1].createwallet("w1")
        self.nodes[2].createwallet("w2")
        w1 = self.nodes[1].get_wallet_rpc("w1")
        w2 = self.nodes[2].get_wallet_rpc("w2")
        addr1 = w1.getnewaddress()
        addr2 = w2.getnewaddress()
        self.nodes[0].sendtoaddress(addr1, 30)
        self.nodes[0].sendtoaddress(addr1, 15)
        self.nodes[0].sendtoaddress(addr2, 30)
        self.nodes[0].sendtoaddress(addr2, 15)
        self.generate(self.nodes[0], 1)

        sendTo1 = self.nodes[0].getnewaddress()
        sendTo2 = self.nodes[0].getnewaddress()
        sendTo3 = self.nodes[0].getnewaddress()

        # The avoid partial spends wallet will always create a change output
        node = self.nodes[2]
        res = w2.send(outputs=[{sendTo1: 10.0}, {sendTo2: 10.0}, {sendTo3: 9.9999}], options={"change_position": 0})
        tx = node.getrawtransaction(res["txid"], True)
        self.assert_change_pos(w2, tx, 0)

        # The default wallet will internally create a tx without change first,
        # then create a second candidate using APS that requires a change output.
        # Ensure that the user-configured change position is kept
        node = self.nodes[1]
        res = w1.send(outputs=[{sendTo1: 10.0}, {sendTo2: 10.0}, {sendTo3: 9.9999}], options={"change_position": 0})
        tx = node.getrawtransaction(res["txid"], True)
        # If the wallet ignores the user's change_position there is still a 25%
        # that the random change position passes the test
        self.assert_change_pos(w1, tx, 0)

if __name__ == '__main__':
    WalletChangeAddressTest().main()
