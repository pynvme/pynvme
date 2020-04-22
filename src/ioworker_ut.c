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


#include "spdk/stdinc.h"
#include "spdk_cunit.h"
#include "spdk_internal/log.h"
#include "spdk_internal/mock.h"

#include "ioworker.c"


// null stubs

struct spdk_log_flag SPDK_LOG_NVME = {
	.name = "nvme",
	.enabled = false,
};

void
spdk_log(enum spdk_log_level level, const char *file, const int line, const char *func,
	 const char *format, ...)
{
}

void* buffer_init(size_t bytes, uint64_t *phys_addr,
                  uint32_t ptype, uint32_t pvalue)
{
  
}

void buffer_fini(void* buf)
{
  
}

uint64_t driver_config_read(void)
{
  
}

uint32_t
spdk_nvme_ns_get_max_io_xfer_size(struct spdk_nvme_ns *ns)
{
	return 1;
}

int
spdk_nvme_qpair_process_completions(struct spdk_nvme_qpair *qpair, uint32_t max_completions)
{
  return 0;
}

int nvme_cpl_is_error(const struct spdk_nvme_cpl* cpl)
{
  return 0;
}

uint32_t spdk_nvme_ns_get_sector_size(struct spdk_nvme_ns *ns)
{
  return 0;
}

void timeval_gettimeofday(struct timeval *tv)
{
  
}

int ns_cmd_read_write(int is_read,
                      struct spdk_nvme_ns* ns,
                      struct spdk_nvme_qpair* qpair,
                      void* buf,
                      size_t len,
                      uint64_t lba,
                      uint16_t lba_count,
                      uint32_t io_flags,
                      spdk_nvme_cmd_cb cb_fn,
                      void* cb_arg)
{
  return 0;
}

void *
spdk_dma_zmalloc(size_t size, size_t align, uint64_t *phys_addr)
{
  return NULL;
}


// stubs
DEFINE_STUB(spdk_nvme_ns_get_num_sectors, uint64_t,
            (struct spdk_nvme_ns *ns), 0);


static struct spdk_nvme_ns ns;
static struct ioworker_global_ctx ctx;
static uint32_t distribution[100];


static void test_ioworker_pass(void)
{
  CU_ASSERT(true);
}

// test cases
static void test_ioworker_distribution_init_single_1000(void)
{
  uint64_t max_lba = 1000;

  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // single active region
  distribution[0] = 10000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, max_lba/100);

  free(ctx.args);  
}

static void test_ioworker_distribution_init_single_10000(void)
{
  uint64_t max_lba = 10000;

  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // single active region
  distribution[0] = 10000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, max_lba/100);

  free(ctx.args);
}

static void test_ioworker_distribution_init_single_10000_last(void)
{
  uint64_t max_lba = 10000;

  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // single active region
  distribution[99] = 10000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 9900);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, 10000);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 9900);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, 10000);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 9900);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, 10000);

  free(ctx.args);
}

static void test_ioworker_distribution_init_dual_20000(void)
{
  uint64_t max_lba = 20000;

  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  distribution[0] = 5000;
  distribution[1] = 5000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, max_lba/100+max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, max_lba/100+max_lba/100);

  free(ctx.args);
}


static void test_ioworker_distribution_init_two_end_20000(void)
{
  uint64_t max_lba = 20000;
  
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  distribution[0] = 5000;
  distribution[99] = 5000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, max_lba-max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, max_lba);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, max_lba-max_lba/100);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, max_lba);
  
  free(ctx.args);  
}

static void test_ioworker_distribution_init_two_end_19999(void)
{
  uint64_t max_lba = 19999;
  
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  distribution[0] = 5000;
  distribution[99] = 5000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, 199);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, 199);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, 19701);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, 19999);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 19701);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, 19999);
  
  free(ctx.args);  
}

static void test_ioworker_distribution_init_two_end_20001(void)
{
  uint64_t max_lba = 20001;
  
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  distribution[0] = 5000;
  distribution[99] = 5000;
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, 200);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, 200);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, 19800);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, 20001);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 19800);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, 20001);
  
  free(ctx.args);  
}


