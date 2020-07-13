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

#include "ioworker.h"
#include "../spdk/lib/nvme/nvme_internal.h"


static void ioworker_iosize_init(struct ioworker_global_ctx* ctx)
{
  unsigned int sl_index = 0;

  assert(ctx->args->lba_size_ratio_sum <= 10000);
  for (unsigned int i=0; i<ctx->args->lba_size_list_len; i++)
  {
    for (unsigned int j=0; j<ctx->args->lba_size_list_ratio[i]; j++)
    {
      SPDK_DEBUGLOG(SPDK_LOG_NVME, "sl table %d: %d\n", sl_index, i);
      ctx->sl_table[sl_index++] = i;
    }
  }
  assert(sl_index == ctx->args->lba_size_ratio_sum);
}


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


static inline void timeradd_usecond(struct timeval* now,
                                    unsigned long useconds,
                                    struct timeval* due)
{
  struct timeval duration;

  duration.tv_sec = useconds/1000000ULL;
  duration.tv_usec = useconds%1000000ULL;
  timeradd(now, &duration, due);
}

static bool ioworker_send_one_is_finish(struct ioworker_args* args,
                                        struct ioworker_global_ctx* c,
                                        struct timeval* now)
{
  if (c->io_sequence)
  {
    // touch the end of the trace
    if (c->io_sequence_index >= c->io_sequence_count)
    {
      SPDK_DEBUGLOG(SPDK_LOG_NVME, "ioworker finish, sequence sent %ld io\n", c->io_count_sent);
      return true;
    }
  }

  // limit by io count, and/or time, which happens first
  if (c->io_count_sent == args->io_count)
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "ioworker finish, sent %ld io\n", c->io_count_sent);
    return true;
  }

  assert(c->io_count_sent < args->io_count);

  if (timercmp(now, &c->due_time, >))
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "ioworker finish, due time %ld us\n", c->due_time.tv_usec);
    return true;
  }

  return false;
}

static uint32_t ioworker_get_duration(struct timeval* start, struct timeval* now)
{
  struct timeval diff;
  uint32_t msec;

  if (timercmp(now, start, >))
  {
    timersub(now, start, &diff);
    msec = diff.tv_sec*1000ULL;
    return msec + (diff.tv_usec+500)/1000ULL;
  }

  // something wrong
  SPDK_INFOLOG(SPDK_LOG_NVME, "%ld.%06ld\n", now->tv_sec, now->tv_usec);
  SPDK_INFOLOG(SPDK_LOG_NVME, "%ld.%06ld\n", start->tv_sec, start->tv_usec);
  assert(false);
}

static uint32_t ioworker_update_rets(struct ioworker_io_ctx* ctx,
                                     struct ioworker_rets* ret,
                                     struct timeval* now)
{
  struct timeval diff;
  uint32_t latency;

  timersub(now, &ctx->time_sent, &diff);
  latency = timeval_to_us(&diff);
  if (latency > ret->latency_max_us)
  {
    ret->latency_max_us = latency;
  }

  if (ctx->opcode == 0x02)
  {
    ret->io_count_read ++;
  }
  else
  {
    ret->io_count_nonread ++;
  }

  return latency;
}

static inline void ioworker_update_io_count_per_second(
    struct ioworker_global_ctx* gctx,
    struct ioworker_args* args,
    struct ioworker_rets* rets)
{
  uint64_t current_io_count = rets->io_count_read + rets->io_count_nonread;

  // update to next second
  timeradd_usecond(&gctx->time_next_sec, 1000000ULL, &gctx->time_next_sec);
  args->io_counter_per_second[gctx->last_sec ++] = current_io_count - gctx->io_count_till_last_sec;
  gctx->io_count_till_last_sec = current_io_count;
}

