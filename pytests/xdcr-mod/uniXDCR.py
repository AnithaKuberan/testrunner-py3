from couchbase.documentgenerator import BlobGenerator, DocumentGenerator
from membase.helper.rebalance_helper import RebalanceHelper
from xdcrbasetests import XDCRReplicationBaseTest
from remote.remote_util import RemoteMachineShellConnection
from memcached.helper.data_helper import MemcachedClientHelper
from random import randrange

#Assumption that at least 2 nodes on every cluster

import time

class unidirectional(XDCRReplicationBaseTest):
    def setUp(self):
        super(unidirectional, self).setUp()

        self.gen_create = BlobGenerator('loadOne', 'loadOne', self._value_size, end=self._num_items)
        self.gen_delete = BlobGenerator('loadOne', 'loadOne-', self._value_size,
            start=int((self._num_items) * (float)(100 - self._percent_delete) / 100), end=self._num_items)
        self.gen_update = BlobGenerator('loadOne', 'loadOne-', self._value_size, start=0,
            end=int(self._num_items * (float)(self._percent_update) / 100))

    def tearDown(self):
        super(unidirectional, self).tearDown()

        """Verify the stats at the destination cluster
        1. Data Validity check - using kvstore-node key-value check
        2. Item count check on source versus destination
        3. For deleted items, check the CAS/SeqNo/Expiry/Flags for same key on source/destination
        * Make sure to call expiry_pager function to flush out temp items(deleted/expired items)"""

    def verify_xdcr_stats(self, src_nodes, dest_nodes):
        if self._num_items in (1000, 10000):
            self._timeout = 180
        elif self._num_items in (10000, 50000):
            self._timeout = 300
        elif self._num_items in (50000, 100000):
            self._timeout = 500
        elif self._num_items >=100000:
            self._timeout = 600

        if self._failover is not None:
            self._timeout*= 2

        self._log.info("Verify xdcr replication stats at Destination Cluster : {0}".format(dest_nodes[0].ip))
        self._log.info("Waiting for for {0} seconds, for replication to catchup ...".format(self._timeout))
        time.sleep(self._timeout)

        self._wait_for_stats_all_buckets(dest_nodes)
        self._expiry_pager(src_nodes[0])
        self._expiry_pager(dest_nodes[0])
        self._verify_stats_all_buckets(dest_nodes)
        self._verify_all_buckets(dest_nodes[0])

        if self._doc_ops is not None:
            if "update" in self._doc_ops:
                self._verify_revIds(src_nodes[0], dest_nodes[0], "update")

            if "delete" in self._doc_ops:
                self._verify_revIds(src_nodes[0], dest_nodes[0], "delete")

    """Testing Unidirectional load( Loading only at source) Verifying whether XDCR replication is successful on
    subsequent destination clusters.Create/Update/Delete operations are performed based on doc-ops specified by the user. """
    def load_with_ops(self):
        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        """Setting up creates/updates/deletes at source nodes"""

        if self._doc_ops is not None:
            if "create" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_create, "create", self._expires)
            if "update" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_update, "update", self._expires)
            if "delete" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_delete, "delete", 0)
            self._wait_for_stats_all_buckets(src_nodes)

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        dest_key_index = 1
        for key in ord_keys[1:]:
            if dest_key_index == ord_keys_len:
                break
            dest_key = ord_keys[dest_key_index]
            dest_nodes = self._clusters_dic[dest_key]

            self.verify_xdcr_stats(src_nodes, dest_nodes)
            dest_key_index += 1

    """Testing Unidirectional load( Loading only at source) Verifying whether XDCR replication is successful on
    subsequent destination clusters. Create/Update/Delete are performed in parallel- doc-ops specified by the user. """

    def load_with_async_ops(self):
        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        self._load_all_buckets(src_master, self.gen_create, "create", 0)
        tasks = []
        """Setting up creates/updates/deletes at source nodes"""
        if self._doc_ops is not None:
            # allows multiple of them but one by one
            if "update" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_update, "update", self._expires))
            if "create" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_create, "create", self._expires))
            if "delete" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_delete, "delete", 0))
        time.sleep(5)
        for task in tasks:
            task.result()

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        self._wait_for_stats_all_buckets(src_nodes)

        dest_key_index = 1
        for key in ord_keys[1:]:
            if dest_key_index == ord_keys_len:
                break
            dest_key = ord_keys[dest_key_index]
            dest_nodes = self._clusters_dic[dest_key]

            self.verify_xdcr_stats(src_nodes, dest_nodes)

            dest_key_index += 1

    """Testing Unidirectional load( Loading only at source). Failover node at Source/Destination while
    Create/Update/Delete are performed after based on doc-ops specified by the user.
    Verifying whether XDCR replication is successful on subsequent destination clusters. """


    def load_with_ops_with_warmup(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        time.sleep(30)
        #warmup
        warmupnodes = []
        dest_warm_flag = 0
        if self._warmup == "source":
            warmupnode = src_nodes
        elif self._warmup == "destination":
            warmupnode = dest_nodes
        elif self._warmup == "all":
            warmupnode = src_nodes
            dest_warm_flag = 1
        warmupnodes.append(warmupnode[randrange(1, len(warmupnode))])
        self.do_a_warm_up(warmupnodes[0])
        if dest_warm_flag == 1:
            warmupnodes.append(dest_nodes[randrange(1, len(dest_nodes))])
            self.do_a_warm_up(warmupnodes[1])
        time.sleep(30)

        #Setting up doc-ops at source nodes
        if (self._doc_ops is not None):
            # allows multiple of them but one by one
            if "create" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_create, "create", self._expires)
            if "update" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_update, "update", self._expires)
            if "delete" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_delete, "delete", 0)
            self._wait_for_stats_all_buckets(src_nodes)

        time.sleep(60)

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        # Checking replication at destination clusters
        dest_key_index = 1
        for key in ord_keys[1:]:
            if dest_key_index == ord_keys_len:
                break
            dest_key = ord_keys[dest_key_index]
            dest_nodes = self._clusters_dic[dest_key]

            for server in warmupnodes:
                mc = MemcachedClientHelper.direct_client(server, "default")
                start = time.time()
                while time.time() - start < 150:
                    if mc.stats()["ep_warmup_thread"] == "complete":
                        self._log.info("Warmed up: %s items " % (mc.stats()["curr_items_tot"]))
                        time.sleep(10)
                        break
                    elif mc.stats()["ep_warmup_thread"] == "running":
                        self._log.info(
                            "Still warming up .. curr_items_tot : %s" % (mc.stats()["curr_items_tot"]))
                        continue
                    else:
                        self._log.info("Value of ep_warmup_thread does not exist, exiting from this server")
                        break
                if mc.stats()["ep_warmup_thread"] == "running":
                    self._log.info("ERROR: ep_warmup_thread's status not complete")
                mc.close()

            self.verify_xdcr_stats(src_nodes, dest_nodes)
            dest_key_index += 1

    def load_with_ops_with_warmup_master(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        time.sleep(30)
        #warmup
        warmupnodes = []
        dest_warm_flag = 0
        if self._warmup == "source":
            warmupnodes.append(src_master)
        elif self._warmup == "destination":
            warmupnodes.append(dest_master)
        elif self._warmup == "all":
            warmupnodes.append(src_master)
            dest_warm_flag = 1
        self.do_a_warm_up(warmupnodes[0])
        if dest_warm_flag == 1:
            warmupnodes.append(dest_master)
            self.do_a_warm_up(warmupnodes[1])
        time.sleep(30)

        #Setting up doc-ops at source nodes
        if (self._doc_ops is not None):
            # allows multiple of them but one by one
            if "create" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_create, "create", 0)
            if "update" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_update, "update", self._expires)
            if "delete" in self._doc_ops:
                self._load_all_buckets(src_master, self.gen_delete, "delete", 0)
            self._wait_for_stats_all_buckets(src_nodes)

        time.sleep(60)

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        # Checking replication at destination clusters
        dest_key_index = 1
        for key in ord_keys[1:]:
            if dest_key_index == ord_keys_len:
                break
            dest_key = ord_keys[dest_key_index]
            dest_nodes = self._clusters_dic[dest_key]

            for server in warmupnodes:
                mc = MemcachedClientHelper.direct_client(server, "default")
                start = time.time()
                while time.time() - start < 150:
                    if mc.stats()["ep_warmup_thread"] == "complete":
                        self._log.info("Warmed up: %s items " % (mc.stats()["curr_items_tot"]))
                        time.sleep(10)
                        break
                    elif mc.stats()["ep_warmup_thread"] == "running":
                        self._log.info(
                            "Still warming up .. curr_items_tot : %s" % (mc.stats()["curr_items_tot"]))
                        continue
                    else:
                        self._log.info("Value of ep_warmup_thread does not exist, exiting from this server")
                        break
                if mc.stats()["ep_warmup_thread"] == "running":
                    self._log.info("ERROR: ep_warmup_thread's status not complete")
                mc.close()

            self.verify_xdcr_stats(src_nodes, dest_nodes)
            dest_key_index += 1

    def load_with_async_ops_with_warmup(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        self._load_all_buckets(src_master, self.gen_create, "create", 0)

        time.sleep(30)
        #warmup
        warmupnodes = []
        dest_warm_flag = 0
        if self._warmup == "source":
            warmupnode = src_nodes
        elif self._warmup == "destination":
            warmupnode = dest_nodes
        elif self._warmup == "all":
            warmupnode = src_nodes
            dest_warm_flag = 1
        warmupnodes.append(warmupnode[randrange(1, len(warmupnode))])
        self.do_a_warm_up(warmupnodes[0])
        if dest_warm_flag == 1:
            warmupnodes.append(dest_nodes[randrange(1, len(dest_nodes))])
            self.do_a_warm_up(warmupnodes[1])
        time.sleep(30)

        tasks = []
        #Setting up doc-ops at source nodes
        if (self._doc_ops is not None):
            # allows multiple of them but one by one
            if "update" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_update, "update", self._expires))
            if "create" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_create, "create", self._expires))
            if "delete" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_delete, "delete", 0))
            time.sleep(60)
        for task in tasks:
            task.result()

        time.sleep(30)

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        self._wait_for_stats_all_buckets(src_nodes)

        # Checking replication at destination clusters
        dest_key_index = 1
        for key in ord_keys[1:]:
            if dest_key_index == ord_keys_len:
                break
            dest_key = ord_keys[dest_key_index]
            dest_nodes = self._clusters_dic[dest_key]

            for server in warmupnodes:
                mc = MemcachedClientHelper.direct_client(server, "default")
                start = time.time()
                while time.time() - start < 150:
                    if mc.stats()["ep_warmup_thread"] == "complete":
                        self._log.info("Warmed up: %s items " % (mc.stats()["curr_items_tot"]))
                        time.sleep(10)
                        break
                    elif mc.stats()["ep_warmup_thread"] == "running":
                        self._log.info(
                            "Still warming up .. curr_items_tot : %s" % (mc.stats()["curr_items_tot"]))
                        continue
                    else:
                        self._log.info("Value of ep_warmup_thread does not exist, exiting from this server")
                        break
                if mc.stats()["ep_warmup_thread"] == "running":
                    self._log.info("ERROR: ep_warmup_thread's status not complete")
                mc.close()

            self.verify_xdcr_stats(src_nodes, dest_nodes)
            dest_key_index += 1

    def load_with_async_ops_with_warmup_master(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        dest_nodes = self._clusters_dic[1]
        src_master = src_nodes[0]
        dest_master = dest_nodes[0]

        self._load_all_buckets(src_master, self.gen_create, "create", 0)

        time.sleep(30)
        #warmup
        warmupnodes = []
        dest_warm_flag = 0
        if self._warmup == "source":
            warmupnodes.append(src_master)
        elif self._warmup == "destination":
            warmupnodes.append(dest_master)
        elif self._warmup == "all":
            warmupnodes.append(src_master)
            dest_warm_flag = 1
        self.do_a_warm_up(warmupnodes[0])
        if dest_warm_flag == 1:
            warmupnodes.append(dest_master)
            self.do_a_warm_up(warmupnodes[1])
        time.sleep(30)

        tasks = []
        #Setting up doc-ops at source nodes
        if (self._doc_ops is not None):
            # allows multiple of them but one by one
            if "update" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_update, "update", self._expires))
            if "create" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_create, "create", self._expires))
            if "delete" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_delete, "delete", 0))
            time.sleep(60)
        for task in tasks:
            task.result()

        time.sleep(30)

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        self._wait_for_stats_all_buckets(src_nodes)

        # Checking replication at destination clusters
        dest_key_index = 1
        for key in ord_keys[1:]:
            if dest_key_index == ord_keys_len:
                break
            dest_key = ord_keys[dest_key_index]
            dest_nodes = self._clusters_dic[dest_key]

            for server in warmupnodes:
                mc = MemcachedClientHelper.direct_client(server, "default")
                start = time.time()
                while time.time() - start < 150:
                    if mc.stats()["ep_warmup_thread"] == "complete":
                        self._log.info("Warmed up: %s items " % (mc.stats()["curr_items_tot"]))
                        time.sleep(10)
                        break
                    elif mc.stats()["ep_warmup_thread"] == "running":
                        self._log.info(
                            "Still warming up .. curr_items_tot : %s" % (mc.stats()["curr_items_tot"]))
                        continue
                    else:
                        self._log.info("Value of ep_warmup_thread does not exist, exiting from this server")
                        break
                if mc.stats()["ep_warmup_thread"] == "running":
                    self._log.info("ERROR: ep_warmup_thread's status not complete")
                mc.close()

            self.verify_xdcr_stats(src_nodes, dest_nodes)
            dest_key_index += 1

    def load_with_failover(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        self._load_all_buckets(src_master, self.gen_create, "create", self._expires)

        time.sleep(60)

        if "source" in self._failover:
            i = randrange(1, len(src_nodes))
            self._log.info(" Failing over Source Non-Master Node {0}".format(src_nodes[i].ip))
            self._cluster_helper.failover(src_nodes, [src_nodes[i]])
            self._log.info(" Rebalance out Source Non-Master Node {0}".format(src_nodes[i].ip))
            self._cluster_helper.rebalance(src_nodes, [], [src_nodes[i]])
            src_nodes.pop(i)
        if "destination" in self._failover:
            i = randrange(1, len(dest_nodes))
            self._log.info(" Failing over Destination Non-Master Node {0}".format(dest_nodes[i].ip))
            self._cluster_helper.failover(dest_nodes, [dest_nodes[i]])
            self._log.info(" Rebalance out Destination Non-Master Node {0}".format(dest_nodes[i].ip))
            self._cluster_helper.rebalance(dest_nodes, [], [dest_nodes[i]])
            dest_nodes.pop(i)

        time.sleep(5)
        tasks = []
        """Setting up creates/updates/deletes at source nodes"""
        if self._doc_ops is not None:
            if "update" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_update, "update", self._expires))
            if "delete" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_delete, "delete", self._expires))
        time.sleep(15)
        for task in tasks:
            task.result()

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        self.verify_xdcr_stats(src_nodes, dest_nodes)

    """Testing Unidirectional load( Loading only at source). Failover node at Source/Destination while
    Create/Update/Delete are performed in parallel based on doc-ops specified by the user.
    Verifying whether XDCR replication is successful on subsequent destination clusters. """

    def load_with_failover_master(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        self._load_all_buckets(src_master, self.gen_create, "create", self._expires)

        time.sleep(60)

        if "source" in self._failover:
            i = randrange(1, len(src_nodes))
            self._log.info(" Failing over Source Master Node {0}".format(src_master.ip))
            self._cluster_helper.failover(src_nodes, [src_master])
            self._log.info(" Rebalance out Source Master Node {0}".format(src_master.ip))
            self._cluster_helper.rebalance(src_nodes, [], [src_master])
            src_nodes.remove(src_master)
            src_master=src_nodes[0]

        if "destination" in self._failover:
            self._log.info(" Failing over Destination Master Node {0}".format(dest_master.ip))
            self._cluster_helper.failover(dest_nodes, [dest_master])
            self._log.info(" Rebalance out Destination Master Node {0}".format(dest_master.ip))
            self._cluster_helper.rebalance(dest_nodes, [], [dest_master])
            dest_nodes.remove(dest_master)
            dest_master=dest_nodes[0]

        time.sleep(10)
        tasks = []
        """Setting up creates/updates/deletes at source nodes"""
        if self._doc_ops is not None:
            if "update" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_update, "update", self._expires))
            if "delete" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_delete, "delete", self._expires))
        time.sleep(15)
        for task in tasks:
            task.result()

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        self.verify_xdcr_stats(src_nodes, dest_nodes)

    """Testing Unidirectional load( Loading only at source). Failover node at Source/Destination while
    Create/Update/Delete are performed in parallel based on doc-ops specified by the user.
    Verifying whether XDCR replication is successful on subsequent destination clusters. """

    def load_with_async_failover(self):

        ord_keys = self._clusters_keys_olst
        ord_keys_len = len(ord_keys)

        src_nodes = self._clusters_dic[0]
        src_master = src_nodes[0]

        dest_nodes = self._clusters_dic[1]
        dest_master = dest_nodes[0]

        self._load_all_buckets(src_master, self.gen_create, "create", self._expires)

        time.sleep(60)

        tasks = []
        """Setting up failover while creates/updates/deletes at source nodes"""
        if self._doc_ops is not None:
            if "source" in self._failover:
                i = randrange(1, len(src_nodes))
                tasks.extend(self._async_failover(src_nodes, [src_nodes[i]]))
                self._log.info(" Failing over Source Node {0}".format(src_nodes[i].ip))
            if "destination" in self._failover:
                i = randrange(1, len(dest_nodes))
                tasks.extend(self._async_failover(dest_nodes, [dest_nodes[i]]))
                self._log.info(" Failing over Destination Node {0}".format(dest_nodes[i].ip))
            if "update" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_update, "update", self._expires))
            if "delete" in self._doc_ops:
                tasks.extend(self._async_load_all_buckets(src_master, self.gen_delete, "delete", self._expires))
        time.sleep(15)
        for task in tasks:
            task.result()

        src_buckets = self._get_cluster_buckets(src_master)
        dest_buckets = self._get_cluster_buckets(dest_master)
        for src_bucket in src_buckets:
            for dest_bucket in dest_buckets:
                if src_bucket.name==dest_bucket.name:
                    dest_bucket.kvs = src_bucket.kvs

        if "source" in self._failover:
            self._log.info(" Rebalance out Source Node {0}".format(src_nodes[i].ip))
            self._cluster_helper.rebalance(src_nodes, [], [src_nodes[i]])
            src_nodes.pop(i)

        if "destination" in self._failover:
            self._log.info(" Rebalance out Destination Node {0}".format(dest_nodes[i].ip))
            self._cluster_helper.rebalance(dest_nodes, [], [dest_nodes[i]])
            dest_nodes.pop(i)

            self.verify_xdcr_stats(src_nodes, dest_nodes)


            #ToDO - Failover and ADD BACK NODE