static void test_ioworker_distribution_init_even(void)
{
  uint64_t max_lba = 20000;
  
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  for (int i=0; i<100; i++)
  {
    distribution[i] = 100;
  }
  ctx.args->region_end = max_lba;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, 200);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, 200);
  CU_ASSERT_EQUAL(ctx.dl_table[100].lba_start, 200);
  CU_ASSERT_EQUAL(ctx.dl_table[100].lba_end, 400);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, 10000);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, 10200);
  CU_ASSERT_EQUAL(ctx.dl_table[5001].lba_start, 10000);
  CU_ASSERT_EQUAL(ctx.dl_table[5001].lba_end, 10200);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 19800);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, 20000);
  
  free(ctx.args);  
}


static void test_ioworker_distribution_init_not_even(void)
{
  uint64_t max_lba = 54099;
  
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  distribution[0] = 1;
  distribution[99] = 9999;

  ctx.args->region_end = 54092;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, 540);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 53460);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, 54092);
  CU_ASSERT_EQUAL(ctx.dl_table[100].lba_start, 53460);
  CU_ASSERT_EQUAL(ctx.dl_table[100].lba_end, 54092);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, 53460);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, 54092);
  CU_ASSERT_EQUAL(ctx.dl_table[5001].lba_start, 53460);
  CU_ASSERT_EQUAL(ctx.dl_table[5001].lba_end, 54092);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 53460);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, 54092);
  
  free(ctx.args);  
}

static void test_ioworker_distribution_init_jedec(void)
{
  uint64_t max_lba = 5400000095ULL;
  
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  // two active region
  for (int i=0; i<100; i++)
  {
    distribution[i] = 25;
  }
  for (int i=0; i<20; i++)
  {
    distribution[i] = 200;
  }
  for (int i=0; i<5; i++)
  {
    distribution[i] = 1000;
  }

  ctx.args->region_end = 5400000090ULL;
  MOCK_SET(spdk_nvme_ns_get_num_sectors, max_lba);

  // run test
  ioworker_distribution_init(&ns, &ctx, distribution);

  // result
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[0].lba_end, 54000000);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[1].lba_end, 54000000);
  CU_ASSERT_EQUAL(ctx.dl_table[998].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[998].lba_end, 54000000);
  CU_ASSERT_EQUAL(ctx.dl_table[999].lba_start, 0);
  CU_ASSERT_EQUAL(ctx.dl_table[999].lba_end, 54000000);
  CU_ASSERT_EQUAL(ctx.dl_table[1000].lba_start, 54000000);
  CU_ASSERT_EQUAL(ctx.dl_table[1000].lba_end, 108000000);
  CU_ASSERT_EQUAL(ctx.dl_table[1999].lba_start, 54000000);
  CU_ASSERT_EQUAL(ctx.dl_table[1999].lba_end, 108000000);
  CU_ASSERT_EQUAL(ctx.dl_table[4999].lba_start, 54000000*4);
  CU_ASSERT_EQUAL(ctx.dl_table[4999].lba_end, 54000000*5);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_start, 54000000*5);
  CU_ASSERT_EQUAL(ctx.dl_table[5000].lba_end, 54000000*6);
  CU_ASSERT_EQUAL(ctx.dl_table[5200].lba_start, 54000000*6);
  CU_ASSERT_EQUAL(ctx.dl_table[5200].lba_end, 54000000*7);
  CU_ASSERT_EQUAL(ctx.dl_table[7999].lba_start, 54000000*19);
  CU_ASSERT_EQUAL(ctx.dl_table[7999].lba_end, 54000000*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8000].lba_start, 54000000*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8000].lba_end, 54000000*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8001].lba_start, 54000000*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8001].lba_end, 54000000*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8002].lba_start, 54000000ULL*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8002].lba_end, 54000000ULL*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8003].lba_start, 54000000ULL*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8003].lba_end, 54000000ULL*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8004].lba_start, 54000000ULL*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8004].lba_end, 54000000ULL*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8005].lba_start, 54000000ULL*20);
  CU_ASSERT_EQUAL(ctx.dl_table[8005].lba_end, 54000000ULL*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8025].lba_start, 54000000ULL*21);
  CU_ASSERT_EQUAL(ctx.dl_table[8025].lba_end, 54000000ULL*22);
  CU_ASSERT_EQUAL(ctx.dl_table[9995].lba_start, 54000000ULL*99);
  CU_ASSERT_EQUAL(ctx.dl_table[9995].lba_end, 5400000090ULL);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_start, 54000000ULL*99);
  CU_ASSERT_EQUAL(ctx.dl_table[9999].lba_end, 5400000090ULL);
  
  free(ctx.args);  
}