static void ioworker_one_cb(void* ctx_in, const struct spdk_nvme_cpl *cpl)
{
  uint32_t latency_us;
  struct timeval now;
  struct ioworker_io_ctx* ctx = (struct ioworker_io_ctx*)ctx_in;
  struct ioworker_args* args = ctx->gctx->args;
  struct ioworker_global_ctx* gctx = ctx->gctx;
  struct ioworker_rets* rets = gctx->rets;

  gctx->io_count_cplt ++;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "sent: %ld; cplt: %ld\n",
                gctx->io_count_sent, gctx->io_count_cplt);

  // update statistics in ret structure
  timeval_gettimeofday(&now);
  assert(rets != NULL);
  latency_us = ioworker_update_rets(ctx, rets, &now);
  gctx->total_latency_us += latency_us;

  // update all op counter
  args->op_counter[ctx->op_index] ++;

  // update io count per latency
  if (args->io_counter_per_latency != NULL)
  {
    args->io_counter_per_latency[MIN(US_PER_S-1, latency_us)] ++;
  }

  if (gctx->io_sequence)
  {
    // replay next io
    uint32_t ios_index = gctx->io_sequence_index;

    if (ios_index < gctx->io_sequence_count)
    {
      timeradd_usecond(&gctx->io_sequence_start,
                       gctx->io_sequence[ios_index].timestamp,
                       &ctx->time_sent);
      ctx->io_sequence_index = ios_index;
      gctx->io_sequence_index ++;
    }
  }
  else if (gctx->io_delay_time.tv_usec != 0)
  {
    // throttle IOPS by setting delay time and insert to pending list
    timeradd(&gctx->io_due_time, &gctx->io_delay_time, &gctx->io_due_time);
    ctx->time_sent = gctx->io_due_time;
  }

  // check status
  if (true == nvme_cpl_is_error(cpl))
  {
    // terminate ioworker when any error happen
    // only keep the first error code
    uint16_t error = ((*(unsigned short*)(&cpl->status))>>1)&0x7ff;
    SPDK_ERRLOG("ioworker error happen in cpl, error %x\n", error);
    gctx->flag_finish = true;
    if (rets->error == 0)
    {
      rets->error = error;
    }
  }

  // update io counter per second when required
  if (args->io_counter_per_second != NULL)
  {
    if (timercmp(&now, &gctx->time_next_sec, >))
    {
      ioworker_update_io_count_per_second(gctx, args, rets);
    }
  }

  // check if all io are sent
  if (gctx->flag_finish != true)
  {
    //update finish flag
    struct timeval now;
    timeval_gettimeofday(&now);
    gctx->flag_finish = ioworker_send_one_is_finish(args, gctx, &now);
  }

  if (gctx->flag_finish != true)
  {
    STAILQ_INSERT_TAIL(&gctx->pending_io_list, ctx, next);
    gctx->io_count_sent ++;
  }

  if (args->cmdlog_list_len != 0)
  {
    // find the location of ioworker_cmdlog to update
    unsigned int cmdlog_index = gctx->current_cmdlog_index++;
    if (cmdlog_index == args->cmdlog_list_len)
    {
      // wrap to the beginning
      cmdlog_index = 0;
      gctx->current_cmdlog_index = 1;
    }

    // update command information to ioworker_cmdlog
    struct ioworker_cmdlog* cmd = &args->cmdlog_list[cmdlog_index];
    memcpy(cmd, &ctx->cmd, sizeof(ctx->cmd));
  }
}

static inline uint64_t ioworker_send_one_lba_sequential(struct ioworker_args* args,
                                                        struct ioworker_global_ctx* gctx)
{
  uint64_t ret;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "gctx lba: 0x%lx, end: 0x%lx\n",
                gctx->sequential_lba, args->region_end);

  ret = gctx->sequential_lba;
  if (ret >= args->region_end)
  {
    ret = args->region_start;
  }

  return ret;
}

static inline uint64_t ioworker_send_one_lba_random(struct ioworker_args* args,
                                                    struct ioworker_global_ctx* gctx)
{
  uint64_t start;
  uint64_t end;

  // for distributed IO, pick up a random section first
  if (gctx->distribution)
  {
    uint32_t index = random()%10000;
    start = gctx->dl_table[index].lba_start;
    end = gctx->dl_table[index].lba_end;
  }
  else
  {
    start = args->region_start;
    end = args->region_end;
  }

