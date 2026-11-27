# Has anyone built this? Prior art for the parallel-hybrid bicycle

Yes — and this is the reassuring part of the recommendation. **The parallel hybrid
is not a concept, it is a product category.** You can buy every part of it off
the shelf today, and several manufacturers ship it as a complete bike.

The distinction matters: the *series* hybrid (chainless) is the rare, commercially
marginal one. The *parallel* hybrid — chain stays, direct-drive hub adds torque,
regen on braking — has been in continuous production since roughly 2010.

## Production systems shipping today

### Stromer (Swiss, 2010–present)

The clearest commercial proof of the design. Stromer S-Pedelecs use a **TDCM
direct-drive hub motor** in the rear wheel with adjustable recuperation, and their
own technical documentation is unusually explicit about the mechanism:

> "The advantage of a hub motor is the possibility of recuperation. The mid-motor
> does not have this capability. The TDCM hub motor used by Stromer acts like a
> dynamo in this regard: it converts the rotational movement of the rear wheel
> into electricity, which recharges the battery."
> — Stromer technical knowledge base, "Recuperation and recuperation"

Note what that sentence says: **the mid-drive cannot do this.** If you want regen,
you need a direct-drive hub. That is a hard constraint, not a preference, because
mid-drives and geared hubs freewheel — the motor is mechanically disconnected from
the wheel when you stop pedalling, so there is nothing to turn it.

Stromer also uses the motor as an **electronic lock** (the magnets resist rotation
when unpowered), which is a nice illustration that a DD hub's "drag" is a feature
you can exploit rather than purely a cost.

### Zehus (Italian, 2014–present) — "All In One"

A different packaging of the same idea: motor, battery, controller and sensors all
inside the rear hub. Two product lines with genuinely different control strategies:

- **HORIZON** — "automatic energy recovery through a technology similar to hybrid
  cars", i.e. regen is automatic and invisible to the rider.
- **HALOS** — classic assist modes plus **manual** energy recovery.

The manual-recovery mode on HALOS is interesting: it is exactly the "I want to
recover energy deliberately" behaviour that motivated this whole design discussion.
Zehus shipped it in a hub you can retrofit.

### Grin Technologies (Canadian) — the component route

Not a bike brand: a component vendor that sells exactly the bill of materials
recommended in this repo's design note. The **All-Axle** direct-drive hub (3.9 kg),
**Phaserunner** FOC controller, **Cycle Analyst** instrumentation, and a range of
packs. Their documentation is the most honest in the industry on what regen is
actually worth:

> "On a typical ride with a Grin direct-drive setup, expect it to recover somewhere
> in the range of 3 to 8% of your energy. On a loaded cargo bike or a recumbent
> trike the numbers climb: one of our staff riders gets about 20% of their energy
> back from regen on a recumbent trike and has not changed a brake pad in over
> 8,000 km."
> — ebikes.ca, "Regen"

That 3–8% is the number to plan against. Note the second sentence too: **20% on a
trike, and no brake pads in 8,000 km.** The braking-wear benefit is often worth
more than the energy.

### Superpedestrian Copenhagen Wheel (2013–2019, discontinued)

A rear wheel with motor, battery and sensors integrated, offering regen braking
and an "Exercise Mode" that deliberately increases resistance. Commercially it did
not survive, but it demonstrated the all-in-one-hub form factor a decade before it
became common. Worth knowing as a caution: integration alone is not enough to sell
a bike.

### Others in the same family

- **TDCM** — the Taiwanese motor maker behind Stromer's hubs; sells DD hubs to
  other OEMs.
- **BionX** (2000s–2018) — early DD hub with regen, went bankrupt; a reminder that
  the technology being sound does not make the business sound.
- **Golden Motor, Nine Continent, Crystalyte** — long-running DD hub suppliers
  used in countless conversions.

## What nobody has shipped

Worth being straight about the gaps, so the design note does not overclaim:

- **A mainstream production bike with a *series* hybrid and a battery buffer** —
  only Mando Footloose and Schaeffler Free Drive, both niche (see
  `crank-alternator-efficiency.md`).
- **A production bike with supercapacitors as the primary store** — Tournon's
  thesis prototype is the closest thing to a real build, and it existed as a
  research vehicle. No commercial product.
- **A chainless bike that is *more* efficient than a chain** — because it is not
  physically plausible at bicycle power levels, as the model in this repo shows.

## Why the parallel hybrid won commercially

Three reasons, in order of importance:

1. **You keep the chain's 96% for the rider's own watts.** The rider's power never
   goes through a generator, so there is no efficiency tax to justify. This is the
   whole argument, and it is why the design survives commercial contact while the
   chainless one does not.
2. **Regen comes free with the motor you already have.** A direct-drive hub is a
   motor and a generator in one part. Nothing extra to buy.
3. **It degrades gracefully.** Dead battery, dead controller, snapped wire — you
   still have a bicycle. A series hybrid with a failed generator is a very heavy
   scooter you cannot propel.

That third point is underrated and shows up in the failure analysis: every
commercial parallel hybrid is still a bike when the electronics die.

## Verdict for this project

The design you liked is not speculative — it is what Stromer has been selling for
fifteen years, what Zehus sells as a hub, and what Grin sells as a kit. Building
one is an assembly and tuning problem, not a research problem.

The only genuinely novel thing in this repo is the *quantitative* comparison that
shows why the chainless variant of your original idea loses, and why the parallel
variant does not.

## Sources

- Stromer, "Recuperation and recuperation", stromer-tech.info knowledge base.
- Zehus, "The All In One" product page (HORIZON / HALOS recovery modes).
- Grin Technologies, "Ebike Regenerative Braking (Regen)", ebikes.ca/resources/learn/regen.html
  (3–8% typical, 20% recumbent trike, no brake pads in 8,000 km).
- Grin Technologies, V3 Rear All-Axle Motor Owner Guide.
- Electric Bike Review, Stromer ST3 review (TDCM gearless direct-drive, adjustable
  energy recapture).
- Electric Bike Review, Zehus BIKE+ All in One review; Superpedestrian Copenhagen
  Wheel reviews.
- Electrek, 2019-07-10, on Grin's GMAC and the ~5% typical regen range gain.
