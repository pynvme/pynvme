/*-
 *   BSD LICENSE
 *
 *   Copyright (c) Crane Chu <cranechu@gmail.com>
 *   All rights reserved.
 *
 *   Redistribution and use in source and binary forms, with or without
 *   modification, are permitted provided that the following conditions
 *   are met:
 *
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in
 *       the documentation and/or other materials provided with the
 *       distribution.
 *     * Neither the name of Intel Corporation nor the names of its
 *       contributors may be used to endorse or promote products derived
 *       from this software without specific prior written permission.
 *
 *   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 *   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 *   OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 *   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 *   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 *   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */


#include "driver.h"

#include "../spdk/lib/nvme/nvme_internal.h"


static uint64_t* g_driver_io_token_ptr = NULL;
static uint64_t* g_driver_config_ptr = NULL;
static bool g_driver_crc32_memory_enough = false;


////module: timeval
///////////////////////////////

static struct timespec tv_diff;


static void timeval_init(void)
{
  struct timespec ts;
  struct timeval tv;

  gettimeofday(&tv, NULL);
  clock_gettime(CLOCK_MONOTONIC, &ts);

  tv_diff.tv_sec = tv.tv_sec-ts.tv_sec-1;
  tv_diff.tv_nsec = (1<<30)+tv.tv_usec*1000-ts.tv_nsec;
}


uint32_t timeval_to_us(struct timeval* t)
{
  return t->tv_sec*US_PER_S + t->tv_usec;
}


void timeval_gettimeofday(struct timeval *tv)
{
  struct timespec ts;

  assert(tv != NULL);

  // gettimeofday is affected by NTP and etc, so use clock_gettime
  clock_gettime(CLOCK_MONOTONIC, &ts);
  tv->tv_sec = ts.tv_sec+tv_diff.tv_sec;
  tv->tv_usec = (ts.tv_nsec+tv_diff.tv_nsec)>>10;
  if (tv->tv_usec > US_PER_S)
  {
    tv->tv_sec += tv->tv_usec/US_PER_S;
    tv->tv_usec = tv->tv_usec%US_PER_S;
  }
}


////module: buffer
///////////////////////////////

void* buffer_init(size_t bytes, uint64_t *phys_addr,
                  uint32_t ptype, uint32_t pvalue)
{
  uint32_t pattern = 0;
  void* buf = spdk_dma_zmalloc(bytes, 0x1000, NULL);
  if (buf == NULL)
  {
    return NULL;
  }

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "buffer: alloc ptr at %p, size %ld\n",
                buf, bytes);

  // get the physical address
  if (phys_addr && buf)
  {
    *phys_addr= spdk_vtophys(buf, NULL);
  }

  if (ptype == 0)
  {
    // if pvalue is not zero, set data buffer all-one
    if (pvalue != 0)
    {
      pattern = 0xffffffff;
    }
  }
  else if (ptype == 32)
  {
    pattern = pvalue;
  }
  else if (ptype == 0xbeef)
  {
    // for random buffer, size the buffer all-zero first
    pattern = 0;
  }

  // set the buffer by 32-bit pattern
  //spdk_dma_zmalloc has set the buffer all-zero already
  if (pattern != 0)
  {
    uint32_t* ptr = buf;

    // left remaining unaligned bytes unset
    for (uint32_t i=0; i<bytes/sizeof(pattern); i++)
    {
      ptr[i] = pattern;
    }
  }

  // fill random data according to the percentage
  if (ptype == 0xbeef)
  {
    uint32_t count = 0;
    int fd = open("/dev/urandom", O_RDONLY);

    assert(pvalue <= 100);  // here needs a percentage <= 100
    count = (size_t)(bytes*pvalue/100);
    count = MIN(count, bytes);
    read(fd, buf, count);
    close(fd);
  }

  return buf;
}

static inline uint32_t buffer_calc_csum(uint64_t* ptr, int len)
{
  uint32_t crc = spdk_crc32c_update(ptr, len, 0)>>1;

  //reserve 0: nomapping
  //reserve 0xffffffff: uncorrectable
  if (crc == 0) crc = 1;
  if (crc == 0x7fffffff) crc = 0x7ffffffe;

  return crc;
}

static void buffer_fill_rawdata(void* buf,
                                uint64_t lba,
                                uint32_t lba_count,
                                uint32_t lba_size)
{
  // token is keeping increasing, so every write has different data
  uint64_t token = __atomic_fetch_add(g_driver_io_token_ptr,
                                      lba_count,
                                      __ATOMIC_SEQ_CST);

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "token: %ld, lba 0x%lx, lba count %d\n", token, lba, lba_count);

  for (uint32_t i=0; i<lba_count; i++, lba++)
  {
    uint64_t* ptr = (uint64_t*)(buf+i*lba_size);

    //first and last 64bit-words are filled with special data
    ptr[0] = lba;
    ptr[lba_size/sizeof(uint64_t)-1] = token+i;
  }
}

static inline void buffer_update_crc(struct spdk_nvme_ns* ns,
                                     uint32_t* crc_table_data,
                                     const void* buf,
                                     const unsigned long lba_first,
                                     const uint32_t lba_count,
                                     const uint32_t lba_size)
{
  // keep crc in memory if allocated
  // suppose device modify data correctly. If the command fails, we cannot
  // tell what part of data is updated, while what not. Even when atomic
  // write is supported, we still cannot tell that.
  for (uint64_t i=0, lba=lba_first; i<lba_count; i++, lba++)
  {
    if (lba < ns->table_size/sizeof(uint32_t))
    {
      SPDK_DEBUGLOG(SPDK_LOG_NVME, "lba %ld\n", lba);

      uint64_t* ptr = (uint64_t*)(buf+i*lba_size);
      crc_table_data[lba] = buffer_calc_csum(ptr, lba_size);
    }
  }
}

static inline int buffer_verify_lba(const void* buf,
                                    const unsigned long lba_first,
                                    const uint32_t lba_count,
                                    const uint32_t lba_size)
{
  for (uint64_t i=0, lba=lba_first; i<lba_count; i++, lba++)
  {
    uint64_t expected_lba = *(uint64_t*)(buf+i*lba_size);

    // exclude nomapping cases
    if (expected_lba != lba &&
        expected_lba != 0 &&
        expected_lba != (uint64_t)-1)
    {
      return -2;
    }
  }

  return 0;
}

static inline int buffer_verify_data(struct spdk_nvme_ns* ns,
                                     const void* buf,
                                     const unsigned long lba_first,
                                     const uint32_t lba_count,
                                     const uint32_t lba_size)
{
  for (uint64_t i=0, lba=lba_first; i<lba_count; i++, lba++)
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "lba %ld\n", lba);

    if (lba < ns->table_size/sizeof(uint32_t))
    {
      crc_table_t* crc_table = (crc_table_t*)ns->crc_table;
      uint32_t expected_crc = (0x7fffffff&crc_table->data[lba]);
      if (expected_crc == 0)
      {
        // no mapping, nothing to verify
        continue;
      }
      if (expected_crc == 0x7fffffff)
      {
        SPDK_WARNLOG("lba uncorrectable: lba 0x%lx\n", lba);
        return -1;
      }

      uint64_t* ptr = (uint64_t*)(buf+i*lba_size);
      uint32_t computed_crc = buffer_calc_csum(ptr, lba_size);
      if (computed_crc != expected_crc)
      {
        assert(expected_crc != 0);  // exclude nomapping
        SPDK_WARNLOG("crc mismatch: lba 0x%lx, expected crc 0x%x, but got: 0x%x\n",
                     lba, expected_crc, computed_crc);
        return -3;
      }
    }
  }

  return 0;
}

void buffer_fini(void* buf)
{
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "buffer: free ptr at %p\n", buf);
  assert(buf != NULL);
  spdk_dma_free(buf);
}


////crc32 table
///////////////////////////////

static void crc32_clear(struct spdk_nvme_ns *ns,
                        uint64_t lba,
                        uint64_t len,
                        bool uncorr)
{
  uint32_t c = uncorr ? 0x7fffffff : 0;
  crc_table_t* crc_table = (crc_table_t*)ns->crc_table;

  assert(ns != NULL);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "clear crc: lba %ld, len %ld, uncorr %d\n", lba, len, uncorr);

  if (crc_table != NULL && lba*sizeof(uint32_t) < ns->table_size)
  {
    assert(ns->table_size != 0);

    // clear crc table if it exists and cover the lba range
    if (lba*sizeof(uint32_t)+len > ns->table_size)
    {
      len = ns->table_size - lba*sizeof(uint32_t);
    }

    SPDK_DEBUGLOG(SPDK_LOG_NVME, "clear checksum table, "
                  "lba 0x%lx, c %d, len %ld\n", lba, c, len);
    for (uint64_t i=0; i<len/sizeof(uint32_t); i++)
    {
      crc_table->data[lba+i] = c;
    }
  }
}


