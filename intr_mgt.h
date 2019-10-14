#include "spdk/nvme.h"

uint32_t intc_get_cmd_vec_info(struct spdk_nvme_qpair *q);
void intc_unmask(struct spdk_nvme_qpair *q);
void intc_mask(struct spdk_nvme_qpair *q);
bool intc_isset(struct spdk_nvme_qpair *q);
void intc_clear(struct spdk_nvme_qpair* q);
void intc_init(struct spdk_nvme_ctrlr *ctrlr);
void intc_fini(struct spdk_nvme_ctrlr *ctrlr);