static int suite_ioworker_distribution_init(void)
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_pass);
  CU_ADD_TEST(s, test_ioworker_distribution_init_single_1000);
  CU_ADD_TEST(s, test_ioworker_distribution_init_single_10000);
  CU_ADD_TEST(s, test_ioworker_distribution_init_single_10000_last);
  CU_ADD_TEST(s, test_ioworker_distribution_init_dual_20000);
  CU_ADD_TEST(s, test_ioworker_distribution_init_two_end_20000);
  CU_ADD_TEST(s, test_ioworker_distribution_init_two_end_19999);
  CU_ADD_TEST(s, test_ioworker_distribution_init_two_end_20001);
  CU_ADD_TEST(s, test_ioworker_distribution_init_even);
  CU_ADD_TEST(s, test_ioworker_distribution_init_not_even);
  CU_ADD_TEST(s, test_ioworker_distribution_init_jedec);
  
	return 0;
}


// test cases
static void test_timeradd_usecond_add_0(void)
{
  struct timeval now = {10, 100};
  struct timeval due = {0, 0};
  
  timeradd_usecond(&now, 0, &due);
  
  CU_ASSERT_EQUAL(due.tv_sec, 10);
  CU_ASSERT_EQUAL(due.tv_usec, 100);
}

static void test_timeradd_usecond_add_1(void)
{
  struct timeval now = {10, 10};
  struct timeval due = {0, 0};
  
  timeradd_usecond(&now, 1, &due);
  
  CU_ASSERT_EQUAL(due.tv_sec, 10);
  CU_ASSERT_EQUAL(due.tv_usec, 11);
}

static void test_timeradd_usecond_add_100(void)
{
  struct timeval now = {10, 1000*1000ULL};
  struct timeval due = {0, 0};
  
  timeradd_usecond(&now, 100, &due);
  
  CU_ASSERT_EQUAL(due.tv_sec, 11);
  CU_ASSERT_EQUAL(due.tv_usec, 100);
}

static void test_timeradd_usecond_add_10000000(void)
{
  struct timeval now = {10, 1ULL};
  struct timeval due = {0, 0};
  
  timeradd_usecond(&now, 10000000, &due);
  
  CU_ASSERT_EQUAL(due.tv_sec, 20);
  CU_ASSERT_EQUAL(due.tv_usec, 1);
}

static int suite_timeradd_usecond()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_timeradd_usecond_add_0);
  CU_ADD_TEST(s, test_timeradd_usecond_add_1);
  CU_ADD_TEST(s, test_timeradd_usecond_add_100);
  CU_ADD_TEST(s, test_timeradd_usecond_add_10000000);
  
	return 0;
}


static void test_ioworker_send_one_is_finish_io_count_full()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  struct timeval now;
  bool ret;
  
  args.io_count = 100;
  ctx.io_count_sent = 100;

  ret = ioworker_send_one_is_finish(&args, &ctx, &now);

  CU_ASSERT_EQUAL(ret, true);
}
                                                      

static void test_ioworker_send_one_is_finish_time_full()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  struct timeval now;
  bool ret;
  
  args.io_count = 100;
  ctx.io_count_sent = 99;
  now.tv_sec = 100;
  now.tv_usec = 8800;
  ctx.due_time.tv_sec = 100;
  ctx.due_time.tv_usec = 8000;
  
  ret = ioworker_send_one_is_finish(&args, &ctx, &now);

  CU_ASSERT_EQUAL(ret, true);
}

static void test_ioworker_send_one_is_finish_time_long_full()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  struct timeval now;
  bool ret;
  
  args.io_count = 100;
  ctx.io_count_sent = 99;
  now.tv_sec = 10000000UL+500*3600UL;
  now.tv_usec = 8800;
  ctx.due_time.tv_sec = 10000000UL+500*3600UL;
  ctx.due_time.tv_usec = 8000;
  
  ret = ioworker_send_one_is_finish(&args, &ctx, &now);

  CU_ASSERT_EQUAL(ret, true);
  
  args.io_count = 100;
  ctx.io_count_sent = 99;
  now.tv_sec = 10000000UL+500*3600UL;
  now.tv_usec = 8800;
  ctx.due_time.tv_sec = 10000000UL+500*3600UL;
  ctx.due_time.tv_usec = 8801;
  
  ret = ioworker_send_one_is_finish(&args, &ctx, &now);

  CU_ASSERT_EQUAL(ret, false);
}
                                                      