static void crc32_clear_ranges(struct spdk_nvme_ns* ns,
                               void* buf, unsigned int count)
{
  struct spdk_nvme_dsm_range *ranges = (struct spdk_nvme_dsm_range*)buf;

  for (unsigned int i=0; i<count; i++)
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "deallocate lba 0x%lx, count %d\n",
                  ranges[i].starting_lba,
                  ranges[i].length);
    crc32_clear(ns,
                ranges[i].starting_lba,
                ranges[i].length * sizeof(uint32_t),
                false);
  }
}


static void crc32_set_lock_bits(struct spdk_nvme_ns* ns,
                                crc_table_t* crc_table,
                                uint64_t slba,
                                uint64_t nlb,
                                bool lock)
{
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "slba 0x%lx, nlb %ld, lock %d\n", slba, nlb, lock);

  if (crc_table != NULL && slba*sizeof(uint32_t) < ns->table_size)
  {
    // clear crc table if it exists and cover the lba range
    if ((slba+nlb)*sizeof(uint32_t) > ns->table_size)
    {
      nlb = ns->table_size/sizeof(uint32_t) - slba;
    }

    for (uint64_t i=0; i<nlb; i++)
    {
      if (lock)
      {
        crc_table->data[slba+i] |= 0x80000000;
      }
      else
      {
        crc_table->data[slba+i] &= ~0x80000000;
      }
    }
  }
}


static bool crc32_check_lock_bits(struct spdk_nvme_ns* ns,
                                  crc_table_t* crc_table,
                                  uint64_t slba,
                                  uint16_t nlb)
{
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "slba 0x%lx, nlb %d\n", slba, nlb);

  if (crc_table != NULL && slba*sizeof(uint32_t) < ns->table_size)
  {
    // clear crc table if it exists and cover the lba range
    if ((slba+nlb)*sizeof(uint32_t) > ns->table_size)
    {
      nlb = ns->table_size/sizeof(uint32_t) - slba;
    }

    for (uint16_t i=0; i<nlb; i++)
    {
      if (crc_table->data[slba+i] & 0x80000000)
      {
        // one lba is locked
        SPDK_DEBUGLOG(SPDK_LOG_NVME, "lba 0x%lx is locked\n", slba+i);
        return true;
      }
    }
  }

  // no lba was locked
  return false;
}


bool crc32_lock_lba(struct nvme_request* req)
{
  struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(req->qpair->ctrlr, req->cmd.nsid);

  if (ns == NULL || req->qpair == req->qpair->ctrlr->adminq)
  {
    return true;
  }

  // check lockers for each LBA
  if (req->cmd.opc == 1 ||   //write
      req->cmd.opc == 2 ||   //read
      req->cmd.opc == 4 ||   //write uncorrectable
      req->cmd.opc == 5 ||   //compare
      req->cmd.opc == 8)     //write zeroes
  {
    bool locked;

    locked = crc32_check_lock_bits(ns, ns->crc_table,
                                   *(uint64_t*)&req->cmd.cdw10,
                                   (uint16_t)req->cmd.cdw12+1);
    if (locked == false)
    {
      // lock each LBA
      crc32_set_lock_bits(ns, ns->crc_table,
                          *(uint64_t*)&req->cmd.cdw10,
                          (uint16_t)req->cmd.cdw12+1,
                          true);

      // locked LBA successfully
      return true;
    }
  }
  else if (req->cmd.opc == 9)      //dsm
  {
    void* buf = req->payload.contig_or_cb_arg;
    struct spdk_nvme_dsm_range *ranges = (struct spdk_nvme_dsm_range*)buf;
    unsigned int count = (uint8_t)req->cmd.cdw10+1;
    bool locked = true;

    for (unsigned int i=0; i<count; i++)
    {
      locked = crc32_check_lock_bits(ns, ns->crc_table,
                                     ranges[i].starting_lba,
                                     ranges[i].length);
      if (locked == true)
      {
        //lba is already lock by others
        break;
      }
    }

    if (locked == false)
    {
      // no lba is locked, so locked all of them
      for (unsigned int i=0; i<count; i++)
      {
        // lock each LBA
        crc32_set_lock_bits(ns, ns->crc_table,
                            ranges[i].starting_lba,
                            ranges[i].length,
                            true);
      }

      // locked LBA successfully
      return true;
    }
  }
  else
  {
    // other no data command like flush
    return true;
  }

  // cannot lock all LBA
  return false;
}


void crc32_unlock_lba(struct nvme_request* req)
{
  struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(req->qpair->ctrlr, req->cmd.nsid);

  if (ns == NULL || req->qpair == req->qpair->ctrlr->adminq)
  {
    return;
  }

  // check lockers for each LBA
  if (req->cmd.opc == 1 ||   //write
      req->cmd.opc == 2 ||   //read
      req->cmd.opc == 4 ||   //write uncorrectable
      req->cmd.opc == 5 ||   //compare
      req->cmd.opc == 8)     //write zeroes
  {
    // unlock each LBA
    crc32_set_lock_bits(ns, ns->crc_table,
                        *(uint64_t*)&req->cmd.cdw10,
                        (uint16_t)req->cmd.cdw12+1,
                        false);
  }
  else if (req->cmd.opc == 9)      //dsm
  {
    void* buf = req->payload.contig_or_cb_arg;
    struct spdk_nvme_dsm_range *ranges = (struct spdk_nvme_dsm_range*)buf;
    unsigned int count = (uint8_t)req->cmd.cdw10+1;

    for (unsigned int i=0; i<count; i++)
    {
      // unlock each LBA
      crc32_set_lock_bits(ns, ns->crc_table,
                          ranges[i].starting_lba,
                          ranges[i].length,
                          false);
    }
  }
  else
  {
    // other no data command like flush
  }
}


void crc32_unlock_all(struct spdk_nvme_ctrlr* ctrlr)
{
  for (uint32_t nsid = 1; nsid <= ctrlr->num_ns; nsid++)
  {
    struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(ctrlr, nsid);

    crc32_set_lock_bits(ns, ns->crc_table,
                        0,
                        ns->table_size/sizeof(uint32_t),
                        false);
  }
}


uint64_t crc32_skip_uncorr(struct spdk_nvme_ns* ns, uint64_t slba, uint32_t nlba)
{
  crc_table_t* crc_table = (crc_table_t*)ns->crc_table;

  if (crc_table != NULL && slba*sizeof(uint32_t) < ns->table_size)
  {
    // TODO: check nlba
    while (crc_table->data[slba] == 0x7fffffff) {
      slba ++;
    }
  }
  
  return slba;
}


////cmd log
///////////////////////////////

struct cmd_log_entry_t {
  // cmd and cpl
  struct spdk_nvme_cmd cmd;
  struct timeval time_cmd;
  struct spdk_nvme_cpl cpl;
  uint32_t cpl_latency_us;
  bool overlap_allocated;

  // for data verification after read
  void* buf;

  // callback to user cb functions
  struct nvme_request* req;
  void* cb_arg;
};
static_assert(sizeof(struct cmd_log_entry_t) == 128, "cacheline aligned");

struct cmd_log_table_t {
  struct cmd_log_entry_t table[CMD_LOG_DEPTH];
  uint32_t head_index;
  uint32_t tail_index;
  uint32_t latest_latency_us;
  uint16_t latest_cid;
  uint16_t intr_vec;
  uint16_t intr_enabled;
  uint16_t dummy[53];
};
static_assert(sizeof(struct cmd_log_table_t)%64 == 0, "cacheline aligned");

static void _cmdlog_uname(struct spdk_nvme_qpair* q, char* name, uint32_t len)
{
  assert(q != NULL);
  snprintf(name, len, "cmdlog_table_%s_%d_%d_%s",
           q->ctrlr->trid.traddr, q->id, getpid(), q->ctrlr->trid.subnqn);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "cmdlog name: %s\n", name);
}


void cmdlog_init(struct spdk_nvme_qpair* q)
{
  char cmdlog_name[64];

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "cmdlog init: %p\n", q);
  _cmdlog_uname(q, cmdlog_name, sizeof(cmdlog_name));
  assert(q->pynvme_cmdlog == NULL);
  q->pynvme_cmdlog = spdk_memzone_reserve(cmdlog_name,
                                          sizeof(struct cmd_log_table_t),
                                          0,
                                          SPDK_MEMZONE_NO_IOVA_CONTIG);
  assert(q->pynvme_cmdlog != NULL);  // may not close qpair in the script
}


void cmdlog_free(struct spdk_nvme_qpair* q)
{
  char cmdlog_name[64];

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "cmdlog free: %p\n", q);
  _cmdlog_uname(q, cmdlog_name, sizeof(cmdlog_name));
  spdk_memzone_free(cmdlog_name);
  q->pynvme_cmdlog = NULL;
}


