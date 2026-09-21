// level_meter.scd
// Tap each piezo — shows peak amplitude per ADAT channel at offset 8.
// Use values to calibrate thresholds in 07_material_inputs_8ch.scd.

Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    "BOOT OK - level meter running".postln;
    "Tap each piezo firmly. Watch the peak levels printed below.".postln;
    "Format: ch1..ch8 | peak values since last print".postln;

    SynthDef(\levelMeter, {
        var ins = Array.fill(8, { |i| SoundIn.ar(i + 12) });
        // Very fast attack, moderate release — catches transient taps
        var amps = ins.collect { |sig| Amplitude.kr(sig, 0.001, 0.15) };
        SendReply.kr(Impulse.kr(10), '/levels', amps);
    }).add;

    OSCdef(\levels, { |msg|
        var amps = msg[3..10];
        var anyHot = amps.any { |a| a > 0.005 };
        if(anyHot) {
            var str = amps.collect { |a, i|
                var bar = if(a > 0.005) { "*" } { "." };
                "ch%:% %".format(i+1, bar, a.round(0.001).asString.padLeft(5))
            }.join("  ");
            str.postln;
        };
    }, '/levels');

    s.sync;
    Synth(\levelMeter);

    "Ready — tap piezos now. Quiet channels show nothing.".postln;
};

s.boot;
