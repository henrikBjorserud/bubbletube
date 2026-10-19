// 02_input_scanner.scd
// Cycles through hardware inputs and routes the current one to stereo out.
// Use this to find which SoundIn channel corresponds to each piezo/preamp input.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "BOOT OK - input scanner".postln;

    SynthDef(\scanIn, {
        var idx, sig, amp;

        // Controls
        idx = \idx.kr(0);          // which input channel to monitor
        amp = \amp.kr(0.15);       // master monitor level (start low)

        // Read selected input
        sig = SoundIn.ar(idx);

        // Piezo-friendly quick cleanup so it doesn't destroy your ears
        sig = HPF.ar(sig, 80);
        sig = LPF.ar(sig, 8000);
        sig = Compander.ar(sig, sig, 0.25, 1, 0.2, 0.003, 0.15);

        Out.ar(0, (sig * amp) ! 2);
    }).add;

    s.sync; // wait until SynthDef is received by server

    x = Synth(\scanIn, [\idx, 0, \amp, 0.12]);

    // Scan settings
    ~maxCh = 15;     // scan up to input 15 (ADAT is 8..15)
    ~stepS = 1.0;    // seconds per channel
    ~i = 8;          // start at first ADAT input, skip empty analog 0..7

    "Scanning channels 0..".post; ~maxCh.postln;

    // Routine: every ~stepS seconds, switch to next input
    r = Routine({
        loop {
            ("NOW MONITORING INPUT: " ++ ~i).postln;
            x.set(\idx, ~i);
            ~stepS.wait;
            ~i = (~i + 1) % (~maxCh + 1);
        }
    }).play(SystemClock);

    "RUNNING: touch a piezo; note the input number when you hear it.".postln;
};

s.boot;