static void cmdlog_update_crc_admin(struct spdk_nvme_cmd* cmd,
                                    struct spdk_nvme_ctrlr* ctrlr)
{
  if (cmd->opc == 0x80)
  {
    // format
    // crc table is cleared in ns_refresh, because the lba format may be changed
  }
  else if (cmd->opc == 0x84)
  {
    // sanitize: clear all ns
    for (uint32_t nsid = 1; nsid <= ctrlr->num_ns; nsid++)
    {
      struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(ctrlr, nsid);
      crc32_clear(ns, 0, ns->table_size, false);
    }
  }
}


static void cmdlog_update_crc_io(struct spdk_nvme_cmd* cmd,
                                 struct spdk_nvme_ns* ns,
                                 void* buf)
{
  uint64_t lba = cmd->cdw10 + ((uint64_t)(cmd->cdw11)<<32);
  uint16_t lba_count = (cmd->cdw12 & 0xffff) + 1;
  uint32_t lba_size = spdk_nvme_ns_get_sector_size(ns);
  crc_table_t* crc_table = (crc_table_t*)ns->crc_table;

  // update write data
  if (crc_table != NULL)
  {
    switch (cmd->opc)
    {
      case 1:
        // command write
        assert(buf != NULL);
        buffer_update_crc(ns, crc_table->data, buf, lba, lba_count, lba_size);
        break;

      case 4:
        //write uncorrectable
        crc32_clear(ns, lba, lba_count*sizeof(uint32_t), true);
        break;

      case 8:
        //write zerores
        crc32_clear(ns, lba, lba_count*sizeof(uint32_t), false);
        break;

      case 9:
        //dsm
        assert(buf != NULL);
        crc32_clear_ranges(ns, buf, (cmd->cdw10&0xff)+1);
        break;

      default:
        break;
    }
  }
}


static void cmdlog_update_crc(struct cmd_log_entry_t* log_entry)
{
  struct spdk_nvme_cmd* cmd = &log_entry->cmd;
  struct spdk_nvme_ctrlr* ctrlr = log_entry->req->qpair->ctrlr;

  // admin queue
  if (log_entry->req->qpair->id == 0)
  {
    cmdlog_update_crc_admin(cmd, ctrlr);
  }
  else
  {
    // io queue
    struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(ctrlr, cmd->nsid);

    assert(ns != NULL);
    cmdlog_update_crc_io(cmd, ns, log_entry->buf);
  }
}


static int cmdlog_verify_crc(struct cmd_log_entry_t* log_entry)
{
  int ret = 0;
  struct spdk_nvme_cmd* cmd = &log_entry->cmd;
  struct spdk_nvme_ctrlr* ctrlr = log_entry->req->qpair->ctrlr;

  // read command
  if (log_entry->req->qpair->id != 0 && log_entry->cmd.opc == 2)
  {
    struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(ctrlr, cmd->nsid);
    uint64_t lba = cmd->cdw10 + ((uint64_t)(cmd->cdw11)<<32);
    uint16_t lba_count = (cmd->cdw12 & 0xffff) + 1;
    uint32_t lba_size = spdk_nvme_ns_get_sector_size(ns);
    crc_table_t* crc_table = (crc_table_t*)ns->crc_table;

    assert(ns != NULL);
    assert(log_entry->buf != NULL);

    // data verify is enabled
    if (crc_table && crc_table->enabled)
    {
      // verify lba
      ret = buffer_verify_lba(log_entry->buf, lba, lba_count, lba_size);
      if (ret == 0)
      {
        //verify data pattern and crc
        ret = buffer_verify_data(ns, log_entry->buf, lba, lba_count, lba_size);
      }
      else
      {
        // lba wrong, verify crc with expected lba, instead of given lba
        uint64_t expected_lba = *(uint64_t*)(log_entry->buf);
        ret = buffer_verify_data(ns, log_entry->buf, expected_lba, lba_count, lba_size);
        if (ret == 0)
        {
          // crc ok, so it is a real lba mismatch, mapping error
          SPDK_WARNLOG("lba mismatch: lba 0x%lx, but got: 0x%lx\n", lba, expected_lba);
          ret = -2;
        }
      }
    }
  }

  return ret;
}


void cmdlog_cmd_cpl(struct nvme_request* req, struct spdk_nvme_cpl* cpl)
{
  struct timeval diff;
  struct timeval now;
  struct cmd_log_entry_t* log_entry = req->cmdlog_entry;
  struct cmd_log_table_t* cmdlog = req->qpair->pynvme_cmdlog;

  if (log_entry == NULL)
  {
    return;
  }

  assert(cpl != NULL);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "cmd completed, cid %d\n", log_entry->cpl.cid);

  //check if the log entry is still for this completed cmd
  if (log_entry->req == NULL || log_entry->req != req)
  {
    //it's an overlapped entry, just skip cmdlog callback
    SPDK_NOTICELOG("skip overlapped cmdlog entry %p, cmd %s\n",
                   log_entry, cmd_name(req->cmd.opc, req->qpair->id==0?0:1));
    assert(false);
    return;
  }

  timeval_gettimeofday(&now);
  memcpy(&log_entry->cpl, cpl, sizeof(struct spdk_nvme_cpl));
  timersub(&now, &log_entry->time_cmd, &diff);
  log_entry->cpl_latency_us = timeval_to_us(&diff);
  cmdlog->latest_latency_us = log_entry->cpl_latency_us;

  //update crc table when command completes successfully, except for write uncorrectable
  if ((cpl->status.sc == 0 && cpl->status.sct == 0) ||
      (log_entry->cmd.opc == 4))
  {
    // write-like commnds
    cmdlog_update_crc(log_entry);

    // read commands: verify data
    if (0 != cmdlog_verify_crc(log_entry))
    {
      //verify data wrong
      assert(log_entry->req);

      //Unrecovered Read Error: The read data could not be recovered from the media.
      SPDK_NOTICELOG("original cpl:\n");
      spdk_nvme_qpair_print_completion(log_entry->req->qpair, cpl);
      cpl->status.sct = 0x07;  // change to vendor specific unrecovered read error
      cpl->status.sc = 0x81;
    }
  }

  //recover callback argument
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "recover req %p cb arg, entry %p, old %p, new %p\n",
                log_entry->req, log_entry, log_entry->req->cb_arg, log_entry->cb_arg);
  log_entry->req = NULL;
  req->cmdlog_entry = NULL;

  //free the allocated log entry in request
  if (log_entry->overlap_allocated)
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "free overlapped cmdlog entry %p, cmd %s\n",
                  log_entry, cmd_name(req->cmd.opc, req->qpair->id==0?0:1));
    spdk_dma_free(log_entry);
  }
}


// for spdk internel ues: nvme_qpair_submit_request
void cmdlog_add_cmd(struct spdk_nvme_qpair* qpair, struct nvme_request* req)
{
  struct cmd_log_table_t* log_table = qpair->pynvme_cmdlog;
  assert(log_table != NULL);
  uint32_t head_index = log_table->head_index;
  uint32_t tail_index = log_table->tail_index;
  struct cmd_log_entry_t* log_entry = &log_table->table[tail_index];

  assert(req != NULL);
  assert(tail_index < CMD_LOG_DEPTH);

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "cmdlog: add cmd %s\n",
                cmd_name(req->cmd.opc, qpair->id==0?0:1));

  // keep the latest cid for inqury by scripts later
  log_table->latest_cid = req->cmd.cid;

  if (log_entry->req != NULL)
  {
    // this entry is overlapped before command complete
    // keep cmdlog_entry in request
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "overlapped cmd in cmdlog: %p\n", log_entry);
    log_entry->req->cmdlog_entry = spdk_dma_zmalloc(sizeof(*log_entry), 64, NULL);
    log_entry->overlap_allocated = true;
    memcpy(log_entry->req->cmdlog_entry, log_entry, sizeof(*log_entry));
  }

  log_entry->overlap_allocated = false;
  log_entry->buf = req->payload.contig_or_cb_arg;
  log_entry->cpl_latency_us = 0;
  memcpy(&log_entry->cmd, &req->cmd, sizeof(struct spdk_nvme_cmd));
  timeval_gettimeofday(&log_entry->time_cmd);

  // link req and cmdlog entry
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "save req %p cb arg to entry %p, new %p, old %p\n",
                req, log_entry, req->cb_arg, log_entry->cb_arg);
  log_entry->req = req;
  req->cmdlog_entry = log_entry;

  // inc tail to commit the new cmd only when it is sent successfully
  tail_index += 1;
  if (tail_index == CMD_LOG_DEPTH)
  {
    tail_index = 0;
  }
  log_table->tail_index = tail_index;

  // inc head to remove the old one
  if (head_index == tail_index)
  {
    head_index += 1;
    if (head_index == CMD_LOG_DEPTH)
    {
      head_index = 0;
      log_table->head_index = head_index;
    }
  }
}

