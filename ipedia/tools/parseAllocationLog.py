import sys, re

class Chunk:
    
    def __init__(self, address, size, fileName, fileLine):
        self.address=address
        self.size=size
        self.fileName=fileName
        self.fileLine=fileLine

deallocRe=re.compile(r"^\-\t0x([0-9a-hA-H]{8})$")
allocRe=re.compile(r"^\+\t0x([0-9a-hA-H]{8})\t(\d+)\t(.+): (\d+)$")
chunks=dict()
allocated=0
maxAllocated=0
f=file(sys.argv[1])
for line in f:
    isAlloc=False
    m=deallocRe.match(line)
    if not m:
        isAlloc=True        
        m=allocRe.match(line)
    address=int(m.group(1), 16)
    if isAlloc:
        chunk=Chunk(address, int(m.group(2)), m.group(3), int(m.group(4)))
        chunks[address]=chunk
        allocated=allocated+chunk.size
        if allocated>maxAllocated:
            maxAllocated=allocated
    else:
        if chunks.has_key(address):
            chunk=chunks[address]
            allocated=allocated-chunk.size
            del chunks[address]

print "Maximum estimated memory usage: %d bytes" % maxAllocated

for chunk in chunks.itervalues():
    print "Possible memory leak: %s: %d (%d bytes)" % (chunk.fileName, chunk.fileLine, chunk.size)

