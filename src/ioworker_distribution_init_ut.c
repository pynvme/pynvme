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

uint32_t timeval_to_us(struct timeval* t)
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

// test cases
static void test_ioworker_distribution_init_1000(void)
{
  uint64_t max_lba = 1000;

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
}

static void test_ioworker_distribution_init_10000(void)
{
  uint64_t max_lba = 10000;

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

}

static void test_ioworker_pass(void)
{
  CU_ASSERT(true);
}


static int ut_init(void)
{
  ctx.args = malloc(sizeof(struct ioworker_args));
  memset(ctx.dl_table, 0, sizeof(ctx.dl_table));
  memset(distribution, 0, sizeof(distribution));

  return 0;
}

static int ut_clear(void)
{
  free(ctx.args);

  return 0;
}

int main()
{
  CU_Suite* s;
	unsigned int	num_failures;

	if (CU_initialize_registry() != CUE_SUCCESS) {
		return CU_get_error();
	}

  s = CU_add_suite("ioworker", ut_init, ut_clear);
	if (s == NULL) {
		CU_cleanup_registry();
		return CU_get_error();
	}

  CU_ADD_TEST(s, test_ioworker_pass);
  CU_ADD_TEST(s, test_ioworker_distribution_init_1000);
  CU_ADD_TEST(s, test_ioworker_distribution_init_10000);
  
  CU_basic_set_mode(CU_BRM_VERBOSE);
  CU_basic_run_tests();
	num_failures = CU_get_number_of_failures();
	CU_cleanup_registry();
	return num_failures;
}