//// probe callbacks
///////////////////////////////

struct cb_ctx {
  struct spdk_nvme_transport_id* trid;
  struct spdk_nvme_ctrlr* ctrlr;
};

static bool probe_cb(void *cb_ctx,
                     const struct spdk_nvme_transport_id *trid,
                     struct spdk_nvme_ctrlr_opts *opts)
{
  if (trid->trtype == SPDK_NVME_TRANSPORT_PCIE)
  {
    struct spdk_nvme_transport_id* target = ((struct cb_ctx*)cb_ctx)->trid;
    if (0 != spdk_nvme_transport_id_compare(target, trid))
    {
      SPDK_ERRLOG("Wrong address %s\n", trid->traddr);
      return false;
    }

    opts->use_cmb_sqs = false;
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "attaching to pcie device: %s\n",
                 trid->traddr);
  }
  else
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "attaching to NVMe over Fabrics controller at %s:%s: %s\n",
                 trid->traddr, trid->trsvcid, trid->subnqn);
  }

  /* Set io_queue_size to UINT16_MAX, NVMe driver
   * will then reduce this to MQES to maximize
   * the io_queue_size as much as possible.
   */
  opts->io_queue_size = UINT16_MAX;

  /* Set the header and data_digest */
  opts->header_digest = false;
  opts->data_digest = false;

  // disable keep alive function in controller side
  opts->keep_alive_timeout_ms = 0;

  // not send shnnotification by defaut, leave it to users scripts
  opts->no_shn_notification = true;

  return true;
}


static void attach_cb(void *cb_ctx,
                      const struct spdk_nvme_transport_id *trid,
                      struct spdk_nvme_ctrlr *ctrlr,
                      const struct spdk_nvme_ctrlr_opts *opts)
{
  ((struct cb_ctx*)cb_ctx)->ctrlr = ctrlr;
}


////module: pcie ctrlr
///////////////////////////////

struct spdk_pci_device* pcie_init(struct spdk_nvme_ctrlr* ctrlr)
{
  assert(ctrlr->trid.trtype == SPDK_NVME_TRANSPORT_PCIE);
  return spdk_nvme_ctrlr_get_pci_device(ctrlr);
}

int pcie_cfg_read8(struct spdk_pci_device* pci,
                   unsigned char* value,
                   unsigned int offset)
{
  return spdk_pci_device_cfg_read8(pci, value, offset);
}

int pcie_cfg_write8(struct spdk_pci_device* pci,
                    unsigned char value,
                    unsigned int offset)
{
  return spdk_pci_device_cfg_write8(pci, value, offset);
}


////module: nvme ctrlr
///////////////////////////////

struct ctrlr_entry {
  struct spdk_nvme_ctrlr  *ctrlr;
  STAILQ_ENTRY(ctrlr_entry) next;
};

STAILQ_HEAD(, ctrlr_entry) g_controllers = STAILQ_HEAD_INITIALIZER(g_controllers);

static struct spdk_nvme_ctrlr* nvme_probe(char* traddr, unsigned int port)
{
  struct spdk_nvme_transport_id trid;
  struct cb_ctx cb_ctx;
  int rc;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "looking for NVMe @%s\n", traddr);

  // device address
  memset(&trid, 0, sizeof(trid));
  if (port != 0)
  {
    // ip address: fixed port to 4420
    trid.trtype = SPDK_NVME_TRANSPORT_TCP;
    trid.adrfam = SPDK_NVMF_ADRFAM_IPV4;
    strncpy(trid.traddr, traddr, SPDK_NVMF_TRADDR_MAX_LEN);
    snprintf(trid.trsvcid, sizeof(trid.trsvcid), "%d", port);
    snprintf(trid.subnqn, sizeof(trid.subnqn), "%s", SPDK_NVMF_DISCOVERY_NQN);
  }
  else
  {
    // pcie address: contains ':' characters
    trid.trtype = SPDK_NVME_TRANSPORT_PCIE;
    strncpy(trid.traddr, traddr, SPDK_NVMF_TRADDR_MAX_LEN);
  }

  cb_ctx.trid = &trid;
  cb_ctx.ctrlr = NULL;
  rc = spdk_nvme_probe(&trid, &cb_ctx, probe_cb, attach_cb, NULL);
  if (rc != 0 || cb_ctx.ctrlr == NULL)
  {
    SPDK_WARNLOG("not found device: %s, rc %d, cb_ctx.ctrlr %p\n",
                 trid.traddr, rc, cb_ctx.ctrlr);
    return NULL;
  }

  return cb_ctx.ctrlr;
}

struct spdk_nvme_ctrlr* nvme_init(char * traddr, unsigned int port)
{
  struct spdk_nvme_ctrlr* ctrlr;

  //enum the device
  ctrlr = nvme_probe(traddr, port);
  if (ctrlr == NULL)
  {
    return NULL;
  }

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "found device: %s, %p\n",
                ctrlr->trid.traddr, ctrlr);

  if (true != spdk_process_is_primary())
  {
    // init intc table in secondary processes for PCIe SSD
    if (ctrlr->trid.trtype == SPDK_NVME_TRANSPORT_PCIE)
    {
      ctrlr->pynvme_intc_ctrl = intc_lookup_ctrl(ctrlr);
      assert(ctrlr->pynvme_intc_ctrl != NULL);
    }
  }

  if (spdk_process_is_primary())
  {
    // add new ctrlr
    struct ctrlr_entry* e = malloc(sizeof(struct ctrlr_entry));
    assert(e);
    e->ctrlr = ctrlr;
    spdk_nvme_ctrlr_register_aer_callback(ctrlr, NULL, NULL);
    STAILQ_INSERT_TAIL(&g_controllers, e, next);
  }

  return ctrlr;
}

int nvme_fini(struct spdk_nvme_ctrlr* ctrlr)
{
  assert(ctrlr != NULL);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "free ctrlr: %s\n", ctrlr->trid.traddr);

  if (spdk_process_is_primary())
  {
    // io qpairs should all be deleted before closing master controller
    struct spdk_nvme_qpair  *qpair;
    TAILQ_FOREACH(qpair, &ctrlr->active_io_qpairs, tailq)
    {
      qpair_free(qpair);
    }

    //remove ctrlr from list
    struct ctrlr_entry* e;
    struct ctrlr_entry* tmp;
    STAILQ_FOREACH_SAFE(e, &g_controllers, next, tmp)
    {
      if (e->ctrlr == ctrlr)
      {
        STAILQ_REMOVE(&g_controllers, e, ctrlr_entry, next);
        free(e);
        break;
      }
    }
  }

  return spdk_nvme_detach(ctrlr);
}

void nvme_bar_recover(struct spdk_nvme_ctrlr* ctrlr)
{
  nvme_pcie_bar_remap_recover(ctrlr);
}

void nvme_bar_remap(struct spdk_nvme_ctrlr* ctrlr)
{
  int ret = nvme_pcie_bar_remap(ctrlr);
  assert(ret == 0);
}

int nvme_set_reg32(struct spdk_nvme_ctrlr* ctrlr,
                   unsigned int offset,
                   unsigned int value)
{
  return nvme_transport_ctrlr_set_reg_4(ctrlr, offset, value);
}

int nvme_get_reg32(struct spdk_nvme_ctrlr* ctrlr,
                   unsigned int offset,
                   unsigned int* value)
{
  return nvme_transport_ctrlr_get_reg_4(ctrlr, offset, value);
}

int nvme_set_reg64(struct spdk_nvme_ctrlr* ctrlr,
                   unsigned int offset,
                   unsigned long value)
{
  return nvme_transport_ctrlr_set_reg_8(ctrlr, offset, value);
}

int nvme_get_reg64(struct spdk_nvme_ctrlr* ctrlr,
                   unsigned int offset,
                   unsigned long* value)
{
  return nvme_transport_ctrlr_get_reg_8(ctrlr, offset, value);
}

int nvme_set_adminq(struct spdk_nvme_ctrlr *ctrlr)
{
  int rc;

  rc = nvme_pcie_ctrlr_enable(ctrlr);
  if (rc == 0)
  {
    rc = nvme_pcie_qpair_reset(ctrlr->adminq);
  }

  return rc;
}


int nvme_wait_completion_admin(struct spdk_nvme_ctrlr* ctrlr)
{
  int32_t rc;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;
  struct cmd_log_table_t* cmdlog = ctrlr->adminq->pynvme_cmdlog;

  // check msix interrupt
  if (cmdlog->intr_enabled)
  {
    if (intr_ctrl->msg_data[0] == 0)
    {
      // to check it again later
      return 0;
    }

    // mask the interrupt
    intc_mask(ctrlr->adminq);
  }

  // process all the completions
  rc = spdk_nvme_ctrlr_process_admin_completions(ctrlr);

  // clear and un-mask the interrupt
  if (cmdlog->intr_enabled)
  {
    intr_ctrl->msg_data[0] = 0;
    intc_unmask(ctrlr->adminq);
  }

  return rc;
}


