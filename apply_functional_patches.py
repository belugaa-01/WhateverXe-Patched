#!/usr/bin/env python3
"""Functional patches for Alder Lake-U (i3-1215U, 0x46B3) on WhateverXe 0.6.1 (commit 68a2427).
 1. Accept 6-bpc firmware eDP scanout (dpSource, linearPlan, framebuffer-memory inspect) + CPU test.
 2. Let XE::display13SSTPort() accept an eDP panel port whose field +0x550 is 0 (Combo DDI A/B).
No diagnostic code. Run from the repo root. Idempotent; each file is written only if all its edits match."""
import sys,os
def edit(path,pairs):
    if not os.path.exists(path): print("MISSING:",path); return False
    raw=open(path,"rb").read().decode("utf-8"); crlf="\r\n" in raw; s=raw.replace("\r\n","\n"); changed=False
    for name,old,new in pairs:
        if new in s: print("  already applied:",name); continue
        if s.count(old)!=1: print("  FAILED (anchor found %d times, need 1): %s"%(s.count(old),name)); return False
        s=s.replace(old,new); changed=True; print("  applied:",name)
    if changed: open(path,"wb").write((s.replace("\n","\r\n") if crlf else s).encode("utf-8"))
    return True
ok=True
print("WhateverXe/kern_alderlake_n.hpp")
ok&=edit("WhateverXe/kern_alderlake_n.hpp",[
 ("dpSource: allow 6 bpc on panel path",
  "    return (trans&0xFF700000U)==(0x82000000U|((ddi+1)<<27)) &&\n        !(trans&((1U<<15)|(1U<<9))) && !ctl2 &&",
  "    // Transcoder colour depth (bits 22:20): 0 = 8 bpc, 2 = 6 bpc. Internal eDP\n"
  "    // panels commonly run 6 bpc with dithering from the 8-bpc linear plane.\n"
  "    // Accept 6 bpc only for the panel path; external DP keeps the 8-bpc rule.\n"
  "    // The value is captured in the readout and re-checked by dpSourceUnchanged.\n"
  "    const unsigned bpc=(trans>>20)&7;\n"
  "    return (trans&0xFF000000U)==(0x82000000U|((ddi+1)<<27)) &&\n"
  "        (bpc==0 || (panel && bpc==2)) &&\n"
  "        !(trans&((1U<<15)|(1U<<9))) && !ctl2 &&"),
 ("linearPlan: allow 6 bpc for eDP",
  "       ((trans>>20)&7)!=0 || (pipeConf&0xC0000000)!=0xC0000000 ||",
  "       (((trans>>20)&7)!=0 && !(protocol==GOPProtocol::EDP && ((trans>>20)&7)==2)) ||\n       (pipeConf&0xC0000000)!=0xC0000000 ||")])
print("WhateverXe/kern_display13_fb_memory.hpp")
ok&=edit("WhateverXe/kern_display13_fb_memory.hpp",[
 ("inspect: allow 6 bpc for eDP boot scanout",
  "(dp ? ((trans>>24)&7)!=2 : ((trans>>24)&7)>1) || ((trans>>20)&7) || (conf&0xC0000000)!=0xC0000000 ||",
  "(dp ? ((trans>>24)&7)!=2 : ((trans>>24)&7)>1) ||\n            (((trans>>20)&7) && !(dp && panel && ((trans>>20)&7)==2)) || (conf&0xC0000000)!=0xC0000000 ||")])
print("WhateverXe/kern_xe.cpp")
ok&=edit("WhateverXe/kern_xe.cpp",[
 ("display13SSTPort: accept eDP port with field 0x550 == 0",
  "Display13FBMemory::field<uint32_t>(p,0x550)!=(config[0]>=3?4U:1U)",
  "(Display13FBMemory::field<uint32_t>(p,0x550)!=(config[0]>=3?4U:1U) && /* eDP port field 0x550 */"
  "!(config[0]<2 && (s->adlnOutputWiring.panel&(1U<<config[0])) && !Display13FBMemory::field<uint32_t>(p,0x550)))")])
print("tests/display13_linear_dp.cpp")
ok&=edit("tests/display13_linear_dp.cpp",[
 ("add 6-bpc eDP test",
  "    auto bad=firmware(0,0,4,true);bad.regs[0x60540]=0x80000000;\n",
  "    // eDP panels often run 6 bpc (TRANS_DDI_FUNC_CTL bits 22:20 = 2) with dithering from the\n"
  "    // 8-bpc plane. Accept it only as a panel source; every other depth, and external DP, stays rejected.\n"
  "    for(unsigned ddi=0;ddi<2;++ddi)for(unsigned pipe=0;pipe<3;++pipe)for(unsigned bpc=1;bpc<8;++bpc) {\n"
  "        auto io=firmware(pipe,ddi,2,true);io.regs[0x60400+0x1000*pipe]|=bpc<<20;\n"
  "        auto boot=readDisplay(io,true);LinearPlan plan;const bool sixBit=bpc==2;\n"
  "        assert(dpSource(boot,pipe,ddi,nullptr,true)==sixBit);\n"
  "        assert(!dpSource(boot,pipe,ddi));\n"
  "        assert(linearPlan(boot,plan,ddi,GOPProtocol::EDP)==(sixBit?LinearStatus::Ready:LinearStatus::InvalidDPSource));\n"
  "        assert(linearPlan(boot,plan,ddi,GOPProtocol::DP)==LinearStatus::InvalidDPSource);\n"
  "        if(sixBit) {\n"
  "            auto r=reinitializeLinear(io,boot,true,ddi,GOPProtocol::EDP);\n"
  "            assert(r.status==LinearStatus::Success && dpSourceUnchanged(io,boot,pipe,ddi,0,nullptr,true));\n"
  "        }\n"
  "    }\n"
  "    auto bad=firmware(0,0,4,true);bad.regs[0x60540]=0x80000000;\n")])
print("\nALL FUNCTIONAL PATCHES APPLIED" if ok else "\nSOME EDITS FAILED - see messages above")
sys.exit(0 if ok else 1)
