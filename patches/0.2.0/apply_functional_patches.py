#!/usr/bin/env python3
"""Functional patches for Xe-LP (Display 13) laptops with a 6-bpc internal eDP panel (tested: i3-1215U, 0x46B3).
Works on WhateverXe 0.6.1 (68a2427) and 0.8.0. Each edit has one anchor variant per upstream layout.
 1. Accept 6-bpc firmware eDP scanout (dpSource, linearPlan, framebuffer-memory inspect) + CPU test.
 2. Let XE::display13SSTPort() accept an eDP panel port whose field +0x550 is 0 (Combo DDI A/B).
Includes one optional, CPU-only diagnostic (N97NativeBlockReason). Run from the repo root. Idempotent; a file is written only if all its edits match."""
import sys,os
NO_DIAG='--no-diagnostic' in sys.argv   # build the functional patch without the optional diagnostic code
def edit(path,edits):
    if not os.path.exists(path): print("MISSING:",path); return False
    raw=open(path,"rb").read().decode("utf-8"); crlf="\r\n" in raw; s=raw.replace("\r\n","\n"); changed=False
    for name,variants in edits:
        if NO_DIAG and name.startswith("[optional] "): print("  skipped (--no-diagnostic):",name); continue
        if any(new in s for _,new in variants): print("  already applied:",name); continue
        hit=[(o,n) for o,n in variants if s.count(o)==1]
        if not hit and name.startswith("[optional] "): print("  skipped (optional, anchor not found): %s"%name); continue
        if not hit: print("  FAILED (no anchor variant matched exactly once): %s"%name); return False
        o,n=hit[0]; s=s.replace(o,n); changed=True; print("  applied: %s  [layout %d of %d]"%(name,variants.index((o,n))+1,len(variants)))
    if changed: open(path,"wb").write((s.replace("\n","\r\n") if crlf else s).encode("utf-8"))
    return True
ok=True
print("WhateverXe/kern_alderlake_n.hpp")
ok&=edit("WhateverXe/kern_alderlake_n.hpp",[
 ("dpSource: allow 6 bpc on panel path",[(
  "    return (trans&0xFF700000U)==(0x82000000U|((ddi+1)<<27)) &&\n        !(trans&((1U<<15)|(1U<<9))) && !ctl2 &&",
  "    // Transcoder colour depth (bits 22:20): 0 = 8 bpc, 2 = 6 bpc. Internal eDP\n"
  "    // panels commonly run 6 bpc with dithering from the 8-bpc linear plane.\n"
  "    // Accept 6 bpc only for the panel path; external DP keeps the 8-bpc rule.\n"
  "    // The value is captured in the readout and re-checked by dpSourceUnchanged.\n"
  "    const unsigned bpc=(trans>>20)&7;\n"
  "    return (trans&0xFF000000U)==(0x82000000U|((ddi+1)<<27)) &&\n"
  "        (bpc==0 || (panel && bpc==2)) &&\n"
  "        !(trans&((1U<<15)|(1U<<9))) && !ctl2 &&")]),
 ("linearPlan: allow 6 bpc for eDP",[(
  "       ((trans>>20)&7)!=0 || (pipeConf&0xC0000000)!=0xC0000000 ||",
  "       (((trans>>20)&7)!=0 && !(protocol==GOPProtocol::EDP && ((trans>>20)&7)==2)) ||\n       (pipeConf&0xC0000000)!=0xC0000000 ||")])])
print("WhateverXe/kern_display13_fb_memory.hpp")
ok&=edit("WhateverXe/kern_display13_fb_memory.hpp",[
 ("inspect: allow 6 bpc for eDP boot scanout",[
  # 0.6.1 layout
  ("(dp ? ((trans>>24)&7)!=2 : ((trans>>24)&7)>1) || ((trans>>20)&7) || (conf&0xC0000000)!=0xC0000000 ||",
   "(dp ? ((trans>>24)&7)!=2 : ((trans>>24)&7)>1) ||\n            (((trans>>20)&7) && !(dp && panel && ((trans>>20)&7)==2)) || (conf&0xC0000000)!=0xC0000000 ||"),
  # 0.8.0 layout (combined 'source' expression)
  ("(dp ? ((trans>>24)&7)==2 : ((trans>>24)&7)<=1) && !((trans>>20)&7);",
   "(dp ? ((trans>>24)&7)==2 : ((trans>>24)&7)<=1) &&\n            (!((trans>>20)&7) || (dp && panel && ((trans>>20)&7)==2));")])])
