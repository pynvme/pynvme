#
#  BSD LICENSE
#
#  Copyright (c) Crane Chu <cranechu@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions
#  are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#    * Neither the name of Intel Corporation nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


cdef extern from "driver.h":
    ctypedef struct qpair:
        pass
    ctypedef struct ctrlr:
        pass
    ctypedef struct namespace:
        pass
    ctypedef struct pcie:
        pass
    ctypedef struct cpl:
        pass
    ctypedef struct ioworker_args:
        unsigned long lba_start
        unsigned short lba_size
        unsigned short lba_align
        bint lba_random
        unsigned long region_start
        unsigned long region_end
        unsigned short read_percentage
        unsigned int iops
        unsigned long io_count
        unsigned int seconds
        unsigned int qdepth
        unsigned int* io_counter_per_second
        unsigned int* io_counter_per_latency
    ctypedef struct ioworker_rets:
        unsigned long io_count_read
        unsigned long io_count_write
        unsigned int mseconds
        unsigned int latency_max_us
        unsigned short error

    ctypedef void(*cmd_cb_func)(void * cmd_cb_arg, const cpl * cpl)
    ctypedef void(*aer_cb_func)(void * are_cb_arg, const cpl * cpl)
    ctypedef void(*timeout_cb_func)(void * cb_arg, ctrlr * ctrlr,
                                    qpair * qpair, unsigned short cid)

    int driver_init()
    int driver_fini()
    unsigned long driver_config(unsigned long cfg_word)

    pcie * pcie_init(ctrlr * c)
    int pcie_cfg_read8(pcie * pci,
                       unsigned char * value,
                       unsigned int offset)
    int pcie_cfg_write8(pcie * pci,
                        unsigned char value,
                        unsigned int offset)

    ctrlr * nvme_init(char * traddr, unsigned int port)
    int nvme_fini(ctrlr * c)
    int nvme_set_reg32(ctrlr * c,
                       unsigned int offset,
                       unsigned int value)
    int nvme_get_reg32(ctrlr * c,
                       unsigned int offset,
                       unsigned int * value)
    int nvme_set_reg64(ctrlr * c,
                       unsigned int offset,
                       unsigned long value)
    int nvme_get_reg64(ctrlr * c,
                       unsigned int offset,
                       unsigned long * value)

    void nvme_deallocate_ranges(namespace *c,
                                void * buf, unsigned int count)
    int nvme_wait_completion_admin(ctrlr * c)
    void nvme_cmd_cb_print_cpl(void * qpair, const cpl * cpl)
    int nvme_send_cmd_raw(ctrlr * c,
                          qpair * qpair,
                          unsigned int cdw0,
                          unsigned int nsid,
                          void * buf, size_t len,
                          unsigned int cdw10,
                          unsigned int cdw11,
                          unsigned int cdw12,
                          unsigned int cdw13,
                          unsigned int cdw14,
                          unsigned int cdw15,
                          cmd_cb_func cb_fn,
                          void * cb_arg)
    bint nvme_cpl_is_error(const cpl * cpl)
    namespace * nvme_get_ns(ctrlr * c, unsigned int nsid)

    void nvme_register_aer_cb(ctrlr * ctrlr,
                              aer_cb_func aer_cb,
                              void * aer_cb_arg)
    void nvme_register_timeout_cb(ctrlr * ctrlr,
                                  timeout_cb_func timeout_cb,
                                  unsigned int timeout)

    void * buffer_init(size_t bytes, unsigned long* phys_addr)
    void buffer_fini(void * buf)

    qpair * qpair_create(ctrlr * c, int prio, int depth)
    int qpair_wait_completion(qpair * q, unsigned int max_completions)
    int qpair_get_id(qpair * q)
    int qpair_free(qpair * q)

    namespace * ns_init(ctrlr * c, unsigned int nsid)
    int ns_refresh(namespace * ns, unsigned int nsid, ctrlr * c)
    int ns_cmd_read_write(bint is_read,
                          namespace * ns,
                          qpair * qpair,
                          void * buf,
                          size_t len,
                          unsigned long lba,
                          unsigned int lba_count,
                          unsigned int io_flags,
                          cmd_cb_func cb_fn,
                          void * cb_arg)
    unsigned int ns_get_sector_size(namespace * ns)
    unsigned long ns_get_num_sectors(namespace * ns)
    int ns_fini(namespace * ns)
    void ns_crc32_clear(namespace * ns, unsigned long lba, unsigned long lba_count, bint sanitize, bint uncorr)

    int ioworker_entry(namespace* ns,
                       qpair* qpair,
                       ioworker_args* args,
                       ioworker_rets* rets)

    char* log_buf_dump(const char * header, const void * buf, size_t len)
    void log_cmd_dump(qpair * qpair, size_t count)
    void log_cmd_dump_admin(ctrlr * ctrlr, size_t count)

    const char* cmd_name(unsigned char opc, int set)

    void intc_clear(qpair * q)
    bint intc_isset(qpair * q)
    void intc_mask(qpair * q)
    void intc_unmask(qpair * q)