int nvme_send_cmd_raw(struct spdk_nvme_ctrlr* ctrlr,
                      struct spdk_nvme_qpair *qpair,
                      unsigned int cdw0,
                      unsigned int nsid,
                      void* buf, size_t len,
                      unsigned int cdw10,
                      unsigned int cdw11,
                      unsigned int cdw12,
                      unsigned int cdw13,
                      unsigned int cdw14,
                      unsigned int cdw15,
                      spdk_nvme_cmd_cb cb_fn,
                      void* cb_arg)
{
  int rc = 0;
  struct spdk_nvme_cmd cmd;

  assert(ctrlr != NULL);

  //setup cmd structure
  memset(&cmd, 0, sizeof(struct spdk_nvme_cmd));
  *(unsigned int*)&cmd = cdw0;
  cmd.nsid = nsid;
  cmd.cdw10 = cdw10;
  cmd.cdw11 = cdw11;
  cmd.cdw12 = cdw12;
  cmd.cdw13 = cdw13;
  cmd.cdw14 = cdw14;
  cmd.cdw15 = cdw15;

  if (qpair)
  {
    //send io cmd in qpair
    rc = spdk_nvme_ctrlr_cmd_io_raw(ctrlr, qpair, &cmd, buf, len, cb_fn, cb_arg);
  }
  else
  {
    //not qpair, admin cmd
    rc = spdk_nvme_ctrlr_cmd_admin_raw(ctrlr, &cmd, buf, len, cb_fn, cb_arg);
  }

  return rc;
}

void nvme_register_timeout_cb(struct spdk_nvme_ctrlr* ctrlr,
                              spdk_nvme_timeout_cb timeout_cb,
                              unsigned int msec)
{
  spdk_nvme_ctrlr_register_timeout_callback(
      ctrlr, (uint64_t)msec*1000ULL, timeout_cb, NULL);
}

int nvme_cpl_is_error(const struct spdk_nvme_cpl* cpl)
{
  return spdk_nvme_cpl_is_error(cpl);
}


struct spdk_nvme_ns* nvme_get_ns(struct spdk_nvme_ctrlr* ctrlr,
                                 uint32_t nsid)
{
  return spdk_nvme_ctrlr_get_ns(ctrlr, nsid);
}

////module: qpair
///////////////////////////////

struct spdk_nvme_qpair *qpair_create(struct spdk_nvme_ctrlr* ctrlr,
                                     unsigned int prio,
                                     unsigned int depth,
                                     bool ien,
                                     unsigned short iv)
{
  struct spdk_nvme_qpair* qpair;
  struct spdk_nvme_io_qpair_opts opts;

  //user options
  memset(&opts, 0, sizeof(opts));
  opts.qprio = prio;
  opts.io_queue_size = depth;
  opts.io_queue_requests = depth;
  opts.delay_pcie_doorbell = false;
  opts.intr_enable = ien;
  opts.intr_vector = iv;
  
  qpair = spdk_nvme_ctrlr_alloc_io_qpair(ctrlr, &opts, sizeof(opts));
  if (qpair == NULL)
  {
    SPDK_WARNLOG("alloc io qpair fail\n");
    return NULL;
  }

  // no need to abort commands in test
  qpair->no_deletion_notification_needed = 1;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "created qpair %d\n", qpair->id);
  return qpair;
}

int qpair_wait_completion(struct spdk_nvme_qpair *qpair, uint32_t max_completions)
{
  int rc = 0;

  rc = spdk_nvme_qpair_process_completions(qpair, max_completions);

  // pynvme: retry one queued request for LBA confliction
  if (!STAILQ_EMPTY(&qpair->queued_req))
  {
    struct nvme_request *req = STAILQ_FIRST(&qpair->queued_req);
    STAILQ_REMOVE_HEAD(&qpair->queued_req, stailq);
    nvme_qpair_submit_request(qpair, req);
  }

  return rc;
}

int qpair_get_id(struct spdk_nvme_qpair* q)
{
  // q NULL is admin queue
  return q ? q->id : 0;
}

uint16_t qpair_get_latest_cid(struct spdk_nvme_qpair* q,
                              struct spdk_nvme_ctrlr* c)
{
  struct cmd_log_table_t* log_table;

  if (q == NULL)
  {
    q = c->adminq;
  }

  assert(q != NULL);
  assert(q->ctrlr == c);
  log_table = q->pynvme_cmdlog;
  return log_table->latest_cid;
}

uint32_t qpair_get_latest_latency(struct spdk_nvme_qpair* q,
                                  struct spdk_nvme_ctrlr* c)
{
  struct cmd_log_table_t* log_table;

  if (q == NULL)
  {
    q = c->adminq;
  }

  assert(q != NULL);
  assert(q->ctrlr == c);
  log_table = q->pynvme_cmdlog;
  return log_table->latest_latency_us;
}

int qpair_free(struct spdk_nvme_qpair* q)
{
  assert(q != NULL);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "free qpair: %d\n", q->id);
  return spdk_nvme_ctrlr_free_io_qpair(q);
}


////module: namespace
///////////////////////////////

static void _ns_uname(struct spdk_nvme_ns* ns, char* name, uint32_t len)
{
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "ns %p\n", ns);
  uint64_t uid = spdk_nvme_ns_get_data(ns)->eui64;
  snprintf(name, len, "ns_crc32_table_%s_%d_%lx",
           ns->ctrlr->trid.traddr, ns->id, uid);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "crc table name: %s\n", name);
}


static int ns_table_init(struct spdk_nvme_ns* ns, uint64_t table_size)
{
  crc_table_t* crc_table = (crc_table_t*)ns->crc_table;
  char memzone_name[64];
  _ns_uname(ns, memzone_name, sizeof(memzone_name));

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "crc table init, ns %p, size: %ld\n",
                ns, table_size);

  if (spdk_process_is_primary())
  {
    assert(crc_table == NULL);

    // get the shared memory for crc table, and the verify enabled flag
    crc_table = spdk_memzone_reserve(memzone_name,
                                     table_size+sizeof(crc_table_t),
                                     0,
                                     SPDK_MEMZONE_NO_IOVA_CONTIG);
    if (crc_table == NULL)
    {
      SPDK_NOTICELOG("memory is not large enough to keep CRC32 table.\n");
      SPDK_NOTICELOG("Data verification is disabled!\n");
    }
  }
  else
  {
    // find the shared memory for token
    crc_table = spdk_memzone_lookup(memzone_name);
    if (crc_table == NULL)
    {
      SPDK_NOTICELOG("cannot find the crc_table in secondary process!\n");
    }
  }

  if (crc_table != NULL)
  {
    assert(crc_table->data);
    crc_table->size = table_size;
    ns->table_size = table_size;

    g_driver_crc32_memory_enough = true;  // obsoloted
  }

  ns->crc_table = (void*)crc_table;

  return 0;
}


static void ns_table_fini(struct spdk_nvme_ns* ns)
{
  char memzone_name[64];
  _ns_uname(ns, memzone_name, sizeof(memzone_name));

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "crc table fini, ns %p\n", ns);

  if (spdk_process_is_primary())
  {
    // update crc because namespace may changed after controller reset
    ns->crc_table = spdk_memzone_lookup(memzone_name);
    if (ns->crc_table != NULL)
    {
      spdk_memzone_free(memzone_name);
      ns->crc_table = NULL;
    }
  }
}


struct spdk_nvme_ns* ns_init(struct spdk_nvme_ctrlr* ctrlr,
                             uint32_t nsid,
                             uint64_t nlba_verify)
{
  struct spdk_nvme_ns* ns = spdk_nvme_ctrlr_get_ns(ctrlr, nsid);

  assert(ctrlr != NULL);
  assert(nsid > 0);
  assert(ns != NULL);

  uint64_t nsze = spdk_nvme_ns_get_num_sectors(ns);
  if (nlba_verify > 0)
  {
    // limit verify area to save memory usage
    nsze = MIN(nsze, nlba_verify);
  }

  if (0 != ns_table_init(ns, sizeof(uint32_t)*nsze))
  {
    return NULL;
  }

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "ctrlr %p, nsid %d, ns %p, crc table %p\n",
                ctrlr, nsid, ns, ns->crc_table);
  return ns;
}


int ns_refresh(struct spdk_nvme_ns *ns, uint32_t id,
               struct spdk_nvme_ctrlr *ctrlr)
{
  int ret = 0;
  crc_table_t* crc_table = (crc_table_t*)ns->crc_table;

