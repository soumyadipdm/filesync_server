import grpc
from filesync_server.lib.file_util import blocks
from filesync_server.lib.file_util import file_checksum
from filesync_server.pb import rpc_pb2
from filesync_server.pb import rpc_pb2_grpc


def main():
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = rpc_pb2_grpc.FileSyncRpcStub(channel)

        filename = "/home/unixuser/test.tar.gz"
        csum = file_checksum(filename)
        blockcsums = []
        for blockcsum in blocks(filename, size=4096, is_data=False):
            cs = rpc_pb2.Checksum()
            cs.checksum = blockcsum
            blockcsums.append(cs)

        file = rpc_pb2.File()
        file.name = "test.tar.gz"
        file.checksum.checksum = csum
        file.blocksize = 4096
        file.blockcsums.extend(blockcsums)

        patch = stub.GetPatch(file)
        print(patch.blocks)
