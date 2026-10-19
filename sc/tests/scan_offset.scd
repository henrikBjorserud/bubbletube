// scan_offset.scd
// Tries ADAT offset 8, then 12 — touch a piezo and listen for which one produces sound.
// Watch the post window for which offset is active.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    SynthDef(\scan, {
        var offset = \offset.kr(8);
        var ins = Array.fill(8, { |i| SoundIn.ar(i + offset) });
        var sum = Mix(ins);
        Out.ar(0, (sum * 0.3) ! 2);
    }).add;

    s.sync;

    x = Synth(\scan, [\offset, 10]);
    "RUNNING with offset 10 — touch wall, listen for sound".postln;

    8.wait;
    "Switching to offset 8...".postln;
    x.set(\offset, 8);
    "RUNNING with offset 8 — touch wall, listen for sound".postln;

    8.wait;
    "Switching to offset 4...".postln;
    x.set(\offset, 4);
    "RUNNING with offset 4 — touch wall, listen for sound".postln;

    8.wait;
    "Switching to offset 12...".postln;
    x.set(\offset, 12);
    "RUNNING with offset 12 — touch wall, listen for sound".postln;
};

s.boot;
