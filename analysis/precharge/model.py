"""Bounded, non-vendor stdlib time-domain screening; not hardware qualification.
Forward Euler with dt convergence test. Source is Thevenin R plus current clips.
AUX is a UVLO hysteretic constant-power load with finite startup envelope.
All unspecified loads/timing are design allocations, NOT measured components.
"""
from dataclasses import dataclass, asdict
import json
from power_budget import CTRL_INPUT_W, SINK_INPUT_W, BUS_LEAKAGE_W, SINK_STARTUP_W, SINK_STARTUP_S

@dataclass
class Config:
    pack_v: float = 58.4
    cap_f: float = .0015  # entry-milestone assembled ceiling
    precharge_ohm: float = 22
    bleed_ohm: float = 10000
    source_ohm: float = .15  # assumed, must measure minimum AND maximum
    main_ohm: float = .012  # screening pair resistance, not hot rating
    source_limit_a: float = 15  # assumed upstream supply limit; not provided by switch
    charge_limit_a: float = 2  # hypothetical external BMS/source acceptance
    controller_w: float = CTRL_INPUT_W  # protected pack-side allocation
    sink_w: float = SINK_INPUT_W  # bus-input budget for independent sink control only
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
    welded: bool = False  # physical bypass fixture, NOT diagnostic oracle
    off_path_alarm: bool = False  # measured external diagnostic input
    main_path_available: bool = True
    pm_quiet_valid: bool = True
    gate_valid: bool = True  # external monitor input, not implemented hardware
    diagnostic_load_valid: bool = True
    sink_on_v: float = 17.36
    sink_off_v: float = 16.13
    timeout_s: float = .300
    dt_s: float = .00005
    duration_s: float = 3

def simulate(c=Config()):
    v=c.initial_bus_v
    state='CHECK'; fault=''; ready=0.; close=None; mismatch=None
    aux=False; aux_age=0.; ep=ed=ec=0.; peak=0.; vmax=v; dump=False
    sink_on=False; sink_age=0.; sink_starts=0; esink=0.; ebus=0.; eseries=0.; ebleed=0.; eaux=0.
    valid=36 <= c.pack_v <= 58.4
    if valid and v>c.pack_v+1: fault='hot_bus'; state='FAULT'
    for n in range(int(c.duration_s/c.dt_s)):
        t=n*c.dt_s
        regen=c.regen_a if t >= c.regen_start_s else 0.
        if state=='CHECK' and t>=.02:
            if c.off_path_alarm: fault='unexpected_connection'; state='FAULT'
            elif v>c.pack_v+1 and valid: fault='hot_bus'; state='FAULT'
            elif valid: state='PRE'
        if state=='PRE':
            ready=ready+c.dt_s if abs(c.pack_v-v)<1 else 0
            if ready>=.02:
                state='MAIN'; close=t; mismatch=c.pack_v-v
            elif t>=c.timeout_s: fault='timeout'; state='FAULT'
        if state in ('PRE','MAIN') and t>=c.timeout_s:
            fault='timeout'; state='FAULT'
        if state=='MAIN' and close is not None and t-close>=.060:
            if c.gate_valid and c.pm_quiet_valid and c.diagnostic_load_valid and abs(c.pack_v-v)<.30:
                state='RUN'
            else: fault='main_not_proven'; state='FAULT'
        if state in ('MAIN','RUN') and regen>0 and not c.charge_allowed:
            fault='charge_refused'; state='FAULT'
        main=((state in ('MAIN','RUN') and c.main_path_available) or c.welded) and valid
        pre=state=='PRE' or (state=='MAIN' and t-close<.020)
        # Component-derived sink supply stays bus-powered; availability is not guaranteed.
        # Main aux is inhibited, sink is NEVER inhibited by pack sequencing.
        enable=(not c.delayed_aux or state=='RUN')
        if not enable or v<c.aux_off_v: aux=False; aux_age=0
        elif v>=c.aux_on_v: aux=True
        if v<c.sink_off_v: sink_on=False; sink_age=0.
        elif v>=c.sink_on_v and not sink_on: sink_on=True; sink_starts+=1
        sink_power=0.
        if sink_on:
            sink_age+=c.dt_s
            sink_power=SINK_STARTUP_W if sink_age<SINK_STARTUP_S else c.sink_w
        load=(sink_power+BUS_LEAKAGE_W)/max(v,6) if v>=6 else 0
        esink+=load*v*c.dt_s
        if state=='MAIN' and t-close>=.020 and c.diagnostic_load_valid:
            load+=v/330

        if aux:
            aux_age+=c.dt_s
            load+=12*(c.surge_a if aux_age<c.surge_s else c.aux_run_a)/c.efficiency/max(v,6)
        eaux+=load*v*c.dt_s
        # Total load energy includes startup and diagnostic pulse.
        ip=0.; resistance=0.
        if main or pre:
            resistance=c.source_ohm+(c.main_ohm if main else c.precharge_ohm)
            headroom=max(0,c.source_limit_a-c.controller_w/max(c.pack_v,1))
            ip=max(-c.charge_limit_a if c.charge_allowed else 0,
                   min(headroom,(c.pack_v-v)/resistance))
        if pre and not main: ep+=ip*ip*c.precharge_ohm*c.dt_s
        if main or pre: eseries+=ip*ip*resistance*c.dt_s
        ebus+=ip*c.pack_v*c.dt_s
        ebleed+=v*v/c.bleed_ohm*c.dt_s
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
                precharge_j=ep,dump_j=ed,charge_j=ec,peak_pack_a=peak, sink_starts=sink_starts, sink_j=esink,
                source_j=ebus, series_j=eseries, bleed_j=ebleed, load_j=eaux,
                capacitor_j=.5*c.cap_f*(v*v-c.initial_bus_v**2))

if __name__=='__main__':
    cases={'delayed':Config(),'early_bus_aux':Config(delayed_aux=False),
           'short':Config(short_ohm=1),'limited':Config(source_limit_a=.03),
           'pm_no_pack':Config(pack_v=0,regen_a=1),
           'refused_regen':Config(regen_a=1,regen_start_s=1.2,charge_allowed=False),
           'accepted_regen':Config(regen_a=1,regen_start_s=1.2),'welded':Config(welded=True)}
    print(json.dumps({k:simulate(v) for k,v in cases.items()},indent=2))