print("WhateverXe/kern_xe.cpp")
ok&=edit("WhateverXe/kern_xe.cpp",[
 ("display13SSTPort: accept eDP port with field 0x550 == 0",[
  # 0.6.1 layout
  ("Display13FBMemory::field<uint32_t>(p,0x550)!=(config[0]>=3?4U:1U)",
   "(Display13FBMemory::field<uint32_t>(p,0x550)!=(config[0]>=3?4U:1U) && /* eDP port field 0x550 */"
   "!(config[0]<2 && (s->adlnOutputWiring.panel&(1U<<config[0])) && !Display13FBMemory::field<uint32_t>(p,0x550)))"),
  # 0.8.0 layout (adds a Type-C case)
  ("Display13FBMemory::field<uint32_t>(p,0x550)!=(config[0]>=3?((s->adlnOutputWiring.typeC&(1U<<config[0]))?3U:4U):1U)",
   "(Display13FBMemory::field<uint32_t>(p,0x550)!=(config[0]>=3?((s->adlnOutputWiring.typeC&(1U<<config[0]))?3U:4U):1U) && /* eDP port field 0x550 */"
   "!(config[0]<2 && (s->adlnOutputWiring.panel&(1U<<config[0])) && !Display13FBMemory::field<uint32_t>(p,0x550)))")])
 ,("[optional] N97NativeBlockReason diagnostic (why the native start is blocked)",[(
  'pci->setProperty("N97NativeReservedGGTT",prefix);',
  'pci->setProperty("N97NativeReservedGGTT",prefix);\n'
  '        { // Diagnostic only: record why the native start is (not) allowed. CPU-only; no extra hardware access.\n'
  '            uint64_t why[8] {1};\n'
  '            why[1]=(!aperture ? 1ULL<<0 : 0) | ((aperture && aperture->getLength()!=0x10000000) ? 1ULL<<1 : 0) |\n'
  '                (page_size!=4096 ? 1ULL<<2 : 0) | (!physicalOptions ? 1ULL<<3 : 0) |\n'
  '                ((pci->configRead16(4)&6)!=6 ? 1ULL<<4 : 0) | (!checkKernelArgument("-allow3d") ? 1ULL<<5 : 0) |\n'
  '                (!checkKernelArgument("-disablegfxfirmware") ? 1ULL<<6 : 0) |\n'
  '                (checkKernelArgument("-wex-adln-scanout") ? 1ULL<<7 : 0) | (checkKernelArgument("-wex-adln-gpu") ? 1ULL<<8 : 0) |\n'
  '                (!prefix ? 1ULL<<16 : 0) | (!renderReady ? 1ULL<<17 : 0);\n'
  '            why[2]=sourceProof[3];why[3]=sourceProof[2];why[4]=bootDDI;\n'
  '            why[5]=aperture ? aperture->getLength() : 0;why[6]=mapperOptions;why[7]=systemMapper;\n'
  '            pci->setProperty("N97NativeBlockReason",why,sizeof(why));\n'
  '            if(why[1])SYSLOG("igfx","Native start blocked: reason mask=%llx linearPlan=%llu protocol=%llu ddi=%llu",why[1],why[2],why[3],why[4]);\n'
  '        }')])]) 
print("tests/display13_linear_dp.cpp")
ok&=edit("tests/display13_linear_dp.cpp",[
 ("add 6-bpc eDP test",[(
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
  "    auto bad=firmware(0,0,4,true);bad.regs[0x60540]=0x80000000;\n")])])
print("\nALL FUNCTIONAL PATCHES APPLIED" if ok else "\nSOME EDITS FAILED - nothing was written for the failing file; send the messages above")
sys.exit(0 if ok else 1)
