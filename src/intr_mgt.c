/*-
 *   BSD LICENSE
 *
 *   Copyright (c) Yongqiang Wang <yongqiangwang66@163.com>
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

#include "intr_mgt.h"
#include "../spdk/lib/nvme/nvme_internal.h"


#define INTC_CTRL_NAME   "intc_ctrl_name%p"


//// software MSIx INTC
///////////////////////////////
static uint8_t pcie_find_cap_base_addr(struct spdk_pci_device *pci, uint8_t cid)
{
  uint8_t get_cid = 0;
  uint8_t next_offset = 0;

  spdk_pci_device_cfg_read8(pci, &next_offset, 0x34);
  while (next_offset != 0)
  {
    spdk_pci_device_cfg_read8(pci, &get_cid, next_offset);
    if (get_cid == cid)
    {
      //find the expected cap
      break;
    }

    spdk_pci_device_cfg_read8(pci, &next_offset, next_offset + 1);
  }

  return next_offset;
}

static bool msi_intc_init(struct spdk_nvme_ctrlr *ctrlr, intr_ctrl_t** intr_mgt)
{
  struct spdk_pci_device *pci = spdk_nvme_ctrlr_get_pci_device(ctrlr);
  uint8_t msi_cap_base = 0;
  uint16_t control = 0;
  msi_intr_ctrl *msi_ctrl = NULL;//&intr_ctrl.msi_info;
  intr_ctrl_t* intr_info = NULL;
  uint8_t max_dev_vector_shift = 0;
  uint64_t msg_addr = 0;
  char intc_name[64];

  msi_cap_base = pcie_find_cap_base_addr(pci, 0x05);
  if (msi_cap_base == 0)
  {
    SPDK_WARNLOG("no msi capability found!\n");
    return false;
  }

  // collect intc information of this controller
  snprintf(intc_name, 64, INTC_CTRL_NAME, ctrlr);
  intr_info = spdk_memzone_reserve(intc_name,
                                   (sizeof(uint32_t) * MAX_VECTOR_NUM),
                                   0,
                                   0);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "intr info 0x%lx\n", (uint64_t)intr_info);
  assert(intr_info != NULL);
  msi_ctrl = &intr_info->msi_info;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "cap base value 0x%x\n", msi_cap_base);
  spdk_pci_device_cfg_read16(pci, &control, (msi_cap_base + 2));
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "mc reg value 0x%08x\n", control);
  msi_ctrl->pvm_support = (control & BIT(8));

  //config msg address & msg data
  msg_addr = spdk_vtophys(&intr_info->msg_data[0], NULL);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msg physical addr value 0x%lx\n", msg_addr);
  spdk_pci_device_cfg_write32(pci, (uint32_t)msg_addr, (msi_cap_base + 4));
  spdk_pci_device_cfg_write32(pci, (uint32_t)(msg_addr >> 32), (msi_cap_base + 8));
  //config msi intr msg data
  spdk_pci_device_cfg_write16(pci, 0x0001, msi_cap_base + 0xc);
  //config msg vector number, enable msi interrupt
  max_dev_vector_shift = (control >> 1) & 0xe;
  max_dev_vector_shift = MIN((MAX_VECTOR_NUM_SHIFT-1), max_dev_vector_shift);
  //msi_ctrl->multi_msi_vector = 1 << max_dev_vector_shift;
  intr_info->max_vec_num = (1 << max_dev_vector_shift);
  control |= (max_dev_vector_shift << 4) | BIT(0);
  spdk_pci_device_cfg_write16(pci, control, msi_cap_base + 2);

  intr_info->msi_en = 1;
  *intr_mgt = intr_info;
  return true;
}

static bool msix_intc_init(struct spdk_nvme_ctrlr *ctrlr, intr_ctrl_t** intr_mgt)
{
  struct spdk_pci_device *pci = spdk_nvme_ctrlr_get_pci_device(ctrlr);
  uint8_t msix_base = 0;
  uint16_t control = 0;
  uint32_t bir_val = 0;
  uint32_t bar_offset = 0;
  uint32_t vector_num = 0;
  msix_intr_ctrl* msix_ctrl = NULL;//&intr_ctrl.msix_info;
  msix_entry* msix_table = NULL;
  intr_ctrl_t* intr_info = NULL;
  bool ret = true;
  int rc;
  void *table_addr;
  uint64_t phys_addr;
  uint64_t size;
  char intc_name[64];

  // pynvme: enable msix interrupt
  //SPDK_ERRLOG("msix intr int, intr mgt 0x%lx\n", (uint64_t)intr_mgt);
  msix_base = pcie_find_cap_base_addr(pci, 0x11);
  if (msix_base == 0)
  {
    SPDK_WARNLOG("no msix capability found!\n");
    return false;
  }

  // collect intc information of this controller
  snprintf(intc_name, 64, INTC_CTRL_NAME, ctrlr);
  intr_info = spdk_memzone_reserve(intc_name,
                                   sizeof(intr_ctrl_t),
                                   0,
                                   0);
  assert(intr_info != NULL);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "intr info 0x%lx\n", (uint64_t)intr_info);
  msix_ctrl = &intr_info->msix_info;

  //find address of MSIX table.
  spdk_pci_device_cfg_read32(pci, &bir_val, (msix_base + 4));
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix bir %x\n", bir_val);
  bar_offset = bir_val & (~0x7);
  bir_val = bir_val & 0x7;
  if ((bir_val != 0x0) && (bir_val != 0x04))
  {
    ret = false;
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "mapping MSIX table to an invalid bar, msix init fail, switch the interrupt to msi\n");
    return ret;
  }
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix bir %x, bar offset %x\n", bir_val, bar_offset);

  //find msix capability
  spdk_pci_device_cfg_read16(pci, &control, (msix_base + 2));
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix control: 0x%x\n", control);

  vector_num = (control & 0x7fff) + 1;
  vector_num = MIN(vector_num, MAX_VECTOR_NUM);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "vector_num %d\n", vector_num);
  intr_info->max_vec_num = vector_num;

  //map bar phys_addr to virtual addr
  rc = spdk_pci_device_map_bar(pci, bir_val, &table_addr, &phys_addr, &size);
  assert(rc == 0);

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix table addr %lx\n", (uint64_t)table_addr);
  //init msix_ctrl structure
  msix_ctrl->bir = bir_val;
  msix_ctrl->bir_offset = bar_offset;
  msix_ctrl->phys_addr = phys_addr;
  msix_ctrl->vir_addr = (uintptr_t)table_addr;
  msix_ctrl->size = size;
  msix_ctrl->msix_table = table_addr + bar_offset;

  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix table addr 2 0x%lx\n", (uint64_t)table_addr);
  //config msix table
  msix_table = (msix_entry *)(table_addr + bar_offset);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix table addr %lx\n", (uint64_t)msix_table);

  // fill msix_data address in msix table, one entry for one qpair, disable
  for (uint32_t i = 0; i < vector_num; i++)
  {
    uint64_t addr = spdk_vtophys(&intr_info->msg_data[i], NULL);

    SPDK_DEBUGLOG(SPDK_LOG_NVME, "vec %d, msix data addr %lx\n", i, addr);

    // clear the interrupt
    //cmd_log_queue_table[i].msix_data = 0;
    //cmd_log_queue_table[i].msix_enabled = true;
    intr_info->msg_data[i] = 0;

    // fill the vector table
    msix_table[i].msg_addr = addr;
    msix_table[i].msg_data = 1;
    msix_table[i].mask = 0;
    msix_table[i].rsvd = 0;
  }

  // enable msix
  control |= 0x8000;
  spdk_pci_device_cfg_write16(pci, control, msix_base + 2);

  intr_info->msix_en = 1;
  *intr_mgt = intr_info;
  return ret;
}

void intc_init(struct spdk_nvme_ctrlr *ctrlr)
{
  bool ret;
  
  // interrupt is enabled on PCIe devices only
  assert(ctrlr->trid.trtype == SPDK_NVME_TRANSPORT_PCIE);

  //search msix first, if the operation fail, will switch to msi intr
  ret = msix_intc_init(ctrlr, &ctrlr->pynvme_intc_ctrl);
  if (ret == false)
  {
    ret = msi_intc_init(ctrlr, &ctrlr->pynvme_intc_ctrl);
  }

  assert(ret == true);  // controller must support at least one kind of interrupt
}

static void intc_info_release(struct spdk_nvme_ctrlr* ctrlr)
{
  char intc_name[64];

  snprintf(intc_name, 64, INTC_CTRL_NAME, ctrlr);
  spdk_memzone_free(intc_name);
  ctrlr->pynvme_intc_ctrl = NULL;
}

void* intc_lookup_ctrl(struct spdk_nvme_ctrlr* ctrlr)
{
  char intc_name[64];

  snprintf(intc_name, 64, INTC_CTRL_NAME, ctrlr);
  return spdk_memzone_lookup(intc_name);
}

void intc_fini(struct spdk_nvme_ctrlr *ctrlr)
{
  uint8_t cap_base;
  uint16_t control;
  struct spdk_pci_device *pci = spdk_nvme_ctrlr_get_pci_device(ctrlr);
  intr_ctrl_t *intr_ctrl = ctrlr->pynvme_intc_ctrl;

  // interrupt is enabled on PCIe devices only
  assert(ctrlr->trid.trtype == SPDK_NVME_TRANSPORT_PCIE);
  assert(intr_ctrl != NULL);

  if (intr_ctrl->msix_en == 1)
  {
    // find msix capability
    cap_base = pcie_find_cap_base_addr(pci, 0x11);
    spdk_pci_device_cfg_read16(pci, &control, cap_base + 2);

    // disable msix
    control &= (~0x8000);
    spdk_pci_device_cfg_write16(pci, control, cap_base + 2);
  }
  else if (intr_ctrl->msi_en == 1)
  {
    cap_base = pcie_find_cap_base_addr(pci, 0x05);
    spdk_pci_device_cfg_read16(pci, &control, cap_base + 2);

    //disable msi enable
    control &= (~BIT(0));
    spdk_pci_device_cfg_write16(pci, control, cap_base + 2);
  }
  intc_info_release(ctrlr);
}

static uint16_t intc_get_vec(struct spdk_nvme_qpair* q)
{
  struct spdk_nvme_ctrlr* ctrlr = q->ctrlr;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;

  // interrupt is enabled on PCIe devices only
  assert(q->trtype == SPDK_NVME_TRANSPORT_PCIE);
  assert(intr_ctrl != NULL);

  return (q->intr_vector % intr_ctrl->max_vec_num);
}

void intc_clear(struct spdk_nvme_qpair* q)
{
  struct spdk_nvme_ctrlr* ctrlr = q->ctrlr;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;

  // interrupt is enabled on PCIe devices only
  assert(q->trtype == SPDK_NVME_TRANSPORT_PCIE);
  assert(intr_ctrl != NULL);

  if (intr_ctrl->msix_en != 0)
  {
    intr_ctrl->msg_data[q->id] = 0;
  }
  else if (intr_ctrl->msi_en != 0)
  {
    intr_ctrl->msg_data[0] = 0;
  }
}

bool intc_isset(struct spdk_nvme_qpair *q)
{
  uint8_t vector_id = 0;
  bool ret = true;
  struct spdk_nvme_ctrlr* ctrlr = q->ctrlr;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;
  //struct cmd_log_table_t* cmd_log = (struct cmd_log_table_t*)q->pynvme_cmdlog;

  // interrupt is enabled on PCIe devices only
  assert(q->trtype == SPDK_NVME_TRANSPORT_PCIE);

  vector_id = intc_get_vec(q);
  SPDK_DEBUGLOG(SPDK_LOG_NVME, "vector id %d\n", vector_id);
  if (intr_ctrl->msix_en == 1)
  {
    //vector_id = intc_get_vec(q);//intr_ctrl->qpair_vec[q->id];
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "msix enable\n");
    ret = (intr_ctrl->msg_data[vector_id] != 0);
  }
  else if (intr_ctrl->msi_en == 1)
  {
    //vector_id = intr_ctrl->qpair_vec[q->id];
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "msi vector id %d\n", vector_id);
    ret = (vector_id == (intr_ctrl->msg_data[0] & 0xff));
  }
  return ret;
}

void intc_mask(struct spdk_nvme_qpair *q)
{
  //uint32_t q_id = q->id;
  struct spdk_nvme_ctrlr* ctrlr = q->ctrlr;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;
  //struct cmd_log_table_t* cmd_log = q->pynvme_cmdlog;
  uint32_t vector_id;
  uint32_t raw_val = 0;

  // interrupt is enabled on PCIe devices only
  if (q->trtype == SPDK_NVME_TRANSPORT_PCIE)
  {
    vector_id = intc_get_vec(q);
    if (intr_ctrl->msix_en == 1)
    {
      msix_entry *msix_table = NULL;

      msix_table = (msix_entry *)(intr_ctrl->msix_info.vir_addr + intr_ctrl->msix_info.bir_offset);
      msix_table[vector_id].mask = 1;
    }
    else if (intr_ctrl->msi_en == 1)
    {
      nvme_get_reg32(q->ctrlr, offsetof(struct spdk_nvme_registers, intms), &raw_val);
      raw_val |= BIT(vector_id);
      nvme_set_reg32(q->ctrlr, offsetof(struct spdk_nvme_registers, intms), raw_val);
    }
  }
}

void intc_unmask(struct spdk_nvme_qpair *q)
{
  struct spdk_nvme_ctrlr* ctrlr = q->ctrlr;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;
  uint32_t vector_id;
  uint32_t raw_val;
  msix_entry *msix_table = NULL;

  // interrupt is enabled on PCIe devices only
  if (q->trtype == SPDK_NVME_TRANSPORT_PCIE)
  {
    vector_id = intc_get_vec(q);
    if (intr_ctrl->msix_en == 1)
    {
      msix_table = (msix_entry *)(intr_ctrl->msix_info.vir_addr + intr_ctrl->msix_info.bir_offset);
      msix_table[vector_id].mask = 0;
    }
    else if (intr_ctrl->msi_en == 1)
    {
      raw_val = nvme_get_reg32(q->ctrlr, offsetof(struct spdk_nvme_registers, intmc), &raw_val);
      raw_val |= BIT(vector_id);
      nvme_set_reg32(q->ctrlr, offsetof(struct spdk_nvme_registers, intmc), raw_val);
    }
  }
}

uint32_t intc_get_cmd_vec_info(struct spdk_nvme_qpair *q)
{
  struct spdk_nvme_ctrlr* ctrlr = q->ctrlr;
  intr_ctrl_t* intr_ctrl = ctrlr->pynvme_intc_ctrl;
  uint16_t vector_id = 0;

  if (intr_ctrl->msi_en || intr_ctrl->msix_en)
  {
    vector_id = intc_get_vec(q);
    SPDK_DEBUGLOG(SPDK_LOG_NVME, "vector id: %d\n", vector_id);
  }

  return vector_id;
}
