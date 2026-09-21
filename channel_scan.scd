// channel_scan.scd
// Watches ALL channels 0-15. Tap each piezo and see which index lights up.
// Use this to find the correct offset when ADAT layout is uncertain.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numWireBufs = 256;

s.waitForBoot {
    "BOOT OK - scanning channels 0-15".postln;
    "Tap any piezo — active channels printed below.".postln;

    SynthDef(\chanScan, {
        var ins  = Array.fill(20, { |i| SoundIn.ar(i) });
        var amps = ins.collect { |sig| Amplitude.kr(sig, 0.001, 0.15) };
        SendReply.kr(Impulse.kr(5), '/scan', amps);
    }).add;

    OSCdef(\scan, { |msg|
        var amps = msg[3..22];
        var anyHot = amps.any { |a| a > 0.001 };
        if(anyHot) {
            amps.do { |a, i| if(a > 0.001) { "  ch% : %".format(i, a.round(0.0001)).postln } };
            "---".postln;
        };
    }, '/scan');

    s.sync;
    Synth(\chanScan);
};

s.reboot;