  if (crc_table != NULL)
  {
    assert(ns->table_size != 0);
    uint32_t enabled = crc_table->enabled;

    ns_table_fini(ns);
    nvme_ns_construct(ns, id, ctrlr);
    ret = ns_table_init(ns, ns->table_size);
    if (ret == 0)
    {
      // keep the same enabled flag
      crc_table = (crc_table_t*)ns->crc_table;
      assert(crc_table);
      crc_table->enabled = enabled;
      crc32_clear(ns, 0, ns->table_size, false);
    }
  }

  return ret;
}


bool ns_verify_enable(struct spdk_nvme_ns* ns, bool enable)
{
  crc_table_t* crc_table = (crc_table_t*)ns->crc_table;

  SPDK_INFOLOG(SPDK_LOG_NVME, "enable inline data verify: %d\n", enable);

  if (crc_table != NULL)
  {
    // crc is created, so verify is possible
    crc_table->enabled = enable;
    return true;
  }

  return false;
}


int nvme_set_ns(struct spdk_nvme_ctrlr *ctrlr)
{
  int rc;
  uint32_t nn = ctrlr->cdata.nn;

  // pynvme: test device has no namespace, something wrong
  if (nn == 0) {
    SPDK_ERRLOG("controller has no namespace\n");
    return -1;
  }

  rc = spdk_nvme_ctrlr_construct_namespaces(ctrlr);
  if (rc == 0)
  {
    // init each namepace
    for (uint32_t i=0; i<nn; i++)
    {
      crc_table_t* crc_table;
      struct spdk_nvme_ns* ns = &ctrlr->ns[i];

      assert(ns != NULL);
      nvme_ns_construct(ns, i+1, ctrlr);

      // init pynvme data in namespace
      char memzone_name[64];
      _ns_uname(ns, memzone_name, sizeof(memzone_name));
      crc_table = spdk_memzone_lookup(memzone_name);
      if (crc_table)
      {
        ns->table_size = crc_table->size;
        ns->crc_table = (void*)crc_table;
      }

      SPDK_DEBUGLOG(SPDK_LOG_NVME, "init namespace %d, crc table %p\n",
                    i+1, ns->crc_table);
    }
  }

  return rc;
}


int ns_cmd_io(uint8_t opcode,
              struct spdk_nvme_ns* ns,
              struct spdk_nvme_qpair* qpair,
              void* buf,
              size_t len,
              uint64_t lba,
              uint32_t lba_count,
              uint32_t io_flags,
              spdk_nvme_cmd_cb cb_fn,
              void* cb_arg,
              unsigned int dword13,
              unsigned int dword14,
              unsigned int dword15)
{
  struct spdk_nvme_cmd cmd;
  uint32_t lba_size = spdk_nvme_ns_get_sector_size(ns);

  assert(qpair != NULL);

  //validate data buffer
  assert(buf != NULL);
  assert((io_flags&0xffff) == 0);
  // buffer is large enough to hold data
  assert(len >= lba_count*lba_size);

  // correct the buffer size
  len = MIN(len, lba_count*lba_size);

  //setup cmd structure
  memset(&cmd, 0, sizeof(struct spdk_nvme_cmd));
  cmd.opc = opcode;
  cmd.nsid = ns->id;
  cmd.cdw10 = lba;
  cmd.cdw11 = lba>>32;
  cmd.cdw12 = io_flags | (lba_count-1);
  cmd.cdw13 = dword13;
  cmd.cdw14 = dword14;
  cmd.cdw15 = dword15;

  if ((opcode&3) == 0)
  {
    // no data to transfer
    buf = NULL;
    len = 0;
  }

  if (opcode == 9)
  {
    // trim operation: only single range
    *(uint32_t*)(buf+4) = lba_count;
    *(uint64_t*)(buf+8) = lba;
    len = lba_size;
    cmd.cdw10 = 0;
    cmd.cdw11 = 4;
    cmd.cdw12 = 0;
  }

  //fill write buffer with lba, token, and checksum
  if (opcode == 1)
  {
    //for write buffer
    buffer_fill_rawdata(buf, lba, lba_count, lba_size);
  }

  qpair->pynvme_io_in_second ++;
  qpair->pynvme_lba_in_second += (lba_count*lba_size);

  //send io cmd in qpair
  return nvme_send_cmd_raw(ns->ctrlr, qpair, opcode,
                           ns->id, buf, len,
                           cmd.cdw10, cmd.cdw11, cmd.cdw12,
                           cmd.cdw13, cmd.cdw14, cmd.cdw15,
                           cb_fn, cb_arg);
}

uint32_t ns_get_sector_size(struct spdk_nvme_ns* ns)
{
  return spdk_nvme_ns_get_sector_size(ns);
}

uint64_t ns_get_num_sectors(struct spdk_nvme_ns* ns)
{
  return spdk_nvme_ns_get_num_sectors(ns);
}

int ns_fini(struct spdk_nvme_ns* ns)
{
  ns_table_fini(ns);
  return 0;
}


////module: log
///////////////////////////////

char* log_buf_dump(const char* header, const void* buf, size_t len, size_t base)
{
  size_t size;
  FILE* fd = NULL;
  char* tmpname = "/tmp/pynvme_buf_dump.tmp";
  static char dump_buf[64*1024];

  // dump buf is limited
  assert(len <= 4096);

  errno = 0;
  fd = fopen(tmpname, "w+");
  if (fd == NULL)
  {
    SPDK_WARNLOG("fopen: %s\n", strerror(errno));
    return NULL;
  }

  spdk_log_dump(fd, header, buf+base, len, base);

  // get file size
  size = ftell(fd);

  errno = 0;
  if (-1 == fseek(fd, 0, SEEK_SET))
  {
    SPDK_WARNLOG("lseek: %s\n", strerror(errno));
    return NULL;
  }

  // read the data from temporary file
  errno=0;
  if (fread(dump_buf, size, 1, fd) == 0)
  {
    SPDK_WARNLOG("read: %s\n", strerror(errno));
    return NULL;
  }

  fclose(fd);
  dump_buf[size] = '\0';
  return dump_buf;
}

void log_cmd_dump(struct spdk_nvme_qpair* qpair, size_t count)
{
  struct cmd_log_table_t* cmdlog = qpair->pynvme_cmdlog;
  struct cmd_log_entry_t* table = cmdlog->table;
  uint16_t qid = qpair->id;
  uint32_t dump_count = count;
  uint32_t seq = 0;
  uint32_t index;

  // print cmdlog from tail to head
  assert(cmdlog != NULL);
  assert(table != NULL);
  index = cmdlog->tail_index;

  if (count == 0 || count > CMD_LOG_DEPTH)
  {
    dump_count = CMD_LOG_DEPTH;
  }

  // cmdlog is NOT SQ/CQ. cmdlog keeps CMD/CPL for script test debug purpose
  SPDK_NOTICELOG("dump ctrlr %s, qpair %d, from %d to %d, count %d\n",
                 qpair->ctrlr->trid.traddr, qid,
                 index, cmdlog->head_index, dump_count);

  // only send the most recent part of cmdlog
  while (seq++ < dump_count)
  {
    // get the next index to read log
    if (index == 0)
    {
      index = CMD_LOG_DEPTH;
    }
    index -= 1;

    // no timeval, empty slot, not print
    struct timeval tv = table[index].time_cmd;
    if (timercmp(&tv, &(struct timeval){0}, >))
    {
      struct tm* time;
      char tmbuf[128];

      //cmd part
      tv = table[index].time_cmd;
      time = localtime(&tv.tv_sec);
      strftime(tmbuf, sizeof(tmbuf), "%Y-%m-%d %H:%M:%S", time);
      SPDK_NOTICELOG("index %d, %s.%06ld\n", index, tmbuf, tv.tv_usec);
      spdk_nvme_qpair_print_command(qpair, &table[index].cmd);

      //cpl part
      if (table[index].cpl_latency_us != 0)
      {
        // a completed command, display its cpl cdws
        struct timeval time_cpl = (struct timeval){0};
        time_cpl.tv_usec = table[index].cpl_latency_us;
        timeradd(&tv, &time_cpl, &time_cpl);

        //get the string of cpl date/time
        time = localtime(&time_cpl.tv_sec);
        strftime(tmbuf, sizeof(tmbuf), "%Y-%m-%d %H:%M:%S", time);
        SPDK_NOTICELOG("index %d, %s.%06ld\n", index, tmbuf, time_cpl.tv_usec);
        spdk_nvme_qpair_print_completion(qpair, &table[index].cpl);
      }
    }
  }
}

void log_cmd_dump_admin(struct spdk_nvme_ctrlr* ctrlr, size_t count)
{
  log_cmd_dump(ctrlr->adminq, count);
}


////module: commands name, SPDK
///////////////////////////////

