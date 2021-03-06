#!/usr/bin/env python
"""
Python based SDK client interface

"""
import crc32
import time
from memcached.helper.old_kvstore import ClientKeyValueStore
from couchbase.bucket import Bucket as CouchbaseBucket
from couchbase.cluster import Cluster, ClusterOptions
from couchbase_core.cluster import PasswordAuthenticator
from couchbase.exceptions import CouchbaseError, BucketNotFoundError, AuthError
from mc_bin_client import MemcachedError
from couchbase_core.n1ql import N1QLQuery, N1QLRequest
import couchbase_core

import json


class SDKClient(object):
    """Python SDK Client Implementation for testrunner - master branch Implementation"""

    def __init__(self, bucket, hosts = ["localhost"] , scheme = "couchbase",
                 ssl_path = None, uhm_options = None, password=None,
                 quiet=True, certpath = None, transcoder = None, ipv6=False, compression=True):
        self.connection_string = \
            self._createString(scheme = scheme, bucket = bucket, hosts = hosts,
                               certpath = certpath, uhm_options = uhm_options, ipv6=ipv6, compression=compression)
        self.bucket = bucket
        self.password = password
        self.quiet = quiet
        self.transcoder = transcoder
        self.default_timeout = 1
        self._createConn()
        couchbase_core.set_json_converters(json.dumps, json.loads)

    def _createString(self, scheme ="couchbase", bucket = None, hosts = ["localhost"], certpath = None,
                      uhm_options = "", ipv6=False, compression=True):
        connection_string = "{0}://{1}".format(scheme, ", ".join(hosts).replace(" ", ""))
        # if bucket != None:
        #     connection_string = "{0}/{1}".format(connection_string, bucket)
        if uhm_options != None:
            connection_string = "{0}?{1}".format(connection_string, uhm_options)
        if ipv6 == True:
            if "?" in connection_string:
                connection_string = "{0},ipv6=allow".format(connection_string)
            else:
                connection_string = "{0}?ipv6=allow".format(connection_string)
        if compression == True:
            if "?" in connection_string:
                connection_string = "{0},compression=on".format(connection_string)
            else:
                connection_string = "{0}?compression=on".format(connection_string)
        else:
            if "?" in connection_string:
                connection_string = "{0},compression=off".format(connection_string)
            else:
                connection_string = "{0}?compression=off".format(connection_string)
        if scheme == "couchbases":
            if "?" in connection_string:
                connection_string = "{0},certpath={1}".format(connection_string, certpath)
            else:
                connection_string = "{0}?certpath={1}".format(connection_string, certpath)
        return connection_string

    def _createConn(self):
        try:
            cluster = Cluster(self.connection_string, ClusterOptions(PasswordAuthenticator(self.bucket, 'password')))
            #cluster.authenticate(PasswordAuthenticator(self.bucket, 'password'))
            self.cb = cluster.bucket(self.bucket)
            self.default_collection = self.cb.default_collection()
        except BucketNotFoundError:
             raise
        except AuthError:
            # Try using default user created by the tests, if any, in case there is no user with bucket name in the
            # cluster.
            try:
                cluster = Cluster(self.connection_string,
                                  ClusterOptions(PasswordAuthenticator("cbadminbucket", 'password')),
                                  bucket_class=CouchbaseBucket)
                self.cb = cluster.bucket(self.bucket)
                self.default_collection = self.cb.default_collection()
            except AuthError:
                raise

    def reconnect(self):
        self.cb.close()
        self._createConn()

    def close(self):
        self.cb._close()

    def counter_in(self, key, path, delta, create_parents=True, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.counter_in(key, path, delta, create_parents= create_parents, cas= cas, ttl= ttl, persist_to= persist_to, replicate_to= replicate_to)
            else:
                return self.default_collection.counter_in(key, path, delta, create_parents= create_parents, cas= cas, ttl= ttl, persist_to= persist_to, replicate_to= replicate_to)
        except CouchbaseError as e:
            raise

    def arrayappend_in(self, key, path, value, create_parents=True, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.arrayappend_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.arrayappend_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def arrayprepend_in(self, key, path, value, create_parents=True, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.arrayprepend_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.arrayprepend_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def arrayaddunique_in(self, key, path, value, create_parents=True, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.addunique_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.addunique_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def arrayinsert_in(self, key, path, value, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.arrayinsert_in(key, path, value, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.arrayinsert_in(key, path, value, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def remove_in(self, key, path,  cas=0, ttl=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.remove_in(key, path, cas = cas, ttl = ttl)
            else:
                self.default_collection.remove_in(key, path, cas = cas, ttl = ttl)
        except CouchbaseError as e:
            raise

    def mutate_in(self, key, collection=None, *specs, **kwargs):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.mutate_in(key, *specs, **kwargs)
            else:
                self.default_collection.mutate_in(key, *specs, **kwargs)
        except CouchbaseError as e:
            raise

    def lookup_in(self, key, collection=None, *specs, **kwargs):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.lookup_in(key, *specs, **kwargs)
            else:
                self.default_collection.lookup_in(key, *specs, **kwargs)
        except CouchbaseError as e:
            raise

    def get_in(self, key, path, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                result = self.collection.get_in(key, path)
            else:
                result = self.default_collection.get_in(key, path)
            return self.__translate_get(result)
        except CouchbaseError as e:
            raise

    def exists_in(self, key, path, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.exists_in(key, path)
            else:
                self.default_collection.exists_in(key, path)
        except CouchbaseError as e:
            raise

    def replace_in(self, key, path, value, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.replace_in(key, path, value, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.replace_in(key, path, value, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def insert_in(self, key, path, value, create_parents=True, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.insert_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.insert_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def upsert_in(self, key, path, value, create_parents=True, cas=0, ttl=0, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.upsert_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.upsert_in(key, path, value, create_parents=create_parents, cas=cas, ttl=ttl, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            raise

    def append(self, key, value, cas=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.append(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.append(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.append(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.append(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def append_multi(self, keys, cas=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.append_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.append_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.append_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.append_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def prepend(self, key, value, cas=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.prepend(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.prepend(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                if collection:
                    self.collection.prepend(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.prepend(key, value, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def prepend_multi(self, keys, cas=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.prepend_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.prepend_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.prepend_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.prepend_multi(keys, cas=cas, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def replace(self, key, value, cas=0, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.replace( key, value, cas=cas, ttl=ttl, format=format,
                                        persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.replace( key, value, cas=cas, ttl=ttl, format=format,
                                    persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.replace( key, value, cas=cas, ttl=ttl, format=format,
                                    persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.replace( key, value, cas=cas, ttl=ttl, format=format,
                                    persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def replace_multi(self, keys, cas=0, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.replace_multi( keys, cas=cas, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.replace_multi( keys, cas=cas, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.replace_multi( keys, cas=cas, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.replace_multi( keys, cas=cas, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def cas(self, key, value, cas=0, ttl=0, format=None, collection=None):
        if collection:
            self.collection_connect(collection)
            return self.collection.replace(key, value, cas=cas, format=format)
        else:
            return self.default_collection.replace(key, value, cas=cas, format=format)

    def delete(self,key, cas=0, quiet=True, persist_to=0, replicate_to=0, collection=None):
        self.remove(key, cas=cas, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to, collection=collection)

    def remove(self,key, cas=0, quiet=True, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.remove(key, cas=cas, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to)
            else:
                return self.default_collection.remove(key, cas=cas, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            self.remove(key, cas=0, quiet=True, persist_to=0, replicate_to=0, collection=None)

    def delete(self, keys, quiet=True, persist_to=0, replicate_to=0, collection=None):
        return self.remove(self, keys, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to, collection=collection)

    def remove_multi(self, keys, quiet=True, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.remove_multi(keys, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.remove_multi(keys, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.remove_multi(keys, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.remove_multi(keys, quiet=quiet, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def set(self, key, value, cas=0, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        return self.upsert(key, value, cas=cas, ttl=ttl, format=format, persist_to=persist_to,
                           replicate_to=replicate_to, collection=collection)

    def collection_connect(self, collection):
        coll = collection.split(".")
        scope = self.cb.scope(coll[0])
        self.collection = scope.collection(coll[1])

    def upsert(self, key, value, cas=0, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                rvs = self.collection.upsert(key, value, cas, ttl, format, persist_to, replicate_to)
                print ("the result for key {} is {} and value is {}".format(key, rvs.__dict__, self.collection.get(key).content_as[str]))
                return rvs
            else:
                return self.default_collection.upsert(key, value, cas, ttl, format, persist_to, replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    return self.collection.upsert(key, value, cas, ttl, format, persist_to, replicate_to)
                else:
                    return self.default_collection.upsert(key, value, cas, ttl, format, persist_to, replicate_to)
            except CouchbaseError as e:
                raise

    def set_multi(self, keys, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        return self.upsert_multi(keys, ttl=ttl, format=format, persist_to=persist_to,
                                 replicate_to=replicate_to, collection=collection)

    def upsert_mult(self, keys, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        self.collection_connect(collection)
        for key, value in keys.iteritems():
            self.collection.upsert(key, value, 0, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            print(self.collection.get(key))


    def upsert_multi(self, keys, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                rvs = self.collection.upsert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                rvs = self.default_collection.upsert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as exc:
            print("hit couchbase error for collection {}".format(collection))
            print("retrying")
            self.upsert_multi(keys, ttl=0, format=format, persist_to=persist_to, replicate_to=replicate_to)

            # try:
            #     time.sleep(10)
            #     if collection:
            #         self.collection_connect(collection)
            #         self.collection.upsert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            #     else:
            #         self.cb.upsert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            # except CouchbaseError as e:
            #     raise

    def insert(self, key, value, ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.insert(key, value, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            else:
                self.default_collection.insert(key, value, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.insert(key, value, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.insert(key, value, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def insert_multi(self, keys,  ttl=0, format=None, persist_to=0, replicate_to=0, collection=None):
        print("inside insert multi")
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.insert_multi(keys, ttl=ttl, format=format, persist_to=persist_to,
                                             replicate_to=replicate_to)
            else:
                self.default_collection.insert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection_connect(collection)
                    self.collection.insert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
                else:
                    self.default_collection.insert_multi(keys, ttl=ttl, format=format, persist_to=persist_to, replicate_to=replicate_to)
            except CouchbaseError as e:
                raise

    def touch(self, key, ttl = 0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.touch(key, ttl=ttl)
            else:
                self.default_collection.touch(key, ttl=ttl)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection_connect(collection)
                    self.collection.touch(key, ttl=ttl)
                else:
                    self.default_collection.touch(key, ttl=ttl)
            except CouchbaseError as e:
                raise

    def touch_multi(self, keys, ttl = 0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.touch_multi(keys, ttl=ttl)
            else:
                self.default_collection.touch_multi(keys, ttl=ttl)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection_connect(collection)
                    self.collection.touch_multi(keys, ttl=ttl)
                else:
                    self.default_collection.touch_multi(keys, ttl=ttl)
            except CouchbaseError as e:
                raise

    def decr(self, key, delta=1, initial=None, ttl=0, collection=None):
        self.counter(key, delta=-delta, initial=initial, ttl=ttl, collection=collection)

    def decr_multi(self, keys, delta=1, initial=None, ttl=0, collection=None):
        self.counter_multi(keys, delta=-delta, initial=initial, ttl=ttl, collection=collection)

    def incr(self, key, delta=1, initial=None, ttl=0, collection=None):
        self.counter(key, delta=delta, initial=initial, ttl=ttl, collection=collection)

    def incr_multi(self, keys, delta=1, initial=None, ttl=0, collection=None):
        self.counter_multi(keys, delta=delta, initial=initial, ttl=ttl, collection=collection)

    def counter(self, key, delta=1, initial=None, ttl=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.counter(key, delta=delta, initial=initial, ttl=ttl)
            else:
                self.default_collection.counter(key, delta=delta, initial=initial, ttl=ttl)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.counter(key, delta=delta, initial=initial, ttl=ttl)
                else:
                    self.default_collection.counter(key, delta=delta, initial=initial, ttl=ttl)
            except CouchbaseError as e:
                raise

    def counter_multi(self, keys, delta=1, initial=None, ttl=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.counter_multi(keys, delta=delta, initial=initial, ttl=ttl)
            else:
                self.default_collection.counter_multi(keys, delta=delta, initial=initial, ttl=ttl)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.counter_multi(keys, delta=delta, initial=initial, ttl=ttl)
                else:
                    self.default_collection.counter_multi(keys, delta=delta, initial=initial, ttl=ttl)
            except CouchbaseError as e:
                raise

    def get(self, key, ttl=0, quiet=True, replica=False, no_format=False, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                rv = self.collection.get(key, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)
            else:
                rv = self.default_collection.get(key, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)
            return self.__translate_get(rv)
        except CouchbaseError as e:
            self.get(key, ttl=0, quiet=True, replica=False, no_format=False, collection=None)

    def rget(self, key, replica_index=None, quiet=True, collection=None):
        try:
            data  = self.rget(key, replica_index=replica_index, quiet=quiet, collection=collection)
            return self.__translate_get(data)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                data  = self.rget(key, replica_index=replica_index, quiet=quiet, collection=collection)
                return self.__translate_get(data)
            except CouchbaseError as e:
                raise

    def get_multi(self, keys, ttl=0, quiet=True, replica=False, no_format=False, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                data = self.collection.get_multi(keys, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)
            else:
                data = self.default_collection.get_multi(keys, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)
            return self.__translate_get_multi(data)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection_connect(collection)
                    data = self.collection.get_multi(keys, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)
                else:
                    data = self.default_collection.get_multi(keys, ttl=ttl, quiet=quiet, replica=replica, no_format=no_format)
                return self.__translate_get_multi(data)
            except CouchbaseError as e:
                raise

    def rget_multi(self, key, replica_index=None, quiet=True, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                data = self.collection.rget_multi(key, replica_index=None, quiet=quiet)
            else:
                data = self.default_collection.rget_multi(key, replica_index=None, quiet=quiet)
            return self.__translate_get_multi(data)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    data = self.collection.rget_multi(key, replica_index=None, quiet=quiet)
                else:
                    data = self.default_collection.rget_multi(key, replica_index=None, quiet=quiet)
                return self.__translate_get_multi(data)
            except CouchbaseError as e:
                raise

    def stats(self, keys=None, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                stat_map = self.collection.stats(keys = keys)
            else:
                stat_map = self.default_collection.stats(keys = keys)
            return stat_map
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    return self.collection.stats(keys = keys)
                else:
                    return self.default_collection.stats(keys = keys)
            except CouchbaseError as e:
                raise

    def errors(self, clear_existing=True, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                rv = self.collection.errors(clear_existing = clear_existing)
            else:
                rv = self.default_collection.errors(clear_existing = clear_existing)
            return rv
        except CouchbaseError as e:
            raise

    def observe(self, key, master_only=False, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.observe(key, master_only = master_only)
            else:
                return self.default_collection.observe(key, master_only = master_only)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    return self.collection.observe(key, master_only = master_only)
                else:
                    return self.default_collection.observe(key, master_only = master_only)
            except CouchbaseError as e:
                raise

    def observe_multi(self, keys, master_only=False, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                data = self.collection.observe_multi(keys, master_only = master_only)
            else:
                data = self.default_collection.observe_multi(keys, master_only = master_only)
            return self.__translate_observe_multi(data)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    data = self.collection.observe_multi(keys, master_only = master_only)
                else:
                    data = self.default_collection.observe_multi(keys, master_only = master_only)
                return self.__translate_observe_multi(data)
            except CouchbaseError as e:
                raise

    def endure(self, key, persist_to=-1, replicate_to=-1, cas=0, check_removed=False, timeout=5.0, interval=0.010, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.endure(key, persist_to=persist_to, replicate_to=replicate_to,
                               cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
            else:
                self.default_collection.endure(key, persist_to=persist_to, replicate_to=replicate_to,
                           cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.endure(key, persist_to=persist_to, replicate_to=replicate_to,
                    cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
                else:
                    self.default_collection.endure(key, persist_to=persist_to, replicate_to=replicate_to,
                           cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
            except CouchbaseError as e:
                raise

    def endure_multi(self, keys, persist_to=-1, replicate_to=-1, cas=0, check_removed=False, timeout=5.0, interval=0.010, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                self.collection.endure(keys, persist_to=persist_to, replicate_to=replicate_to,
                           cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
            else:
                self.default_collection.endure(keys, persist_to=persist_to, replicate_to=replicate_to,
                           cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    self.collection.endure(keys, persist_to=persist_to, replicate_to=replicate_to,
                               cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
                else:
                    self.default_collection.endure(keys, persist_to=persist_to, replicate_to=replicate_to,
                               cas=cas, check_removed=check_removed, timeout=timeout, interval=interval)
            except CouchbaseError as e:
                raise

    def lock(self, key, ttl=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                data = self.collection.lock(key, ttl = ttl)
            else:
                data = self.default_collection.lock(key, ttl = ttl)
            return self.__translate_get(data)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    data = self.collection.lock(key, ttl = ttl)
                else:
                    data = self.default_collection.lock(key, ttl = ttl)
                return self.__translate_get(data)
            except CouchbaseError as e:
                raise

    def lock_multi(self, keys, ttl=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                data = self.collection.lock_multi(keys, ttl = ttl)
            else:
                data = self.default_collection.lock_multi(keys, ttl = ttl)
            return self.__translate_get_multi(data)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    data = self.collection.lock_multi(keys, ttl = ttl)
                else:
                    data = self.default_collection.lock_multi(keys, ttl = ttl)
                return self.__translate_get_multi(data)
            except CouchbaseError as e:
                raise

    def unlock(self, key, ttl=0, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.unlock(key)
            else:
                return self.default_collection.unlock(key)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    return self.collection.unlock(key)
                else:
                    return self.default_collection.unlock(key)
            except CouchbaseError as e:
                raise

    def unlock_multi(self, keys, collection=None):
        try:
            if collection:
                self.collection_connect(collection)
                return self.collection.unlock_multi(keys)
            else:
                return self.default_collection.unlock_multi(keys)
        except CouchbaseError as e:
            try:
                time.sleep(10)
                if collection:
                    return self.collection.unlock_multi(keys)
                else:
                    return self.default_collection.unlock_multi(keys)
            except CouchbaseError as e:
                raise

    def n1ql_query(self, statement, prepared=False):
        try:
            return N1QLQuery(statement, prepared)
        except CouchbaseError as e:
            raise

    def n1ql_request(self, query):
        try:
            return N1QLRequest(query, self.cb)
        except CouchbaseError as e:
            raise

    def __translate_get_multi(self, data):
        map = {}
        if data == None:
            return map
        for key, result in list(data.items()):
            result = result._original
            map[key] = [result.flags, result.cas, result.value]
        return map

    def __translate_get_multi_results(self, data):
        success = dict()
        fail = dict()
        if data is None:
            return success, fail
        for key, result in list(data.items()):
            result = result._original
            if result.status:
                success[key] = dict()
                success[key]['value'] = result.value
                success[key]['cas'] = result.cas
            else:
                fail[key] = dict()
                fail[key]['cas'] = result.cas
                fail[key]['error'] = result.error
                fail[key]['value'] = dict()
        return success, fail

    def __translate_get(self, data):
        data = data._original
        return data.flags, data.cas, data.value

    def __translate_delete(self, data):
        return data

    def __translate_observe(self, data):
        return data

    def __translate_observe_multi(self, data):
        map = {}
        if data == None:
            return map
        for key, result in list(data.items()):
            map[key] = result.value
        return map

    def __translate_upsert_multi(self, data):
        map = {}
        if data == None:
            return map
        for key, result in list(data.items()):
            map[key] = result
        return map

    def __translate_upsert_op(self, data):
        return data.rc, data.success, data.errstr, data.key



class SDKSmartClient(object):
      def __init__(self, rest, bucket, compression=True, info = None):
        self.rest = rest
        if hasattr(bucket, 'name'):
            self.bucket=bucket.name
        else:
            self.bucket=bucket

        if hasattr(bucket, 'saslPassword'):
            self.saslPassword = bucket.saslPassword
        else:
            bucket_info = rest.get_bucket(bucket)
            self.saslPassword = bucket_info.saslPassword


        if rest.ip == "127.0.0.1":
            self.host = "{0}:{1}".format(rest.ip, rest.port)
            self.scheme = "http"
        else:
            self.host = rest.ip
            self.scheme = "couchbase"
        self.client = SDKClient(self.bucket, hosts = [self.host], scheme = self.scheme, password = self.saslPassword,
                                compression=compression)

      def reset(self, compression=True, rest=None):
        self.client = SDKClient(self.bucket, hosts = [self.host], scheme = self.scheme, password = self.saslPassword,
                                compression=compression)

      def memcached(self, key):
        return self.client

      def set(self, key, exp, flags, value, collection=None):
          rc =  self.client.set(key, value, ttl = exp, collection=collection)

      def append(self, key, value, collection=None):
          return self.client.set(key, value, collection=collection)

      def observe(self, key, collection=None):
          return self.client.observe(key, collection=collection)

      def get(self, key, collection=None):
          return self.client.get(key, collection=collection)

      def getr(self, key, replica_index=0, collection=None):
          return self.client.rget(key, replica_index=replica_index, collection=collection)

      def setMulti(self, exp, flags, key_val_dic, pause = None, timeout = 5.0, parallel=None, collection=None):
          try:
                self.client.cb.timeout = timeout

                # return self.client.upsert_multi(key_val_dic, ttl = exp)
                return self.client.upsert_multi(key_val_dic, ttl = exp, collection=collection)
          finally:
                self.client.cb.timeout = self.client.default_timeout

      def getMulti(self, keys_lst, pause = None, timeout_sec = 5.0, parallel=None, collection=None):
          try:
              self.client.cb.timeout = timeout_sec
              map = self.client.get_multi(keys_lst, collection=collection)
              return map
          finally:
              self.client.cb.timeout = self.client.default_timeout


      def getrMulti(self, keys_lst, replica_index= None, pause = None, timeout_sec = 5.0, parallel=None, collection=None):
          try:
              self.client.cb.timeout = timeout_sec
              map = self.client.rget_multi(keys_lst, replica_index = replica_index, collection=collection)
              return map
          finally:
              self.client.cb.timeout = self.client.default_timeout

      def delete(self, key, collection=None):
          return self.client.remove(key, collection=collection)
      
      def _send_op(self, func, *args):
        backoff = .001
        while True:
            try:
                print("the args are {}, {}, {}".format(args[0], args[1], args[2]))
                return func(*args)
            except MemcachedError as error:
                if error.status == ERR_ETMPFAIL and backoff < .5:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise error
            except (EOFError, IOError, socket.error) as error:
                raise MemcachedError(ERR_NOT_MY_VBUCKET, "Connection reset with error: {0}".format(error))
      
      def generic_request(self, func, *args):
        key = args[0]
        vb_error = 0
        while True:
            try:
                return self._send_op(func, *args)
            except MemcachedError as error:
                raise error
     
            

class SDKBasedKVStoreAwareSmartClient(SDKSmartClient):
    def __init__(self, rest, bucket, kv_store=None, info=None, store_enabled=True):
        SDKSmartClient.__init__(self, rest, bucket, info)
        self.kv_store = kv_store or ClientKeyValueStore()
        self.store_enabled = store_enabled
        self._rlock = threading.Lock()

    def set(self, key, value, ttl=-1, collection=None):
        self._rlock.acquire()
        try:
            if ttl >= 0:
                self.memcached(key).set(key, ttl, 0, value, collection=collection)
            else:
                self.memcached(key).set(key, 0, 0, value, collection=collection)

            if self.store_enabled:
                self.kv_store.write(key, hashlib.md5(value).digest(), ttl)
        except MemcachedError as e:
            self._rlock.release()
            raise MemcachedError(e.status, e.msg)
        except AssertionError:
            self._rlock.release()
            raise AssertionError
        except:
            self._rlock.release()
            raise Exception("General Exception from KVStoreAwareSmartClient.set()")

        self._rlock.release()

    """
    " retrieve meta data of document from disk
    """
    def get_doc_metadata(self, num_vbuckets, key):
        vid = crc32.crc32_hash(key) & (num_vbuckets - 1)

        mc = self.memcached(key)
        metadatastats = None

        try:
            metadatastats = mc.stats("vkey {0} {1}".format(key, vid))
        except MemcachedError:
            msg = "key {0} doesn't exist in memcached".format(key)
            self.log.info(msg)

        return metadatastats


    def delete(self, key, collection=None):
        try:
            self._rlock.acquire()
            opaque, cas, data = self.memcached(key).delete(key, collection=collection)
            if self.store_enabled:
                self.kv_store.delete(key)
            self._rlock.release()
            if cas == 0:
                raise MemcachedError(7, "Invalid cas value")
        except Exception as e:
            self._rlock.release()
            raise MemcachedError(7, str(e))

    def get_valid_key(self, key):
        return self.get_key_check_status(key, "valid")

    def get_deleted_key(self, key):
        return self.get_key_check_status(key, "deleted")

    def get_expired_key(self, key):
        return self.get_key_check_status(key, "expired")

    def get_all_keys(self):
        return list(self.kv_store.keys())

    def get_all_valid_items(self):
        return self.kv_store.valid_items()

    def get_all_deleted_items(self):
        return self.kv_store.deleted_items()

    def get_all_expired_items(self):
        return self.kv_store.expired_items()

    def get_key_check_status(self, key, status):
        item = self.kv_get(key)
        if(item is not None  and item["status"] == status):
            return item
        else:
            msg = "key {0} is not valid".format(key)
            self.log.info(msg)
            return None

    # safe kvstore retrieval
    # return dict of {key,status,value,ttl}
    # or None if not found
    def kv_get(self, key):
        item = None
        try:
            item = self.kv_store.read(key)
        except KeyError:
            msg = "key {0} doesn't exist in store".format(key)
            # self.log.info(msg)

        return item

    # safe memcached retrieval
    # return dict of {key, flags, seq, value}
    # or None if not found
    def mc_get(self, key):
        item = self.mc_get_full(key)
        if item is not None:
            item["value"] = hashlib.md5(item["value"]).digest()
        return item

    # unhashed value
    def mc_get_full(self, key):
        item = None
        try:
            x, y, value = self.memcached(key).get(key)
            item = {}
            item["key"] = key
            item["flags"] = x
            item["seq"] = y
            item["value"] = value
        except MemcachedError:
            msg = "key {0} doesn't exist in memcached".format(key)

        return item

    def kv_mc_sync_get(self, key, status):
        self._rlock.acquire()
        kv_item = self.get_key_check_status(key, status)
        mc_item = self.mc_get(key)
        self._rlock.release()

        return kv_item, mc_item