static void test_ioworker_send_one_is_finish_both_full()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  struct timeval now;
  bool ret;
  
  args.io_count = 99;
  ctx.io_count_sent = 99;
  now.tv_sec = 100;
  now.tv_usec = 8800;
  ctx.due_time.tv_sec = 99;
  ctx.due_time.tv_usec = 8000;
  
  ret = ioworker_send_one_is_finish(&args, &ctx, &now);

  CU_ASSERT_EQUAL(ret, true);
}

static void test_ioworker_send_one_is_finish_none_full()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  struct timeval now;
  bool ret;
  
  args.io_count = 99;
  ctx.io_count_sent = 9;
  now.tv_sec = 100;
  now.tv_usec = 8800;
  ctx.due_time.tv_sec = 999;
  ctx.due_time.tv_usec = 8000;
  
  ret = ioworker_send_one_is_finish(&args, &ctx, &now);

  CU_ASSERT_EQUAL(ret, false);
}
                                                      
static int suite_ioworker_send_one_is_finish()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_send_one_is_finish_io_count_full);
  CU_ADD_TEST(s, test_ioworker_send_one_is_finish_time_full);
  CU_ADD_TEST(s, test_ioworker_send_one_is_finish_time_long_full);
  CU_ADD_TEST(s, test_ioworker_send_one_is_finish_both_full);
  CU_ADD_TEST(s, test_ioworker_send_one_is_finish_none_full);
  
	return 0;
}


static void test_ioworker_get_duration_small()
{
  struct timeval now;
  struct timeval start;
  uint32_t ret;
  
  now.tv_sec = 100;
  now.tv_usec = 8801;
  start.tv_sec = 100;
  start.tv_usec = 8800;
  
  ret = ioworker_get_duration(&start, &now);

  CU_ASSERT_EQUAL(ret, 0);
}

static void test_ioworker_get_duration_1ms()
{
  struct timeval now;
  struct timeval start;
  uint32_t ret;
  
  now.tv_sec = 100;
  now.tv_usec = 9801;
  start.tv_sec = 100;
  start.tv_usec = 8800;
  
  ret = ioworker_get_duration(&start, &now);

  CU_ASSERT_EQUAL(ret, 1);
}

static void test_ioworker_get_duration_1001ms()
{
  struct timeval now;
  struct timeval start;
  uint32_t ret;
  
  now.tv_sec = 101;
  now.tv_usec = 9801;
  start.tv_sec = 100;
  start.tv_usec = 8800;
  
  ret = ioworker_get_duration(&start, &now);

  CU_ASSERT_EQUAL(ret, 1001);
}

static void test_ioworker_get_duration_999ms()
{
  struct timeval now;
  struct timeval start;
  uint32_t ret;
  
  now.tv_sec = 101;
  now.tv_usec = 0;
  start.tv_sec = 100;
  start.tv_usec = 1499;
  
  ret = ioworker_get_duration(&start, &now);

  CU_ASSERT_EQUAL(ret, 999);
}

static void test_ioworker_get_duration_998ms()
{
  struct timeval now;
  struct timeval start;
  uint32_t ret;
  
  now.tv_sec = 101;
  now.tv_usec = 0;
  start.tv_sec = 100;
  start.tv_usec = 1501;
  
  ret = ioworker_get_duration(&start, &now);

  CU_ASSERT_EQUAL(ret, 998);
}

static void test_ioworker_get_duration_large()
{
  struct timeval now;
  struct timeval start;
  uint32_t ret;
  
  now.tv_sec = 1000*3600UL;
  now.tv_usec = 0;
  start.tv_sec = 0;
  start.tv_usec = 0;
  
  ret = ioworker_get_duration(&start, &now);

  CU_ASSERT_EQUAL(ret, 3600000000UL);
}

static int suite_ioworker_get_duration()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_get_duration_small);
  CU_ADD_TEST(s, test_ioworker_get_duration_1ms);
  CU_ADD_TEST(s, test_ioworker_get_duration_1001ms);
  CU_ADD_TEST(s, test_ioworker_get_duration_999ms);
  CU_ADD_TEST(s, test_ioworker_get_duration_998ms);
  CU_ADD_TEST(s, test_ioworker_get_duration_large);
  
	return 0;
}


DEFINE_STUB(timeval_to_us, uint32_t, (struct timeval* t), 0);

