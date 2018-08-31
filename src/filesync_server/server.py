#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import time
from concurrent import futures

import filesync_server.pb.rpc_pb2 as rpc_pb2
import filesync_server.pb.rpc_pb2_grpc as rpc_pb2_grpc
import grpc
from filesync_server.lib.file_util import ServedFile
from filesync_server.lib.util import setup_logging

log = logging.getLogger(__name__)


class Servicer(rpc_pb2_grpc.FileSyncRpcServicer):
    def GetPatch(self, request, context):
        log.debug("Servicing request for %s", request.name)

        filepath = os.path.join("/tmp", request.name)
        fb = ServedFile(filepath, blocksize=request.blocksize)

        if fb.checksum == request.checksum.checksum:
            # client already has the file, just return the checksum
            patch = rpc_pb2.Patch()
            patch.name = request.name
            patch.checksum.checksum = fb.checksum

            return patch

        csums = [csum.checksum for csum in request.blockcsums]
        blocks_list = []
        index = 0
        for block in fb.patch(csums):
            if isinstance(block, tuple):
                checksum, data = block
                bl = rpc_pb2.Block()
                bl.number = index
                bl.checksum.checksum = checksum
                bl.data = data
                blocks_list.append(bl)
            else:
                bl = rpc_pb2.Block()
                bl.number = index
                bl.existing = block
                blocks_list.append(bl)
            index += 1

        patch = rpc_pb2.Patch()
        patch.name = request.name
        patch.checksum.checksum = fb.checksum
        patch.blocks.extend(blocks_list)

        return patch


def main():
    setup_logging(log)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    rpc_pb2_grpc.add_FileSyncRpcServicer_to_server(Servicer(), server)
    server.add_insecure_port('[::]:50051')

    server.start()

    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        server.stop(0)