static const char *
admin_opc_name(uint8_t opc)
{
  switch (opc) {
    case SPDK_NVME_OPC_DELETE_IO_SQ:
      return "Delete I/O Submission Queue";
    case SPDK_NVME_OPC_CREATE_IO_SQ:
      return "Create I/O Submission Queue";
    case SPDK_NVME_OPC_GET_LOG_PAGE:
      return "Get Log Page";
    case SPDK_NVME_OPC_DELETE_IO_CQ:
      return "Delete I/O Completion Queue";
    case SPDK_NVME_OPC_CREATE_IO_CQ:
      return "Create I/O Completion Queue";
    case SPDK_NVME_OPC_IDENTIFY:
      return "Identify";
    case SPDK_NVME_OPC_ABORT:
      return "Abort";
    case SPDK_NVME_OPC_SET_FEATURES:
      return "Set Features";
    case SPDK_NVME_OPC_GET_FEATURES:
      return "Get Features";
    case SPDK_NVME_OPC_ASYNC_EVENT_REQUEST:
      return "Asynchronous Event Request";
    case SPDK_NVME_OPC_NS_MANAGEMENT:
      return "Namespace Management";
    case SPDK_NVME_OPC_FIRMWARE_COMMIT:
      return "Firmware Commit";
    case SPDK_NVME_OPC_FIRMWARE_IMAGE_DOWNLOAD:
      return "Firmware Image Download";
    case SPDK_NVME_OPC_DEVICE_SELF_TEST:
      return "Device Self-test";
    case SPDK_NVME_OPC_NS_ATTACHMENT:
      return "Namespace Attachment";
    case SPDK_NVME_OPC_KEEP_ALIVE:
      return "Keep Alive";
    case SPDK_NVME_OPC_DIRECTIVE_SEND:
      return "Directive Send";
    case SPDK_NVME_OPC_DIRECTIVE_RECEIVE:
      return "Directive Receive";
    case SPDK_NVME_OPC_VIRTUALIZATION_MANAGEMENT:
      return "Virtualization Management";
    case SPDK_NVME_OPC_NVME_MI_SEND:
      return "NVMe-MI Send";
    case SPDK_NVME_OPC_NVME_MI_RECEIVE:
      return "NVMe-MI Receive";
    case SPDK_NVME_OPC_DOORBELL_BUFFER_CONFIG:
      return "Doorbell Buffer Config";
    case SPDK_NVME_OPC_FORMAT_NVM:
      return "Format NVM";
    case SPDK_NVME_OPC_SECURITY_SEND:
      return "Security Send";
    case SPDK_NVME_OPC_SECURITY_RECEIVE:
      return "Security Receive";
    case SPDK_NVME_OPC_SANITIZE:
      return "Sanitize";
    case SPDK_NVME_OPC_FABRIC:
      return "Fabrics Command";
    default:
      if (opc >= 0xC0) {
        return "Vendor specific";
      }
      return "Unknown";
  }
}

static const char *
io_opc_name(uint8_t opc)
{
  switch (opc) {
    case SPDK_NVME_OPC_FLUSH:
      return "Flush";
    case SPDK_NVME_OPC_WRITE:
      return "Write";
    case SPDK_NVME_OPC_READ:
      return "Read";
    case SPDK_NVME_OPC_WRITE_UNCORRECTABLE:
      return "Write Uncorrectable";
    case SPDK_NVME_OPC_COMPARE:
      return "Compare";
    case SPDK_NVME_OPC_WRITE_ZEROES:
      return "Write Zeroes";
    case SPDK_NVME_OPC_DATASET_MANAGEMENT:
      return "Dataset Management";
    case SPDK_NVME_OPC_RESERVATION_REGISTER:
      return "Reservation Register";
    case SPDK_NVME_OPC_RESERVATION_REPORT:
      return "Reservation Report";
    case SPDK_NVME_OPC_RESERVATION_ACQUIRE:
      return "Reservation Acquire";
    case SPDK_NVME_OPC_RESERVATION_RELEASE:
      return "Reservation Release";
    case SPDK_NVME_OPC_FABRIC:
      return "Fabrics Connect";
    case SPDK_NVME_OPC_ZONE_MANAGEMENT_SEND:
      return "Zone Management Send";
    case SPDK_NVME_OPC_ZONE_MANAGEMENT_RECEIVE:
      return "Zone Management Receive";
    case SPDK_NVME_OPC_ZONE_APPEND:
      return "Zone Management Append";
    default:
      if (opc >= 0x80) {
        return "Vendor specific";
      }
      return "Unknown command";
  }
}

const char* cmd_name(uint8_t opc, int set)
{
  if (set == 0)
  {
    return admin_opc_name(opc);
  }
  else if (set == 1)
  {
    return io_opc_name(opc);
  }
  else
  {
    return "Unknown command set";
  }
}


////rpc
///////////////////////////////

static void* rpc_server(void* args)
{
  int rc = 0;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "starting rpc server ...\n");

  // start the rpc
  rc = spdk_rpc_listen("/var/tmp/pynvme.sock");
  if (rc != 0)
  {
    SPDK_WARNLOG("rpc fail to get the sock \n");
    return NULL;
  }

  // pynvme run as root, but rpc client no need
  chmod("/var/tmp/pynvme.sock", 0777);

  spdk_rpc_set_state(SPDK_RPC_STARTUP);

  while(1)
  {
    spdk_rpc_accept();
    usleep(100000);
  }

  spdk_rpc_close();
}


static void rpc_list_qpair_content(struct spdk_json_write_ctx *w,
                                   struct spdk_nvme_qpair* q)
{
  uint32_t os = nvme_transport_qpair_outstanding_count(q);
  int8_t mn[SPDK_NVME_CTRLR_MN_LEN+1];

  strncpy(mn, q->ctrlr->cdata.mn, SPDK_NVME_CTRLR_MN_LEN);
  mn[SPDK_NVME_CTRLR_MN_LEN] = '\0';

  spdk_json_write_object_begin(w);

  spdk_json_write_named_string(w, "ctrlr", q->ctrlr->trid.traddr);
  spdk_json_write_named_uint32(w, "qid", q->id+1);  // 0 means octal
  spdk_json_write_named_uint32(w, "outstanding", MIN(os, 100));
  spdk_json_write_named_uint64(w, "qpair", (uint64_t)q);
  spdk_json_write_named_string(w, "model", mn);

  spdk_json_write_object_end(w);
}


static void
rpc_list_all_qpair(struct spdk_jsonrpc_request *request,
                   const struct spdk_json_val *params)
{
  struct spdk_json_write_ctx *w;

  w = spdk_jsonrpc_begin_result(request);
  if (w == NULL)
  {
    return;
  }

  spdk_json_write_array_begin(w);

  //find all inited nvme controllers
  struct ctrlr_entry* e;
  STAILQ_FOREACH(e, &g_controllers, next)
  {
    // admin qpair
    rpc_list_qpair_content(w, e->ctrlr->adminq);

    // io qpairs
    struct spdk_nvme_qpair  *q;
    TAILQ_FOREACH(q, &e->ctrlr->active_io_qpairs, tailq)
    {
      rpc_list_qpair_content(w, q);
    }
  }

  spdk_json_write_array_end(w);
  spdk_jsonrpc_end_result(request, w);
}
SPDK_RPC_REGISTER("list_all_qpair", rpc_list_all_qpair, SPDK_RPC_STARTUP | SPDK_RPC_RUNTIME)


static void
rpc_get_iostat(struct spdk_jsonrpc_request *request,
               const struct spdk_json_val *params)
{
  struct spdk_json_write_ctx *w;
  uint64_t iops = 0;
  uint64_t bw = 0;

  w = spdk_jsonrpc_begin_result(request);
  if (w == NULL)
  {
    return;
  }

  spdk_json_write_array_begin(w);

  // calculate performance of all io qpairs of all devices
  struct ctrlr_entry* e;
  STAILQ_FOREACH(e, &g_controllers, next)
  {
    // io qpairs
    struct spdk_nvme_qpair  *q;
    TAILQ_FOREACH(q, &e->ctrlr->active_io_qpairs, tailq)
    {
      iops += q->pynvme_io_in_second;
      bw += q->pynvme_lba_in_second;
      q->pynvme_io_in_second = 0;
      q->pynvme_lba_in_second = 0;
    }
  }

  // fill performance data
  spdk_json_write_uint64(w, bw);
  spdk_json_write_uint64(w, iops);

  spdk_json_write_array_end(w);
  spdk_jsonrpc_end_result(request, w);
}
SPDK_RPC_REGISTER("get_iostat", rpc_get_iostat, SPDK_RPC_STARTUP | SPDK_RPC_RUNTIME)


