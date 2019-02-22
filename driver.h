/*-
 *   BSD LICENSE
 *
 *   Copyright (c) Crane Che <cranechu@gmail.com>
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


typedef struct spdk_nvme_qpair qpair;
typedef struct spdk_nvme_ctrlr ctrlr;
typedef struct spdk_nvme_ns namespace;
typedef struct spdk_pci_device pcie;
typedef struct spdk_nvme_cpl cpl;


typedef struct ioworker_args
{
  unsigned long lba_start;
  unsigned short lba_size;
  unsigned short lba_align;
  int lba_random;
  unsigned long region_start;
  unsigned long region_end;
  unsigned short read_percentage;
  unsigned int iops;
  unsigned long io_count;
  unsigned int seconds;
  unsigned int qdepth;
  unsigned int* io_counter_per_second;
  unsigned int* io_counter_per_latency;
} ioworker_args;

typedef struct ioworker_rets
{
  unsigned long io_count_read;
  unsigned long io_count_write;
  unsigned int mseconds;
  unsigned int latency_max_us;  
  unsigned short error;
} ioworker_rets;
  
extern int driver_init(void);
extern int driver_fini(void);
extern void driver_config(uint64_t cfg_word);

extern pcie* pcie_init(struct spdk_nvme_ctrlr* ctrlr);
extern int pcie_cfg_read8(struct spdk_pci_device* pci,
                          unsigned char* value,
                          unsigned int offset);
extern int pcie_cfg_write8(struct spdk_pci_device* pci,
                           unsigned char value,
                           unsigned int offset);

extern ctrlr* nvme_init(char * traddr);
extern ctrlr* nvme_probe(char * traddr);
extern int nvme_fini(struct spdk_nvme_ctrlr* c);
extern int nvme_set_reg32(struct spdk_nvme_ctrlr* ctrlr,
                          unsigned int offset,
                          unsigned int value);
extern int nvme_get_reg32(struct spdk_nvme_ctrlr* ctrlr,
                          unsigned int offset,
                          unsigned int* value);

extern int nvme_wait_completion_admin(struct spdk_nvme_ctrlr* c);
extern void nvme_cmd_cb_print_cpl(void* qpair, const struct spdk_nvme_cpl* cpl);


typedef void (*cmd_cb_func)(void* cb_arg,
                                 const struct spdk_nvme_cpl* cpl);
extern int nvme_send_cmd_raw(struct spdk_nvme_ctrlr* ctrlr,
                             struct spdk_nvme_qpair *qpair,
                             unsigned int opcode,
                             unsigned int nsid,
                             void* buf, size_t len, 
                             unsigned int cdw10,
                             unsigned int cdw11,
                             unsigned int cdw12,
                             unsigned int cdw13,
                             unsigned int cdw14,
                             unsigned int cdw15,
                             cmd_cb_func cb_fn,
                             void* cb_arg);
extern int nvme_cpl_is_error(const struct spdk_nvme_cpl* cpl);

typedef void (*spdk_nvme_aer_cb)(void* aer_cb_arg,
                                 const struct spdk_nvme_cpl* cpl);
extern void nvme_register_aer_cb(struct spdk_nvme_ctrlr* ctrlr,
                                 spdk_nvme_aer_cb aer_cb,
                                 void* aer_cb_arg);
typedef void (*spdk_nvme_timeout_cb)(void *cb_arg,
				     struct spdk_nvme_ctrlr *ctrlr,
				     struct spdk_nvme_qpair *qpair,
				     uint16_t cid);
extern void nvme_register_timeout_cb(struct spdk_nvme_ctrlr* ctrlr,
                                     spdk_nvme_timeout_cb timeout_cb,
                                     unsigned int timeout);

extern void* buffer_init(size_t bytes, uint64_t *phys_addr);
extern void buffer_fini(void* buf);

extern qpair* qpair_create(struct spdk_nvme_ctrlr *c,
                           int prio, int depth);
extern int qpair_wait_completion(struct spdk_nvme_qpair *q, uint32_t max_completions);
extern int qpair_get_id(struct spdk_nvme_qpair* q);
extern int qpair_free(struct spdk_nvme_qpair* q);
    
extern namespace* ns_init(ctrlr* c, unsigned int nsid);
extern int ns_cmd_read_write(int is_read, 
                             struct spdk_nvme_ns* ns,
                             struct spdk_nvme_qpair *qpair,
                             void *buf,
                             size_t len,
                             uint64_t lba,
                             uint16_t lba_count,
                             uint32_t io_flags,
                             cmd_cb_func cb_fn,
                             void* cb_arg);
extern uint32_t ns_get_sector_size(namespace* ns);
extern uint64_t ns_get_num_sectors(namespace* ns);
extern int ns_fini(struct spdk_nvme_ns* ns);

extern void crc32_clear(uint64_t lba, uint64_t lba_count, int sanitize, int uncorr);

extern int ioworker_entry(struct spdk_nvme_ns* ns,
                          struct spdk_nvme_qpair *qpair,
                          ioworker_args* args,
                          ioworker_rets* rets);
extern void* ioworker_progress_init(char* name);
extern void* ioworker_progress_find(char* name);
extern void ioworker_progress_fini(char* name);

extern void log_buf_dump(const char* header, const void* buf, size_t len);
extern void log_cmd_dump(struct spdk_nvme_qpair* qpair, size_t count);
extern void log_cmd_dump_admin(struct spdk_nvme_ctrlr* ctrlr, size_t count);

extern const char* cmd_name(uint8_t opc, int set);
