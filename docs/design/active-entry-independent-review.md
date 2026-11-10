# Independent inhibited-entry review

Reviewed inherited e6693cd6e359c483a889a2619053c19ae0513f86, including legibility merge 38d036b; latest fetched GitHub master fb100ef is its ancestor. Accepted for archival default-branch publication as **inhibited, unfinished schematic**, not operational protected entry.

Independently downloaded TI TPSI3052 SLVSGS3B from https://www.ti.com/lit/ds/symlink/tpsi3052.pdf. Table 5-1 agrees with U400/U401 pins 1 EN, 2 PXFR, 3 VDDP, 4 VSSP, 5 VSSS, 6 VDDM, 7 VDDH, 8 VDRV. Section 6.3 requires like-type split capacitors with CDIV2 >=3 CDIV1; fitted 470n/100n C0G 5% yields worst ratio 4.25. VSSS remains each FET pair's common-source node, never arbitrary PGND. Four 150V candidate FETs remain source-to-source; R402/R412 fitted zero-ohm EN inhibits remain intact.

Independent execution against inherited worktree: 37/37 normal tests (105.505s), 37/37 optimized tests (76.695s); native strict ERC exit 5, eight violations. No claim ERC-clean, physical qualification, switch timing, SOA or safe energization. Legibility's connectivity invariant remains covered by tests. CTRL supply subsequently added separately; its stricter nine-error ERC is documented in ctrl-supply-milestone.md.

GitHub default publication was a fast-forward fb100ef to e6693cd; no overwrite or unrelated master history dropped. Follow-on supply is a separate review branch. No PCB or energization authorized.