static void test_ioworker_update_rets_latency_read()
{
  struct ioworker_io_ctx ctx;
  struct ioworker_rets rets;
  struct timeval now;
  uint32_t ret;

  MOCK_SET(timeval_to_us, 200);
  
  rets.latency_max_us = 100;
  ctx.is_read = true;
  rets.io_count_read = 10;
  rets.io_count_write = 11;
  
  ret = ioworker_update_rets(&ctx, &rets, &now);

  CU_ASSERT_EQUAL(rets.latency_max_us, 200);
  CU_ASSERT_EQUAL(ret, 200);
  CU_ASSERT_EQUAL(rets.io_count_read, 11);
  CU_ASSERT_EQUAL(rets.io_count_write, 11);
}

static void test_ioworker_update_rets_latency_write()
{
  struct ioworker_io_ctx ctx;
  struct ioworker_rets rets;
  struct timeval now;
  uint32_t ret;

  MOCK_SET(timeval_to_us, 2000);
  
  rets.latency_max_us = 100;
  ctx.is_read = false;
  rets.io_count_read = 10;
  rets.io_count_write = 11;
  
  ret = ioworker_update_rets(&ctx, &rets, &now);

  CU_ASSERT_EQUAL(rets.latency_max_us, 2000);
  CU_ASSERT_EQUAL(ret, 2000);
  CU_ASSERT_EQUAL(rets.io_count_read, 10);
  CU_ASSERT_EQUAL(rets.io_count_write, 12);
}

static void test_ioworker_update_rets_latency_large_write()
{
  struct ioworker_io_ctx ctx;
  struct ioworker_rets rets;
  struct timeval now;
  uint32_t ret;

  MOCK_SET(timeval_to_us, 4000000000U);
  
  rets.latency_max_us = 100;
  ctx.is_read = false;
  rets.io_count_read = 10;
  rets.io_count_write = 11;
  
  ret = ioworker_update_rets(&ctx, &rets, &now);

  CU_ASSERT_EQUAL(rets.latency_max_us, 4000000000U);
  CU_ASSERT_EQUAL(ret, 4000000000U);
  CU_ASSERT_EQUAL(rets.io_count_read, 10);
  CU_ASSERT_EQUAL(rets.io_count_write, 12);
}

static void test_ioworker_update_rets_read()
{
  struct ioworker_io_ctx ctx;
  struct ioworker_rets rets;
  struct timeval now;
  uint32_t ret;

  MOCK_SET(timeval_to_us, 2000);
  
  rets.latency_max_us = 10000;
  ctx.is_read = true;
  rets.io_count_read = 10;
  rets.io_count_write = 11;
  
  ret = ioworker_update_rets(&ctx, &rets, &now);

  CU_ASSERT_EQUAL(rets.latency_max_us, 10000);
  CU_ASSERT_EQUAL(ret, 2000);
  CU_ASSERT_EQUAL(rets.io_count_read, 11);
  CU_ASSERT_EQUAL(rets.io_count_write, 11);
}

static void test_ioworker_update_rets_write()
{
  struct ioworker_io_ctx ctx;
  struct ioworker_rets rets;
  struct timeval now;
  uint32_t ret;

  MOCK_SET(timeval_to_us, 2000);
  
  rets.latency_max_us = 10000;
  ctx.is_read = false;
  rets.io_count_read = 10;
  rets.io_count_write = 11;
  
  ret = ioworker_update_rets(&ctx, &rets, &now);

  CU_ASSERT_EQUAL(rets.latency_max_us, 10000);
  CU_ASSERT_EQUAL(ret, 2000);
  CU_ASSERT_EQUAL(rets.io_count_read, 10);
  CU_ASSERT_EQUAL(rets.io_count_write, 12);
}

static int suite_ioworker_update_rets()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_update_rets_latency_read);
  CU_ADD_TEST(s, test_ioworker_update_rets_latency_write);
  CU_ADD_TEST(s, test_ioworker_update_rets_latency_large_write);
  CU_ADD_TEST(s, test_ioworker_update_rets_read);
  CU_ADD_TEST(s, test_ioworker_update_rets_write);
  
	return 0;
}

