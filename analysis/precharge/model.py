"""Bounded, non-vendor stdlib time-domain screening; not hardware qualification.
Forward Euler with dt convergence test. Source is Thevenin R plus current clips.
AUX is a UVLO hysteretic constant-power load with finite startup envelope.
All unspecified loads/timing are design allocations, NOT measured components.
"""
from dataclasses import dataclass, asdict
import json

@dataclass
class Config:
    pack_v: float = 58.4
    cap_f: float = .0015  # entry-milestone assembled ceiling
    precharge_ohm: float = 100
    bleed_ohm: float = 10000
    source_ohm: float = .15  # assumed, must measure minimum AND maximum
    main_ohm: float = .012  # screening pair resistance, not hot rating
    source_limit_a: float = 15  # assumed upstream supply limit; not provided by switch
    charge_limit_a: float = 2  # hypothetical external BMS/source acceptance
    controller_w: float = .5  # protected pack-side allocation
    sink_w: float = .1  # bus-input budget for independent sink control only
    aux_run_a: float = .1  # 12 V output allocation
    surge_a: float = .3  # 12 V startup current allocation
    surge_s: float = .03
    efficiency: float = .8
    aux_on_v: float = 30
    aux_off_v: float = 28
    delayed_aux: bool = True
    initial_bus_v: float = 0
    short_ohm: float = 0
    regen_a: float = 0
    regen_start_s: float = 0
    charge_allowed: bool = True
    welded: bool = False
    dt_s: float = .00005
    duration_s: float = 3

def simulate(c=Config()):
    v=c.initial_bus_v
    state='CHECK'; fault=''; ready=0.; close=None; mismatch=None
    aux=False; aux_age=0.; ep=ed=ec=0.; peak=0.; vmax=v; dump=False
    valid=36 <= c.pack_v <= 58.4
    if valid and v>c.pack_v+1: fault='hot_bus'; state='FAULT'
    for n in range(int(c.duration_s/c.dt_s)):
        t=n*c.dt_s
        regen=c.regen_a if t >= c.regen_start_s else 0.
        if state=='CHECK' and t>=.02:
            if c.welded: fault='unexpected_connection'; state='FAULT'
            elif v>c.pack_v+1 and valid: fault='hot_bus'; state='FAULT'
            elif valid: state='PRE'
        if state=='PRE':
            ready=ready+c.dt_s if abs(c.pack_v-v)<1 else 0
            if ready>=.02:
                state='MAIN'; close=t; mismatch=c.pack_v-v
            elif t>=1.5: fault='timeout'; state='FAULT'
        if state=='MAIN' and close is not None and t-close>=.02: state='RUN'
        if state in ('MAIN','RUN') and regen>0 and not c.charge_allowed:
            fault='charge_refused'; state='FAULT'
        main=(state in ('MAIN','RUN') or c.welded) and valid
        pre=state=='PRE'
        # A separate small always-bus-powered sink supply is allocated 0.1 W.
        # Main aux is inhibited, sink is NEVER inhibited by pack sequencing.
        enable=(not c.delayed_aux or state=='RUN')
        if not enable or v<c.aux_off_v: aux=False; aux_age=0
        elif v>=c.aux_on_v: aux=True
        load=c.sink_w/max(v,6) if v>=15 else 0
        if aux:
            aux_age+=c.dt_s
            load+=12*(c.surge_a if aux_age<c.surge_s else c.aux_run_a)/c.efficiency/max(v,6)
        # Sink standby consumption is included, not silently removed.
        ip=0.
        if main or pre:
            resistance=c.source_ohm+(c.main_ohm if main else c.precharge_ohm)
            headroom=max(0,c.source_limit_a-c.controller_w/max(c.pack_v,1))
            ip=max(-c.charge_limit_a if c.charge_allowed else 0,
                   min(headroom,(c.pack_v-v)/resistance))
        if pre: ep+=ip*ip*c.precharge_ohm*c.dt_s
        if ip<0: ec+=-ip*c.pack_v*c.dt_s
        peak=max(peak,abs(ip))
        if v>=60: dump=True
        elif v<=59: dump=False
        sink=v/9.4 if dump and v>=15 else 0
        ed+=sink*v*c.dt_s
        dv=(ip+regen-load-v/c.bleed_ohm-sink-(v/c.short_ohm if c.short_ohm else 0))/c.cap_f
        v=max(0,v+dv*c.dt_s); vmax=max(vmax,v)
    return dict(run=state=='RUN',state=state,fault=fault,close_s=close,
                close_mismatch_v=mismatch,final_bus_v=v,max_bus_v=vmax,
                precharge_j=ep,dump_j=ed,charge_j=ec,peak_pack_a=peak)

if __name__=='__main__':
    cases={'delayed':Config(),'early_bus_aux':Config(delayed_aux=False),
           'short':Config(short_ohm=1),'limited':Config(source_limit_a=.03),
           'pm_no_pack':Config(pack_v=0,regen_a=1),
           'refused_regen':Config(regen_a=1,regen_start_s=1.2,charge_allowed=False),
           'accepted_regen':Config(regen_a=1,regen_start_s=1.2),'welded':Config(welded=True)}
    print(json.dumps({k:simulate(v) for k,v in cases.items()},indent=2))
