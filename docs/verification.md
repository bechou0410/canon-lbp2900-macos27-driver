# Verification scope — v27.3.3

English is the default repository documentation. See [Vietnamese README](../README.vi.md) for the same user-facing feature matrix.

## Current package

v27.3.3 is the project release number, not an assertion that macOS 27.3 was tested. The hardware host runs macOS 27.2 on Apple Silicon with an LBP2900. LBP2900B and x86_64 are build targets; their hardware qualification remains open.

The published v27.3.3 PKG is Developer ID signed and Apple notarized. The stapled ticket validates, and Gatekeeper assessment returns `accepted` with source `Notarized Developer ID`. The release checksum applies to the stapled package.

Fifteen checks cover the real Canon-derived payload: curated model/resource selection; exact input hash, architecture and patch preimage guards; both-slice signatures; dependency and rpath closure; actual render equivalence in five cases; separate notification endpoints; both official/private payload overlay orders; guarded lifecycle/removal; real OS process ownership with a short monitor name; real CUPS queue-presence detection; one installer carrying both localized resource sets and the unchanged Canon license; same-version/historical-payload upgrades with interrupted preparation; and live read-only IPP state queries.

Canon machine instructions remain unchanged from 0.2.4; v27.3.3 redirects CCPD’s CUPS dependency to a private cancellation bridge and adds a fresh-process helper. The Utility's display-name metadata and corresponding signature change. Post-install setup now discovers exactly one connected USB LBP2900, refuses ambiguous or foreign existing queues, and invokes the existing checked configure path. The automated suite does not submit print jobs. The final v27.3 package was installed on the hardware host: post-install USB discovery created the native queue, bootstrapped its desktop service and opened the Utility. The verification restored the prior queue defaults/default printer and confirmed the unrelated Epson queue/PPD was unchanged. No print job was submitted. A macOS behavior discovered during this check—successful `lpstat` exit with no matching queue output—was corrected by checking actual queue output; queue/URI checks also avoid translated status prefixes.

## Inherited physical evidence

The development sequence used six authorized sheets, each confirmed by the user: four on patch-only 0.1.0, one before official reinstall on 0.2.1 and one afterward through Preview on 0.2.2. Utility status/job controls, cover/USB recovery and native PDE loading were observed. The official reinstall preserved private files and an actual print. Notification routing was retested on 0.2.3 with both runtimes active and no paper.

The 0.2.4 manual-install failure used a direct USB queue without the native transport/service. Configuring both restored Ready to Print through the actual macOS Open Printer Utility button. Canon's own no-queue termination crash was not binary-patched; correct setup avoids that path.

## Installer languages

The automatic package carries `en.lproj` and `vi.lproj` plus an English fallback. Only one automatic bilingual PKG is built and published from v27.3.2 onward; the older releases remain in GitHub history. Welcome, Read Me and Conclusion content are localized; native navigation follows macOS, Canon dialogs stay English and the Canon agreement stays in its original English. The welcome view is a static native text view, so no custom language tabs are claimed.

The resource layout follows the local `productbuild(1)` documentation for `.lproj` resources and Apple's [distribution XML reference](https://developer.apple.com/library/archive/documentation/DeveloperTools/Reference/DistributionDefinitionRef/Chapters/Distribution_XML_Ref.html).

## Remaining qualification

LBP2900B/Intel hardware, other Macs and macOS 27 point releases, logout/reboot, Cleaning, all physical media/quality choices, other Canon printer hardware and endurance remain unqualified. Screenshots show actual Installer/Utility windows. The current user-supplied images are published unchanged at the user’s explicit request. No additional sheets are used for v27.3.

## Reinstallation in v27.3.1

The package now accepts an intact project-owned installation instead of unconditionally rejecting existing private paths. Real retained 0.2.0, 0.2.4 and 27.3 package payloads exercise upgrade and repeated overlay; current-version reinstall always runs when historical archives are unavailable. Tests preserve the queue ownership URI, remove retired payload files, recover an interrupted preparation and refuse modified/foreign files. Real process checks also exclude an external application that loads a private library.

Preinstall records queue pause states through IPP and the running private agents, pauses queues, rejects pending CUPS jobs and stops the private runtime. Postinstall verifies the new payload and restores the recorded state. Existing queue PPD/options, URI/default and unrelated printer files are untouched. A stuck private USB monitor can receive KILL only after its executable ownership is rechecked. Physical Canon jobs already handed off from CUPS must still be finished/cancelled in Utility before installation.

The final v27.3.1 packages passed all 13 checks (55.124 seconds). At that release, authenticated live upgrade and same-version installation were unqualified: the optional authentication request was cancelled before installation started. The v27.3.3 live upgrade evidence below supersedes the upgrade limitation; same-version live Installer qualification remains open. No additional physical print is part of this change.

## Current packaging and screenshots

v27.3.2 removes the separate language artifacts and their build switches. Driver lifecycle and native code are unchanged. The user supplied screenshots of the v27.3.1 installer and Utility showing Ready to Print, Top Cover Open and Out of Paper. They demonstrate the displayed states; they do not by themselves establish new physical printing or a successful in-place upgrade. The README presents these images together while retaining the detailed validation limits here.

The final v27.3.2 package passed all 13 checks in 71.838 seconds. This packaging update did not install a driver or submit a print job on the host.

## Cancel crash discovered after prior acceptance

On 2026-10-08 at 16:42, Cancel in Canon Printer Utility during out-of-paper caused the private CCPD data agent to abort. The stack enters cupsCancelJob, CUPS localization, CoreFoundation and performForkChildInitialize. A 15:10 report has the same stack. No new StatusMonitor crash report was observed for this incident. The orphan USB monitor consumed about one CPU core after the service died. Earlier successful cancellations and the prior 13 tests did not cover this failure.

A real-library reproducer using a nonexistent queue/job after fork produced SIGABRT without submitting a print job. v27.3.3 routes only CCPD’s cupsCancelJob through a new executable helper, preserves all other CUPS APIs by re-export, and restores Canon’s SIGCHLD handler after reaping the helper. A separate regression first failed with exit 4 when the inherited handler incorrectly requested daemon termination, then passed with the signal handling correction. Invalid arguments and a missing helper return failure. A held-job integration probe exposed that Canon’s hard-coded root request identity is rejected for a desktop user’s own job; the fresh helper therefore uses its effective UID’s account name. No Objective-C fork-safety setting is disabled.

The installed 27.3.1 orphan monitor was stopped after executable ownership and empty CUPS queue checks. The user subsequently installed the final v27.3.3 package and, after confirming an empty tray for the Cancel retest, reported that it worked smoothly. This is user-reported hardware acceptance, not an agent-observed sequence of button presses.

Final candidate v27.3.3 passed all 15 checks. A separate live CUPS integration probe created an indefinitely held job, confirmed pending-held through IPP, cancelled it through the production bridge with return value 1 and verified it was removed. This did not send a page to the printer. After the user’s retest, the installed receipt reports 27.3.3 and the complete installed integrity check passes. Canon and Epson queue PPD hashes and the default-printer state match the pre-install snapshots. CCPD, BackGrounder, monitor and Utility are running; no new CCPD or StatusMonitor crash report was found. This qualifies the reported LBP2900/macOS 27.2 case; other hardware and endurance limits above remain.
