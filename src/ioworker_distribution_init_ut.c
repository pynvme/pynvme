
#include "spdk_cunit.h"
#include "driver.h"

#include "ioworker.c"


uint64_t
spdk_nvme_ns_get_num_sectors(struct spdk_nvme_ns *ns)
{
  return 0;
}


void test_ioworker_distribution_init(void)
{

}

void *
spdk_dma_zmalloc(size_t size, size_t align, uint64_t *phys_addr)
{
  return NULL;
}


int main()
{
  CU_Suite* s;
  
  CU_initialize_registry();
  s = CU_add_suite("ioworker", NULL, NULL);
  CU_add_test(s, "first", test_ioworker_distribution_init);
  CU_basic_set_mode(CU_BRM_VERBOSE);
  CU_basic_run_tests();
  CU_cleanup_registry();
}
