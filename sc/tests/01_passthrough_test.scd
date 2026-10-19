// 01_passthrough_test.scd
// Simple passthrough: mix ADAT inputs 8..15 to stereo out.
// If you hear sound when touching piezos, the full chain is working.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "BOOT OK - passthrough test".postln;

    SynthDef(\passthrough, {
        var ins, sum;
        var amp = \amp.kr(0.3);

        ins = Array.fill(8, { |i| SoundIn.ar(i + 12) });
        ins = ins.collect { |sig| HPF.ar(sig, 80) };

        sum = Mix(ins);

        Out.ar(0, (sum * amp) ! 2);
    }).add;

    s.sync;

    x = Synth(\passthrough, [\amp, 0.3]);

    "RUNNING: touch any piezo - you should hear it. Ctrl+C to stop.".postln;
};

s.boot;
