# Verification scope — v27.3

English is the default repository documentation. See [Vietnamese README](../README.vi.md) for the same user-facing feature matrix.

## Current package

v27.3 is the project release number, not an assertion that macOS 27.3 was tested. The hardware host runs macOS 27.2 on Apple Silicon with an LBP2900. LBP2900B and x86_64 are build targets; their hardware qualification remains open.

Ten offline checks passed against the real Canon-derived payload: curated model/resource selection; exact input hash, architecture and patch preimage guards; both-slice signatures; dependency and rpath closure; actual render equivalence in five cases; separate notification endpoints; both official/private payload overlay orders; guarded lifecycle/removal; real OS process ownership with a short monitor name; and all three installer language variants carrying the same payload and unchanged Canon license.

Native machine code is unchanged from 0.2.4. The Utility's display-name metadata and corresponding signature change. Post-install setup now discovers exactly one connected USB LBP2900, refuses ambiguous or foreign existing queues, and invokes the existing checked configure path. No test submits a print job.

## Inherited physical evidence

The development sequence used six authorized sheets, each confirmed by the user: four on patch-only 0.1.0, one before official reinstall on 0.2.1 and one afterward through Preview on 0.2.2. Utility status/job controls, cover/USB recovery and native PDE loading were observed. The official reinstall preserved private files and an actual print. Notification routing was retested on 0.2.3 with both runtimes active and no paper.

The 0.2.4 manual-install failure used a direct USB queue without the native transport/service. Configuring both restored Ready to Print through the actual macOS Open Printer Utility button. Canon's own no-queue termination crash was not binary-patched; correct setup avoids that path.

## Installer languages

The automatic package carries `en.lproj` and `vi.lproj` plus an English fallback. Separate `-en.pkg` and `-vi.pkg` variants provide explicit language choice. Welcome, Read Me and Conclusion content are localized; native navigation follows macOS, Canon dialogs stay English and the Canon agreement stays in its original English. The welcome view is a static native text view, so no custom language tabs are claimed.

The resource layout follows the local `productbuild(1)` documentation for `.lproj` resources and Apple's [distribution XML reference](https://developer.apple.com/library/archive/documentation/DeveloperTools/Reference/DistributionDefinitionRef/Chapters/Distribution_XML_Ref.html).

## Remaining qualification

LBP2900B/Intel hardware, other Macs and macOS 27 point releases, logout/reboot, Cleaning, all physical media/quality choices, other Canon printer hardware and endurance remain unqualified. Screenshots show actual Installer/Utility windows; machine identifiers and document titles are excluded. No additional sheets are used for v27.3.
