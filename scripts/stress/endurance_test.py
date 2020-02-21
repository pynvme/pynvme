import pytest
import zipfile
import logging
import nvme as d


def test_ioworker_jedec_enterprise_workload(nvme0n1):
    distribution = [1000]*5 + [200]*15 + [25]*80
    iosz_distribution = {1: 4,
                         2: 1,
                         3: 1,
                         4: 1,
                         5: 1,
                         6: 1,
                         7: 1,
                         8: 67,
                         16: 10,
                         32: 7,
                         64: 3,
                         128: 3}

    nvme0n1.ioworker(io_size=iosz_distribution,
                     lba_random=True,
                     qdepth=128,
                     distribution = distribution,
                     read_percentage=0,
                     ptype=0xbeef, pvalue=100, 
                     time=12*3600).start().close()


def test_replay_jedec_client_trace(nvme0, nvme0n1):
    q = d.Qpair(nvme0, 1024)
    buf = d.Buffer(256*512, "write", 100, 0xbeef) # upto 128K
    batch = 0
    counter = 0

    nvme0n1.format(512)
    with zipfile.ZipFile("scripts/stress/MasterTrace_128GB-SSD.zip") as z:
        for s in z.open("Client_128_GB_Master_Trace.txt"):
            l = str(s)[7:-5]
            #logging.info(l)

            if l[0] == 'h':
                # flush
                nvme0n1.flush(q)
                counter += 1
            else:
                op, slba, nlba = l.split()
                slba = int(slba)
                nlba = int(nlba)
                if op == 'e':
                    # write
                    while nlba:
                        n = min(nlba, 256)
                        nvme0n1.write(q, buf, slba, n)
                        counter += 1
                        slba += n
                        nlba -= n
                elif op == 's':
                    # trims
                    buf.set_dsm_range(0, slba, nlba)
                    nvme0n1.dsm(q, buf, 1)
                    counter += 1
                else:
                    logging.info(l)

            # reap in batch for better efficiency
            if counter > 100:
                q.waitdone(counter)
                if batch % 1000 == 0:
                    logging.info("replay batch %d" % (batch//1000))
                batch += 1
                counter = 0

    q.waitdone(counter)