  // pick up a random lba in the section
  if (end == start)
  {
    return start;
  }
  else
  {
    assert(end>start);
    return (random()%(end-start)) + start;
  }
}


static inline uint32_t ioworker_send_one_size(struct ioworker_args* args,
                                              struct ioworker_global_ctx* gctx,
                                              uint16_t* lba_align)
{
  uint32_t si = gctx->sl_table[random()%args->lba_size_ratio_sum];
  uint32_t ret = args->lba_size_list[si];

  *lba_align = args->lba_size_list_align[si];
  return ret;
}


static inline uint64_t ioworker_send_one_lba(struct ioworker_args* args,
                                             struct ioworker_global_ctx* gctx,
                                             uint16_t lba_align,
                                             uint16_t lba_count)
{
  uint64_t ret;
  bool is_random = (random()%100) < args->lba_random;

  if (is_random == false)
  {
    ret = ioworker_send_one_lba_sequential(args, gctx);
  }
  else
  {
    ret = ioworker_send_one_lba_random(args, gctx);
  }

  ret = ALIGN_UP(ret, lba_align);
  if (ret >= args->region_end)
  {
    ret = ALIGN_DOWN(ret-1, lba_align);
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "ret 0x%lx, align 0x%x, end 0x%lx, seq 0x%lx\n",
                  ret, lba_align, args->region_end, gctx->sequential_lba);
    assert(ret < args->region_end);
  }

  // setup for next sequential io
  if (is_random == false)
  {
    if (args->lba_step_valid)
    {
      gctx->sequential_lba = ret+args->lba_step;
    }
    else
    {
      // no step specified, write in next lba
      gctx->sequential_lba = ret+lba_count;
    }
  }

  return ret;
}


static int ioworker_send_one(struct spdk_nvme_ns* ns,
                             struct spdk_nvme_qpair *qpair,
                             struct ioworker_io_ctx* ctx,
                             struct ioworker_global_ctx* gctx)
{
  int ret;
  uint16_t lba_align;
  void* buf;
  struct ioworker_args* args = gctx->args;
  uint32_t op_list_index = gctx->op_table[random()%100];
  uint8_t opcode = args->op_list[op_list_index];
  uint32_t lba_count = ioworker_send_one_size(args, gctx, &lba_align);
  uint64_t lba_starting = ioworker_send_one_lba(args, gctx, lba_align, lba_count);
  uint32_t sector_size = spdk_nvme_ns_get_sector_size(ns);

  // replay io sequence
  if (gctx->io_sequence)
  {
    uint32_t ios_index = ctx->io_sequence_index;

    op_list_index = 0;
    opcode = gctx->io_sequence[ios_index].op;
    lba_count = gctx->io_sequence[ios_index].nlba;
    lba_starting = gctx->io_sequence[ios_index].slba;
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "one io: index %d, lba %lu, count %d, opcode %d\n",
                  ios_index,  lba_starting, lba_count, opcode);
  }

  // trancate the tail out of the region
  lba_count = MIN(lba_count, args->region_end-lba_starting);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "one io: ctx %p, lba %lu, count %d, align %d, opcode %d\n",
                ctx, lba_starting, lba_count, lba_align, opcode);

  assert(ctx->data_buf != NULL);
  assert(ctx->write_buf != NULL);
  assert(lba_starting <= args->region_end);

  // keep cmd information for logging at completion time
  ctx->cmd.lba = lba_starting;
  ctx->cmd.count = lba_count;
  ctx->cmd.opcode = opcode;

  // send command to driver
  buf = ((opcode==1) ? ctx->write_buf : ctx->data_buf);
  ret = ns_cmd_io(opcode, ns, qpair,
                  buf, lba_count*sector_size,
                  lba_starting, lba_count,
                  0,  //do not have more options in ioworkers
                  ioworker_one_cb, ctx,
                  0, 0, 0);  //no PI, DSM, directive ...
  if (ret != 0)
  {
    SPDK_ERRLOG("ioworker error happen in sending cmd\n");
    gctx->flag_finish = true;
    return ret;
  }

  //sent one io cmd successfully
  ctx->opcode = opcode;
  ctx->op_index = op_list_index;
  timeval_gettimeofday(&ctx->time_sent);
  return 0;
}