static void
rpc_get_cmdlog(struct spdk_jsonrpc_request *request,
               const struct spdk_json_val *params)
{
  size_t count;
  struct spdk_nvme_qpair* q;
  struct spdk_json_write_ctx *w;

  if (params == NULL)
  {
    SPDK_WARNLOG("no parameters\n");
    spdk_jsonrpc_send_error_response(request, SPDK_JSONRPC_ERROR_INVALID_PARAMS,
                                     "Invalid parameters");
    return;
  }

  if (spdk_json_decode_array(params, spdk_json_decode_uint64,
                             &q, 1, &count, sizeof(uint64_t)))
  {
    SPDK_WARNLOG("spdk_json_decode_object failed\n");
    spdk_jsonrpc_send_error_response(request, SPDK_JSONRPC_ERROR_INVALID_PARAMS,
                                     "Invalid parameters");
    return;
  }

  if (count != 1)
  {
    SPDK_WARNLOG("only 1 parameter required for qid\n");
    spdk_jsonrpc_send_error_response(request, SPDK_JSONRPC_ERROR_INVALID_PARAMS,
                                     "Invalid parameters");
    return;
  }

  assert(q);
  assert(q->ctrlr);
  assert(q->pynvme_cmdlog);

  w = spdk_jsonrpc_begin_result(request);
  if (w == NULL)
  {
    return;
  }

  // find the cmdlog
  struct cmd_log_table_t* cmdlog = q->pynvme_cmdlog;
  struct cmd_log_entry_t* table = cmdlog->table;
  uint32_t index = cmdlog->tail_index;
  uint32_t seq = 1;

  // list the cmdlog in reversed order
  spdk_json_write_array_begin(w);

  // only send the most recent part of cmdlog
  do
  {
    // get the next index to read log
    if (index == 0)
    {
      index = CMD_LOG_DEPTH;
    }
    index -= 1;

    // no timeval, empty slot, not print
    char tmbuf[128];
    struct tm* time;
    struct timeval time_cmd = table[index].time_cmd;
    if (timercmp(&time_cmd, &(struct timeval){0}, >))
    {
      // get the string of the op name
      const char* cmdname = cmd_name(table[index].cmd.opc, q->id==0?0:1);
      uint32_t* cmd = (uint32_t*)&table[index].cmd;

      //get the string of date/time
      time = localtime(&time_cmd.tv_sec);
      strftime(tmbuf, sizeof(tmbuf), "%Y-%m-%d %H:%M:%S", time);

      spdk_json_write_string_fmt(w, "%s.%06ld [cmd%03d: %s]\n"
                                 "0x%08x, 0x%08x, 0x%08x, 0x%08x\n"
                                 "0x%08x, 0x%08x, 0x%08x, 0x%08x\n"
                                 "0x%08x, 0x%08x, 0x%08x, 0x%08x\n"
                                 "0x%08x, 0x%08x, 0x%08x, 0x%08x",
                                 tmbuf, time_cmd.tv_usec,
                                 seq, cmdname,
                                 cmd[0], cmd[1], cmd[2], cmd[3],
                                 cmd[4], cmd[5], cmd[6], cmd[7],
                                 cmd[8], cmd[9], cmd[10], cmd[11],
                                 cmd[12], cmd[13], cmd[14], cmd[15]);

      if (table[index].cpl_latency_us != 0)
      {
        // a completed command, display its cpl cdws
        struct timeval time_cpl = (struct timeval){0};
        time_cpl.tv_sec = table[index].cpl_latency_us/US_PER_S;
        time_cpl.tv_usec = table[index].cpl_latency_us%US_PER_S;
        timeradd(&time_cmd, &time_cpl, &time_cpl);

        //get the string of cpl date/time
        time = localtime(&time_cpl.tv_sec);
        strftime(tmbuf, sizeof(tmbuf), "%Y-%m-%d %H:%M:%S", time);

        uint32_t* cpl = (uint32_t*)&table[index].cpl;
        const char* sts = nvme_qpair_get_status_string(&table[index].cpl);
        spdk_json_write_string_fmt(w, "%s.%06ld: [cpl: %s] \n"
                                   "0x%08x, 0x%08x, 0x%08x, 0x%08x\n",
                                   tmbuf, time_cpl.tv_usec,
                                   sts,
                                   cpl[0], cpl[1], cpl[2], cpl[3]);
      }
      else
      {
        spdk_json_write_string_fmt(w, "not completed\n...\n");
      }
    }
  } while (seq++ < 128);

  spdk_json_write_array_end(w);
  spdk_jsonrpc_end_result(request, w);
}
SPDK_RPC_REGISTER("get_cmdlog", rpc_get_cmdlog, SPDK_RPC_STARTUP | SPDK_RPC_RUNTIME)


////driver system
///////////////////////////////

#define DRIVER_IO_TOKEN_NAME      "driver_io_token"

static void driver_init_token(void)
{
  if (spdk_process_is_primary())
  {
    assert(g_driver_io_token_ptr == NULL);
    g_driver_io_token_ptr = spdk_memzone_reserve(DRIVER_IO_TOKEN_NAME,
                                                 sizeof(uint64_t),
                                                 0,
                                                 0);

    // avoid token 0
    *g_driver_io_token_ptr = 1;
  }
  else
  {
    g_driver_io_token_ptr = spdk_memzone_lookup(DRIVER_IO_TOKEN_NAME);
  }

  assert(g_driver_io_token_ptr != NULL);
}


#define DRIVER_GLOBAL_CONFIG_NAME "driver_global_config"

static void driver_init_config(void)
{
  if (spdk_process_is_primary())
  {
    assert(g_driver_config_ptr == NULL);
    g_driver_config_ptr = spdk_memzone_reserve(DRIVER_GLOBAL_CONFIG_NAME,
                                               sizeof(uint64_t),
                                               0,
                                               0);
    *g_driver_config_ptr = 0;
  }
  else
  {
    g_driver_config_ptr = spdk_memzone_lookup(DRIVER_GLOBAL_CONFIG_NAME);
  }

  assert(g_driver_config_ptr != NULL);
}


int driver_init(void)
{
  char buf[64];
  struct spdk_env_opts opts;
  struct stat sb;
  int shm_id = getpid();

  // at least 4-core system
  assert(get_nprocs() >= 4);

  // get the shared memory group id among primary and secondary processes
  sprintf(buf, "/var/run/dpdk/spdk%d", getppid());
  if (stat(buf, &sb) == 0 && S_ISDIR(sb.st_mode))
  {
    //it is a secondary process
    shm_id = getppid();
  }

  // distribute multiprocessing to different cores
  spdk_env_opts_init(&opts);
  sprintf(buf, "0x%llx", 1ULL<<((getpid()%(get_nprocs()-1))+1));
  opts.core_mask = buf;
  opts.shm_id = shm_id;
  opts.name = "pynvme";
  opts.mem_size = 256;
  opts.hugepage_single_segments = true;
  if (spdk_env_init(&opts) < 0)
  {
    fprintf(stderr, "Unable to initialize SPDK env\n");
    return -1;
  }

  // distribute multiprocessing to different cores
  // log level setup
  spdk_log_set_flag("nvme");
  spdk_log_set_print_level(SPDK_LOG_INFO);

  // start rpc server in primary process only
  if (spdk_process_is_primary())
  {
    pthread_t rpc_t;
    pthread_create(&rpc_t, NULL, rpc_server, NULL);
  }

  driver_init_config();
  driver_init_token();

  // init timer
  timeval_init();

  return 0;
}


int driver_fini(void)
{
  // clear global shared data
  if (spdk_process_is_primary())
  {
    spdk_memzone_free(DRIVER_IO_TOKEN_NAME);
    spdk_memzone_free(DRIVER_GLOBAL_CONFIG_NAME);
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "pynvme driver unloaded.\n");
  }

  g_driver_io_token_ptr = NULL;
  g_driver_config_ptr = NULL;
  g_driver_crc32_memory_enough = false;

  return spdk_env_cleanup();
}


uint64_t driver_config(uint64_t cfg_word)
{
  assert(g_driver_config_ptr != NULL);

  if (cfg_word & 1)
  {
    // enable verify, to check if it can be enabled
    if (g_driver_crc32_memory_enough != true)
    {
      cfg_word &= ~((uint64_t)1);
    }
  }

  return *g_driver_config_ptr = cfg_word;
}


uint64_t driver_config_read(void)
{
  return *g_driver_config_ptr;
}

void driver_srand(unsigned int seed)
{
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "set random seed: 0x%x\n", seed);
  srandom(seed);
}

uint32_t driver_io_qpair_count(struct spdk_nvme_ctrlr* ctrlr)
{
  return spdk_nvme_io_qpair_count(ctrlr);
}

bool driver_no_secondary(struct spdk_nvme_ctrlr* ctrlr)
{
  return spdk_nvme_secondary_process_nonexist(ctrlr);
}

void driver_init_num_queues(struct spdk_nvme_ctrlr* ctrlr, uint32_t cdw0)
{
  struct spdk_nvme_cpl cpl;

  memset(&cpl, 0, sizeof(cpl));
  cpl.cdw0 = cdw0;
  return spdk_nvme_ctrlr_get_num_queues_done(ctrlr, &cpl);
}