static void test_ioworker_update_io_count_per_second_1()
{
  struct ioworker_global_ctx ctx;
  struct ioworker_args args;
  struct ioworker_rets rets;

  rets.io_count_read = 0;
  rets.io_count_write = 1;
  ctx.last_sec = 10;
  ctx.time_next_sec.tv_sec = 1;
  ctx.time_next_sec.tv_usec = 100;
  ctx.io_count_till_last_sec = 0;
  args.io_counter_per_second = malloc(sizeof(uint32_t)*20);
  args.io_counter_per_second[10] = 0;
  
  ioworker_update_io_count_per_second(&ctx, &args, &rets);

  CU_ASSERT_EQUAL(ctx.last_sec, 11);
  CU_ASSERT_EQUAL(ctx.time_next_sec.tv_sec, 2);
  CU_ASSERT_EQUAL(ctx.time_next_sec.tv_usec, 100);
  CU_ASSERT_EQUAL(args.io_counter_per_second[10], 1);
  CU_ASSERT_EQUAL(ctx.io_count_till_last_sec, 1);

  free(args.io_counter_per_second);
}

static void test_ioworker_update_io_count_per_second_100000_long()
{
  struct ioworker_global_ctx ctx;
  struct ioworker_args args;
  struct ioworker_rets rets;

  rets.io_count_read = 30000;
  rets.io_count_write = 80000;
  ctx.last_sec = 500*3600;
  ctx.time_next_sec.tv_sec = 12345;
  ctx.time_next_sec.tv_usec = 0;
  ctx.io_count_till_last_sec = 10000;
  args.io_counter_per_second = malloc(sizeof(uint32_t)*1000*3600);
  args.io_counter_per_second[500*3600] = 0;
  
  ioworker_update_io_count_per_second(&ctx, &args, &rets);

  CU_ASSERT_EQUAL(ctx.last_sec, 500*3600+1);
  CU_ASSERT_EQUAL(ctx.time_next_sec.tv_sec, 12346);
  CU_ASSERT_EQUAL(ctx.time_next_sec.tv_usec, 0);
  CU_ASSERT_EQUAL(args.io_counter_per_second[500*3600], 100000);
  CU_ASSERT_EQUAL(ctx.io_count_till_last_sec, 110000);

  free(args.io_counter_per_second);
}

static int suite_ioworker_update_io_count_per_second()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_update_io_count_per_second_1);
  CU_ADD_TEST(s, test_ioworker_update_io_count_per_second_100000_long);

	return 0;
}


static int test_ioworker_iosize_init_single()
{
  struct ioworker_global_ctx ctx;
  struct ioworker_args args;
  uint32_t ratio = 10;
  
  ctx.args = &args;
  args.lba_size_list_len = 1;
  args.lba_size_list_ratio = &ratio;
  args.lba_size_ratio_sum = 10;
  
  ioworker_iosize_init(&ctx);

  CU_ASSERT_EQUAL(args.lba_size_ratio_sum, 10);
  CU_ASSERT_EQUAL(ctx.sl_table[0], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[1], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[9], 0);
}

static int test_ioworker_iosize_init_dual()
{
  struct ioworker_global_ctx ctx;
  struct ioworker_args args;
  uint32_t ratio[] = {1, 2};
  
  ctx.args = &args;
  args.lba_size_list_len = 2;
  args.lba_size_list_ratio = &ratio[0];
  args.lba_size_ratio_sum = 3;
  
  ioworker_iosize_init(&ctx);

  CU_ASSERT_EQUAL(args.lba_size_ratio_sum, 3);
  CU_ASSERT_EQUAL(ctx.sl_table[0], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[1], 1);
  CU_ASSERT_EQUAL(ctx.sl_table[2], 1);
}

