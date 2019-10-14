#include "spdk/nvme.h"

void intc_unmask(struct spdk_nvme_qpair *q);
void intc_mask(struct spdk_nvme_qpair *q);
bool intc_isset(struct spdk_nvme_qpair *q);
void intc_clear(struct spdk_nvme_qpair* q);
void intc_init(struct spdk_nvme_ctrlr *ctrlr);
void intc_fini(struct spdk_nvme_ctrlr *ctrlr);
void* intc_lookup_ctrl(struct spdk_nvme_ctrlr* ctrlr);