static void ioworker_add_cpu_time(struct timeval* start, struct timeval* cpu_time)
{
  struct timeval now = {0, 0};
  struct timeval diff = {0, 0};

  // collect cpu time for utilization rate
  timeval_gettimeofday(&now);
  timersub(&now, start, &diff);
  timeradd(&diff, cpu_time, cpu_time);
}


int ioworker_entry(struct spdk_nvme_ns* ns,
                   struct spdk_nvme_qpair *qpair,
                   struct ioworker_args* args,
                   struct ioworker_rets* rets)
{
  int ret = 0;
  uint64_t nsze = spdk_nvme_ns_get_num_sectors(ns);
  uint32_t sector_size = spdk_nvme_ns_get_sector_size(ns);
  uint32_t max_xfer_size = spdk_nvme_ns_get_max_io_xfer_size(ns);
  struct ioworker_io_ctx* io_ctx = malloc(sizeof(struct ioworker_io_ctx)*args->qdepth);
  struct ioworker_global_ctx gctx;
  struct timeval test_start;
  uint64_t seconds;

  assert(ns != NULL);
  assert(qpair != NULL);
  assert(args != NULL);
  assert(rets != NULL);
  assert(io_ctx != NULL);

  //init rets
  rets->io_count_read = 0;
  rets->io_count_nonread = 0;
  rets->latency_max_us = 0;
  rets->mseconds = 0;
  rets->error = 0;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.lba_start = %ld\n", args->lba_start);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.lba_step = %d\n", args->lba_step);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.lba_step_valid = %d\n", args->lba_step_valid);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.lba_size_max = %d\n", args->lba_size_max);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.lba_align_max = %d\n", args->lba_align_max);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.lba_random = %d\n", args->lba_random);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.region_start = %ld\n", args->region_start);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.region_end = %ld\n", args->region_end);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.op_num = %d\n", args->op_num);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.iops = %d\n", args->iops);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.io_count = %ld\n", args->io_count);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.seconds = %d\n", args->seconds);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.qdepth = %d\n", args->qdepth);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.pvalue = %d\n", args->pvalue);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.ptype = %d\n", args->ptype);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.io_sequence = %p\n", args->io_sequence);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.io_sequence_len = %d\n", args->io_sequence_len);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.cmdlog_list = %p\n", args->cmdlog_list);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "args.cmdlog_list_len = %d\n", args->cmdlog_list_len);

  //check args
  assert(args->lba_size_max != 0);
  assert(args->region_start < args->region_end);
  assert(args->qdepth <= CMD_LOG_DEPTH/2);
  assert(args->cmdlog_list_len < 1024*1024);

  if (args->io_sequence)
  {
    // io size is unknown, so set to max transfer size
    args->lba_size_max = max_xfer_size/sector_size;
  }

  // check io size
  if (args->lba_size_max*sector_size > max_xfer_size)
  {
    SPDK_WARNLOG("IO size is larger than max xfer size, %d\n", max_xfer_size);
    rets->error = 0x0002;  // Invalid Field in Command
    free(io_ctx);
    return -2;
  }

  //revise args
  if (args->io_count == 0)
  {
    args->io_count = (unsigned long)-1;
  }
  if (args->seconds == 0 || args->seconds > 1000*3600ULL)
  {
    // run ioworker for 1000hr at most (due to 32-bit mseconds)
    args->seconds = 1000*3600ULL;
  }
  seconds = args->seconds;

  //adjust region to start_lba's region, but included here
  args->region_start = ALIGN_UP(args->region_start, args->lba_align_max);
  args->region_end = MIN(nsze, args->region_end);
  // truncate the last io at the region end, so do need to adjust region end
  //args->region_end = args->region_end-args->lba_size_max;
  //args->region_end = ALIGN_DOWN(args->region_end, args->lba_size_max);
  //args->region_end = ALIGN_DOWN(args->region_end, args->lba_align_max);

  if (args->lba_start < args->region_start)
  {
    args->lba_start = args->region_start;
  }
  if (args->io_count < args->qdepth)
  {
    args->qdepth = args->io_count+1;
  }

  // reserve one depth in the queue
  args->qdepth -= 1;

  //init global ctx
  memset(&gctx, 0, sizeof(gctx));
  gctx.ns = ns;
  gctx.qpair = qpair;
  gctx.sequential_lba = args->lba_start;
  gctx.io_count_sent = 0;
  gctx.io_count_cplt = 0;
  gctx.flag_finish = false;
  gctx.args = args;
  gctx.rets = rets;
  gctx.current_cmdlog_index = 0;
  timeval_gettimeofday(&test_start);
  timeradd_usecond(&test_start, 1000000ULL*seconds, &gctx.due_time);
  gctx.io_delay_time.tv_sec = 0;
  gctx.io_delay_time.tv_usec = args->iops ? US_PER_S/args->iops : 0;
  gctx.io_due_time = test_start;
  timeradd_usecond(&test_start, 1000000ULL, &gctx.time_next_sec);
  gctx.io_count_till_last_sec = 0;
  gctx.last_sec = 0;
  gctx.io_sequence = args->io_sequence;
  gctx.io_sequence_count = args->io_sequence_len;
  gctx.io_sequence_index = 0;
  timeval_gettimeofday(&gctx.io_sequence_start);

  // calculate distribution lookup table
  if (args->distribution)
  {
    gctx.distribution = true;
    ioworker_distribution_init(ns, &gctx, args->distribution);
  }

  // calculate io_size lookup table
  ioworker_iosize_init(&gctx);

  // build op/cmd lookup table
  uint32_t op_table_index = 0;
  for (unsigned int i=0; i<args->op_num; i++)
  {
    for (unsigned int j=0; j<args->op_counter[i]; j++)
    {
      gctx.op_table[op_table_index++] = i;
    }
  }
  assert(op_table_index == 100);

  // sending the first batch of IOs, all remaining IOs are sending
  // in callbacks till end
  STAILQ_INIT(&gctx.pending_io_list);
  uint32_t buffer_size = args->lba_size_max * sector_size;
  uint32_t pool_size = buffer_size * args->qdepth * 2;
  void* buffer_pool = buffer_init(pool_size, NULL, args->ptype, args->pvalue);
  if (buffer_pool == NULL)
  {
    SPDK_WARNLOG("memory alloc fail, buffer pool size: %d\n", pool_size);
    free(io_ctx);
    return -5;
  }

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "prepare buffer %d\n", pool_size);
  for (unsigned int i=0; i<args->qdepth; i++)
  {
    io_ctx[i].data_buf = buffer_pool+buffer_size*2*i;
    io_ctx[i].write_buf = buffer_pool+buffer_size*2*i+buffer_size;
    io_ctx[i].gctx = &gctx;

    // set time to send it for the first time
    if (gctx.io_sequence)
    {
      uint32_t ios_index = gctx.io_sequence_index;

      if (ios_index >= gctx.io_sequence_count)
      {
        continue;
      }

      timeradd_usecond(&gctx.io_sequence_start,
                       gctx.io_sequence[ios_index].timestamp,
                       &io_ctx[i].time_sent);
      io_ctx[i].io_sequence_index = ios_index;
      gctx.io_sequence_index ++;
    }
    else if (gctx.io_delay_time.tv_usec != 0)
    {
      // control IOPS
      timeradd(&gctx.io_due_time, &gctx.io_delay_time, &gctx.io_due_time);
      io_ctx[i].time_sent = gctx.io_due_time;
    }
    else
    {
      // free run
      timeval_gettimeofday(&io_ctx[i].time_sent);
    }

    STAILQ_INSERT_TAIL(&gctx.pending_io_list, &io_ctx[i], next);
    gctx.io_count_sent ++;
  }

  // callbacks check the end condition and mark the flag. Check the
  // flag here if it is time to stop the ioworker and return the
  // statistics data
  struct ioworker_io_ctx* head_io = STAILQ_FIRST(&gctx.pending_io_list);
  struct timeval now = {0, 0};
  struct timeval cpu_time = {0, 0};
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "start sending IO ... \n");
  while (gctx.io_count_sent != gctx.io_count_cplt ||
         gctx.flag_finish != true ||
         head_io != NULL)
  {
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "sent %ld cplt %ld, finish %d, head %p\n",
                  gctx.io_count_sent, gctx.io_count_cplt,
                  gctx.flag_finish, head_io);

    // check time and send all pending io
    timeval_gettimeofday(&now);
    if (head_io && timercmp(&now, &head_io->time_sent, >))
    {
      ioworker_send_one(ns, qpair, head_io, &gctx);
      STAILQ_REMOVE_HEAD(&gctx.pending_io_list, next);
      ioworker_add_cpu_time(&now, &cpu_time);
    }

    //exceed 30 seconds more than the expected test time, abort ioworker
    if (ioworker_get_duration(&test_start, &now) > (seconds+30)*1000ULL)
    {
      //ioworker timeout
      SPDK_ERRLOG("ioworker timeout, io sent %ld, io cplt %ld, finish %d\n",
                  gctx.io_count_sent, gctx.io_count_cplt, gctx.flag_finish);
      ret = -4;
      break;
    }

    // check terminate signal from main process
    if ((driver_config_read() & DCFG_IOW_TERM) != 0)
    {
      SPDK_DEBUGLOG(SPDK_LOG_NVME, "force termimate ioworker\n");
      break;
    }

    // collect completions
    timeval_gettimeofday(&now);
    if (spdk_nvme_qpair_process_completions(qpair, 0) > 0)
    {
      // valid process, add cpu time
      ioworker_add_cpu_time(&now, &cpu_time);
    }

    // pynvme: retry one queued request for LBA confliction
    if (!STAILQ_EMPTY(&qpair->queued_req))
    {
      struct nvme_request *req = STAILQ_FIRST(&qpair->queued_req);
      STAILQ_REMOVE_HEAD(&qpair->queued_req, stailq);
      nvme_qpair_submit_request(qpair, req);
    }

    // update the head io after process completion
    head_io = STAILQ_FIRST(&gctx.pending_io_list);
  }

  // final return values
  assert(now.tv_sec != 0);
  rets->mseconds = ioworker_get_duration(&test_start, &now)+1;
  rets->cpu_usage = timeval_to_us(&cpu_time)/1000;
  rets->latency_average_us = gctx.total_latency_us/(rets->io_count_read+rets->io_count_nonread);

  //release buffer pool
  buffer_fini(buffer_pool);

  // handle cmdlog_list
  if (args->cmdlog_list_len != 0)
  {
    uint32_t head = gctx.current_cmdlog_index;
    uint32_t length = args->cmdlog_list_len;
    struct ioworker_cmdlog* cmdlog_list_tmp =
        malloc(args->cmdlog_list_len*sizeof(struct ioworker_cmdlog));

    assert(cmdlog_list_tmp);

    // copy the first part
    memcpy(&cmdlog_list_tmp[0],
           &args->cmdlog_list[head],
           sizeof(struct ioworker_cmdlog)*(length-head));

    // copy the second part
    memcpy(&cmdlog_list_tmp[args->cmdlog_list_len-head],
           &args->cmdlog_list[0],
           sizeof(struct ioworker_cmdlog)*head);

    // copy back to cmdlog_list
    memcpy(&args->cmdlog_list[0],
           &cmdlog_list_tmp[0],
           sizeof(struct ioworker_cmdlog)*length);

    free(cmdlog_list_tmp);
  }

  free(io_ctx);
  return ret;
}
