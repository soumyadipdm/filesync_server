import logging
import grpc
from filesync_server.lib.file_util import ReceivedFile
from filesync_server.lib.file_util import blocks
from filesync_server.lib.file_util import file_checksum
from filesync_server.lib.util import setup_logging
from filesync_server.pb import rpc_pb2
from filesync_server.pb import rpc_pb2_grpc


log = logging.getLogger()


def main():
    """main function"""
    setup_logging(log)

    with grpc.insecure_channel("localhost:50051") as channel:
        stub = rpc_pb2_grpc.FileSyncRpcStub(channel)

        filename = "/home/unixuser/test.tar.gz"
        csum = file_checksum(filename)
        blockcsums = []
        blocksize = 4096
        log.debug("Setting block size to: %d bytes", blocksize)
        log.debug("Existing file: %s, checksum: %s", filename, csum)
        for blockcsum in blocks(filename, size=blocksize, is_data=False):
            cs = rpc_pb2.Checksum()
            cs.checksum = blockcsum
            blockcsums.append(cs)

        file = rpc_pb2.File()
        file.name = "test.tar.gz"
        file.checksum.checksum = csum
        file.blocksize = blocksize
        file.blockcsums.extend(blockcsums)

        log.debug("Requesting patch for %s", file.name)

        patch = stub.GetPatch(file)

        rfile = ReceivedFile(filename, blocksize)
        rfile.apply_patch(patch.blocks, patch.checksum.checksum)
