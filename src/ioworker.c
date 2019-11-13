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


// used for callback
struct ioworker_io_ctx {
  void* data_buf;
  bool is_read;
  struct timeval time_sent;
  struct ioworker_global_ctx* gctx;

  // next pending io
	STAILQ_ENTRY(ioworker_io_ctx) next;
};

struct ioworker_distribution_lookup {
  uint64_t lba_start;
  uint64_t lba_end;
};

struct ioworker_global_ctx {
  struct ioworker_args* args;
  struct ioworker_rets* rets;
  struct spdk_nvme_ns* ns;
  struct spdk_nvme_qpair *qpair;
  struct timeval due_time;
  struct timeval io_due_time;
  struct timeval io_delay_time;
  struct timeval time_next_sec;
  uint64_t io_count_till_last_sec;
  uint64_t sequential_lba;
  uint64_t io_count_sent;
  uint64_t io_count_cplt;
  uint32_t last_sec;
  bool flag_finish;

  // distribution loopup table
  bool distribution;
  struct ioworker_distribution_lookup dl_table[10000];

  // io_size lookup table
  uint32_t sl_table[10000];

  // pending io list
	STAILQ_HEAD(, ioworker_io_ctx)	pending_io_list;
};


static void ioworker_distribution_init(struct spdk_nvme_ns* ns,
                                       struct ioworker_global_ctx* ctx,
                                       uint32_t* distribution)
{
  uint32_t lookup_index = 0;
  uint64_t lba_max = spdk_nvme_ns_get_num_sectors(ns);
  uint64_t lba_section = lba_max/100;
  uint64_t section_start;
  uint64_t section_end;

  for (uint32_t i=0; i<100; i++)
  {
    section_start = lba_section*i;
    section_end = section_start+lba_section;
    if (i == 99)
    {
      section_end = ctx->args->region_end;
    }

    // fill lookup table
    for (uint32_t j=0; j<distribution[i]; j++)
    {
      SPDK_DEBUGLOG(SPDK_LOG_NVME, "%d: [%lu - %lu]\n", lookup_index, section_start, section_end);
      ctx->dl_table[lookup_index].lba_start = section_start;
      ctx->dl_table[lookup_index].lba_end = section_end;
      lookup_index ++;
    }
  }

  // set last section
  assert(lookup_index == 10000);
}