static int test_ioworker_iosize_init_jedec()
{
  struct ioworker_global_ctx ctx;
  struct ioworker_args args;
  uint32_t ratio[] = {4, 1, 1, 1, 1, 1, 1, 67, 10, 7, 3, 3};
  
  ctx.args = &args;
  args.lba_size_list_len = 12;
  args.lba_size_list_ratio = &ratio[0];
  args.lba_size_ratio_sum = 100;
  
  ioworker_iosize_init(&ctx);

  CU_ASSERT_EQUAL(args.lba_size_ratio_sum, 100);
  CU_ASSERT_EQUAL(ctx.sl_table[0], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[1], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[2], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[3], 0);
  CU_ASSERT_EQUAL(ctx.sl_table[4], 1);
  CU_ASSERT_EQUAL(ctx.sl_table[5], 2);
  CU_ASSERT_EQUAL(ctx.sl_table[6], 3);
  CU_ASSERT_EQUAL(ctx.sl_table[7], 4);
  CU_ASSERT_EQUAL(ctx.sl_table[8], 5);
  CU_ASSERT_EQUAL(ctx.sl_table[9], 6);
  CU_ASSERT_EQUAL(ctx.sl_table[10], 7);
  CU_ASSERT_EQUAL(ctx.sl_table[11], 7);
  CU_ASSERT_EQUAL(ctx.sl_table[12], 7);
  CU_ASSERT_EQUAL(ctx.sl_table[76], 7);
  CU_ASSERT_EQUAL(ctx.sl_table[77], 8);
  CU_ASSERT_EQUAL(ctx.sl_table[86], 8);
  CU_ASSERT_EQUAL(ctx.sl_table[87], 9);
  CU_ASSERT_EQUAL(ctx.sl_table[93], 9);
  CU_ASSERT_EQUAL(ctx.sl_table[94], 10);
  CU_ASSERT_EQUAL(ctx.sl_table[95], 10);
  CU_ASSERT_EQUAL(ctx.sl_table[96], 10);
  CU_ASSERT_EQUAL(ctx.sl_table[97], 11);
  CU_ASSERT_EQUAL(ctx.sl_table[98], 11);
  CU_ASSERT_EQUAL(ctx.sl_table[99], 11);
}

static int suite_ioworker_iosize_init()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_iosize_init_single);
  CU_ADD_TEST(s, test_ioworker_iosize_init_dual);
  CU_ADD_TEST(s, test_ioworker_iosize_init_jedec);

	return 0;
}


static void test_ioworker_send_one_lba_seq()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  uint16_t lba_align = 1;
  uint16_t lba_count = 1;
  uint64_t ret;

  args.lba_random = 0;
  args.region_end = 100;
  args.region_start = 0;
  args.lba_step = 1;
  ctx.sequential_lba = 0;

  ret = ioworker_send_one_lba(&args, &ctx, lba_align, lba_count);

  CU_ASSERT_EQUAL(ret, 0);
  CU_ASSERT_EQUAL(ctx.sequential_lba, 1);
}

static void test_ioworker_send_one_lba_seq_end()
{
  struct ioworker_args args;
  struct ioworker_global_ctx ctx;
  uint16_t lba_align = 1;
  uint16_t lba_count = 1;
  uint64_t ret;

  args.lba_random = 0;
  args.region_end = 99;
  args.region_start = 0;
  args.lba_step = 1;
  ctx.sequential_lba = 100;

  ret = ioworker_send_one_lba(&args, &ctx, lba_align, lba_count);

  CU_ASSERT_EQUAL(ret, 0);
  CU_ASSERT_EQUAL(ctx.sequential_lba, 1);
  
  ret = ioworker_send_one_lba(&args, &ctx, lba_align, lba_count);

  CU_ASSERT_EQUAL(ret, 1);
  CU_ASSERT_EQUAL(ctx.sequential_lba, 2);

  lba_align = 4;
  lba_count = 4;
  args.lba_random = 0;
  args.region_end = 100;
  args.region_start = 0;
  args.lba_step = 4;
  ctx.sequential_lba = 100;

  ret = ioworker_send_one_lba(&args, &ctx, lba_align, lba_count);

  CU_ASSERT_EQUAL(ret, 100);
  CU_ASSERT_EQUAL(ctx.sequential_lba, 104);
  
  ret = ioworker_send_one_lba(&args, &ctx, lba_align, lba_count);

  CU_ASSERT_EQUAL(ret, 0);
  CU_ASSERT_EQUAL(ctx.sequential_lba, 4);
}

static int suite_ioworker_send_one_lba()
{
  CU_Suite* s = CU_add_suite(__func__, NULL, NULL);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_send_one_lba_seq);
  CU_ADD_TEST(s, test_ioworker_send_one_lba_seq_end);

	return 0;
}


int main()
{
	unsigned int	num_failures;

	if (CU_initialize_registry() != CUE_SUCCESS) {
		return CU_get_error();
	}

  suite_timeradd_usecond();
  suite_ioworker_distribution_init();
  suite_ioworker_send_one_is_finish();
  suite_ioworker_get_duration();
  suite_ioworker_update_rets();
  suite_ioworker_update_io_count_per_second();
  suite_ioworker_iosize_init();
  suite_ioworker_send_one_lba();
  
  CU_basic_run_tests();
	num_failures = CU_get_number_of_failures();
	CU_cleanup_registry();
	return num_failures;
}
