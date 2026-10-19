// Print amplitude of each ADAT channel every second — touch each piezo
Server.default.options.device = "Scarlett 18i8 USB";
Server.default.options.numInputBusChannels = 20;
Server.default.options.numOutputBusChannels = 8;

s.waitForBoot {
    var amps = Array.fill(8, { Bus.control(s, 1) });

    SynthDef(\meter, {
        var ins = Array.fill(8, { |i| SoundIn.ar(i + 10) });
        ins.do { |sig, i|
            Out.kr(amps[i].index, Amplitude.kr(sig, 0.002, 0.1));
        };
    }).add;

    s.sync;
    Synth(\meter);
    "Touching wall — watch levels:".postln;

    Routine({
        loop {
            1.wait;
            amps.do { |b, i|
                b.get { |v| ("ch" + (i+10).asString + ":" + v.round(0.001).asString).postln };
            };
        };
    }).play;
};

s.boot;
